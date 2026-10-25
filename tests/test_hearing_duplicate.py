"""Test de la duplicación de audiencias (continuaciones)."""

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


def test_duplicate_hearing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "duplicate.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        case_id = service.create_case_file(CaseFileCreate(case_number="DUP-1"))
        when = datetime(2026, 1, 10, 9, 0)
        hearing_id = service.add_hearing(
            case_id,
            HearingScheduleCreate(
                scheduled_at=when,
                hearing_type="Apertura de Juicio",
                notes="Nota original",
            ),
        )
        src = tmp_path / "a.mp3"
        src.write_bytes(b"audio")
        rel_path, filename = service.store_audio_file(str(src))
        service.update_hearing(
            hearing_id,
            HearingScheduleUpdate(
                audio_path=rel_path,
                audio_filename=filename,
                transcription="Acta original",
            ),
        )

        new_id = service.duplicate_hearing(hearing_id)
        assert new_id is not None and new_id != hearing_id
        hearings = {h.id: h for h in service.get_case_file_by_id(case_id).hearings}
        original = hearings[hearing_id]
        copy = hearings[new_id]
        assert copy.scheduled_at == original.scheduled_at + timedelta(days=7)
        assert copy.hearing_type == original.hearing_type
        assert copy.notes == original.notes
        assert copy.status == "Scheduled"
        assert copy.transcription is None
        assert copy.audio_path is None

        assert service.duplicate_hearing(99999) is None
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
