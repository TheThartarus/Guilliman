"""Operaciones de expertos (Expert / funcionarios)."""

from __future__ import annotations

from ..database import session_scope
from ..exceptions import CaseFileNotFoundError
from ..models import CaseFile, Expert
from ..schemas import ExpertCreate
from ._base import _ServiceMixin


class ExpertMethods(_ServiceMixin):
    """Métodos CRUD de expertos vinculados a un expediente."""

    def add_expert(self, case_file_id: int, expert_data: ExpertCreate) -> int:
        """Agrega un experto a un expediente existente.

        Returns:
            El ID del experto creado.

        Raises:
            CaseFileNotFoundError: Si el expediente padre no existe.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                raise CaseFileNotFoundError(case_file_id)
            expert = Expert(**expert_data.model_dump())
            case_file.experts.append(expert)
            session.flush()
            return expert.id

    def update_expert(
        self,
        case_file_id: int,
        expert_id: int,
        expert_data: ExpertCreate,
    ) -> bool:
        """Reemplaza los datos de un experto existente.

        Returns:
            True si el experto fue actualizado; False si no existe o no
            pertenece al expediente indicado.

        Raises:
            CaseFileNotFoundError: Si el expediente padre no existe.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                raise CaseFileNotFoundError(case_file_id)
            expert = session.get(Expert, expert_id)
            if expert is None or expert.case_file_id != case_file_id:
                return False
            for field, value in expert_data.model_dump().items():
                setattr(expert, field, value)
            session.add(expert)
            return True

    def delete_expert(self, expert_id: int) -> bool:
        """Elimina un experto individual por su clave primaria.

        Returns:
            True si el experto fue eliminado; False si no se encontró.
        """
        with session_scope(self._db_path) as session:
            expert = session.get(Expert, expert_id)
            if expert is None:
                return False
            session.delete(expert)
            return True
