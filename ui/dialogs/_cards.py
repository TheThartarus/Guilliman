"""Tarjetas Fluent de fecha usadas por los formularios de diálogo."""

from __future__ import annotations

from datetime import date, datetime

from PyQt5.QtCore import QDate, QTime

from qfluentwidgets import (
    DatePicker,
    FluentIcon,
    SettingCard,
    SwitchButton,
    TimePicker,
)

from ui.date_pickers import apply_spanish_date_picker


class _DateCard(SettingCard):
    """Fecha opcional: tarjeta Fluent con SwitchButton + DatePicker.

    El ``SwitchButton`` indica si la fecha es conocida; apagado = NULL.
    Replica el patrón de ``ui.case_form_view._DateCard`` para coherencia visual.
    """

    def __init__(self, label: str, parent=None, enabled: bool = True) -> None:
        super().__init__(FluentIcon.CALENDAR, label, parent=parent)
        self._switch = SwitchButton()
        self._switch.setChecked(False)
        self._picker = DatePicker()
        self._picker.setDate(QDate.currentDate())
        apply_spanish_date_picker(self._picker)
        self._picker.setEnabled(False)
        self._switch.checkedChanged.connect(self._picker.setEnabled)
        if not enabled:
            self._switch.setEnabled(False)
            self._picker.setEnabled(False)
            self.setToolTip("Aún no disponible en el sistema")
        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self._switch)
        self.hBoxLayout.addSpacing(16)
        self.hBoxLayout.addWidget(self._picker)
        self.hBoxLayout.addSpacing(16)

    @property
    def check(self) -> SwitchButton:
        return self._switch

    @property
    def edit(self):
        return self._picker

    def get(self) -> date | None:
        if not self._switch.isChecked():
            return None
        return self._picker.getDate().toPyDate()

    def set(self, value: date | None) -> None:
        if value is None:
            self._switch.setChecked(False)
            self._picker.setDate(QDate.currentDate())
        else:
            self._switch.setChecked(True)
            self._picker.setDate(QDate(value.year, value.month, value.day))


class _DateTimeCard(SettingCard):
    """Fecha/hora obligatoria: tarjeta Fluent con DatePicker + TimePicker.

    La audiencia requiere fecha y hora, por eso no lleva SwitchButton.
    """

    def __init__(self, label: str, parent=None) -> None:
        super().__init__(FluentIcon.CALENDAR, label, parent=parent)
        self._date = DatePicker()
        self._date.setDate(QDate.currentDate())
        apply_spanish_date_picker(self._date)
        self._time = TimePicker()
        self._time.setTime(QTime.currentTime())
        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self._date)
        self.hBoxLayout.addSpacing(16)
        self.hBoxLayout.addWidget(self._time)
        self.hBoxLayout.addSpacing(16)

    def get(self) -> datetime:
        d = self._date.getDate().toPyDate()
        t = self._time.getTime()
        return datetime(d.year, d.month, d.day, t.hour(), t.minute())

    def set(self, value: datetime) -> None:
        self._date.setDate(QDate(value.year, value.month, value.day))
        self._time.setTime(QTime(value.hour, value.minute))


class _FlaggedDateCard(SettingCard):
    """Tarjeta con SwitchButton (estado booleano) + DatePicker (fecha asociada).

    Cuando el SwitchButton está apagado, la fecha se fuerza a ``None``: la UI
    decide no persistir la fecha si el estado no aplica. Replica el patrón de
    ``_DateCard`` pero separa el flag del valor de fecha.
    """

    def __init__(self, switch_label: str, parent=None) -> None:
        super().__init__(FluentIcon.CALENDAR, switch_label, parent=parent)
        self._switch = SwitchButton()
        self._switch.setChecked(False)
        self._picker = DatePicker()
        self._picker.setDate(QDate.currentDate())
        apply_spanish_date_picker(self._picker)
        self._picker.setEnabled(False)
        self._switch.checkedChanged.connect(self._picker.setEnabled)
        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self._switch)
        self.hBoxLayout.addSpacing(16)
        self.hBoxLayout.addWidget(self._picker)
        self.hBoxLayout.addSpacing(16)

    def get(self) -> tuple[bool, date | None]:
        if not self._switch.isChecked():
            return False, None
        return True, self._picker.getDate().toPyDate()

    def set(self, flag: bool, value: date | None) -> None:
        self._switch.setChecked(bool(flag))
        if value is None:
            self._picker.setDate(QDate.currentDate())
        else:
            self._picker.setDate(QDate(value.year, value.month, value.day))
