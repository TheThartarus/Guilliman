"""
Guilliman Frontend - Localización de los DatePicker de qfluentwidgets al español.

qfluentwidgets no incluye una traducción al español de los nombres de mes en el
selector por columnas (usa internamente ``self.tr('January')`` y no distribuye
un catálogo ``*.qm`` para español), así que inyectamos un formateador de meses en
español y fijamos el ``QLocale`` para el popup de calendario.
"""

from __future__ import annotations

from PyQt5.QtCore import QLocale

from qfluentwidgets import PickerColumnFormatter


class SpanishMonthFormatter(PickerColumnFormatter):
    """Formateador de meses en español para las columnas del DatePicker."""

    def __init__(self) -> None:
        super().__init__()
        self.months = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
        ]

    def encode(self, month):
        return self.months[int(month) - 1]

    def decode(self, value):
        return self.months.index(value) + 1


def apply_spanish_date_picker(picker) -> None:
    """Localiza un ``DatePicker`` al español (columnas de mes + popup calendario)."""
    picker.setMonthFormatter(SpanishMonthFormatter())
    picker.setDateFormat(picker.dateFormat)
    picker.setLocale(QLocale(QLocale.Spanish, QLocale.Spain))
