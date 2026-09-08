"""Helpers compartidos de ``CaseFileService`` (base de los mixins por entidad).

Los mixins de ``db.services`` heredan de ``_ServiceMixin`` para reutilizar
la propiedad de ruta y los aplicadores de actualización parcial (PATCH) sin
duplicar lógica.
"""

from __future__ import annotations

from ..models import CaseFile, HearingSchedule
from ..schemas import CaseFileRead, CaseFileUpdate, HearingScheduleUpdate


class _ServiceMixin:
    """Mixin base: propiedad de ruta y aplicadores PATCH compartidos."""

    @property
    def db_path(self) -> str | None:
        """Ruta de base de datos configurada (None significa la por defecto)."""
        return self._db_path

    @staticmethod
    def _to_case_file_read(case_file: CaseFile) -> CaseFileRead:
        """Convierte un CaseFile ORM en su DTO de lectura."""
        return CaseFileRead.model_validate(case_file)

    @staticmethod
    def _apply_case_file_update(target: CaseFile, updated_data: CaseFileUpdate) -> None:
        """Aplica únicamente los campos establecidos explícitamente en la carga."""
        for field, value in updated_data.model_dump(exclude_unset=True).items():
            setattr(target, field, value)

    @staticmethod
    def _apply_hearing_update(target: HearingSchedule, update: HearingScheduleUpdate) -> None:
        """Aplica únicamente los campos establecidos explícitamente en la carga."""
        for field, value in update.model_dump(exclude_unset=True).items():
            setattr(target, field, value)
