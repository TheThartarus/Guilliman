"""Test de los contadores y flags que alimentan el dashboard."""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (  # noqa: E402
    CaseFileCreate,
    CaseFileService,
    HearingScheduleCreate,
    HearingScheduleUpdate,
)
from db.database import dispose_engine, reset_session_factory  # noqa: E402


def test_pending_counts_and_flags(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "dashboard.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        case_id = service.create_case_file(CaseFileCreate(case_number="DASH-1"))
        now = datetime.now()
        hearing_plain = service.add_hearing(
            case_id, HearingScheduleCreate(scheduled_at=now + timedelta(days=1))
        )
        hearing_acta = service.add_hearing(
            case_id, HearingScheduleCreate(scheduled_at=now + timedelta(days=2))
        )
        hearing_audio = service.add_hearing(
            case_id, HearingScheduleCreate(scheduled_at=now + timedelta(days=3))
        )
        service.update_hearing(
            hearing_acta, HearingScheduleUpdate(transcription="ACTA")
        )
        src = tmp_path / "a.mp3"
        src.write_bytes(b"audio")
        rel_path, filename = service.store_audio_file(str(src))
        service.update_hearing(
            hearing_audio,
            HearingScheduleUpdate(audio_path=rel_path, audio_filename=filename),
        )

        assert service.count_hearings_missing_audio() == 2
        assert service.count_hearings_missing_transcription() == 2

        items = service.list_scheduled_hearings(now, now + timedelta(days=4))
        by_id = {item.hearing_id: item for item in items}
        assert by_id[hearing_plain].has_audio is False
        assert by_id[hearing_plain].has_transcription is False
        assert by_id[hearing_acta].has_transcription is True
        assert by_id[hearing_acta].has_audio is False
        assert by_id[hearing_audio].has_audio is True
        assert by_id[hearing_audio].has_transcription is False
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
