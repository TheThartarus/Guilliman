"""Alta/edición de una apelación de un expediente."""

from __future__ import annotations

import logging

from PyQt5.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QVBoxLayout

from pydantic import ValidationError
from qfluentwidgets import (
    BodyLabel,
    ComboBox,
    FluentStyleSheet,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
)

from db import AppealCreate

from ui.widgets import combo_current_data, combo_set_data, show_error

from ._cards import _DateCard
from ._sizes import APPEAL_DIALOG_HEIGHT, APPEAL_DIALOG_WIDTH

logger = logging.getLogger("guilliman")

APPEAL_CLASSIFICATIONS = ("De autos", "Por sentencia", "Amparo", "Efecto suspensivo")
APPEAL_DECISIONS = ("Con lugar", "Sin lugar")


class AppealDialog(QDialog):
    """Formulario de una apelación; expone ``result_appeal`` al aceptar."""

    def __init__(self, parent, appeal: AppealCreate | None = None) -> None:
        super().__init__(parent)
        FluentStyleSheet.DIALOG.apply(self)
        self.result_appeal: AppealCreate | None = None
        self.setWindowTitle("Editar apelación" if appeal else "Agregar apelación")

        self._filed = _DateCard("Fecha de presentación")
        self._remitted = _DateCard("Remisión a la corte")
        self._returned = _DateCard("Regreso de la corte")

        self._decision = ComboBox()
        self._decision.addItem("—", userData=None)
        for decision in APPEAL_DECISIONS:
            self._decision.addItem(decision, userData=decision)

        self._classification = ComboBox()
        self._classification.addItem("—", userData=None)
        for classification in APPEAL_CLASSIFICATIONS:
            self._classification.addItem(classification, userData=classification)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(SubtitleLabel(self.windowTitle()))

        layout.addWidget(self._filed)
        layout.addWidget(self._remitted)
        layout.addWidget(self._returned)

        form = QFormLayout()
        form.setSpacing(8)
        form.addRow(BodyLabel("Decisión de la corte"), self._decision)
        form.addRow(BodyLabel("Clasificación"), self._classification)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        self.save_btn = PrimaryPushButton("Guardar")
        self.save_btn.clicked.connect(self._on_accept)
        self.cancel_btn = PushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.cancel_btn)
        layout.addLayout(buttons)

        if appeal is not None:
            self._filed.set(appeal.filed_at)
            self._remitted.set(appeal.remitted_to_court_at)
            self._returned.set(appeal.returned_from_court_at)
            combo_set_data(self._decision, appeal.court_decision)
            combo_set_data(self._classification, appeal.classification)

        self.resize(APPEAL_DIALOG_WIDTH, APPEAL_DIALOG_HEIGHT)

    def _build_appeal(self) -> AppealCreate:
        return AppealCreate(
            filed_at=self._filed.get(),
            remitted_to_court_at=self._remitted.get(),
            returned_from_court_at=self._returned.get(),
            court_decision=combo_current_data(self._decision),
            classification=combo_current_data(self._classification),
        )

    def _on_accept(self) -> None:
        try:
            self.result_appeal = self._build_appeal()
        except ValidationError:
            logger.exception("Datos inválidos al guardar una apelación")
            show_error(self, "Revise los datos de la apelación.")
            return
        self.accept()
