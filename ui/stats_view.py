"""Vista de estadísticas y reportes."""

from __future__ import annotations

import logging

from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
    TableWidget,
    TitleLabel,
)

from db import StatisticsSummary

from ui.dialogs import pick_save_pdf
from ui.exporters import export_statistics_csv, export_statistics_pdf
from ui.widgets import show_error, show_info

logger = logging.getLogger("guilliman")


class _StatCard(CardWidget):
    """Tarjeta con un número grande y una etiqueta."""

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


class StatisticsView(QWidget):
    """Resumen estadístico con exportación a PDF y CSV."""

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self._summary: StatisticsSummary | None = None
        self.setObjectName("stats")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)
        layout.addWidget(TitleLabel("Estadísticas"))

        cards = QHBoxLayout()
        self.total_card = _StatCard("Expedientes totales")
        self.active_card = _StatCard("Expedientes activos")
        self.archived_card = _StatCard("Expedientes archivados")
        for card in (self.total_card, self.active_card, self.archived_card):
            cards.addWidget(card, 1)
        layout.addLayout(cards)

        actions = QHBoxLayout()
        self.refresh_btn = PrimaryPushButton("Actualizar")
        self.refresh_btn.clicked.connect(self.refresh)
        self.pdf_btn = PushButton("Exportar PDF")
        self.pdf_btn.clicked.connect(self._on_export_pdf)
        self.csv_btn = PushButton("Exportar CSV")
        self.csv_btn.clicked.connect(self._on_export_csv)
        actions.addWidget(self.refresh_btn)
        actions.addWidget(self.pdf_btn)
        actions.addWidget(self.csv_btn)
        actions.addStretch(1)
        layout.addLayout(actions)

        tables = QHBoxLayout()
        tables.addLayout(self._table_block("Expedientes por tipo de delito", "crimes"))
        tables.addLayout(self._table_block("Expedientes por fiscalía (top 10)", "prosecutors"))
        layout.addLayout(tables)

        layout.addLayout(self._table_block("Audiencias por mes (últimos 12)", "months", 1))

    def _table_block(self, title: str, attr: str, stretch: int = 0) -> QVBoxLayout:
        block = QVBoxLayout()
        block.addWidget(SubtitleLabel(title))
        table = TableWidget()
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Categoría", "Cantidad"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setMinimumHeight(160)
        setattr(self, f"{attr}_table", table)
        block.addWidget(table, stretch or 1)
        return block

    @staticmethod
    def _fill_table(table: TableWidget, items) -> None:
        table.setRowCount(len(items))
        for row, item in enumerate(items):
            table.setItem(row, 0, QTableWidgetItem(item.label))
            cell = QTableWidgetItem(str(item.count))
            table.setItem(row, 1, cell)

    def refresh(self) -> None:
        """Recarga el resumen estadístico desde el servicio."""
        try:
            summary = self.app.service.get_statistics()
        except ValueError as exc:
            logger.exception("Error al cargar estadísticas")
            show_error(self, f"Error al cargar estadísticas: {exc}")
            return
        self._summary = summary
        self.total_card.set_value(summary.total_cases)
        self.active_card.set_value(summary.active_cases)
        self.archived_card.set_value(summary.archived_cases)
        self._fill_table(self.crimes_table, summary.cases_by_crime_type)
        self._fill_table(self.prosecutors_table, summary.cases_by_prosecutor)
        self._fill_table(self.months_table, summary.hearings_by_month)

    def _ensure_summary(self) -> StatisticsSummary | None:
        if self._summary is None:
            self.refresh()
        return self._summary

    def _on_export_pdf(self) -> None:
        summary = self._ensure_summary()
        if summary is None:
            return
        path = pick_save_pdf(self, "estadisticas.pdf")
        if not path:
            return
        try:
            export_statistics_pdf(summary, path)
        except Exception as exc:  # noqa: BLE001 - se informa al usuario
            logger.exception("Error al exportar estadísticas a PDF")
            show_error(self, f"Error al exportar: {exc}")
            return
        show_info(self, "Estadísticas exportadas a PDF.")

    def _on_export_csv(self) -> None:
        summary = self._ensure_summary()
        if summary is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar estadísticas CSV",
            "estadisticas.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        try:
            export_statistics_csv(summary, path)
        except Exception as exc:  # noqa: BLE001 - se informa al usuario
            logger.exception("Error al exportar estadísticas a CSV")
            show_error(self, f"Error al exportar: {exc}")
            return
        show_info(self, "Estadísticas exportadas a CSV.")
