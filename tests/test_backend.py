"""
Guilliman Backend - Script de pruebas.

Inicializa una base de datos SQLite local temporal, y verifica:
    - Creación atómica de expedientes (con acusados y audiencias).
    - Búsqueda por número de expediente y nomenclatura del MP.
    - Lectura por ID, agenda cronológica, filtros y paginación.
    - CRUD completo de expedientes, acusados y audiencias.
    - Unicidad de case_number con error tipado.
    - Excepciones tipadas para entidades inexistentes.
    - Liberación del archivo SQLite en Windows (sin locks) tras close().

Ejecutar desde la raíz del proyecto:
    python tests/test_backend.py
"""

import os
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (
    CaseFileCreate,
    CaseFileService,
    CaseFileUpdate,
    DefendantCreate,
    DuplicateCaseNumberError,
    HearingScheduleCreate,
    HearingScheduleUpdate,
    VictimCreate,
    WitnessCreate,
)
from pydantic import ValidationError

TEST_DB = "test_case_files.db"
TEST_DB_FILE = Path(TEST_DB)


def _clean_test_db() -> None:
    """Elimina la BD temporal si quedó de una ejecución anterior."""
    if TEST_DB_FILE.exists():
        TEST_DB_FILE.unlink()


def _create_sample_case(service: CaseFileService, case_number: str = "01001-2023-00042") -> int:
    """Helper: crea un expediente de prueba completo y retorna su ID."""
    return service.create_case_file(
        CaseFileCreate(
            case_number=case_number,
            prosecutor_file_number="MP-2023-8877",
            prosecutor_name="Lic. Ana Torres",
            defense_attorney="Lic. Carlos Ruiz",
            current_hearing_type="Intermediate stage",
            offense_description="Robbery aggravated by use of violence",
            facts_summary="Defendant allegedly robbed a store on 5th avenue.",
            origin_type="Local",
        ),
        defendants_list=[
            DefendantCreate(full_name="Juan Perez", national_id="1234 56789 0101", verdict_status="Pending"),
            DefendantCreate(
                full_name="Maria Lopez",
                national_id="9876 54321 0101",
                additional_notes="Age 34, address on file.",
            ),
        ],
        hearings_list=[
            HearingScheduleCreate(
                scheduled_at=datetime(2026, 9, 1, 9, 0),
                hearing_type="Preliminary",
                status="Scheduled",
            ),
            HearingScheduleCreate(
                scheduled_at=datetime(2026, 10, 15, 14, 30),
                hearing_type="Opening",
                status="Scheduled",
                notes="Courtroom 3.",
            ),
        ],
    )


