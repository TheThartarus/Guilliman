"""Operaciones de delitos imputados por expediente."""

from __future__ import annotations

from ..database import session_scope
from ..models import CaseFile, Crime
from ..schemas import CrimeCreate
from ._base import _ServiceMixin


class CrimeMethods(_ServiceMixin):
    """Métodos de gestión de los delitos de un expediente."""

    def set_case_crimes(
        self, case_file_id: int, crimes: list[CrimeCreate]
    ) -> bool:
        """Reemplaza todos los delitos del expediente de forma atómica.

        Returns:
            True si el expediente existe; False si no se encontró.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                return False
            case_file.crimes.clear()
            for crime_data in crimes:
                case_file.crimes.append(Crime(**crime_data.model_dump()))
            return True
