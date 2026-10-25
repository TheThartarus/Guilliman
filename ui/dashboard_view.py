"""Vista de inicio: resumen de pendientes y próximas audiencias."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    SubtitleLabel,
    TableWidget,
    TitleLabel,
)

from ui.shared import (
    HEARING_STATUS_LABELS,
    HEARING_TYPE_LABELS,
    format_datetime,
    translate,
)
from ui.widgets import show_error

logger = logging.getLogger("guilliman")


class _StatCard(CardWidget):
    """Tarjeta simple con un número grande y una etiqueta."""

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(2)
        self._value = TitleLabel("—")
        layout.addWidget(self._value)
        layout.addWidget(BodyLabel(label))

    def set_value(self, value: int) -> None:
        self._value.setText(str(value))


class DashboardView(QWidget):
    """Resumen operativo: contadores y audiencias de los próximos 7 días."""

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self._items: list = []
        self.setObjectName("dashboard")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)
        layout.addWidget(TitleLabel("Inicio"))

        cards = QHBoxLayout()
        self.cases_card = _StatCard("Expedientes")
        self.week_card = _StatCard("Audiencias próximas (7 días)")
        self.no_audio_card = _StatCard("Audiencias sin audio")
        self.no_acta_card = _StatCard("Audiencias sin acta")
        for card in (
            self.cases_card,
            self.week_card,
            self.no_audio_card,
            self.no_acta_card,
        ):
            cards.addWidget(card, 1)
        layout.addLayout(cards)

        layout.addWidget(SubtitleLabel("Próximas audiencias (7 días)"))

        self.table = TableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setBorderVisible(True)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Fecha/Hora", "Expediente", "Tipo", "Estado", "Acta", "Audio"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellDoubleClicked.connect(self._on_row_double)
        layout.addWidget(self.table, 1)

    def refresh(self) -> None:
        """Recarga contadores y próximas audiencias."""
        now = datetime.now()
        try:
            total_cases = self.app.service.count_case_files()
            upcoming = self.app.service.list_scheduled_hearings(
                now, now + timedelta(days=7), status="Scheduled"
            )
            missing_audio = self.app.service.count_hearings_missing_audio()
            missing_acta = self.app.service.count_hearings_missing_transcription()
        except ValueError as exc:
            logger.exception("Error al cargar el dashboard")
            show_error(self, f"Error al cargar el inicio: {exc}")
            return

        self.cases_card.set_value(total_cases)
        self.week_card.set_value(len(upcoming))
        self.no_audio_card.set_value(missing_audio)
        self.no_acta_card.set_value(missing_acta)

        self._items = upcoming
        self.table.setRowCount(len(upcoming))
        for row, item in enumerate(upcoming):
            self.table.setItem(
                row, 0, QTableWidgetItem(format_datetime(item.scheduled_at))
            )
            self.table.setItem(row, 1, QTableWidgetItem(item.case_number or ""))
            self.table.setItem(
                row, 2, QTableWidgetItem(translate(item.hearing_type, HEARING_TYPE_LABELS))
            )
            self.table.setItem(
                row, 3, QTableWidgetItem(translate(item.status, HEARING_STATUS_LABELS))
            )
            self.table.setItem(
                row, 4, QTableWidgetItem("Sí" if item.has_transcription else "—")
            )
            self.table.setItem(
                row, 5, QTableWidgetItem("Sí" if item.has_audio else "—")
            )

    def _on_row_double(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._items):
            self.app.shell.open_case_detail(self._items[row].case_file_id)
