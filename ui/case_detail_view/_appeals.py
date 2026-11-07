"""Sección de apelaciones del detalle de expediente."""

from __future__ import annotations

import logging

from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from qfluentwidgets import PushButton, SubtitleLabel, TableWidget

from db import AppealCreate, AppealRead, CaseFileRead

from ui.dialogs import AppealDialog, confirm_delete
from ui.shared import format_date
from ui.widgets import show_error, show_info

logger = logging.getLogger("guilliman")


class _AppealsSection:
    """Métodos de la sección de apelaciones del ``CaseDetailView``."""

    def _selected_appeal(self) -> AppealRead | None:
        row = self.appeals_table.currentRow()
        if 0 <= row < len(self._appeals):
            return self._appeals[row]
        return None

    def _fill_appeals(self, case: CaseFileRead) -> None:
        self._appeals = list(case.appeals)
        self.appeals_table.setRowCount(len(self._appeals))
        for row, appeal in enumerate(self._appeals):
            values = (
                str(appeal.id),
                format_date(appeal.filed_at),
                format_date(appeal.remitted_to_court_at),
                format_date(appeal.returned_from_court_at),
                appeal.court_decision or "—",
                appeal.classification or "—",
            )
            for col, value in enumerate(values):
                self.appeals_table.setItem(row, col, QTableWidgetItem(value))

    def _on_add_appeal(self) -> None:
        dialog = AppealDialog(self)
        if dialog.exec() != QDialog.Accepted or dialog.result_appeal is None:
            return
        try:
            self.app.service.add_appeal(self.case_file_id, dialog.result_appeal)
        except ValueError as exc:
            logger.exception("Error al agregar apelación al caso %s", self.case_file_id)
            show_error(self, str(exc))
            return
        show_info(self, "Apelación agregada.")
        self.load()

    def _on_edit_appeal(self) -> None:
        appeal = self._selected_appeal()
        if appeal is None:
            show_error(self, "Seleccione una apelación de la tabla.")
            return
        current = AppealCreate(
            filed_at=appeal.filed_at,
            remitted_to_court_at=appeal.remitted_to_court_at,
            returned_from_court_at=appeal.returned_from_court_at,
            court_decision=appeal.court_decision,
            classification=appeal.classification,
        )
        dialog = AppealDialog(self, current)
        if dialog.exec() != QDialog.Accepted or dialog.result_appeal is None:
            return
        try:
            ok = self.app.service.update_appeal(
                self.case_file_id, appeal.id, dialog.result_appeal
            )
        except ValueError as exc:
            logger.exception("Error al editar apelación %s", appeal.id)
            show_error(self, str(exc))
            return
        if ok:
            show_info(self, "Apelación actualizada.")
            self.load()
        else:
            show_error(self, "La apelación no existe o no pertenece a este expediente.")

    def _on_delete_appeal(self) -> None:
        appeal = self._selected_appeal()
        if appeal is None:
            show_error(self, "Seleccione una apelación de la tabla.")
            return
        if not confirm_delete(self, f"¿Eliminar la apelación {appeal.id}?"):
            return
        try:
            ok = self.app.service.delete_appeal(appeal.id)
        except ValueError as exc:
            logger.exception("Error al eliminar apelación %s", appeal.id)
            show_error(self, str(exc))
            return
        if ok:
            show_info(self, "Apelación eliminada.")
            self.load()
        else:
            show_error(self, "La apelación no existe.")

    def _build_appeals_section(self) -> QWidget:
        self._appeals: list[AppealRead] = []
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(SubtitleLabel("Apelaciones"))

        row = QHBoxLayout()
        self.add_appeal_btn = PushButton("Agregar")
        self.add_appeal_btn.clicked.connect(self._on_add_appeal)
        self.edit_appeal_btn = PushButton("Editar")
        self.edit_appeal_btn.clicked.connect(self._on_edit_appeal)
        self.delete_appeal_btn = PushButton("Eliminar")
        self.delete_appeal_btn.clicked.connect(self._on_delete_appeal)
        row.addWidget(self.add_appeal_btn)
        row.addWidget(self.edit_appeal_btn)
        row.addWidget(self.delete_appeal_btn)
        vbox.addLayout(row)

        self.appeals_table = TableWidget()
        self.appeals_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.appeals_table.setColumnCount(6)
        self.appeals_table.setHorizontalHeaderLabels(
            [
                "ID",
                "Presentada",
                "Remisión a Corte",
                "Regreso de Corte",
                "Decisión",
                "Clasificación",
            ]
        )
        self.appeals_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.appeals_table.setMinimumHeight(120)
        vbox.addWidget(self.appeals_table, 1)
        return container
