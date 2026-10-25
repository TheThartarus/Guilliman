"""Test del reporte de integridad del almacén de audios."""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (  # noqa: E402
    CaseFileCreate,
    CaseFileService,
    HearingScheduleCreate,
    HearingScheduleUpdate,
)
from db.database import dispose_engine, reset_session_factory  # noqa: E402


def test_audio_integrity_detects_missing_and_outside(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "integrity.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        case_id = service.create_case_file(CaseFileCreate(case_number="INT-1"))
        hearing_id = service.add_hearing(
            case_id,
            HearingScheduleCreate(scheduled_at=datetime(2026, 1, 10, 9, 0)),
        )
        src = tmp_path / "a.mp3"
        src.write_bytes(b"audio")
        rel_path, filename = service.store_audio_file(str(src))
        service.update_hearing(
            hearing_id,
            HearingScheduleUpdate(audio_path=rel_path, audio_filename=filename),
        )
        assert service.check_audio_integrity() == []

        # Borrar el archivo del store ⇒ faltante.
        (tmp_path / "data" / rel_path).unlink()
        issues = service.check_audio_integrity()
        assert len(issues) == 1
        assert issues[0].reason == "missing"
        assert issues[0].case_number == "INT-1"

        # Ruta fuera del almacén ⇒ outside_store.
        service.update_hearing(
            hearing_id,
            HearingScheduleUpdate(audio_path="../evil.mp3", audio_filename="evil.mp3"),
        )
        issues = service.check_audio_integrity()
        assert len(issues) == 1
        assert issues[0].reason == "outside_store"
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
