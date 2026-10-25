"""Test de múltiples delitos por expediente y compatibilidad legacy."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (  # noqa: E402
    CaseFileCreate,
    CaseFileService,
    CrimeCreate,
)
from db.database import dispose_engine, reset_session_factory  # noqa: E402


def _types(case) -> list[str]:
    return [crime.crime_type for crime in sorted(case.crimes, key=lambda c: c.id)]


def test_multiple_crimes(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "crimes.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        case_id = service.create_case_file(
            CaseFileCreate(case_number="MULTI-1"),
            crimes_list=[
                CrimeCreate(
                    crime_type="Droga",
                    drug_quantity=2.5,
                    drug_type="Cocaína",
                ),
                CrimeCreate(
                    crime_type="Armas",
                    weapon_quantity=3,
                    weapon_type="Arma de Fuego",
                ),
            ],
        )
        case = service.get_case_file_by_id(case_id)
        assert _types(case) == ["Droga", "Armas"]
        assert case.crimes[0].drug_quantity == 2.5
        assert case.crimes[1].weapon_quantity == 3

        # El filtro por tipo de delito encuentra cualquier delito del expediente.
        for crime_type in ("Droga", "Armas"):
            assert [
                c.case_number
                for c in service.search_case_files("", crime_type=crime_type)
            ] == ["MULTI-1"]

        # Reemplazo atómico de la lista.
        assert service.set_case_crimes(
            case_id, [CrimeCreate(crime_type="Violencia")]
        )
        assert _types(service.get_case_file_by_id(case_id)) == ["Violencia"]
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
