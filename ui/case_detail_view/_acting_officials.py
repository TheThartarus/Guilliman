"""Sección de funcionarios actuantes del detalle de expediente."""

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

from ui.dialogs import ActingOfficialDialog, confirm_delete
from ui.shared import format_date
from ui.widgets import show_error, show_info

logger = logging.getLogger("guilliman")


class _ActingOfficialsSection:
    """Métodos de la sección de funcionarios actuantes del ``CaseDetailView``."""

    def _selected_official_id(self) -> int | None:
        row = self.officials_table.currentRow()
        if 0 <= row < len(self._official_rows):
            return self._official_rows[row]
        return None

    def _fill_acting_officials(self, case: CaseFileRead) -> None:
        self._official_rows = [o.id for o in case.acting_officials]
        self.officials_table.setRowCount(len(case.acting_officials))
        for row, o in enumerate(case.acting_officials):
            id_item = QTableWidgetItem(str(o.id))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.officials_table.setItem(row, 0, id_item)
            self.officials_table.setItem(row, 1, QTableWidgetItem(o.name or ""))
            self.officials_table.setItem(
                row, 2, QTableWidgetItem("SÍ" if o.appeared else "NO")
            )
            self.officials_table.setItem(row, 3, QTableWidgetItem(format_date(o.appearance_date)))
            self.officials_table.setItem(row, 4, QTableWidgetItem(o.additional_notes or ""))

    def _on_add_official(self) -> None:
        dialog = ActingOfficialDialog(self, self.app, self.case_file_id)
        if dialog.exec():
            self.load()

    def _on_edit_official(self) -> None:
        official_id = self._selected_official_id()
        if official_id is None:
            show_error(self, "Seleccione un funcionario de la tabla.")
            return
        official = next(
            (o for o in self._case.acting_officials if o.id == official_id), None
        )
        dialog = ActingOfficialDialog(self, self.app, self.case_file_id, official)
        if dialog.exec():
            self.load()

    def _on_official_double(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._official_rows):
            official = next(
                (o for o in self._case.acting_officials if o.id == self._official_rows[row]), None
            )
            dialog = ActingOfficialDialog(self, self.app, self.case_file_id, official)
            if dialog.exec():
                self.load()

    def _build_acting_officials_section(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(SubtitleLabel("Actuantes"))

        row = QHBoxLayout()
        self.add_official_btn = PushButton("Agregar funcionario")
        self.add_official_btn.clicked.connect(self._on_add_official)
        self.edit_official_btn = PushButton("Editar funcionario")
        self.edit_official_btn.clicked.connect(self._on_edit_official)
        self.del_official_btn = PushButton("Eliminar funcionario")
        self.del_official_btn.clicked.connect(self._on_del_official)
        row.addWidget(self.add_official_btn)
        row.addWidget(self.edit_official_btn)
        row.addWidget(self.del_official_btn)
        vbox.addLayout(row)

        from PyQt5.QtWidgets import QAbstractItemView, QHeaderView

        self.officials_table = TableWidget()
        self.officials_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.officials_table.setColumnCount(5)
        self.officials_table.setHorizontalHeaderLabels(
            ["ID", "Nombre", "Compareció", "Fecha comparecencia", "Notas"]
        )
        self.officials_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.officials_table.cellDoubleClicked.connect(self._on_official_double)
        vbox.addWidget(self.officials_table, 1)
        return container

    def _on_del_official(self) -> None:
        official_id = self._selected_official_id()
        if official_id is None:
            show_error(self, "Seleccione un funcionario de la tabla.")
            return
        if not confirm_delete(self, "¿Eliminar este funcionario?"):
            return
        try:
            ok = self.app.service.delete_acting_official(official_id)
        except ValueError as exc:
            logger.exception("Error al eliminar funcionario %s", official_id)
            show_error(self, f"Error al eliminar: {exc}")
            return
        if ok:
            show_info(self, "Funcionario eliminado.")
            self.load()
        else:
            show_error(self, "El funcionario no existe.")
