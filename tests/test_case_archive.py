"""Test del archivado lógico de expedientes (soft delete)."""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (  # noqa: E402
    CaseFileCreate,
    CaseFileService,
    HearingScheduleCreate,
)
from db.database import dispose_engine, reset_session_factory  # noqa: E402


def test_archive_and_restore_case_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "archive.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        case_id = service.create_case_file(CaseFileCreate(case_number="ARC-1"))
        service.add_hearing(
            case_id,
            HearingScheduleCreate(scheduled_at=datetime(2026, 1, 10, 9, 0)),
        )
        assert service.count_case_files() == 1
        assert len(service.list_scheduled_hearings()) == 1
        assert service.count_hearings_missing_audio() == 1

        assert service.archive_case_file(case_id)
        assert not service.archive_case_file(case_id)
        assert service.search_case_files("") == []
        assert service.count_case_files() == 0
        assert service.list_scheduled_hearings() == []
        assert service.count_hearings_missing_audio() == 0
        assert [
            c.case_number for c in service.search_case_files("", include_archived=True)
        ] == ["ARC-1"]
        assert service.count_case_files(include_archived=True) == 1
        assert service.get_case_file_by_id(case_id).archived_at is not None

        assert service.unarchive_case_file(case_id)
        assert not service.unarchive_case_file(case_id)
        assert service.count_case_files() == 1
        assert len(service.list_scheduled_hearings()) == 1
        assert service.get_case_file_by_id(case_id).archived_at is None
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
