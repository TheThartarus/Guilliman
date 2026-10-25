"""Helpers compartidos de ``CaseFileService`` (base de los mixins por entidad).

Los mixins de ``db.services`` heredan de ``_ServiceMixin`` para reutilizar
la propiedad de ruta y los aplicadores de actualización parcial (PATCH) sin
duplicar lógica.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ..database import get_app_data_dir
from ..models import CaseFile, HearingSchedule
from ..schemas import CaseFileRead, CaseFileUpdate, HearingScheduleUpdate

logger = logging.getLogger("guilliman")


class _ServiceMixin:
    """Mixin base: propiedad de ruta y aplicadores PATCH compartidos."""

    @staticmethod
    def _delete_stored_file(rel_path: str | None, subdir: str) -> None:
        """Borra un archivo del store indicado, solo si vive dentro de él.

        Ignora archivos ya inexistentes y registra anomalías sin romper el
        borrado de la fila.
        """
        if not rel_path:
            return
        data_dir = get_app_data_dir().resolve()
        store_dir = (data_dir / subdir).resolve()
        target = (data_dir / rel_path).resolve()
        try:
            target.relative_to(store_dir)
        except ValueError:
            logger.warning("Refusing to delete file outside %s: %s", subdir, target)
            return
        if not target.exists():
            logger.info("Stored file already missing, nothing to delete: %s", target)
            return
        try:
            target.unlink()
        except OSError as error:  # p. ej. archivo en uso en Windows
            logger.warning("Could not delete stored file %s: %s", target, error)

    @classmethod
    def _delete_stored_audio(cls, rel_path: str | None) -> None:
        cls._delete_stored_file(rel_path, "audios")

    @classmethod
    def _delete_stored_attachment(cls, rel_path: str | None) -> None:
        cls._delete_stored_file(rel_path, "attachments")

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
