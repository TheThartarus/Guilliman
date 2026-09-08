"""Operaciones de víctimas (Victim)."""

from __future__ import annotations

from ..database import session_scope
from ..exceptions import CaseFileNotFoundError
from ..models import CaseFile, Victim
from ..schemas import VictimCreate
from ._base import _ServiceMixin


class VictimMethods(_ServiceMixin):
    """Métodos CRUD de víctimas vinculadas a un expediente."""

    def add_victim(self, case_file_id: int, victim_data: VictimCreate) -> int:
        """Agrega una víctima a un expediente existente.

        Returns:
            El ID de la víctima creada.

        Raises:
            CaseFileNotFoundError: Si el expediente padre no existe.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                raise CaseFileNotFoundError(case_file_id)
            victim = Victim(**victim_data.model_dump())
            case_file.victims.append(victim)
            session.flush()
            return victim.id

    def update_victim(
        self,
        case_file_id: int,
        victim_id: int,
        victim_data: VictimCreate,
    ) -> bool:
        """Reemplaza los datos de una víctima existente.

        Returns:
            True si la víctima fue actualizada; False si no existe o no
            pertenece al expediente indicado.

        Raises:
            CaseFileNotFoundError: Si el expediente padre no existe.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                raise CaseFileNotFoundError(case_file_id)
            victim = session.get(Victim, victim_id)
            if victim is None or victim.case_file_id != case_file_id:
                return False
            for field, value in victim_data.model_dump().items():
                setattr(victim, field, value)
            session.add(victim)
            return True

    def delete_victim(self, victim_id: int) -> bool:
        """Elimina una víctima individual por su clave primaria.

        Returns:
            True si la víctima fue eliminada; False si no se encontró.
        """
        with session_scope(self._db_path) as session:
            victim = session.get(Victim, victim_id)
            if victim is None:
                return False
            session.delete(victim)
            return True
