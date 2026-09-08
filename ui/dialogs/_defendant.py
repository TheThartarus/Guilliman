"""Formulario de alta/edición de un acusado de un expediente."""

from __future__ import annotations

import logging
from datetime import date

from PyQt5.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QVBoxLayout

from qfluentwidgets import (
    BodyLabel,
    ComboBox,
    FluentStyleSheet,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    SettingCardGroup,
    SubtitleLabel,
    TextEdit,
)

from db import DefendantCreate
from pydantic import ValidationError

from ui.shared import (
    DEFENDANT_STATUS_LABELS,
    DEFENDANT_STATUS_OPTIONS,
    VERDICT_STATUS_LABELS,
    field_errors,
)
from ui.widgets import (
    combo_current_data,
    combo_set_data,
    make_uppercase,
    restrict_input,
    show_error,
    show_info,
)

from ._cards import _DateCard
from ._sizes import DEFENDANT_DIALOG_HEIGHT, DEFENDANT_DIALOG_WIDTH

logger = logging.getLogger("guilliman")


class DefendantDialog(QDialog):
    """Alta/edición de un acusado de un expediente."""

    def __init__(self, parent, app, case_file_id: int, defendant=None) -> None:
        super().__init__(parent)
        FluentStyleSheet.DIALOG.apply(self)
        self.app = app
        self.case_file_id = case_file_id
        self.defendant = defendant
        self.setWindowTitle("Editar acusado" if defendant else "Agregar acusado")
        self._fields: dict = {}

        self._full_name = LineEdit()
        self._full_name.setPlaceholderText("Nombre completo *")
        restrict_input(self._full_name, "letters")
        self._fields["full_name"] = self._full_name

        self._national_id = LineEdit()
        self._national_id.setPlaceholderText("Cédula")
        restrict_input(self._national_id, "digits")
        self._fields["national_id"] = self._national_id

        self._birth_date_card = _DateCard("Fecha de Nacimiento")
        self._fields["birth_date"] = self._birth_date_card

        self._arrest_card = _DateCard("Fecha de Aprehensión")
        self._presentation_card = _DateCard("Fecha de Presentación")
        self._fields["presentation_hearing_date"] = self._presentation_card

        self._notes = TextEdit()
        self._notes.setPlaceholderText("Notas")
        make_uppercase(self._notes)
        self._fields["additional_notes"] = self._notes

        self._address = LineEdit()
        self._address.setPlaceholderText("Dirección")
        restrict_input(self._address, "address")
        self._fields["address"] = self._address

        self._phone = LineEdit()
        self._phone.setPlaceholderText("Teléfono")
        restrict_input(self._phone, "phone")
        self._fields["phone"] = self._phone

        self._status = ComboBox()
        for opt in DEFENDANT_STATUS_OPTIONS:
            self._status.addItem(DEFENDANT_STATUS_LABELS.get(opt, opt), userData=opt)
        self._fields["status"] = self._status

        self._verdict_status = ComboBox()
        for value, label in VERDICT_STATUS_LABELS.items():
            self._verdict_status.addItem(label, userData=value)
        combo_set_data(self._verdict_status, "Pending")
        self._fields["verdict_status"] = self._verdict_status

        self._arresting_agency = LineEdit()
        self._arresting_agency.setPlaceholderText("Organismo Aprehensor")
        restrict_input(self._arresting_agency, "agency")
        self._fields["arresting_agency"] = self._arresting_agency

        if defendant is not None:
            self._full_name.setText(defendant.full_name or "")
            self._national_id.setText(defendant.national_id or "")
            self._birth_date_card.set(defendant.birth_date)
            self._arrest_card.set(defendant.arrest_date)
            self._presentation_card.set(defendant.presentation_hearing_date)
            self._address.setText(defendant.address or "")
            self._phone.setText(defendant.phone or "")
            self._notes.setPlainText(defendant.additional_notes or "")
            if defendant.status:
                combo_set_data(self._status, defendant.status)
            if defendant.verdict_status:
                combo_set_data(self._verdict_status, defendant.verdict_status)
            self._arresting_agency.setText(defendant.arresting_agency or "")

        self._build_buttons()
        self.resize(DEFENDANT_DIALOG_WIDTH, DEFENDANT_DIALOG_HEIGHT)

    def _build_buttons(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(SubtitleLabel(self.windowTitle()))
        form = QFormLayout()
        form.setSpacing(8)
        form.addRow(BodyLabel("Nombre *"), self._full_name)
        form.addRow(BodyLabel("Cédula"), self._national_id)
        form.addRow(BodyLabel("Dirección"), self._address)
        form.addRow(BodyLabel("Teléfono"), self._phone)
        form.addRow(BodyLabel("Estado"), self._status)
        form.addRow(BodyLabel("Veredicto"), self._verdict_status)
        form.addRow(BodyLabel("Organismo Aprehensor"), self._arresting_agency)
        form.addRow(BodyLabel("Notas"), self._notes)
        layout.addLayout(form)

        dates_group = SettingCardGroup("Fechas", self)
        dates_group.addSettingCard(self._birth_date_card)
        dates_group.addSettingCard(self._arrest_card)
        dates_group.addSettingCard(self._presentation_card)
        layout.addWidget(dates_group)

        buttons = QHBoxLayout()
        self.save_btn = PrimaryPushButton("Guardar")
        self.save_btn.clicked.connect(self._on_save)
        self.cancel_btn = PushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.cancel_btn)
        layout.addLayout(buttons)

    @staticmethod
    def _clean(value: str) -> str | None:
        value = (value or "").strip().upper()
        return value if value else None

    def _collect(self) -> dict:
        return {
            "full_name": (self._full_name.text() or "").strip().upper(),
            "national_id": self._clean(self._national_id.text()),
            "birth_date": self._birth_date_card.get(),
            "arrest_date": self._arrest_card.get(),
            "presentation_hearing_date": self._presentation_card.get(),
            "status": combo_current_data(self._status),
            "verdict_status": combo_current_data(self._verdict_status) or "Pending",
            "arresting_agency": self._clean(self._arresting_agency.text()),
            "address": self._clean(self._address.text()),
            "phone": (self._phone.text() or "").strip() or None,
            "additional_notes": self._clean(self._notes.toPlainText()),
        }

    def _mark_errors(self, errors: dict[str, str]) -> None:
        for key, message in errors.items():
            field = self._fields.get(key)
            if field is None:
                continue
            if hasattr(field, "setError"):
                field.setError(message)
            elif hasattr(field, "setToolTip"):
                field.setToolTip(message)

    def _on_save(self) -> None:
        kwargs = self._collect()
        try:
            payload = DefendantCreate(**kwargs)
        except ValidationError as exc:
            logger.exception("Error de validación al guardar acusado")
            self._mark_errors(field_errors(exc))
            show_error(self, "Revise los campos marcados.")
            return

        try:
            if self.defendant is None:
                self.app.service.add_defendant(self.case_file_id, payload)
                show_info(self, "Acusado agregado.")
            else:
                ok = self.app.service.update_defendant(
                    self.case_file_id, self.defendant.id, payload
                )
                if not ok:
                    show_error(self, "El acusado no existe o no pertenece al expediente.")
                    return
                show_info(self, "Acusado actualizado.")
        except ValueError as exc:
            logger.exception("Error al guardar acusado")
            show_error(self, f"Error al guardar: {exc}")
            return
        self.accept()
