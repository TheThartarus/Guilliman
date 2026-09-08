"""
Guilliman Backend - Test de preparación para exportación a PDF.

Valida que ``CaseFileService`` expone, a través de los DTOs, TODOS los campos
que el futuro generador de PDF (agente Frontend) necesitará, de modo que un
cambio que los elimine haga fallar el test en lugar de romper la UI en silencio.

No implementa PDF; solo verifica la capa de datos.

Patrón de limpieza reutilizado de ``test_backend.py``: libera los engines
cacheados y reintenta el borrado del archivo .db (SQLite retiene locks unos
ms en Windows).
"""

import gc
import os
import sys
import time
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (
    CaseFileCreate,
    CaseFileService,
    DefendantCreate,
    HearingScheduleCreate,
)
from db.database import reset_session_factory

TEST_DB = "test_export_data.db"


def _cleanup() -> None:
    """Libera engines y borra la BD temporal con reintentos."""
    reset_session_factory()
    gc.collect()
    for suffix in ("", "-wal", "-shm"):
        path = TEST_DB + suffix
        if not os.path.exists(path):
            continue
        for _attempt in range(10):
            try:
                os.remove(path)
                break
            except PermissionError:
                gc.collect()
                time.sleep(0.2)


def main() -> None:
    _cleanup()
    service = CaseFileService(TEST_DB)
    service.init_db()

    # 1) Expediente completo: 1 acusado y 2 audiencias (una con notas, otra sin).
    case_file_id = service.create_case_file(
        CaseFileCreate(
            case_number="01001-2023-EXPORT",
            prosecutor_file_number="MP-2023-9999",
            prosecutor_name="Lic. Ana Torres",
            defense_attorney="Lic. Carlos Ruiz",
            current_hearing_type="Intermediate stage",
            origin_type="Local",
            offense_description="Robbery aggravated by use of violence",
            facts_summary="Defendant allegedly robbed a store on 5th avenue.",
            indictment_date=date(2026, 1, 10),
            preliminary_hearing_date=date(2026, 3, 15),
            trial_transfer_date=date(2026, 5, 20),
            trial_entry_date=date(2026, 6, 1),
            trial_opening_date=date(2026, 7, 12),
        ),
        defendants_list=[
            DefendantCreate(
                full_name="Juan Perez",
                national_id="1234 56789 0101",
                arrest_date=date(2026, 1, 5),
                additional_notes="Age 40, address on file.",
            ),
        ],
        hearings_list=[
            HearingScheduleCreate(
                scheduled_at=datetime(2026, 8, 1, 9, 0),
                hearing_type="Preliminary",
                status="Scheduled",
                notes="Courtroom 3.",
            ),
            HearingScheduleCreate(
                scheduled_at=datetime(2026, 9, 15, 14, 30),
                hearing_type="Opening",
                status="Scheduled",
            ),
        ],
    )
    assert case_file_id > 0

    # 2) Detalle completo: ASSERT de cada campo requerido por el PDF.
    detail = service.get_case_file_by_id(case_file_id)
    assert detail is not None, "El detalle del expediente no debe ser None"

    expected_case_fields = [
        "case_number",
        "prosecutor_file_number",
        "prosecutor_name",
        "defense_attorney",
        "current_hearing_type",
        "origin_type",
        "offense_description",
        "facts_summary",
        "indictment_date",
        "preliminary_hearing_date",
        "trial_opening_date",
        "trial_transfer_date",
        "trial_entry_date",
    ]
    for field in expected_case_fields:
        assert hasattr(detail, field), f"Falta el campo del expediente: {field}"
        # Los campos sin valor por defecto ya validados por Pydantic; aquí
        # verificamos presencia del atributo en el DTO de lectura.
        _ = getattr(detail, field)

    # Acusados: campos requeridos.
    assert len(detail.defendants) >= 1, "Se esperaba al menos 1 acusado"
    defendant = detail.defendants[0]
    for field in ("full_name", "national_id", "arrest_date", "additional_notes"):
        assert hasattr(defendant, field), f"Falta el campo del acusado: {field}"

    # Audiencias: campos requeridos.
    assert len(detail.hearings) >= 2, "Se esperaban al menos 2 audiencias"
    for field in ("scheduled_at", "hearing_type", "status", "notes"):
        assert hasattr(detail.hearings[0], field), f"Falta el campo de audiencia: {field}"

    # 3) Agenda filtrada por rango que cubre ambas audiencias.
    start = datetime(2026, 7, 1)
    end = datetime(2026, 12, 31)
    agenda = service.list_scheduled_hearings(start, end)
    assert len(agenda) >= 2, "La agenda debe cubrir las 2 audiencias del rango"
    for item in agenda:
        for field in (
            "hearing_id",
            "case_file_id",
            "case_number",
            "scheduled_at",
            "hearing_type",
            "status",
            "notes",
        ):
            assert hasattr(item, field), f"Falta el campo de agenda: {field}"

    # 4) Limpieza de la BD temporal.
    service.close()
    _cleanup()
    assert not os.path.exists(TEST_DB), "La BD temporal no se pudo borrar"

    print("EXPORT DATA TEST OK")


if __name__ == "__main__":
    main()
