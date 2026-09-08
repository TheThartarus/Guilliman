"""Sección de testigos del detalle de expediente (tabla, alta/edición/borrado)."""

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

from ui.dialogs import WitnessDialog, confirm_delete
from ui.shared import format_date
from ui.widgets import show_error, show_info

logger = logging.getLogger("guilliman")


class _WitnessesSection:
    """Métodos de la sección de testigos del ``CaseDetailView``."""

    def _selected_witness_id(self) -> int | None:
        row = self.witnesses_table.currentRow()
        if 0 <= row < len(self._witness_rows):
            return self._witness_rows[row]
        return None

    def _fill_witnesses(self, case: CaseFileRead) -> None:
        self._witness_rows = [w.id for w in case.witnesses]
        self.witnesses_table.setRowCount(len(case.witnesses))
        for row, w in enumerate(case.witnesses):
            id_item = QTableWidgetItem(str(w.id))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.witnesses_table.setItem(row, 0, id_item)
            self.witnesses_table.setItem(row, 1, QTableWidgetItem(w.full_name or ""))
            self.witnesses_table.setItem(row, 2, QTableWidgetItem(w.national_id or ""))
            self.witnesses_table.setItem(
                row, 3, QTableWidgetItem("SÍ" if w.appeared else "NO")
            )
            self.witnesses_table.setItem(
                row, 4, QTableWidgetItem(format_date(w.appearance_date))
            )
            self.witnesses_table.setItem(row, 5, QTableWidgetItem(w.address or ""))
            self.witnesses_table.setItem(row, 6, QTableWidgetItem(w.phone or ""))
            self.witnesses_table.setItem(row, 7, QTableWidgetItem(w.additional_notes or ""))

    def _on_add_witness(self) -> None:
        dialog = WitnessDialog(self, self.app, self.case_file_id)
        if dialog.exec():
            self.load()

    def _on_edit_witness(self) -> None:
        witness_id = self._selected_witness_id()
        if witness_id is None:
            show_error(self, "Seleccione un testigo de la tabla.")
            return
        witness = next(
            (w for w in self._case.witnesses if w.id == witness_id), None
        )
        dialog = WitnessDialog(self, self.app, self.case_file_id, witness)
        if dialog.exec():
            self.load()

    def _on_witness_double(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._witness_rows):
            witness = next(
                (w for w in self._case.witnesses if w.id == self._witness_rows[row]), None
            )
            dialog = WitnessDialog(self, self.app, self.case_file_id, witness)
            if dialog.exec():
                self.load()

    def _build_witnesses_section(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(SubtitleLabel("Testigos"))

        row = QHBoxLayout()
        self.add_witness_btn = PushButton("Agregar testigo")
        self.add_witness_btn.clicked.connect(self._on_add_witness)
        self.edit_witness_btn = PushButton("Editar testigo")
        self.edit_witness_btn.clicked.connect(self._on_edit_witness)
        self.del_witness_btn = PushButton("Eliminar testigo")
        self.del_witness_btn.clicked.connect(self._on_del_witness)
        row.addWidget(self.add_witness_btn)
        row.addWidget(self.edit_witness_btn)
        row.addWidget(self.del_witness_btn)
        vbox.addLayout(row)

        from PyQt5.QtWidgets import QAbstractItemView, QHeaderView

        self.witnesses_table = TableWidget()
        self.witnesses_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.witnesses_table.setColumnCount(8)
        self.witnesses_table.setHorizontalHeaderLabels(
            ["ID", "Nombre", "Cédula", "Compareció", "Fecha comparec.", "Dirección", "Teléfono", "Notas"]
        )
        self.witnesses_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.witnesses_table.cellDoubleClicked.connect(self._on_witness_double)
        vbox.addWidget(self.witnesses_table, 1)
        return container

    def _on_del_witness(self) -> None:
        witness_id = self._selected_witness_id()
        if witness_id is None:
            show_error(self, "Seleccione un testigo de la tabla.")
            return
        if not confirm_delete(self, "¿Eliminar este testigo?"):
            return
        try:
            ok = self.app.service.delete_witness(witness_id)
        except ValueError as exc:
            logger.exception("Error al eliminar testigo %s", witness_id)
            show_error(self, f"Error al eliminar: {exc}")
            return
        if ok:
            show_info(self, "Testigo eliminado.")
            self.load()
        else:
            show_error(self, "El testigo no existe.")
