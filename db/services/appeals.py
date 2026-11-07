"""Operaciones de apelaciones (Appeal)."""

from __future__ import annotations

from ..database import session_scope
from ..exceptions import CaseFileNotFoundError
from ..models import Appeal, CaseFile
from ..schemas import AppealCreate, AppealRead
from ._base import _ServiceMixin


class AppealMethods(_ServiceMixin):
    """Métodos CRUD de apelaciones vinculadas a un expediente."""

    def add_appeal(self, case_file_id: int, appeal_data: AppealCreate) -> int:
        """Agrega una apelación a un expediente existente.

        Returns:
            El ID de la apelación creada.

        Raises:
            CaseFileNotFoundError: Si el expediente padre no existe.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                raise CaseFileNotFoundError(case_file_id)
            appeal = Appeal(**appeal_data.model_dump())
            case_file.appeals.append(appeal)
            session.flush()
            return appeal.id

    def update_appeal(
        self,
        case_file_id: int,
        appeal_id: int,
        appeal_data: AppealCreate,
    ) -> bool:
        """Reemplaza los datos de una apelación existente.

        Returns:
            True si la apelación fue actualizada; False si no existe o no
            pertenece al expediente indicado.

        Raises:
            CaseFileNotFoundError: Si el expediente padre no existe.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                raise CaseFileNotFoundError(case_file_id)
            appeal = session.get(Appeal, appeal_id)
            if appeal is None or appeal.case_file_id != case_file_id:
                return False
            for field, value in appeal_data.model_dump().items():
                setattr(appeal, field, value)
            session.add(appeal)
            return True

    def delete_appeal(self, appeal_id: int) -> bool:
        """Elimina una apelación individual por su clave primaria.

        Returns:
            True si la apelación fue eliminada; False si no se encontró.
        """
        with session_scope(self._db_path) as session:
            appeal = session.get(Appeal, appeal_id)
            if appeal is None:
                return False
            session.delete(appeal)
            return True

    def list_appeals(self, case_file_id: int) -> list[AppealRead]:
        """Lista todas las apelaciones de un expediente.

        Returns:
            Lista de ``AppealRead`` ordenada por fecha de presentación.
            Vacía si el expediente no existe o no tiene apelaciones.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                return []
            appeals = sorted(
                case_file.appeals,
                key=lambda a: (a.filed_at is None, a.filed_at or ""),
            )
            return [AppealRead.model_validate(appeal) for appeal in appeals]
