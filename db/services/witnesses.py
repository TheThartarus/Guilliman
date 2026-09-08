"""Operaciones de testigos (Witness)."""

from __future__ import annotations

from ..database import session_scope
from ..exceptions import CaseFileNotFoundError
from ..models import CaseFile, Witness
from ..schemas import WitnessCreate
from ._base import _ServiceMixin


class WitnessMethods(_ServiceMixin):
    """Métodos CRUD de testigos vinculados a un expediente."""

    def add_witness(self, case_file_id: int, witness_data: WitnessCreate) -> int:
        """Agrega un testigo a un expediente existente.

        Returns:
            El ID del testigo creado.

        Raises:
            CaseFileNotFoundError: Si el expediente padre no existe.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                raise CaseFileNotFoundError(case_file_id)
            witness = Witness(**witness_data.model_dump())
            case_file.witnesses.append(witness)
            session.flush()
            return witness.id

    def update_witness(
        self,
        case_file_id: int,
        witness_id: int,
        witness_data: WitnessCreate,
    ) -> bool:
        """Reemplaza los datos de un testigo existente.

        Returns:
            True si el testigo fue actualizado; False si no existe o no
            pertenece al expediente indicado.

        Raises:
            CaseFileNotFoundError: Si el expediente padre no existe.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                raise CaseFileNotFoundError(case_file_id)
            witness = session.get(Witness, witness_id)
            if witness is None or witness.case_file_id != case_file_id:
                return False
            for field, value in witness_data.model_dump().items():
                setattr(witness, field, value)
            session.add(witness)
            return True

    def delete_witness(self, witness_id: int) -> bool:
        """Elimina un testigo individual por su clave primaria.

        Returns:
            True si el testigo fue eliminado; False si no se encontró.
        """
        with session_scope(self._db_path) as session:
            witness = session.get(Witness, witness_id)
            if witness is None:
                return False
            session.delete(witness)
            return True
