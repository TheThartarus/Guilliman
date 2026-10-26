"""Test de causas conexas."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from db import CaseFileCreate, CaseFileService  # noqa: E402
from db.database import dispose_engine, reset_session_factory  # noqa: E402
from db.exceptions import CaseFileNotFoundError  # noqa: E402


def test_link_cases_is_symmetric_and_idempotent(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "links.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        first = service.create_case_file(CaseFileCreate(case_number="CX-1"))
        second = service.create_case_file(CaseFileCreate(case_number="CX-2"))

        link_id = service.link_cases(first, "cx-2")
        assert service.link_cases(second, "CX-1") == link_id

        from_first = service.list_linked_cases(first)
        from_second = service.list_linked_cases(second)
        assert [item.case_number for item in from_first] == ["CX-2"]
        assert [item.case_number for item in from_second] == ["CX-1"]
        assert from_first[0].link_id == link_id

        assert service.unlink_case(link_id)
        assert service.list_linked_cases(first) == []
        assert service.unlink_case(link_id) is False

        with pytest.raises(ValueError):
            service.link_cases(first, "CX-1")
        with pytest.raises(ValueError):
            service.link_cases(first, "NO-EXISTE")
        with pytest.raises(CaseFileNotFoundError):
            service.link_cases(99999, "CX-1")
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()


def test_deleting_case_drops_link(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "links_del.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        first = service.create_case_file(CaseFileCreate(case_number="CD-1"))
        second = service.create_case_file(CaseFileCreate(case_number="CD-2"))
        service.link_cases(first, "CD-2")
        assert service.delete_case_file(first)
        assert service.list_linked_cases(second) == []
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
