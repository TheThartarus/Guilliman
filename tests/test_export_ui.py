"""
Prueba headless de la exportación a PDF (sin abrir ventana).

Construye datos con ``CaseFileService`` en una BD temporal, genera los PDF de
un expediente y de la agenda, y verifica que los archivos son PDF válidos
(empiezan por %PDF y tienen tamaño > 0). También comprueba que un expediente
con campos None no lanza excepción y produce un PDF válido.
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime, timedelta

from db import (
    CaseFileCreate,
    CaseFileService,
    DefendantCreate,
    DocumentaryCreate,
    ExpertCreate,
    HearingScheduleCreate,
)
from db.database import dispose_engine, reset_session_factory

from ui.exporters import (
    export_agenda_pdf,
    export_case_pdf,
    export_cases_csv,
    export_cases_pdf,
)


def _cleanup(db_path: str) -> None:
    """Libera el engine y elimina los archivos de la BD temporal."""
    try:
        reset_session_factory()
        dispose_engine(db_path)
    except Exception:
        pass
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(db_path + suffix):
            try:
                os.remove(db_path + suffix)
            except OSError:
                pass


def main() -> None:
    db_path = os.path.join(tempfile.gettempdir(), "test_export_ui.db")
    _cleanup(db_path)

    service = CaseFileService(db_path)
    service.init_db()

    case_id = service.create_case_file(
        CaseFileCreate(
            case_number="EXP-2026-PDF",
            prosecutor_file_number="MP-123456",
            prosecutor_name="Fiscal Lopez",
            defense_attorney="Defensor Ramirez",
            current_hearing_type="Apertura",
            arresting_agency="CICPC",
            offense_description="Robo agravado",
            facts_summary="Hechos resumidos de prueba.",
            origin_type="Local",
            indictment_date=date(2026, 1, 10),
            preliminary_hearing_date=date(2026, 2, 1),
            anticipated_proof_date=date(2026, 2, 15),
            trial_opening_date=date(2026, 3, 1),
            trial_transfer_date=date(2026, 4, 1),
            trial_entry_date=date(2026, 5, 1),
        ),
        defendants_list=[
            DefendantCreate(
                full_name="Pedro Prueba",
                national_id="12345678",
                arrest_date=date(2026, 1, 5),
                additional_notes="Sin antecedentes.",
            )
        ],
        hearings_list=[
            HearingScheduleCreate(
                scheduled_at=datetime(2026, 3, 1, 9, 30),
                hearing_type="Apertura de Juicio",
                status="Scheduled",
                notes="Audiencia inicial.",
            ),
            HearingScheduleCreate(
                scheduled_at=datetime(2026, 4, 15, 11, 0),
                hearing_type="Continuación de Juicio",
                status="Deferred",
                notes="",
            ),
        ],
    )

    case = service.get_case_file_by_id(case_id)
    service.add_documentary(
        case_id,
        DocumentaryCreate(
            name="Doc Prueba",
            in_possession=True,
            possession_date=date(2026, 2, 5),
            additional_notes="NOTA DOCUMENTAL X",
        ),
    )
    service.add_expert(
        case_id,
        ExpertCreate(
            name="Experto Prueba",
            appeared=True,
            appearance_date=date(2026, 3, 5),
            additional_notes="NOTA EXPERTO Y",
        ),
    )
    case = service.get_case_file_by_id(case_id)

    with tempfile.TemporaryDirectory() as tmp:
        case_pdf = os.path.join(tmp, "expediente.pdf")
        export_case_pdf(case, case_pdf)
        _assert_pdf(case_pdf, "expediente")
        with open(case_pdf, "rb") as handle:
            case_bytes = handle.read()
        assert b"Prueba Anticipada" in case_bytes, "falta la sección Prueba Anticipada"
        assert b"NOTA DOCUMENTAL X" in case_bytes, "falta nota del documental en el PDF"
        assert b"NOTA EXPERTO Y" in case_bytes, "falta nota del experto en el PDF"

        # Rango que cubre ambas audiencias.
        start = date(2026, 1, 1)
        end = date(2026, 12, 31)
        items = service.list_scheduled_hearings(
            datetime.combine(start, datetime.min.time()),
            datetime.combine(end, datetime.max.time().replace(microsecond=0)),
        )
        agenda_pdf = os.path.join(tmp, "agenda.pdf")
        export_agenda_pdf(items, start, end, agenda_pdf)
        _assert_pdf(agenda_pdf, "agenda")

        # Caso con campos None: no debe lanzar y debe dar PDF válido.
        empty_id = service.create_case_file(
            CaseFileCreate(case_number="EXP-2026-VACIO")
        )
        empty_case = service.get_case_file_by_id(empty_id)
        empty_pdf = os.path.join(tmp, "vacio.pdf")
        export_case_pdf(empty_case, empty_pdf)
        _assert_pdf(empty_pdf, "expediente vacío")

    _cleanup(db_path)
    print("EXPORT UI TEST OK")


def test_export_cases_list_pdf_csv():
    """El listado de expedientes exporta a PDF valido y a CSV."""
    db_path = os.path.join(tempfile.gettempdir(), "test_export_cases_list.db")
    _cleanup(db_path)
    service = CaseFileService(db_path)
    service.init_db()
    service.create_case_file(
        CaseFileCreate(case_number="EXP-LIST-1", prosecutor_name="Fiscal A")
    )
    service.create_case_file(
        CaseFileCreate(case_number="EXP-LIST-2", prosecutor_name="Fiscal B")
    )
    cases = service.search_case_files("", limit=100)
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = os.path.join(tmp, "lista.pdf")
        export_cases_pdf(cases, pdf_path)
        with open(pdf_path, "rb") as fh:
            assert fh.read().startswith(b"%PDF"), "el PDF de lista no es valido"
        csv_path = os.path.join(tmp, "lista.csv")
        export_cases_csv(cases, csv_path)
        with open(csv_path, "r", encoding="utf-8") as fh:
            content = fh.read()
        assert "EXP-LIST-1" in content and "EXP-LIST-2" in content
    _cleanup(db_path)
    print("EXPORT CASES LIST TEST OK")


def _assert_pdf(path: str, label: str) -> None:
    """Verifica que ``path`` es un PDF válido (cabecera y tamaño)."""
    with open(path, "rb") as handle:
        data = handle.read()
    assert data.startswith(b"%PDF"), f"El PDF de {label} no empieza por %PDF"
    assert len(data) > 0, f"El PDF de {label} está vacío"


if __name__ == "__main__":
    main()