def main() -> None:
    _clean_test_db()
    # Base de datos aislada y nueva para esta ejecución de prueba.
    service = CaseFileService(TEST_DB)
    service.init_db()

    print("1) Creando un expediente completo (transacción atómica)...")
    case_file_id = _create_sample_case(service)
    assert case_file_id > 0
    print(f"   -> creado con id={case_file_id}")

    print("2) Buscando por fragmento del número de expediente ('00042')...")
    results = service.search_case_files("00042")
    assert len(results) == 1, f"se esperaba 1 resultado, se obtuvieron {len(results)}"
    found = results[0]
    assert found.case_number == "01001-2023-00042"
    assert len(found.defendants) == 2
    assert {d.full_name for d in found.defendants} == {"Juan Perez", "Maria Lopez"}
    assert len(found.hearings) == 2
    print(f"   -> encontrado: {found.case_number} "
          f"({len(found.defendants)} acusados, {len(found.hearings)} audiencias)")

    print("3) Buscando por nomenclatura del MP ('MP-2023')...")
    results = service.search_case_files("MP-2023")
    assert len(results) == 1
    print(f"   -> encontrado vía nomenclatura: {results[0].case_number}")

    print("4) get_case_file_by_id / list_scheduled_hearings...")
    detail = service.get_case_file_by_id(case_file_id)
    assert detail is not None and detail.id == case_file_id
    agenda = service.list_scheduled_hearings()
    assert len(agenda) >= 2 and agenda[0].scheduled_at <= agenda[-1].scheduled_at
    print(f"   -> detalle OK; la agenda tiene {len(agenda)} audiencia(s), "
          f"ordenadas cronológicamente")

    print("5) update_case_file / add_defendant / add_hearing...")

    assert service.update_case_file(
        case_file_id, CaseFileUpdate(offense_description="Updated description")
    )
    detail = service.get_case_file_by_id(case_file_id)
    assert detail.offense_description == "Updated description"
    new_defendant_id = service.add_defendant(
        case_file_id, DefendantCreate(full_name="Pedro Gomez")
    )
    new_hearing_id = service.add_hearing(
        case_file_id,
        HearingScheduleCreate(
            scheduled_at=datetime(2026, 11, 2, 8, 0),
            hearing_type="Continuation",
        ),
    )
    detail = service.get_case_file_by_id(case_file_id)
    assert detail.offense_description == "Updated description"
    assert len(detail.defendants) == 3 and len(detail.hearings) == 3
    print(f"   -> actualizado; acusado id={new_defendant_id}, audiencia id={new_hearing_id}")

    print("6) update_hearing (PATCH parcial sin perder notas)...")
    assert service.update_hearing(
        new_hearing_id,
        HearingScheduleUpdate(scheduled_at=datetime(2026, 11, 5, 10, 0)),
    )
    detail = service.get_case_file_by_id(case_file_id)
    moved = next(h for h in detail.hearings if h.id == new_hearing_id)
    assert moved.scheduled_at == datetime(2026, 11, 5, 10, 0)
    assert moved.hearing_type == "Continuation", "el PATCH no debió tocar hearing_type"
    print(f"   -> reprogramada a {moved.scheduled_at}; resto de campos intacto")

    print("7) update_defendant (corrección de cédula sin borrar/recrear)...")
    defendant_to_fix = next(d for d in detail.defendants if d.full_name == "Juan Perez")
    assert service.update_defendant(
        case_file_id,
        defendant_to_fix.id,
        DefendantCreate(full_name="Juan Perez", national_id="9999 88888 0101"),
    )
    detail = service.get_case_file_by_id(case_file_id)
    fixed = next(d for d in detail.defendants if d.id == defendant_to_fix.id)
    assert fixed.national_id == "9999 88888 0101"
    assert len(detail.defendants) == 3, "update_defendant no debe cambiar la cantidad"
    print(f"   -> cédula corregida en acusado id={defendant_to_fix.id}")

    print("8) delete_defendant / delete_hearing / update_hearing_status...")
    assert service.delete_defendant(new_defendant_id)
    assert service.update_hearing_status(new_hearing_id, "Deferred", notes="Moved to Nov.")
    assert service.delete_hearing(new_hearing_id)
    detail = service.get_case_file_by_id(case_file_id)
    assert len(detail.defendants) == 2
    assert all(h.id != new_hearing_id for h in detail.hearings)
    print("   -> acusado eliminado, audiencia marcada Deferred y luego eliminada")

    print("9) Unicidad de case_number (error tipado)...")
    try:
        _create_sample_case(service, case_number="01001-2023-00042")
        raise AssertionError("se esperaba DuplicateCaseNumberError")
    except DuplicateCaseNumberError as error:
        assert "00042" in str(error)
        print(f"   -> rechazado correctamente: {error}")
    # La transacción fallida no debe dejar expedientes parciales.
    assert len(service.search_case_files("00042")) == 1

    print("10) Validación Pydantic del vocabulario de defendant_status...")
    try:
        DefendantCreate(full_name="Test", status="Detained")
        raise AssertionError("se esperaba ValidationError por valor legacy")
    except ValidationError:
        print("   -> valor legacy 'Detained' rechazado; usar 'Detenido'")

    print("11) Excepciones tipadas para entidades inexistentes...")
    from db import CaseFileNotFoundError

    try:
        service.add_defendant(99999, DefendantCreate(full_name="Nadie"))
        raise AssertionError("se esperaba CaseFileNotFoundError")
    except CaseFileNotFoundError as error:
        assert "99999" in str(error)
    assert not service.update_defendant(case_file_id, 99999,
                                        DefendantCreate(full_name="Nadie"))
    assert not service.update_hearing(99999, HearingScheduleUpdate(status="Completed"))
    assert not service.update_hearing_status(99999, "Completed")
    assert not service.delete_hearing(99999)
    print("   -> add/update/delete sobre IDs inexistentes manejados tipadamente")

    print("12) Paginación en search_case_files...")
    service.create_case_file(CaseFileCreate(case_number="01001-2023-00077"))
    service.create_case_file(CaseFileCreate(case_number="01001-2024-00099"))
    page1 = service.search_case_files("", limit=2, offset=0)
    page2 = service.search_case_files("", limit=2, offset=2)
    total = service.search_case_files("")
    assert len(page1) == 2 and len(page2) == 1 and len(total) == 3
    assert {c.case_number for c in page1}.isdisjoint({c.case_number for c in page2})
    print(f"   -> 3 expedientes totales; páginas de 2 sin solapamiento")

    print("13) Filtro por estado en list_scheduled_hearings...")
    cancelled_id = service.add_hearing(
        case_file_id,
        HearingScheduleCreate(
            scheduled_at=datetime(2026, 12, 1, 8, 0),
            hearing_type="Continuation",
            status="Cancelled",
        ),
    )
    only_scheduled = service.list_scheduled_hearings(status="Scheduled")
    only_cancelled = service.list_scheduled_hearings(status="Cancelled")
    everything = service.list_scheduled_hearings()
    assert all(h.status == "Scheduled" for h in only_scheduled)
    assert [h.hearing_id for h in only_cancelled] == [cancelled_id]
    assert len(everything) > len(only_cancelled)
    print("   -> filtro por estado funciona (agenda puede excluir 'Cancelled')")

    print("14) delete_case_file (cascada)...")
    assert service.delete_case_file(case_file_id)
    assert service.search_case_files("00042") == []
    orphans = [h for h in service.list_scheduled_hearings()
               if h.case_file_id == case_file_id]
    assert orphans == [], "la cascada falló: quedan audiencias huérfanas"
    print("   -> eliminado; no quedan acusados/audiencias huérfanos")

    print("15) close() libera el archivo SQLite (sin locks en Windows)...")
    service.close()
    assert TEST_DB_FILE.exists(), "la BD debería seguir existiendo antes de borrarla"
    _clean_test_db()  # Fallaría con PermissionError si quedara algún lock.
    assert not TEST_DB_FILE.exists()
    print("   -> archivo .db renombrado/borrado sin errores tras close()")

    print("16) Consistencia count_case_files ↔ search_case_files...")
    # Re-creamos datos de prueba para un escenario rico en filtros.
    svc = CaseFileService(TEST_DB)
    svc.init_db()

    c1 = svc.create_case_file(
        CaseFileCreate(
            case_number="100-2025-001",
            indictment_date=date(2025, 3, 15),
        ),
        defendants_list=[DefendantCreate(full_name="Ana Torres", verdict_status="Pending", status="Detenido")],
        victims_list=[VictimCreate(full_name="Luis Ramirez")],
        witnesses_list=[WitnessCreate(full_name="Sofia Garcia")],
        hearings_list=[
            HearingScheduleCreate(
                scheduled_at=datetime(2025, 6, 10, 9, 0), status="Scheduled"
            ),
        ],
    )
    c2 = svc.create_case_file(
        CaseFileCreate(
            case_number="100-2025-002",
            indictment_date=date(2025, 5, 20),
        ),
        defendants_list=[DefendantCreate(full_name="Pedro Gomez", verdict_status="Acquittal", status="En Libertad")],
        hearings_list=[
            HearingScheduleCreate(
                scheduled_at=datetime(2025, 7, 1, 10, 0), status="Completed"
            ),
        ],
    )
    c3 = svc.create_case_file(
        CaseFileCreate(
            case_number="200-2026-003",
        ),
        defendants_list=[DefendantCreate(full_name="Carlos Ruiz", verdict_status="Pending", status="Detenido")],
    )

    # Escenario 1: sin filtros (todos).
    all_search = svc.search_case_files("")
    all_count = svc.count_case_files()
    assert len(all_search) == all_count == 3

    # Escenario 2: filtro por texto.
    s = svc.search_case_files("001")
    c = svc.count_case_files(query="001")
    assert len(s) == c == 1

    # Escenario 3: filtro por defendant_name.
    s = svc.search_case_files("", defendant_name="Torres")
    c = svc.count_case_files(defendant_name="Torres")
    assert len(s) == c == 1

    # Escenario 4: filtro por victim_name.
    s = svc.search_case_files("", victim_name="Ramirez")
    c = svc.count_case_files(victim_name="Ramirez")
    assert len(s) == c == 1

    # Escenario 5: filtro por witness_name.
    s = svc.search_case_files("", witness_name="Garcia")
    c = svc.count_case_files(witness_name="Garcia")
    assert len(s) == c == 1

    # Escenario 6: filtro por defendant_status.
    s = svc.search_case_files("", defendant_status="Detenido")
    c = svc.count_case_files(defendant_status="Detenido")
    assert len(s) == c == 2

    # Escenario 7: filtro por verdict_status.
    s = svc.search_case_files("", verdict_status="Acquittal")
    c = svc.count_case_files(verdict_status="Acquittal")
    assert len(s) == c == 1

    # Escenario 8: filtro por indictment_date_from/to.
    s = svc.search_case_files(
        "", indictment_date_from=date(2025, 4, 1), indictment_date_to=date(2025, 12, 31)
    )
    c = svc.count_case_files(
        indictment_date_from=date(2025, 4, 1), indictment_date_to=date(2025, 12, 31)
    )
    assert len(s) == c == 1

    # Escenario 9: filtro por hearing_from/to.
    s = svc.search_case_files(
        "",
        hearing_from=datetime(2025, 6, 1),
        hearing_to=datetime(2025, 6, 30),
    )
    c = svc.count_case_files(
        hearing_from=datetime(2025, 6, 1),
        hearing_to=datetime(2025, 6, 30),
    )
    assert len(s) == c == 1

    # Escenario 10: filtros combinados (AND).
    s = svc.search_case_files(
        "", defendant_status="Detenido", verdict_status="Pending"
    )
    c = svc.count_case_files(
        defendant_status="Detenido", verdict_status="Pending"
    )
    assert len(s) == c == 2

    # Escenario 11: paginación — count no afectado por limit/offset.
    s_page = svc.search_case_files("", limit=1, offset=0)
    c_all = svc.count_case_files()
    assert len(s_page) == 1 and c_all == 3

    svc.close()
    print("   -> count y search retornan los mismos resultados para 11 escenarios de filtros")

    print("\nTODAS LAS PRUEBAS PASARON")


if __name__ == "__main__":
    main()
