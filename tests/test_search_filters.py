"""Test de la búsqueda de expedientes por Tipo de Delito."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import CaseFileCreate, CaseFileService, CrimeCreate  # noqa: E402
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
            crimes = [CrimeCreate(crime_type=crime_type)] if crime_type else []
            service.create_case_file(
                CaseFileCreate(case_number=case_number), crimes_list=crimes
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


def test_search_by_text_dates_and_origin(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "search2.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        service.create_case_file(
            CaseFileCreate(
                case_number="B-1",
                offense_description="Robo agravado",
                facts_summary="Sustracción a mano armada en la vía pública",
                location="Sector Centro",
                origin_location="Municipio Libertador",
                indictment_date=date(2026, 3, 15),
            )
        )
        service.create_case_file(
            CaseFileCreate(
                case_number="B-2",
                facts_summary="Hurto simple",
                indictment_date=date(2026, 6, 1),
            )
        )

        # Texto libre sobre descripción, hechos y ubicación.
        for term in ("mano armada", "Sector Centro", "Robo agravado"):
            assert [c.case_number for c in service.search_case_files(term)] == ["B-1"]

        # Procedencia.
        assert [
            c.case_number
            for c in service.search_case_files("", origin_location="Libertador")
        ] == ["B-1"]
        assert service.count_case_files(origin_location="Libertador") == 1

        # Rango de fechas de acusación.
        assert [
            c.case_number
            for c in service.search_case_files(
                "",
                indictment_date_from=date(2026, 1, 1),
                indictment_date_to=date(2026, 4, 1),
            )
        ] == ["B-1"]
        assert [
            c.case_number
            for c in service.search_case_files(
                "", indictment_date_from=date(2026, 5, 1)
            )
        ] == ["B-2"]
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
