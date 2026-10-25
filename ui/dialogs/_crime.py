"""Alta/edición de un delito imputado en un expediente."""

from __future__ import annotations

import logging

from PyQt5.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QVBoxLayout, QWidget

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

from ._sizes import CRIME_DIALOG_HEIGHT, CRIME_DIALOG_WIDTH

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

        type_box = QWidget()
        type_form = QFormLayout(type_box)
        type_form.addRow(BodyLabel("Tipo de Delito *"), self._type)
        layout.addWidget(type_box)

        self._drug_box = QWidget()
        drug_form = QFormLayout(self._drug_box)
        drug_form.addRow(BodyLabel("Cantidad de Droga"), self._drug_quantity)
        drug_form.addRow(BodyLabel("Tipo de Droga"), self._drug_type)
        layout.addWidget(self._drug_box)

        self._weapon_box = QWidget()
        weapon_form = QFormLayout(self._weapon_box)
        weapon_form.addRow(BodyLabel("Cantidad de Armas"), self._weapon_quantity)
        weapon_form.addRow(BodyLabel("Tipo de Armas"), self._weapon_type)
        layout.addWidget(self._weapon_box)

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
        self._update_visibility()
        self.resize(CRIME_DIALOG_WIDTH, CRIME_DIALOG_HEIGHT)

    def _update_visibility(self) -> None:
        crime_type = combo_current_data(self._type)
        self._drug_box.setVisible(crime_type == "Droga")
        self._weapon_box.setVisible(crime_type == "Armas")
        if crime_type != "Droga":
            self._drug_quantity.setValue(0.0)
            self._drug_type.setCurrentIndex(-1)
        if crime_type != "Armas":
            self._weapon_quantity.setValue(0)
            self._weapon_type.setCurrentIndex(-1)

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
