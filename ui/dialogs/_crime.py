"""Alta/edición de un delito imputado en un expediente."""

from __future__ import annotations

import logging

from PyQt5.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QVBoxLayout

from pydantic import ValidationError
from qfluentwidgets import (
    BodyLabel,
    ComboBox,
    DoubleSpinBox,
    FluentStyleSheet,
    PrimaryPushButton,
    PushButton,
    SpinBox,
    SubtitleLabel,
)

from db import CrimeCreate

from ui.shared import CRIME_TYPE_OPTIONS, DRUG_TYPE_LABELS, WEAPON_TYPE_LABELS
from ui.widgets import combo_current_data, combo_set_data, show_error

from ._sizes import CRIME_DIALOG_WIDTH

logger = logging.getLogger("guilliman")


class CrimeDialog(QDialog):
    """Formulario de un delito; expone ``result_crime`` al aceptar."""

    def __init__(self, parent, crime: CrimeCreate | None = None) -> None:
        super().__init__(parent)
        FluentStyleSheet.DIALOG.apply(self)
        self.result_crime: CrimeCreate | None = None
        self.setWindowTitle("Editar delito" if crime else "Agregar delito")

        self._type = ComboBox()
        for option in CRIME_TYPE_OPTIONS:
            self._type.addItem(option, userData=option)

        self._drug_quantity = DoubleSpinBox()
        self._drug_quantity.setRange(0.0, 999999.99)
        self._drug_quantity.setDecimals(2)
        self._drug_quantity.setSpecialValueText("—")
        self._drug_quantity.setSuffix(" g")
        self._drug_type = ComboBox()
        for value, label in DRUG_TYPE_LABELS.items():
            self._drug_type.addItem(label, userData=value)

        self._weapon_quantity = SpinBox()
        self._weapon_quantity.setRange(0, 99999)
        self._weapon_quantity.setSpecialValueText("—")
        self._weapon_quantity.setSuffix(" armas")
        self._weapon_type = ComboBox()
        for value, label in WEAPON_TYPE_LABELS.items():
            self._weapon_type.addItem(label, userData=value)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(SubtitleLabel(self.windowTitle()))

        form = QFormLayout()
        form.setSpacing(8)
        self._type_label = BodyLabel("Tipo de Delito *")
        form.addRow(self._type_label, self._type)
        self._drug_quantity_label = BodyLabel("Cantidad de Droga")
        form.addRow(self._drug_quantity_label, self._drug_quantity)
        self._drug_type_label = BodyLabel("Tipo de Droga")
        form.addRow(self._drug_type_label, self._drug_type)
        self._weapon_quantity_label = BodyLabel("Cantidad de Armas")
        form.addRow(self._weapon_quantity_label, self._weapon_quantity)
        self._weapon_type_label = BodyLabel("Tipo de Armas")
        form.addRow(self._weapon_type_label, self._weapon_type)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        self.save_btn = PrimaryPushButton("Guardar")
        self.save_btn.clicked.connect(self._on_accept)
        self.cancel_btn = PushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.cancel_btn)
        layout.addLayout(buttons)

        if crime is not None:
            combo_set_data(self._type, crime.crime_type)
            if crime.drug_quantity is not None:
                self._drug_quantity.setValue(crime.drug_quantity)
            if crime.drug_type:
                combo_set_data(self._drug_type, crime.drug_type)
            if crime.weapon_quantity is not None:
                self._weapon_quantity.setValue(crime.weapon_quantity)
            if crime.weapon_type:
                combo_set_data(self._weapon_type, crime.weapon_type)

        self._type.currentIndexChanged.connect(self._update_visibility)
        self.setMinimumWidth(CRIME_DIALOG_WIDTH)
        self._update_visibility()

    def _update_visibility(self) -> None:
        crime_type = combo_current_data(self._type)
        is_drug = crime_type == "Droga"
        is_weapon = crime_type == "Armas"
        for label, widget in (
            (self._drug_quantity_label, self._drug_quantity),
            (self._drug_type_label, self._drug_type),
        ):
            label.setVisible(is_drug)
            widget.setVisible(is_drug)
        for label, widget in (
            (self._weapon_quantity_label, self._weapon_quantity),
            (self._weapon_type_label, self._weapon_type),
        ):
            label.setVisible(is_weapon)
            widget.setVisible(is_weapon)
        if not is_drug:
            self._drug_quantity.setValue(0.0)
            self._drug_type.setCurrentIndex(-1)
        if not is_weapon:
            self._weapon_quantity.setValue(0)
            self._weapon_type.setCurrentIndex(-1)
        self.adjustSize()

    def _build_crime(self) -> CrimeCreate:
        crime_type = combo_current_data(self._type)
        data: dict = {"crime_type": crime_type}
        if crime_type == "Droga":
            quantity = self._drug_quantity.value()
            data["drug_quantity"] = quantity if quantity > 0 else None
            data["drug_type"] = combo_current_data(self._drug_type)
        if crime_type == "Armas":
            quantity = self._weapon_quantity.value()
            data["weapon_quantity"] = quantity if quantity > 0 else None
            data["weapon_type"] = combo_current_data(self._weapon_type)
        return CrimeCreate(**data)

    def _on_accept(self) -> None:
        try:
            self.result_crime = self._build_crime()
        except ValidationError:
            logger.exception("Datos inválidos al guardar un delito")
            show_error(self, "Revise los datos del delito.")
            return
        self.accept()
