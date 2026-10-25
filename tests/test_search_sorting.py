"""Test del ordenamiento de resultados y del mapeo fila → expediente."""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

APP = QApplication.instance() or QApplication([])

from db import CaseFileCreate, CaseFileService  # noqa: E402
from db.database import dispose_engine, reset_session_factory  # noqa: E402
from ui.case_search_view import CaseSearchView  # noqa: E402


class _FakeApp:
    def __init__(self, service) -> None:
        self.service = service
        self.shell = None


def test_search_sorting_keeps_row_mapping(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "sorting.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        service.create_case_file(CaseFileCreate(case_number="B-2"))
        service.create_case_file(CaseFileCreate(case_number="A-1"))

        view = CaseSearchView(_FakeApp(service))
        view.refresh()
        assert view.table.rowCount() == 2

        view.table.sortItems(1, Qt.AscendingOrder)
        for row in range(view.table.rowCount()):
            case_number = view.table.item(row, 1).text()
            case_id = view._case_id_at(row)
            assert case_id is not None
            detail = service.get_case_file_by_id(case_id)
            assert detail is not None and detail.case_number == case_number
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
