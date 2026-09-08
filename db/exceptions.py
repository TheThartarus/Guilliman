"""
Guilliman Backend - Excepciones tipadas de la capa de negocio.

Todas heredan de ``ValueError`` para mantener retrocompatibilidad con el
frontend existente (que ya captura ValueError), pero permiten a la UI
distinguir el tipo exacto de error y mostrar mensajes adecuados.
"""

from __future__ import annotations


class GuillimanBackendError(ValueError):
    """Excepción base para todos los errores de negocio del db."""


class CaseFileNotFoundError(GuillimanBackendError):
    """Se solicitó un expediente que no existe."""

    def __init__(self, case_file_id: int) -> None:
        self.case_file_id = case_file_id
        super().__init__(f"Case file with id {case_file_id} does not exist.")


class DefendantNotFoundError(GuillimanBackendError):
    """Se solicitó un acusado que no existe."""

    def __init__(self, defendant_id: int) -> None:
        self.defendant_id = defendant_id
        super().__init__(f"Defendant with id {defendant_id} does not exist.")


class HearingNotFoundError(GuillimanBackendError):
    """Se solicitó una audiencia que no existe."""

    def __init__(self, hearing_id: int) -> None:
        self.hearing_id = hearing_id
        super().__init__(f"Hearing schedule with id {hearing_id} does not exist.")


class DuplicateCaseNumberError(GuillimanBackendError):
    """Ya existe un expediente con el número de expediente suministrado."""

    def __init__(self, case_number: str) -> None:
        self.case_number = case_number
        super().__init__(
            f"A case file with case_number {case_number!r} already exists."
        )


class VictimNotFoundError(GuillimanBackendError):
    """Se solicitó una víctima que no existe."""

    def __init__(self, victim_id: int) -> None:
        self.victim_id = victim_id
        super().__init__(f"Victim with id {victim_id} does not exist.")


class WitnessNotFoundError(GuillimanBackendError):
    """Se solicitó un testigo que no existe."""

    def __init__(self, witness_id: int) -> None:
        self.witness_id = witness_id
        super().__init__(f"Witness with id {witness_id} does not exist.")
