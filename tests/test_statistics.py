"""Test de estadísticas agregadas y exportación de reportes."""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (  # noqa: E402
    CaseFileCreate,
    CaseFileService,
    CrimeCreate,
    HearingScheduleCreate,
)
from db.database import dispose_engine, reset_session_factory  # noqa: E402
from ui.exporters import export_statistics_csv, export_statistics_pdf  # noqa: E402


def test_statistics_summary_and_exports(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "stats.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        service.create_case_file(
            CaseFileCreate(case_number="S-1", prosecutor_name="Fiscal A"),
            crimes_list=[
                CrimeCreate(crime_type="Droga"),
                CrimeCreate(crime_type="Armas"),
            ],
            hearings_list=[
                HearingScheduleCreate(scheduled_at=datetime.now()),
            ],
        )
        service.create_case_file(
            CaseFileCreate(case_number="S-2", prosecutor_name="Fiscal A"),
            crimes_list=[CrimeCreate(crime_type="Droga")],
            hearings_list=[
                HearingScheduleCreate(scheduled_at=datetime.now()),
            ],
        )
        archived_id = service.create_case_file(
            CaseFileCreate(case_number="S-3", prosecutor_name="Fiscal B"),
            crimes_list=[CrimeCreate(crime_type="Violencia")],
        )
        service.archive_case_file(archived_id)

        summary = service.get_statistics()
        assert summary.total_cases == 3
        assert summary.active_cases == 2
        assert summary.archived_cases == 1

        by_crime = {item.label: item.count for item in summary.cases_by_crime_type}
        assert by_crime["Droga"] == 2
        assert by_crime["Armas"] == 1
        assert "Violencia" not in by_crime

        by_prosecutor = {
            item.label: item.count for item in summary.cases_by_prosecutor
        }
        assert by_prosecutor["Fiscal A"] == 2
        assert "Fiscal B" not in by_prosecutor

        assert len(summary.hearings_by_month) == 12
        assert sum(item.count for item in summary.hearings_by_month) == 2

        csv_path = tmp_path / "stats.csv"
        pdf_path = tmp_path / "stats.pdf"
        export_statistics_csv(summary, str(csv_path))
        export_statistics_pdf(summary, str(pdf_path))
        text = csv_path.read_text(encoding="utf-8")
        assert "total_expedientes,3" in text
        assert "delito,Droga,2" in text
        assert pdf_path.is_file() and pdf_path.stat().st_size > 0
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
