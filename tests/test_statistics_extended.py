"""Test de estadísticas extendidas con datos existentes."""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (  # noqa: E402
    CaseFileCreate,
    CaseFileService,
    CrimeCreate,
    DefendantCreate,
    HearingScheduleCreate,
)
from db.database import dispose_engine, reset_session_factory  # noqa: E402


def test_statistics_extended_fields(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "stats_ext.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        when = datetime(2026, 5, 10, 9, 0)

        # Caso 1: activo, delito Droga, veredicto Condena, con audio y transcripción.
        case_1 = service.create_case_file(
            CaseFileCreate(case_number="SE-1", prosecutor_name="Fiscal A", is_emblematic=True),
            crimes_list=[CrimeCreate(crime_type="Droga")],
            hearings_list=[
                HearingScheduleCreate(
                    scheduled_at=when,
                    status="Completed",
                    audio_path="audios/x.mp3",
                    transcription="transcripcion de prueba",
                )
            ],
        )
        service.add_defendant(
            case_1,
            DefendantCreate(
                full_name="Detenido A",
                arrest_date=None,
                status="Detenido",
                verdict_status="Conviction",
            ),
        )

        # Caso 2: activo, delito Armas, veredicto Pendiente, audiencia sin audio ni transcripción.
        case_2 = service.create_case_file(
            CaseFileCreate(case_number="SE-2", prosecutor_name="Fiscal B"),
            crimes_list=[CrimeCreate(crime_type="Armas")],
            hearings_list=[
                HearingScheduleCreate(scheduled_at=when, status="Scheduled")
            ],
        )
        service.add_defendant(
            case_2,
            DefendantCreate(
                full_name="Detenido B",
                arrest_date=None,
                status="En Libertad",
                verdict_status="Pending",
            ),
        )

        # Caso 3: archivado, debe excluirse de contadores activos.
        case_3 = service.create_case_file(
            CaseFileCreate(case_number="SE-3", prosecutor_name="Fiscal C"),
            crimes_list=[CrimeCreate(crime_type="Violencia")],
        )
        service.archive_case_file(case_3)

        summary = service.get_statistics()
        assert summary.total_cases == 3
        assert summary.active_cases == 2
        assert summary.archived_cases == 1
        assert summary.emblematic_cases == 1

        by_crime = {i.label: i.count for i in summary.cases_by_crime_type}
        assert by_crime.get("Droga") == 1
        assert by_crime.get("Armas") == 1
        assert "Violencia" not in by_crime

        by_verdict = {i.label: i.count for i in summary.cases_by_verdict_status}
        assert by_verdict.get("Conviction") == 1
        assert by_verdict.get("Pending") == 1

        by_status = {i.label: i.count for i in summary.hearings_by_status}
        assert by_status.get("Completed") == 1
        assert by_status.get("Scheduled") == 1

        assert summary.cases_missing_audio == 1
        assert summary.cases_missing_transcription == 1
        assert summary.detention_alerts_count == 0
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
