"""Formularios de alta/edición de pruebas documentales y expertos/funcionarios."""

from __future__ import annotations

import logging
from datetime import date

from PyQt5.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QVBoxLayout

from qfluentwidgets import (
    BodyLabel,
    FluentStyleSheet,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
    TextEdit,
)

from db import ActingOfficialCreate, DocumentaryCreate, ExpertCreate
from pydantic import ValidationError

from ui.shared import field_errors
from ui.widgets import (
    make_uppercase,
    restrict_input,
    show_error,
    show_info,
)

from ._cards import _FlaggedDateCard
from ._sizes import (
    ACTING_OFFICIAL_DIALOG_HEIGHT,
    ACTING_OFFICIAL_DIALOG_WIDTH,
    DEFENDANT_DIALOG_WIDTH,
    DOCUMENTARY_DIALOG_HEIGHT,
    DOCUMENTARY_DIALOG_WIDTH,
    EXPERT_DIALOG_HEIGHT,
    EXPERT_DIALOG_WIDTH,
    VICTIM_DIALOG_HEIGHT,
)

logger = logging.getLogger("guilliman")


class _FlaggedRecordDialog(QDialog):
    """Alta/edición de entidades con nombre + fechas condicionadas por flags.

    Las subclases fijan ``create_dto``, ``entity_label``, los métodos del
    service y ``date_specs``: lista de ``(flag_attr, date_attr, switch_label)``.
    El borrado se delega a la vista de detalle (confirmación + recarga), igual
    que con víctimas/testigos.
    """

    create_dto: type
    entity_label: str
    add_method_name: str
    update_method_name: str
    date_specs: list
    dialog_width: int = DEFENDANT_DIALOG_WIDTH
    dialog_height: int = VICTIM_DIALOG_HEIGHT

    def __init__(self, parent, app, case_file_id, record=None) -> None:
        super().__init__(parent)
        FluentStyleSheet.DIALOG.apply(self)
        self.app = app
        self.case_file_id = case_file_id
        self.record = record
        self.record_id = record.id if record is not None else None
        self.setWindowTitle(
            f"Editar {self.entity_label.lower()}"
            if record is not None
            else f"Agregar {self.entity_label.lower()}"
        )
        self._fields: dict = {}

        self._name = LineEdit()
        self._name.setPlaceholderText("Nombre *")
        restrict_input(self._name, "text")
        self._fields["name"] = self._name

        self._date_cards: dict[str, _FlaggedDateCard] = {}
        for flag_attr, _date_attr, _switch_label in self.date_specs:
            card = _FlaggedDateCard(_switch_label)
            setattr(self, f"_{flag_attr}_card", card)
            self._date_cards[flag_attr] = card
            self._fields[flag_attr] = card

        self._notes = TextEdit()
        self._notes.setPlaceholderText("Notas")
        make_uppercase(self._notes)
        self._fields["additional_notes"] = self._notes

        if record is not None:
            self._name.setText(record.name or "")
            self._notes.setPlainText(record.additional_notes or "")
            for flag_attr, date_attr, *_ in self.date_specs:
                flag_val = getattr(record, flag_attr, False)
                date_val = getattr(record, date_attr, None)
                self._date_cards[flag_attr].set(flag_val, date_val)

        self._build_buttons()
        self.resize(self.dialog_width, self.dialog_height)

    def _build_buttons(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(SubtitleLabel(self.windowTitle()))
        form = QFormLayout()
        form.setSpacing(8)
        form.addRow(BodyLabel("Nombre *"), self._name)
        for flag_attr, _date_attr, _switch_label in self.date_specs:
            form.addRow(self._date_cards[flag_attr])
        form.addRow(BodyLabel("Notas"), self._notes)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        self.save_btn = PrimaryPushButton("Guardar")
        self.save_btn.clicked.connect(self._on_save)
        self.cancel_btn = PushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.cancel_btn)
        layout.addLayout(buttons)

    @staticmethod
    def _clean_name(value: str) -> str:
        return (value or "").strip().upper()

    def _collect(self) -> dict:
        data = {"name": self._clean_name(self._name.text())}
        for flag_attr, date_attr, *_ in self.date_specs:
            flag, date_val = self._date_cards[flag_attr].get()
            data[flag_attr] = flag
            data[date_attr] = date_val
        data["additional_notes"] = (
            (self._notes.toPlainText() or "").strip().upper() or None
        )
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
            if self.record is None:
                getattr(self.app.service, self.add_method_name)(self.case_file_id, payload)
                show_info(self, f"{self.entity_label} agregado.")
            else:
                ok = getattr(self.app.service, self.update_method_name)(
                    self.case_file_id, self.record_id, payload
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


class DocumentaryDialog(_FlaggedRecordDialog):
    """Alta/edición de una prueba documental de un expediente."""

    create_dto = DocumentaryCreate
    entity_label = "Documental"
    add_method_name = "add_documentary"
    update_method_name = "update_documentary"
    dialog_width = DOCUMENTARY_DIALOG_WIDTH
    dialog_height = DOCUMENTARY_DIALOG_HEIGHT
    date_specs = [
        ("in_possession", "possession_date", "Fecha de Posesión"),
        ("evacuated", "evacuation_date", "Fecha de Evacuación"),
    ]


class ExpertDialog(_FlaggedRecordDialog):
    """Alta/edición de un experto/funcionario de un expediente."""

    create_dto = ExpertCreate
    entity_label = "Experto"
    add_method_name = "add_expert"
    update_method_name = "update_expert"
    dialog_width = EXPERT_DIALOG_WIDTH
    dialog_height = EXPERT_DIALOG_HEIGHT
    date_specs = [
        ("appeared", "appearance_date", "Fecha de Comparecencia"),
    ]


class ActingOfficialDialog(_FlaggedRecordDialog):
    """Alta/edición de un funcionario actuante de un expediente."""

    create_dto = ActingOfficialCreate
    entity_label = "Funcionario Actuante"
    add_method_name = "add_acting_official"
    update_method_name = "update_acting_official"
    dialog_width = ACTING_OFFICIAL_DIALOG_WIDTH
    dialog_height = ACTING_OFFICIAL_DIALOG_HEIGHT
    date_specs = [
        ("appeared", "appearance_date", "Fecha de Comparecencia"),
    ]
