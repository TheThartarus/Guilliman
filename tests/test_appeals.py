"""Test del ciclo de vida de apelaciones por expediente."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (  # noqa: E402
    AppealCreate,
    CaseFileCreate,
    CaseFileService,
)
from db.database import dispose_engine, reset_session_factory  # noqa: E402


def test_appeals_lifecycle_and_filter(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "appeals.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        case_id = service.create_case_file(CaseFileCreate(case_number="AP-1"))
        service.create_case_file(CaseFileCreate(case_number="AP-2"))

        # Varias apelaciones por expediente.
        first_id = service.add_appeal(
            case_id,
            AppealCreate(
                filed_at=date(2026, 1, 10),
                remitted_to_court_at=date(2026, 1, 20),
                returned_from_court_at=date(2026, 2, 5),
                court_decision="Con lugar",
                classification="De autos",
            ),
        )
        service.add_appeal(
            case_id,
            AppealCreate(
                filed_at=date(2026, 3, 1),
                court_decision="Sin lugar",
                classification="Por sentencia",
            ),
        )

        case = service.get_case_file_by_id(case_id)
        assert len(case.appeals) == 2
        assert [a.case_number for a in service.search_case_files("", has_appeal=True)] == [
            "AP-1"
        ]
        assert [a.case_number for a in service.search_case_files("", has_appeal=False)] == [
            "AP-2"
        ]
        assert service.count_case_files(has_appeal=True) == 1

        # Actualización (reemplazo completo).
        assert service.update_appeal(
            case_id,
            first_id,
            AppealCreate(
                filed_at=date(2026, 1, 10),
                court_decision="Sin lugar",
                classification="Amparo",
            ),
        )
        updated = service.list_appeals(case_id)[0]
        assert updated.court_decision == "Sin lugar"
        assert updated.classification == "Amparo"

        # Eliminación individual.
        assert service.delete_appeal(first_id)
        assert len(service.list_appeals(case_id)) == 1

        # La cascada elimina las apelaciones al borrar el expediente.
        service.delete_case_file(case_id)
        assert service.list_appeals(case_id) == []
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
