"""Alta de un vínculo (causa conexa) por número de expediente."""

from __future__ import annotations

from PyQt5.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QVBoxLayout

from qfluentwidgets import (
    BodyLabel,
    FluentStyleSheet,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
)

from ui.widgets import restrict_input, show_error

from ._sizes import LINK_DIALOG_HEIGHT, LINK_DIALOG_WIDTH


class LinkCaseDialog(QDialog):
    """Pide el número de expediente a vincular; expone ``case_number`` al aceptar."""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        FluentStyleSheet.DIALOG.apply(self)
        self.case_number: str | None = None
        self.setWindowTitle("Vincular expediente")

        self._number = LineEdit()
        self._number.setPlaceholderText("Número de expediente")
        restrict_input(self._number, "code")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(SubtitleLabel(self.windowTitle()))

        form = QFormLayout()
        form.setSpacing(8)
        form.addRow(BodyLabel("Número de expediente"), self._number)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        self.save_btn = PrimaryPushButton("Vincular")
        self.save_btn.clicked.connect(self._on_accept)
        self.cancel_btn = PushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.cancel_btn)
        layout.addLayout(buttons)

        self.resize(LINK_DIALOG_WIDTH, LINK_DIALOG_HEIGHT)

    def _on_accept(self) -> None:
        number = (self._number.text() or "").strip()
        if not number:
            show_error(self, "Indique el número del expediente a vincular.")
            return
        self.case_number = number
        self.accept()
