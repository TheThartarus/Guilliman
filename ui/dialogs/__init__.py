"""
Guilliman Frontend - Diálogos nativos (PyQt5).

Paquete que agrupa las confirmaciones, utilidades de archivo y los formularios
de alta/edición de acusados, audiencias, víctimas, testigos, pruebas
documentales y expertos. Se re-exportan los nombres públicos para que los
importadores existentes (``from ui.dialogs import DefendantDialog``) sigan
funcionando sin cambios tras la refactorización del god file original.
"""

from ._sizes import (
    ACTING_OFFICIAL_DIALOG_HEIGHT,
    ACTING_OFFICIAL_DIALOG_WIDTH,
    DEFENDANT_DIALOG_HEIGHT,
    DEFENDANT_DIALOG_WIDTH,
    DOCUMENTARY_DIALOG_HEIGHT,
    DOCUMENTARY_DIALOG_WIDTH,
    EXPERT_DIALOG_HEIGHT,
    EXPERT_DIALOG_WIDTH,
    HEARING_DIALOG_HEIGHT,
    HEARING_DIALOG_WIDTH,
    VICTIM_DIALOG_HEIGHT,
    VICTIM_DIALOG_WIDTH,
    WITNESS_DIALOG_HEIGHT,
    WITNESS_DIALOG_WIDTH,
)
from ._misc import confirm_delete, pick_save_pdf
from ._cards import _DateCard, _DateTimeCard, _FlaggedDateCard
from ._person import VictimDialog, WitnessDialog, _PersonDialog
from ._defendant import DefendantDialog
from ._record import ActingOfficialDialog, DocumentaryDialog, ExpertDialog, _FlaggedRecordDialog
from ._hearing import HearingDialog
from ._transcription import HearingTranscriptionDialog
from ._detention import DetentionAlertsDialog
from ._crime import CrimeDialog

__all__ = [
    "ActingOfficialDialog",
    "CrimeDialog",
    "DefendantDialog",
    "DetentionAlertsDialog",
    "HearingDialog",
    "HearingTranscriptionDialog",
    "VictimDialog",
    "WitnessDialog",
    "DocumentaryDialog",
    "ExpertDialog",
    "_PersonDialog",
    "_FlaggedRecordDialog",
    "_DateCard",
    "_DateTimeCard",
    "_FlaggedDateCard",
    "confirm_delete",
    "pick_save_pdf",
    "ACTING_OFFICIAL_DIALOG_WIDTH",
    "ACTING_OFFICIAL_DIALOG_HEIGHT",
    "DEFENDANT_DIALOG_WIDTH",
    "DEFENDANT_DIALOG_HEIGHT",
    "HEARING_DIALOG_WIDTH",
    "HEARING_DIALOG_HEIGHT",
    "VICTIM_DIALOG_WIDTH",
    "VICTIM_DIALOG_HEIGHT",
    "WITNESS_DIALOG_WIDTH",
    "WITNESS_DIALOG_HEIGHT",
    "DOCUMENTARY_DIALOG_WIDTH",
    "DOCUMENTARY_DIALOG_HEIGHT",
    "EXPERT_DIALOG_WIDTH",
    "EXPERT_DIALOG_HEIGHT",
]
