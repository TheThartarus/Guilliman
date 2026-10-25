"""Editor del acta/transcripción de una audiencia."""

from __future__ import annotations

import logging

from PyQt5.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout

from qfluentwidgets import (
    FluentStyleSheet,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
    TextEdit,
)

from db import HearingScheduleUpdate

from ui.widgets import show_error, show_info

from ._sizes import TRANSCRIPTION_DIALOG_HEIGHT, TRANSCRIPTION_DIALOG_WIDTH

logger = logging.getLogger("guilliman")


class HearingTranscriptionDialog(QDialog):
    """Edita el acta/transcripción de una audiencia existente.

    No normaliza el texto (ni mayúsculas ni filtros de caracteres): el acta es
    un documento libre que debe conservarse tal como se pega desde el
    procesador de texto.
    """

    def __init__(self, parent, app, hearing) -> None:
        super().__init__(parent)
        FluentStyleSheet.DIALOG.apply(self)
        self.app = app
        self.hearing = hearing
        self.setWindowTitle("Acta / Transcripción")

        self._editor = TextEdit()
        self._editor.setPlaceholderText(
            "Pega aquí la transcripción de la audiencia o redacta el acta..."
        )
        self._editor.setPlainText(hearing.transcription or "")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(
            SubtitleLabel(f"Acta de audiencia — {hearing.scheduled_at:%d/%m/%Y %H:%M}")
        )
        layout.addWidget(self._editor, 1)

        buttons = QHBoxLayout()
        self.save_btn = PrimaryPushButton("Guardar acta")
        self.save_btn.clicked.connect(self._on_save)
        self.cancel_btn = PushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.cancel_btn)
        layout.addLayout(buttons)

        self.resize(TRANSCRIPTION_DIALOG_WIDTH, TRANSCRIPTION_DIALOG_HEIGHT)

    def _on_save(self) -> None:
        text = (self._editor.toPlainText() or "").strip() or None
        try:
            ok = self.app.service.update_hearing(
                self.hearing.id, HearingScheduleUpdate(transcription=text)
            )
        except ValueError as exc:
            logger.exception(
                "Error al guardar el acta de la audiencia %s", self.hearing.id
            )
            show_error(self, f"Error al guardar el acta: {exc}")
            return
        if not ok:
            show_error(self, "La audiencia no existe.")
            return
        show_info(self, "Acta guardada.")
        self.accept()
