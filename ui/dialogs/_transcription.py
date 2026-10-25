"""Editor del acta/transcripción de una audiencia."""

from __future__ import annotations

import logging

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout

from qfluentwidgets import (
    CaptionLabel,
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
        self._saved_text = hearing.transcription or ""

        # Autosave: guarda en la BD tras una pausa de tecleo (evita perder el
        # acta completa si la app se cierra o falla).
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(1500)
        self._autosave_timer.timeout.connect(self._autosave)
        self._editor.textChanged.connect(self._autosave_timer.start)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(
            SubtitleLabel(f"Acta de audiencia — {hearing.scheduled_at:%d/%m/%Y %H:%M}")
        )
        layout.addWidget(self._editor, 1)
        layout.addWidget(CaptionLabel("Los cambios se guardan automáticamente."))

        buttons = QHBoxLayout()
        self.save_btn = PrimaryPushButton("Guardar acta")
        self.save_btn.clicked.connect(self._on_save)
        self.cancel_btn = PushButton("Cerrar")
        self.cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.cancel_btn)
        layout.addLayout(buttons)

        self.resize(TRANSCRIPTION_DIALOG_WIDTH, TRANSCRIPTION_DIALOG_HEIGHT)

    def _autosave(self) -> bool:
        """Guarda silenciosamente el acta si cambió desde el último guardado."""
        self._autosave_timer.stop()
        text = (self._editor.toPlainText() or "").strip() or None
        if text == self._saved_text:
            return True
        try:
            ok = self.app.service.update_hearing(
                self.hearing.id, HearingScheduleUpdate(transcription=text)
            )
        except ValueError:
            logger.exception(
                "Error al autoguardar el acta de la audiencia %s", self.hearing.id
            )
            return False
        if ok:
            self._saved_text = text
        return ok

    def reject(self) -> None:
        """Cierra el diálogo guardando cualquier cambio pendiente."""
        self._autosave()
        super().reject()

    def _on_save(self) -> None:
        self._autosave_timer.stop()
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
        self._saved_text = text
        show_info(self, "Acta guardada.")
        self.accept()
