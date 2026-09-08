"""Operaciones de funcionarios actuantes / aprehensores."""

from __future__ import annotations

from ..database import session_scope
from ..exceptions import CaseFileNotFoundError
from ..models import ActingOfficial, CaseFile
from ..schemas import ActingOfficialCreate
from ._base import _ServiceMixin


class ActingOfficialMethods(_ServiceMixin):
    """Métodos CRUD de funcionarios actuantes vinculados a un expediente."""

    def add_acting_official(self, case_file_id: int, data: ActingOfficialCreate) -> int:
        """Agrega un funcionario actuante a un expediente existente.

        Returns:
            El ID del funcionario creado.

        Raises:
            CaseFileNotFoundError: Si el expediente padre no existe.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                raise CaseFileNotFoundError(case_file_id)
            official = ActingOfficial(**data.model_dump())
            case_file.acting_officials.append(official)
            session.flush()
            return official.id

    def update_acting_official(
        self,
        case_file_id: int,
        official_id: int,
        data: ActingOfficialCreate,
    ) -> bool:
        """Reemplaza los datos de un funcionario actuante existente.

        Returns:
            True si el funcionario fue actualizado; False si no existe o no
            pertenece al expediente indicado.

        Raises:
            CaseFileNotFoundError: Si el expediente padre no existe.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                raise CaseFileNotFoundError(case_file_id)
            official = session.get(ActingOfficial, official_id)
            if official is None or official.case_file_id != case_file_id:
                return False
            for field, value in data.model_dump().items():
                setattr(official, field, value)
            session.add(official)
            return True

    def delete_acting_official(self, official_id: int) -> bool:
        """Elimina un funcionario actuante individual por su clave primaria.

        Returns:
            True si el funcionario fue eliminado; False si no se encontró.
        """
        with session_scope(self._db_path) as session:
            official = session.get(ActingOfficial, official_id)
            if official is None:
                return False
            session.delete(official)
            return True
