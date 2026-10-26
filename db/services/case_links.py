"""Vínculos entre expedientes (causas conexas)."""

from __future__ import annotations

from sqlalchemy import select

from ..database import session_scope
from ..exceptions import CaseFileNotFoundError
from ..models import CaseFile, CaseLink
from ..schemas import LinkedCaseItem
from ._base import _ServiceMixin


class CaseLinkMethods(_ServiceMixin):
    """Alta, baja y listado de causas conexas."""

    def link_cases(self, case_file_id: int, other_case_number: str) -> int:
        """Vincula dos expedientes. El vínculo es simétrico.

        Repetir la misma pareja devuelve el id ya existente.

        Raises:
            CaseFileNotFoundError: Si el expediente de origen no existe.
            ValueError: Si el número está vacío, no existe o es el mismo expediente.
        """
        number = (other_case_number or "").strip().upper()
        if not number:
            raise ValueError("Indique el número del expediente a vincular.")
        with session_scope(self._db_path) as session:
            if session.get(CaseFile, case_file_id) is None:
                raise CaseFileNotFoundError(case_file_id)
            other = session.execute(
                select(CaseFile).where(CaseFile.case_number == number)
            ).scalar_one_or_none()
            if other is None:
                raise ValueError(f"No existe un expediente con el número {number}.")
            if other.id == case_file_id:
                raise ValueError("Un expediente no puede vincularse consigo mismo.")
            low, high = sorted((case_file_id, other.id))
            existing = session.execute(
                select(CaseLink).where(
                    CaseLink.case_file_id == low,
                    CaseLink.related_case_file_id == high,
                )
            ).scalar_one_or_none()
            if existing is not None:
                return existing.id
            link = CaseLink(case_file_id=low, related_case_file_id=high)
            session.add(link)
            session.flush()
            return link.id

    def unlink_case(self, link_id: int) -> bool:
        """Elimina un vínculo. False si no existe."""
        with session_scope(self._db_path) as session:
            link = session.get(CaseLink, link_id)
            if link is None:
                return False
            session.delete(link)
            return True

    def list_linked_cases(self, case_file_id: int) -> list[LinkedCaseItem]:
        """Lista los expedientes vinculados a ``case_file_id``, por número."""
        left = (
            select(CaseLink.id, CaseFile.id, CaseFile.case_number)
            .join(CaseFile, CaseFile.id == CaseLink.related_case_file_id)
            .where(CaseLink.case_file_id == case_file_id)
        )
        right = (
            select(CaseLink.id, CaseFile.id, CaseFile.case_number)
            .join(CaseFile, CaseFile.id == CaseLink.case_file_id)
            .where(CaseLink.related_case_file_id == case_file_id)
        )
        with session_scope(self._db_path) as session:
            rows = session.execute(left.union(right)).all()
        return [
            LinkedCaseItem(link_id=link_id, case_file_id=other_id, case_number=number)
            for link_id, other_id, number in sorted(rows, key=lambda row: row[2])
        ]
