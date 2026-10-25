"""Operaciones de acusados (Defendant)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from ..database import session_scope
from ..exceptions import CaseFileNotFoundError
from ..models import CaseFile, Defendant
from ..schemas import DefendantCreate, DetentionAlertItem
from ._base import _ServiceMixin


class DefendantMethods(_ServiceMixin):
    """Métodos CRUD de acusados vinculados a un expediente."""

    def add_defendant(self, case_file_id: int, defendant_data: DefendantCreate) -> int:
        """Agrega un acusado a un expediente existente.

        Returns:
            El ID del acusado creado.

        Raises:
            CaseFileNotFoundError: Si el expediente padre no existe.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                raise CaseFileNotFoundError(case_file_id)
            defendant = Defendant(**defendant_data.model_dump())
            case_file.defendants.append(defendant)
            session.flush()
            return defendant.id

    def update_defendant(
        self,
        case_file_id: int,
        defendant_id: int,
        defendant_data: DefendantCreate,
    ) -> bool:
        """Reemplaza los datos de un acusado existente.

        Returns:
            True si el acusado fue actualizado; False si no existe o no
            pertenece al expediente indicado.

        Raises:
            CaseFileNotFoundError: Si el expediente padre no existe.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                raise CaseFileNotFoundError(case_file_id)
            defendant = session.get(Defendant, defendant_id)
            if defendant is None or defendant.case_file_id != case_file_id:
                return False
            for field, value in defendant_data.model_dump().items():
                setattr(defendant, field, value)
            session.add(defendant)
            return True

    def delete_defendant(self, defendant_id: int) -> bool:
        """Elimina un acusado individual por su clave primaria.

        Returns:
            True si el acusado fue eliminado; False si no se encontró.
        """
        with session_scope(self._db_path) as session:
            defendant = session.get(Defendant, defendant_id)
            if defendant is None:
                return False
            session.delete(defendant)
            return True

    def list_detention_alerts(self, threshold_days: int) -> list[DetentionAlertItem]:
        """Lista acusados detenidos que alcanzan o superan ``threshold_days``.

        Solo considera expedientes activos (no archivados) y acusados con
        estado ``Detenido`` y ``arrest_date`` registrada.

        Returns:
            Lista ordenada de mayor a menor cantidad de días detenido.
        """
        statement = (
            select(Defendant, CaseFile.case_number)
            .join(CaseFile, Defendant.case_file_id == CaseFile.id)
            .where(Defendant.status == "Detenido")
            .where(Defendant.arrest_date.is_not(None))
            .where(CaseFile.archived_at.is_(None))
        )
        today = date.today()
        alerts: list[DetentionAlertItem] = []
        with session_scope(self._db_path) as session:
            for defendant, case_number in session.execute(statement).all():
                days = max(0, (today - defendant.arrest_date).days)
                if days < threshold_days:
                    continue
                alerts.append(
                    DetentionAlertItem(
                        case_file_id=defendant.case_file_id,
                        case_number=case_number,
                        defendant_id=defendant.id,
                        full_name=defendant.full_name,
                        arrest_date=defendant.arrest_date,
                        days_detained=days,
                        status=defendant.status,
                    )
                )
        alerts.sort(key=lambda item: item.days_detained, reverse=True)
        return alerts
