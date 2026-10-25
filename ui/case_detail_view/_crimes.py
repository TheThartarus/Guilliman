"""Sección de delitos del detalle de expediente (solo lectura)."""

from __future__ import annotations

from PyQt5.QtWidgets import QTableWidgetItem, QVBoxLayout, QWidget

from qfluentwidgets import SubtitleLabel, TableWidget

from db import CaseFileRead


class _CrimesSection:
    """Métodos de la sección de delitos del ``CaseDetailView``."""

    def _fill_crimes(self, case: CaseFileRead) -> None:
        rows = [
            (
                crime.crime_type,
                crime.drug_type,
                crime.drug_quantity,
                crime.weapon_type,
                crime.weapon_quantity,
            )
            for crime in case.crimes
        ]

        self.crimes_table.setRowCount(len(rows))
        for row, (crime_type, drug_type, drug_qty, weapon_type, weapon_qty) in enumerate(rows):
            self.crimes_table.setItem(row, 0, QTableWidgetItem(crime_type or "—"))
            self.crimes_table.setItem(row, 1, QTableWidgetItem(drug_type or "—"))
            self.crimes_table.setItem(
                row, 2, QTableWidgetItem(f"{drug_qty:g} g" if drug_qty is not None else "—")
            )
            self.crimes_table.setItem(row, 3, QTableWidgetItem(weapon_type or "—"))
            self.crimes_table.setItem(
                row,
                4,
                QTableWidgetItem(str(weapon_qty) if weapon_qty is not None else "—"),
            )

    def _build_crimes_section(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(SubtitleLabel("Delitos"))

        from PyQt5.QtWidgets import QAbstractItemView, QHeaderView

        self.crimes_table = TableWidget()
        self.crimes_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.crimes_table.setColumnCount(5)
        self.crimes_table.setHorizontalHeaderLabels(
            ["Tipo", "Droga", "Cantidad", "Arma", "Cantidad"]
        )
        self.crimes_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.crimes_table.setMinimumHeight(110)
        vbox.addWidget(self.crimes_table, 1)
        return container
