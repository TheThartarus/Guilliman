"""Sección de pruebas documentales del detalle de expediente."""

from __future__ import annotations

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from qfluentwidgets import PushButton, SubtitleLabel, TableWidget

from db import CaseFileRead

from ui.dialogs import DocumentaryDialog, confirm_delete
from ui.shared import format_date
from ui.widgets import show_error, show_info

logger = logging.getLogger("guilliman")


class _DocumentariesSection:
    """Métodos de la sección de documentales del ``CaseDetailView``."""

    def _selected_documentary_id(self) -> int | None:
        row = self.documentaries_table.currentRow()
        if 0 <= row < len(self._documentary_rows):
            return self._documentary_rows[row]
        return None

    def _fill_documentaries(self, case: CaseFileRead) -> None:
        self._documentary_rows = [d.id for d in case.documentaries]
        self.documentaries_table.setRowCount(len(case.documentaries))
        for row, d in enumerate(case.documentaries):
            id_item = QTableWidgetItem(str(d.id))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.documentaries_table.setItem(row, 0, id_item)
            self.documentaries_table.setItem(row, 1, QTableWidgetItem(d.name or ""))
            self.documentaries_table.setItem(
                row, 2, QTableWidgetItem("SÍ" if d.in_possession else "NO")
            )
            self.documentaries_table.setItem(
                row, 3, QTableWidgetItem(format_date(d.possession_date))
            )
            self.documentaries_table.setItem(
                row, 4, QTableWidgetItem("SÍ" if d.evacuated else "NO")
            )
            self.documentaries_table.setItem(
                row, 5, QTableWidgetItem(format_date(d.evacuation_date))
            )
            self.documentaries_table.setItem(row, 6, QTableWidgetItem(d.additional_notes or ""))

    def _on_add_documentary(self) -> None:
        dialog = DocumentaryDialog(self, self.app, self.case_file_id)
        if dialog.exec():
            self.load()

    def _on_edit_documentary(self) -> None:
        documentary_id = self._selected_documentary_id()
        if documentary_id is None:
            show_error(self, "Seleccione un documental de la tabla.")
            return
        documentary = next(
            (d for d in self._case.documentaries if d.id == documentary_id), None
        )
        dialog = DocumentaryDialog(self, self.app, self.case_file_id, documentary)
        if dialog.exec():
            self.load()

    def _on_documentary_double(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._documentary_rows):
            documentary = next(
                (d for d in self._case.documentaries if d.id == self._documentary_rows[row]), None
            )
            dialog = DocumentaryDialog(self, self.app, self.case_file_id, documentary)
            if dialog.exec():
                self.load()

    def _build_documentaries_section(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(SubtitleLabel("Documentales"))

        row = QHBoxLayout()
        self.add_documentary_btn = PushButton("Agregar documental")
        self.add_documentary_btn.clicked.connect(self._on_add_documentary)
        self.edit_documentary_btn = PushButton("Editar documental")
        self.edit_documentary_btn.clicked.connect(self._on_edit_documentary)
        self.del_documentary_btn = PushButton("Eliminar documental")
        self.del_documentary_btn.clicked.connect(self._on_del_documentary)
        row.addWidget(self.add_documentary_btn)
        row.addWidget(self.edit_documentary_btn)
        row.addWidget(self.del_documentary_btn)
        vbox.addLayout(row)

        from PyQt5.QtWidgets import QAbstractItemView, QHeaderView

        self.documentaries_table = TableWidget()
        self.documentaries_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.documentaries_table.setColumnCount(7)
        self.documentaries_table.setHorizontalHeaderLabels(
            ["ID", "Nombre", "En posesión", "Fecha recepción", "Evacuado",
             "Fecha evacuación", "Notas"]
        )
        self.documentaries_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.documentaries_table.cellDoubleClicked.connect(self._on_documentary_double)
        vbox.addWidget(self.documentaries_table, 1)
        return container

    def _on_del_documentary(self) -> None:
        documentary_id = self._selected_documentary_id()
        if documentary_id is None:
            show_error(self, "Seleccione un documental de la tabla.")
            return
        if not confirm_delete(self, "¿Eliminar este documental?"):
            return
        try:
            ok = self.app.service.delete_documentary(documentary_id)
        except ValueError as exc:
            logger.exception("Error al eliminar documental %s", documentary_id)
            show_error(self, f"Error al eliminar: {exc}")
            return
        if ok:
            show_info(self, "Documental eliminado.")
            self.load()
        else:
            show_error(self, "El documental no existe.")
