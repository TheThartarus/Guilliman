"""Test de la búsqueda de expedientes por Tipo de Delito."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import CaseFileCreate, CaseFileService  # noqa: E402
from db.database import dispose_engine, reset_session_factory  # noqa: E402


def test_search_by_crime_type(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "search.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        for case_number, crime_type in (
            ("A-1", "Droga"),
            ("A-2", "Armas"),
            ("A-3", "Violencia"),
            ("A-4", None),
        ):
            service.create_case_file(
                CaseFileCreate(case_number=case_number, crime_type=crime_type)
            )

        # Filtro exacto por tipo de delito.
        assert [c.case_number for c in service.search_case_files("", crime_type="Armas")] == ["A-2"]
        assert [c.case_number for c in service.search_case_files("", crime_type="Droga")] == ["A-1"]
        assert service.count_case_files(crime_type="Armas") == 1

        # Combinable con el texto libre.
        assert [
            c.case_number for c in service.search_case_files("A-", crime_type="Violencia")
        ] == ["A-3"]

        # Sin filtro devuelve todos (incluido el expediente sin tipo).
        assert len(service.search_case_files("", crime_type=None)) == 4
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
