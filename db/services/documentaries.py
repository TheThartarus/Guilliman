"""Operaciones de documentales (Documentary / pruebas documentales)."""

from __future__ import annotations

from ..database import session_scope
from ..exceptions import CaseFileNotFoundError
from ..models import CaseFile, Documentary
from ..schemas import DocumentaryCreate
from ._base import _ServiceMixin


class DocumentaryMethods(_ServiceMixin):
    """Métodos CRUD de documentales vinculados a un expediente."""

    def add_documentary(self, case_file_id: int, documentary_data: DocumentaryCreate) -> int:
        """Agrega un documental a un expediente existente.

        Returns:
            El ID del documental creado.

        Raises:
            CaseFileNotFoundError: Si el expediente padre no existe.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                raise CaseFileNotFoundError(case_file_id)
            documentary = Documentary(**documentary_data.model_dump())
            case_file.documentaries.append(documentary)
            session.flush()
            return documentary.id

    def update_documentary(
        self,
        case_file_id: int,
        documentary_id: int,
        documentary_data: DocumentaryCreate,
    ) -> bool:
        """Reemplaza los datos de un documental existente.

        Returns:
            True si el documental fue actualizado; False si no existe o no
            pertenece al expediente indicado.

        Raises:
            CaseFileNotFoundError: Si el expediente padre no existe.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                raise CaseFileNotFoundError(case_file_id)
            documentary = session.get(Documentary, documentary_id)
            if documentary is None or documentary.case_file_id != case_file_id:
                return False
            for field, value in documentary_data.model_dump().items():
                setattr(documentary, field, value)
            session.add(documentary)
            return True

    def delete_documentary(self, documentary_id: int) -> bool:
        """Elimina un documental individual por su clave primaria.

        Returns:
            True si el documental fue eliminado; False si no se encontró.
        """
        with session_scope(self._db_path) as session:
            documentary = session.get(Documentary, documentary_id)
            if documentary is None:
                return False
            session.delete(documentary)
            return True
