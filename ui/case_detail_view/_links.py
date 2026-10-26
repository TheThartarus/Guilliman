"""Sección de causas conexas del detalle de expediente."""

from __future__ import annotations

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from qfluentwidgets import PushButton, SubtitleLabel, TableWidget

from db import CaseFileRead

from ui.dialogs import confirm_delete
from ui.widgets import show_error, show_info

logger = logging.getLogger("guilliman")


class _LinksSection:
    """Métodos de la sección de expedientes vinculados."""

    def _selected_link(self):
        row = self.links_table.currentRow()
        if 0 <= row < len(self._links):
            return self._links[row]
        return None

    def _fill_links(self, _case: CaseFileRead) -> None:
        self._links = self.app.service.list_linked_cases(self.case_file_id)
        self.links_table.setRowCount(len(self._links))
        for row, item in enumerate(self._links):
            self.links_table.setItem(row, 0, QTableWidgetItem(item.case_number))

    def _on_link_case(self) -> None:
        number, accepted = QInputDialog.getText(
            self, "Vincular expediente", "Número de expediente:"
        )
        if not accepted:
            return
        try:
            self.app.service.link_cases(self.case_file_id, number)
        except ValueError as exc:
            logger.exception("Error al vincular expediente %s", self.case_file_id)
            show_error(self, str(exc))
            return
        show_info(self, "Expediente vinculado.")
        self.load()

    def _on_open_link(self) -> None:
        item = self._selected_link()
        if item is None:
            show_error(self, "Seleccione un expediente de la tabla.")
            return
        self.app.shell.open_case_detail(item.case_file_id)

    def _on_unlink_case(self) -> None:
        item = self._selected_link()
        if item is None:
            show_error(self, "Seleccione un expediente de la tabla.")
            return
        if not confirm_delete(self, f"¿Quitar el vínculo con {item.case_number}?"):
            return
        try:
            ok = self.app.service.unlink_case(item.link_id)
        except ValueError as exc:
            logger.exception("Error al quitar vínculo %s", item.link_id)
            show_error(self, str(exc))
            return
        if ok:
            show_info(self, "Vínculo eliminado.")
            self.load()
        else:
            show_error(self, "El vínculo no existe.")

    def _on_link_double(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._links):
            self.links_table.selectRow(row)
            self._on_open_link()

    def _build_links_section(self) -> QWidget:
        self._links = []
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(SubtitleLabel("Causas conexas"))

        row = QHBoxLayout()
        self.link_btn = PushButton("Vincular")
        self.link_btn.clicked.connect(self._on_link_case)
        self.open_link_btn = PushButton("Abrir")
        self.open_link_btn.clicked.connect(self._on_open_link)
        self.unlink_btn = PushButton("Quitar vínculo")
        self.unlink_btn.clicked.connect(self._on_unlink_case)
        row.addWidget(self.link_btn)
        row.addWidget(self.open_link_btn)
        row.addWidget(self.unlink_btn)
        vbox.addLayout(row)

        self.links_table = TableWidget()
        self.links_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.links_table.setColumnCount(1)
        self.links_table.setHorizontalHeaderLabels(["Expediente"])
        self.links_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.links_table.setMinimumHeight(120)
        self.links_table.cellDoubleClicked.connect(self._on_link_double)
        vbox.addWidget(self.links_table)
        return container
