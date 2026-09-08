"""Sección de acusados del detalle de expediente (tabla, alta/edición/borrado)."""

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

from ui.dialogs import DefendantDialog, confirm_delete
from ui.shared import VERDICT_STATUS_LABELS, format_date, translate
from ui.widgets import show_error, show_info

logger = logging.getLogger("guilliman")


class _DefendantsSection:
    """Métodos de la sección de acusados del ``CaseDetailView``."""

    def _selected_defendant_id(self) -> int | None:
        row = self.defendants_table.currentRow()
        if 0 <= row < len(self._defendant_rows):
            return self._defendant_rows[row]
        return None

    def _fill_defendants(self, case: CaseFileRead) -> None:
        self._defendant_rows = [d.id for d in case.defendants]
        self.defendants_table.setRowCount(len(case.defendants))
        for row, d in enumerate(case.defendants):
            id_item = QTableWidgetItem(str(d.id))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.defendants_table.setItem(row, 0, id_item)
            self.defendants_table.setItem(row, 1, QTableWidgetItem(d.full_name or ""))
            self.defendants_table.setItem(row, 2, QTableWidgetItem(d.national_id or ""))
            self.defendants_table.setItem(
                row, 3, QTableWidgetItem(format_date(d.birth_date))
            )
            age_item = QTableWidgetItem(str(d.age) if d.age is not None else "")
            age_item.setTextAlignment(Qt.AlignCenter)
            self.defendants_table.setItem(row, 4, age_item)
            self.defendants_table.setItem(
                row, 5, QTableWidgetItem(translate(d.verdict_status, VERDICT_STATUS_LABELS))
            )
            self.defendants_table.setItem(
                row, 6, QTableWidgetItem(format_date(d.arrest_date))
            )
            self.defendants_table.setItem(row, 7, QTableWidgetItem(d.address or ""))
            self.defendants_table.setItem(row, 8, QTableWidgetItem(d.phone or ""))
            self.defendants_table.setItem(row, 9, QTableWidgetItem(d.additional_notes or ""))

    def _on_add_defendant(self) -> None:
        dialog = DefendantDialog(self, self.app, self.case_file_id)
        if dialog.exec():
            self.load()

    def _on_edit_defendant(self) -> None:
        defendant_id = self._selected_defendant_id()
        if defendant_id is None:
            show_error(self, "Seleccione un acusado de la tabla.")
            return
        defendant = next(
            (d for d in self._case.defendants if d.id == defendant_id), None
        )
        dialog = DefendantDialog(self, self.app, self.case_file_id, defendant)
        if dialog.exec():
            self.load()

    def _on_defendant_double(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._defendant_rows):
            defendant = next(
                (d for d in self._case.defendants if d.id == self._defendant_rows[row]), None
            )
            dialog = DefendantDialog(self, self.app, self.case_file_id, defendant)
            if dialog.exec():
                self.load()

    def _build_defendants_section(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(SubtitleLabel("Acusados"))

        row = QHBoxLayout()
        self.add_defendant_btn = PushButton("Agregar acusado")
        self.add_defendant_btn.clicked.connect(self._on_add_defendant)
        self.edit_defendant_btn = PushButton("Editar acusado")
        self.edit_defendant_btn.clicked.connect(self._on_edit_defendant)
        self.del_defendant_btn = PushButton("Eliminar acusado")
        self.del_defendant_btn.clicked.connect(self._on_del_defendant)
        row.addWidget(self.add_defendant_btn)
        row.addWidget(self.edit_defendant_btn)
        row.addWidget(self.del_defendant_btn)
        vbox.addLayout(row)

        from PyQt5.QtWidgets import QAbstractItemView, QHeaderView

        self.defendants_table = TableWidget()
        self.defendants_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.defendants_table.setColumnCount(10)
        self.defendants_table.setHorizontalHeaderLabels(
            ["ID", "Nombre", "Cédula", "Fecha Nac.", "Edad", "Veredicto", "Fecha aprehensión", "Dirección", "Teléfono", "Notas"]
        )
        self.defendants_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.defendants_table.cellDoubleClicked.connect(self._on_defendant_double)
        vbox.addWidget(self.defendants_table, 1)
        return container

    def _on_del_defendant(self) -> None:
        defendant_id = self._selected_defendant_id()
        if defendant_id is None:
            show_error(self, "Seleccione un acusado de la tabla.")
            return
        if not confirm_delete(self, "¿Eliminar este acusado?"):
            return
        try:
            ok = self.app.service.delete_defendant(defendant_id)
        except ValueError as exc:
            logger.exception("Error al eliminar acusado %s", defendant_id)
            show_error(self, f"Error al eliminar: {exc}")
            return
        if ok:
            show_info(self, "Acusado eliminado.")
            self.load()
        else:
            show_error(self, "El acusado no existe.")
