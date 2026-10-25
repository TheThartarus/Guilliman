"""Listado de alertas por plazo de detención."""

from __future__ import annotations

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QTableWidgetItem,
    QVBoxLayout,
)

from qfluentwidgets import (
    FluentStyleSheet,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
    TableWidget,
)

from ui.shared import format_date
from ui.widgets import show_error

from ._sizes import DETENTION_DIALOG_HEIGHT, DETENTION_DIALOG_WIDTH

logger = logging.getLogger("guilliman")


class DetentionAlertsDialog(QDialog):
    """Acusados detenidos que alcanzan o superan el umbral configurado."""

    def __init__(self, parent, app, threshold_days: int) -> None:
        super().__init__(parent)
        FluentStyleSheet.DIALOG.apply(self)
        self.app = app
        self.threshold_days = threshold_days
        self.selected_case_id: int | None = None
        self._items: list = []
        self.setWindowTitle("Alertas de detención")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(
            SubtitleLabel(f"Detenidos hace {threshold_days} días o más")
        )

        self.table = TableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setBorderVisible(True)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Expediente", "Acusado", "Fecha aprehensión", "Días detenido"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellDoubleClicked.connect(self._on_open_selected)
        layout.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        self.open_btn = PrimaryPushButton("Abrir expediente")
        self.open_btn.clicked.connect(self._on_open_selected)
        self.close_btn = PushButton("Cerrar")
        self.close_btn.clicked.connect(self.reject)
        buttons.addWidget(self.open_btn)
        buttons.addWidget(self.close_btn)
        layout.addLayout(buttons)

        self.resize(DETENTION_DIALOG_WIDTH, DETENTION_DIALOG_HEIGHT)
        self._load()

    def _load(self) -> None:
        try:
            self._items = self.app.service.list_detention_alerts(self.threshold_days)
        except ValueError as exc:
            logger.exception("Error al cargar alertas de detención")
            show_error(self, f"Error al cargar alertas: {exc}")
            return

        self.table.setRowCount(len(self._items))
        for row, item in enumerate(self._items):
            self.table.setItem(row, 0, QTableWidgetItem(item.case_number))
            self.table.setItem(row, 1, QTableWidgetItem(item.full_name))
            self.table.setItem(
                row, 2, QTableWidgetItem(format_date(item.arrest_date))
            )
            days = QTableWidgetItem(str(item.days_detained))
            days.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, days)

    def _on_open_selected(self, *_args) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self._items):
            self.selected_case_id = self._items[row].case_file_id
            self.accept()
