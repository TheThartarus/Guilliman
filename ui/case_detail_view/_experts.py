"""Sección de expertos/funcionarios del detalle de expediente."""

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

from ui.dialogs import ExpertDialog, confirm_delete
from ui.shared import format_date
from ui.widgets import show_error, show_info

logger = logging.getLogger("guilliman")


class _ExpertsSection:
    """Métodos de la sección de expertos del ``CaseDetailView``."""

    def _selected_expert_id(self) -> int | None:
        row = self.experts_table.currentRow()
        if 0 <= row < len(self._expert_rows):
            return self._expert_rows[row]
        return None

    def _fill_experts(self, case: CaseFileRead) -> None:
        self._expert_rows = [e.id for e in case.experts]
        self.experts_table.setRowCount(len(case.experts))
        for row, e in enumerate(case.experts):
            id_item = QTableWidgetItem(str(e.id))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.experts_table.setItem(row, 0, id_item)
            self.experts_table.setItem(row, 1, QTableWidgetItem(e.name or ""))
            self.experts_table.setItem(
                row, 2, QTableWidgetItem("SÍ" if e.appeared else "NO")
            )
            self.experts_table.setItem(row, 3, QTableWidgetItem(format_date(e.appearance_date)))
            self.experts_table.setItem(row, 4, QTableWidgetItem(e.additional_notes or ""))

    def _on_add_expert(self) -> None:
        dialog = ExpertDialog(self, self.app, self.case_file_id)
        if dialog.exec():
            self.load()

    def _on_edit_expert(self) -> None:
        expert_id = self._selected_expert_id()
        if expert_id is None:
            show_error(self, "Seleccione un experto de la tabla.")
            return
        expert = next(
            (e for e in self._case.experts if e.id == expert_id), None
        )
        dialog = ExpertDialog(self, self.app, self.case_file_id, expert)
        if dialog.exec():
            self.load()

    def _on_expert_double(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._expert_rows):
            expert = next(
                (e for e in self._case.experts if e.id == self._expert_rows[row]), None
            )
            dialog = ExpertDialog(self, self.app, self.case_file_id, expert)
            if dialog.exec():
                self.load()

    def _build_experts_section(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(SubtitleLabel("Expertos"))

        row = QHBoxLayout()
        self.add_expert_btn = PushButton("Agregar experto")
        self.add_expert_btn.clicked.connect(self._on_add_expert)
        self.edit_expert_btn = PushButton("Editar experto")
        self.edit_expert_btn.clicked.connect(self._on_edit_expert)
        self.del_expert_btn = PushButton("Eliminar experto")
        self.del_expert_btn.clicked.connect(self._on_del_expert)
        row.addWidget(self.add_expert_btn)
        row.addWidget(self.edit_expert_btn)
        row.addWidget(self.del_expert_btn)
        vbox.addLayout(row)

        from PyQt5.QtWidgets import QAbstractItemView, QHeaderView

        self.experts_table = TableWidget()
        self.experts_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.experts_table.setColumnCount(5)
        self.experts_table.setHorizontalHeaderLabels(
            ["ID", "Nombre", "Compareció", "Fecha comparecencia", "Notas"]
        )
        self.experts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.experts_table.cellDoubleClicked.connect(self._on_expert_double)
        vbox.addWidget(self.experts_table, 1)
        return container

    def _on_del_expert(self) -> None:
        expert_id = self._selected_expert_id()
        if expert_id is None:
            show_error(self, "Seleccione un experto de la tabla.")
            return
        if not confirm_delete(self, "¿Eliminar este experto?"):
            return
        try:
            ok = self.app.service.delete_expert(expert_id)
        except ValueError as exc:
            logger.exception("Error al eliminar experto %s", expert_id)
            show_error(self, f"Error al eliminar: {exc}")
            return
        if ok:
            show_info(self, "Experto eliminado.")
            self.load()
        else:
            show_error(self, "El experto no existe.")
