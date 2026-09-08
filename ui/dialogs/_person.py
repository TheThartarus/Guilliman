"""Formularios de alta/edición de Víctima y Testigo (comparten la misma forma)."""

from __future__ import annotations

import logging

from PyQt5.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QVBoxLayout

from qfluentwidgets import (
    BodyLabel,
    FluentStyleSheet,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    SettingCardGroup,
    SubtitleLabel,
    TextEdit,
)

from db import VictimCreate, WitnessCreate
from pydantic import ValidationError

from ui.shared import field_errors
from ui.widgets import (
    make_uppercase,
    restrict_input,
    show_error,
    show_info,
)

from ._cards import _DateCard, _FlaggedDateCard
from ._sizes import (
    DEFENDANT_DIALOG_WIDTH,
    VICTIM_DIALOG_HEIGHT,
    VICTIM_DIALOG_WIDTH,
    WITNESS_DIALOG_HEIGHT,
    WITNESS_DIALOG_WIDTH,
)

logger = logging.getLogger("guilliman")


class _PersonDialog(QDialog):
    """Alta/edición de Víctima o Testigo (comparten la misma forma de campos).

    Las subclases fijan ``create_dto``, ``entity_label`` y los nombres de los
    métodos del servicio a invocar (``add_method_name`` / ``update_method_name``).
    El borrado se delega a la vista de detalle porque necesita confirmación y
    recarga, igual que con los acusados.
    """

    # Fijados por las subclases.
    create_dto: type
    entity_label: str
    add_method_name: str
    update_method_name: str
    show_birth_date: bool = True
    dialog_width: int = DEFENDANT_DIALOG_WIDTH
    dialog_height: int = VICTIM_DIALOG_HEIGHT

    def __init__(self, parent, app, case_file_id: int, person=None) -> None:
        super().__init__(parent)
        FluentStyleSheet.DIALOG.apply(self)
        self.app = app
        self.case_file_id = case_file_id
        self.person = person
        self.person_id = person.id if person is not None else None
        self.setWindowTitle(
            f"Editar {self.entity_label.lower()}"
            if person is not None
            else f"Agregar {self.entity_label.lower()}"
        )
        self._fields: dict = {}

        self._full_name = LineEdit()
        self._full_name.setPlaceholderText("Nombre completo *")
        restrict_input(self._full_name, "letters")
        self._fields["full_name"] = self._full_name

        self._national_id = LineEdit()
        self._national_id.setPlaceholderText("Cédula")
        restrict_input(self._national_id, "digits")
        self._fields["national_id"] = self._national_id

        self._birth_date_card = None
        if self.show_birth_date:
            self._birth_date_card = _DateCard("Fecha de Nacimiento")
            self._fields["birth_date"] = self._birth_date_card

        self._appeared_card = _FlaggedDateCard("Fecha de Comparecencia")
        self._fields["appeared"] = self._appeared_card

        self._address = LineEdit()
        self._address.setPlaceholderText("Dirección")
        restrict_input(self._address, "address")
        self._fields["address"] = self._address

        self._phone = LineEdit()
        self._phone.setPlaceholderText("Teléfono")
        restrict_input(self._phone, "phone")
        self._fields["phone"] = self._phone

        self._notes = TextEdit()
        self._notes.setPlaceholderText("Notas")
        make_uppercase(self._notes)
        self._fields["additional_notes"] = self._notes

        if person is not None:
            self._full_name.setText(person.full_name or "")
            self._national_id.setText(person.national_id or "")
            if self._birth_date_card is not None:
                self._birth_date_card.set(person.birth_date)
            self._appeared_card.set(person.appeared, person.appearance_date)
            self._address.setText(person.address or "")
            self._phone.setText(person.phone or "")
            self._notes.setPlainText(person.additional_notes or "")

        self._build_buttons()
        self.resize(self.dialog_width, self.dialog_height)

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
        form.addRow(BodyLabel("Notas"), self._notes)
        layout.addLayout(form)

        dates_group = SettingCardGroup("Datos personales", self)
        if self._birth_date_card is not None:
            dates_group.addSettingCard(self._birth_date_card)
        dates_group.addSettingCard(self._appeared_card)
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
        appeared, appearance_date = self._appeared_card.get()
        data: dict = {
            "full_name": (self._full_name.text() or "").strip().upper(),
            "national_id": self._clean(self._national_id.text()),
            "appeared": appeared,
            "appearance_date": appearance_date,
            "address": self._clean(self._address.text()),
            "phone": (self._phone.text() or "").strip() or None,
            "additional_notes": self._clean(self._notes.toPlainText()),
        }
        if self._birth_date_card is not None:
            data["birth_date"] = self._birth_date_card.get()
        return data

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
            payload = self.create_dto(**kwargs)
        except ValidationError as exc:
            logger.exception("Error de validación al guardar %s", self.entity_label.lower())
            self._mark_errors(field_errors(exc))
            show_error(self, "Revise los campos marcados.")
            return

        try:
            if self.person is None:
                getattr(self.app.service, self.add_method_name)(self.case_file_id, payload)
                show_info(self, f"{self.entity_label} agregado.")
            else:
                ok = getattr(self.app.service, self.update_method_name)(
                    self.case_file_id, self.person_id, payload
                )
                if not ok:
                    show_error(
                        self,
                        f"El/La {self.entity_label.lower()} no existe o no pertenece al expediente.",
                    )
                    return
                show_info(self, f"{self.entity_label} actualizado.")
        except ValueError as exc:
            logger.exception("Error al guardar %s", self.entity_label.lower())
            show_error(self, f"Error al guardar: {exc}")
            return
        self.accept()


class VictimDialog(_PersonDialog):
    """Alta/edición de una víctima de un expediente."""

    create_dto = VictimCreate
    entity_label = "Víctima"
    add_method_name = "add_victim"
    update_method_name = "update_victim"
    dialog_width = VICTIM_DIALOG_WIDTH
    dialog_height = VICTIM_DIALOG_HEIGHT


class WitnessDialog(_PersonDialog):
    """Alta/edición de un testigo de un expediente."""

    create_dto = WitnessCreate
    entity_label = "Testigo"
    add_method_name = "add_witness"
    update_method_name = "update_witness"
    show_birth_date = False
    dialog_width = WITNESS_DIALOG_WIDTH
    dialog_height = WITNESS_DIALOG_HEIGHT
