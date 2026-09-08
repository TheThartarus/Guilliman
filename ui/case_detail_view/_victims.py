"""Sección de víctimas del detalle de expediente (tabla, alta/edición/borrado)."""

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

from ui.dialogs import VictimDialog, confirm_delete
from ui.shared import format_date
from ui.widgets import show_error, show_info

logger = logging.getLogger("guilliman")


class _VictimsSection:
    """Métodos de la sección de víctimas del ``CaseDetailView``."""

    def _selected_victim_id(self) -> int | None:
        row = self.victims_table.currentRow()
        if 0 <= row < len(self._victim_rows):
            return self._victim_rows[row]
        return None

    def _fill_victims(self, case: CaseFileRead) -> None:
        self._victim_rows = [v.id for v in case.victims]
        self.victims_table.setRowCount(len(case.victims))
        for row, v in enumerate(case.victims):
            id_item = QTableWidgetItem(str(v.id))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.victims_table.setItem(row, 0, id_item)
            self.victims_table.setItem(row, 1, QTableWidgetItem(v.full_name or ""))
            self.victims_table.setItem(row, 2, QTableWidgetItem(v.national_id or ""))
            self.victims_table.setItem(
                row, 3, QTableWidgetItem(format_date(v.birth_date))
            )
            age_item = QTableWidgetItem(str(v.age) if v.age is not None else "")
            age_item.setTextAlignment(Qt.AlignCenter)
            self.victims_table.setItem(row, 4, age_item)
            self.victims_table.setItem(
                row, 5, QTableWidgetItem("SÍ" if v.appeared else "NO")
            )
            self.victims_table.setItem(
                row, 6, QTableWidgetItem(format_date(v.appearance_date))
            )
            self.victims_table.setItem(row, 7, QTableWidgetItem(v.address or ""))
            self.victims_table.setItem(row, 8, QTableWidgetItem(v.phone or ""))
            self.victims_table.setItem(row, 9, QTableWidgetItem(v.additional_notes or ""))

    def _on_add_victim(self) -> None:
        dialog = VictimDialog(self, self.app, self.case_file_id)
        if dialog.exec():
            self.load()

    def _on_edit_victim(self) -> None:
        victim_id = self._selected_victim_id()
        if victim_id is None:
            show_error(self, "Seleccione una víctima de la tabla.")
            return
        victim = next(
            (v for v in self._case.victims if v.id == victim_id), None
        )
        dialog = VictimDialog(self, self.app, self.case_file_id, victim)
        if dialog.exec():
            self.load()

    def _on_victim_double(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._victim_rows):
            victim = next(
                (v for v in self._case.victims if v.id == self._victim_rows[row]), None
            )
            dialog = VictimDialog(self, self.app, self.case_file_id, victim)
            if dialog.exec():
                self.load()

    def _build_victims_section(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(SubtitleLabel("Víctimas"))

        row = QHBoxLayout()
        self.add_victim_btn = PushButton("Agregar víctima")
        self.add_victim_btn.clicked.connect(self._on_add_victim)
        self.edit_victim_btn = PushButton("Editar víctima")
        self.edit_victim_btn.clicked.connect(self._on_edit_victim)
        self.del_victim_btn = PushButton("Eliminar víctima")
        self.del_victim_btn.clicked.connect(self._on_del_victim)
        row.addWidget(self.add_victim_btn)
        row.addWidget(self.edit_victim_btn)
        row.addWidget(self.del_victim_btn)
        vbox.addLayout(row)

        from PyQt5.QtWidgets import QAbstractItemView, QHeaderView

        self.victims_table = TableWidget()
        self.victims_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.victims_table.setColumnCount(10)
        self.victims_table.setHorizontalHeaderLabels(
            ["ID", "Nombre", "Cédula", "Fecha Nac.", "Edad", "Compareció", "Fecha comparec.", "Dirección", "Teléfono", "Notas"]
        )
        self.victims_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.victims_table.cellDoubleClicked.connect(self._on_victim_double)
        vbox.addWidget(self.victims_table, 1)
        return container

    def _on_del_victim(self) -> None:
        victim_id = self._selected_victim_id()
        if victim_id is None:
            show_error(self, "Seleccione una víctima de la tabla.")
            return
        if not confirm_delete(self, "¿Eliminar esta víctima?"):
            return
        try:
            ok = self.app.service.delete_victim(victim_id)
        except ValueError as exc:
            logger.exception("Error al eliminar víctima %s", victim_id)
            show_error(self, f"Error al eliminar: {exc}")
            return
        if ok:
            show_info(self, "Víctima eliminada.")
            self.load()
        else:
            show_error(self, "La víctima no existe.")
