"""Formulario de alta/edición de una audiencia de un expediente."""

from __future__ import annotations

import logging
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QVBoxLayout,
)

from qfluentwidgets import (
    BodyLabel,
    ComboBox,
    FluentStyleSheet,
    PrimaryPushButton,
    PushButton,
    SettingCardGroup,
    SubtitleLabel,
    TextEdit,
)

from db import HearingScheduleCreate
from pydantic import ValidationError

from ui.shared import (
    HEARING_STATUS_LABELS,
    HEARING_TYPE_OPTIONS,
    field_errors,
)
from ui.widgets import (
    combo_current_data,
    combo_set_data,
    make_uppercase,
    show_error,
    show_info,
)

from ._cards import _DateTimeCard
from ._sizes import HEARING_DIALOG_HEIGHT, HEARING_DIALOG_WIDTH

logger = logging.getLogger("guilliman")

AUDIO_FILTER = "Audio (*.mp3 *.wav *.m4a *.ogg *.aac)"


class HearingDialog(QDialog):
    """Alta/edición de una audiencia de un expediente."""

    def __init__(self, parent, app, case_file_id: int, hearing=None) -> None:
        super().__init__(parent)
        FluentStyleSheet.DIALOG.apply(self)
        self.app = app
        self.case_file_id = case_file_id
        self.hearing = hearing
        self.setWindowTitle("Editar audiencia" if hearing else "Agregar audiencia")
        self._fields: dict = {}

        self._scheduled_card = _DateTimeCard("Fecha y hora de la audiencia *")

        self._hearing_type = ComboBox()
        for label, stored in HEARING_TYPE_OPTIONS:
            self._hearing_type.addItem(label, userData=stored)
        self._fields["hearing_type"] = self._hearing_type

        self._status = ComboBox()
        for value, label in HEARING_STATUS_LABELS.items():
            self._status.addItem(label, userData=value)
        combo_set_data(self._status, "Scheduled")
        self._fields["status"] = self._status

        self._notes = TextEdit()
        self._notes.setPlaceholderText("Notas")
        make_uppercase(self._notes)
        self._fields["notes"] = self._notes

        # Audio adjunto: se copia a la tienda del backend al seleccionarlo.
        self._audio_path: str | None = None
        self._audio_filename: str | None = None
        self._audio_btn = PushButton("Seleccionar audio…")
        self._audio_btn.clicked.connect(self._on_pick_audio)
        self._clear_audio_btn = PushButton("Quitar audio")
        self._clear_audio_btn.clicked.connect(self._clear_audio)
        self._audio_label = BodyLabel("Sin audio")
        self._set_audio(None, None)

        if hearing is not None:
            self._set_audio(hearing.audio_path, hearing.audio_filename)
            self._scheduled_card.set(hearing.scheduled_at)
            if hearing.hearing_type:
                # Busca por userData (valor almacenado); si no se encuentra
                # (registro legacy), añade un ítem temporal para preservarlo.
                idx = self._hearing_type.findData(hearing.hearing_type)
                if idx < 0:
                    self._hearing_type.addItem(hearing.hearing_type, userData=hearing.hearing_type)
                    idx = self._hearing_type.findData(hearing.hearing_type)
                self._hearing_type.setCurrentIndex(idx)
            if hearing.status:
                combo_set_data(self._status, hearing.status)
            self._notes.setPlainText(hearing.notes or "")

        self._build_buttons()
        self.resize(HEARING_DIALOG_WIDTH, HEARING_DIALOG_HEIGHT)

    def _build_buttons(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(SubtitleLabel(self.windowTitle()))
        form = QFormLayout()
        form.setSpacing(8)
        form.addRow(BodyLabel("Tipo"), self._hearing_type)
        form.addRow(BodyLabel("Estado"), self._status)
        form.addRow(BodyLabel("Notas"), self._notes)
        audio_row = QHBoxLayout()
        audio_row.addWidget(self._audio_btn)
        audio_row.addWidget(self._clear_audio_btn)
        audio_row.addWidget(self._audio_label, 1)
        form.addRow(BodyLabel("Audio"), audio_row)
        layout.addLayout(form)

        schedule_group = SettingCardGroup("Programación", self)
        schedule_group.addSettingCard(self._scheduled_card)
        layout.addWidget(schedule_group)

        buttons = QHBoxLayout()
        self.save_btn = PrimaryPushButton("Guardar")
        self.save_btn.clicked.connect(self._on_save)
        self.cancel_btn = PushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.cancel_btn)
        layout.addLayout(buttons)

    def _set_audio(self, path: str | None, filename: str | None) -> None:
        self._audio_path = path
        self._audio_filename = filename
        self._audio_label.setText(filename or "Sin audio")
        self._clear_audio_btn.setEnabled(bool(path))

    def _on_pick_audio(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar audio", "", AUDIO_FILTER
        )
        if not path:
            return
        try:
            # ponytail: método privado del backend; usar el público cuando exista.
            rel_path, filename = self.app.service._copy_audio_to_store(path)
        except OSError as exc:
            logger.exception("Error al adjuntar audio a la audiencia")
            show_error(self, f"No se pudo adjuntar el audio: {exc}")
            return
        self._set_audio(rel_path, filename)

    def _clear_audio(self) -> None:
        self._set_audio(None, None)

    def _collect(self) -> dict:
        return {
            "scheduled_at": self._scheduled_card.get(),
            "hearing_type": combo_current_data(self._hearing_type),
            "status": combo_current_data(self._status) or "Scheduled",
            "notes": (self._notes.toPlainText() or "").strip().upper() or None,
            "audio_path": self._audio_path,
            "audio_filename": self._audio_filename,
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
        from db import HearingScheduleCreate

        kwargs = self._collect()
        scheduled_at = kwargs["scheduled_at"]
        if scheduled_at < datetime.now():
            unchanged = self.hearing is not None and scheduled_at == self.hearing.scheduled_at
            if not unchanged:
                show_error(self, "No se puede programar una audiencia en una fecha pasada.")
                return
        try:
            payload = HearingScheduleCreate(**kwargs)
        except ValidationError as exc:
            logger.exception("Error de validación al guardar audiencia")
            self._mark_errors(field_errors(exc))
            show_error(self, "Revise los campos marcados.")
            return

        try:
            if self.hearing is None:
                self.app.service.add_hearing(self.case_file_id, payload)
                show_info(self, "Audiencia agregada.")
            else:
                ok = self.app.service.update_hearing(self.hearing.id, payload)
                if not ok:
                    show_error(self, "La audiencia no existe.")
                    return
                show_info(self, "Audiencia actualizada.")
        except ValueError as exc:
            logger.exception("Error al guardar audiencia")
            show_error(self, f"Error al guardar: {exc}")
            return
        self.accept()
