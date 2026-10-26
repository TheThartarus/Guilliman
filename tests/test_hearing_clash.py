"""Test de detección de choque de agenda (misma fecha/hora)."""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (  # noqa: E402
    CaseFileCreate,
    CaseFileService,
    HearingClashItem,
    HearingScheduleCreate,
)
from db.database import dispose_engine, reset_session_factory  # noqa: E402


def test_hearing_clash_detects_same_slot(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "clash.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        case_1 = service.create_case_file(CaseFileCreate(case_number="CL-1"))
        case_2 = service.create_case_file(CaseFileCreate(case_number="CL-2"))
        when = datetime(2026, 3, 5, 9, 0)

        h1 = service.add_hearing(
            case_1, HearingScheduleCreate(scheduled_at=when, hearing_type="Apertura de Juicio")
        )

        # Sin otra audiencia distinta en el mismo slot, no hay choque real.
        assert service.find_hearing_clashes(when, exclude_hearing_id=h1) == []

        h2 = service.add_hearing(
            case_2, HearingScheduleCreate(scheduled_at=when, hearing_type="Preliminar")
        )

        clashes = service.find_hearing_clashes(when)
        assert len(clashes) == 2
        ids = {c.hearing_id for c in clashes}
        assert ids == {h1, h2}
        assert all(isinstance(c, HearingClashItem) for c in clashes)
        assert all(c.scheduled_at == when for c in clashes)

        # Editando h1 y excluyéndolo, solo queda h2.
        clashes_excl = service.find_hearing_clashes(when, exclude_hearing_id=h1)
        assert len(clashes_excl) == 1
        assert clashes_excl[0].hearing_id == h2
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()


def test_hearing_clash_ignores_archived_cases(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "clash_arch.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        case_1 = service.create_case_file(CaseFileCreate(case_number="CLA-1"))
        case_2 = service.create_case_file(CaseFileCreate(case_number="CLA-2"))
        when = datetime(2026, 4, 1, 10, 0)

        service.add_hearing(case_1, HearingScheduleCreate(scheduled_at=when))
        h2 = service.add_hearing(case_2, HearingScheduleCreate(scheduled_at=when))

        service.archive_case_file(case_1)

        clashes = service.find_hearing_clashes(when)
        assert len(clashes) == 1
        assert clashes[0].hearing_id == h2
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
