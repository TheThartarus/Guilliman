"""Operaciones de audiencias (HearingSchedule) y vista de agenda."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select

from ..database import session_scope
from ..exceptions import CaseFileNotFoundError
from ..models import CaseFile, HearingSchedule
from ..schemas import HearingScheduleCreate, HearingScheduleUpdate, ScheduledHearingItem
from ._base import _ServiceMixin

logger = logging.getLogger("guilliman")


class HearingMethods(_ServiceMixin):
    """Métodos de audiencias y listado de agenda."""

    def list_scheduled_hearings(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        status: str | None = None,
    ) -> list[ScheduledHearingItem]:
        """Lista audiencias ordenadas cronológicamente para vistas de calendario.

        Returns:
            Lista de ``ScheduledHearingItem``. Una lista vacía si no hay
            audiencias en el rango o con el estado solicitado.
        """
        statement = (
            select(HearingSchedule, CaseFile.case_number)
            .join(CaseFile, HearingSchedule.case_file_id == CaseFile.id)
            .order_by(HearingSchedule.scheduled_at)
        )
        if start_date is not None:
            statement = statement.where(HearingSchedule.scheduled_at >= start_date)
        if end_date is not None:
            statement = statement.where(HearingSchedule.scheduled_at <= end_date)
        if status is not None:
            statement = statement.where(HearingSchedule.status == status)

        items: list[ScheduledHearingItem] = []
        with session_scope(self._db_path) as session:
            rows = session.execute(statement).all()
            for hearing, case_number in rows:
                items.append(
                    ScheduledHearingItem(
                        hearing_id=hearing.id,
                        case_file_id=hearing.case_file_id,
                        case_number=case_number,
                        scheduled_at=hearing.scheduled_at,
                        hearing_type=hearing.hearing_type,
                        status=hearing.status,
                        notes=hearing.notes,
                    )
                )
        return items

    def add_hearing(self, case_file_id: int, hearing_data: HearingScheduleCreate) -> int:
        """Agrega una audiencia a un expediente existente.

        Returns:
            El ID de la audiencia creada.

        Raises:
            CaseFileNotFoundError: Si el expediente padre no existe.
            ValueError: Si la fecha programada es anterior a la fecha actual.
        """
        if hearing_data.scheduled_at < datetime.now():
            logger.warning(
                "Attempted to schedule hearing in the past: %s",
                hearing_data.scheduled_at,
            )
            raise ValueError(
                "No se puede programar una audiencia en una fecha pasada."
            )
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                raise CaseFileNotFoundError(case_file_id)
            hearing = HearingSchedule(**hearing_data.model_dump())
            case_file.hearings.append(hearing)
            session.flush()
            return hearing.id

    def update_hearing(self, hearing_id: int, update: HearingScheduleUpdate) -> bool:
        """Actualiza una audiencia (semántica PATCH).

        Returns:
            True si la audiencia fue actualizada; False si no existe.
        """
        with session_scope(self._db_path) as session:
            hearing = session.get(HearingSchedule, hearing_id)
            if hearing is None:
                return False
            self._apply_hearing_update(hearing, update)
            session.add(hearing)
            return True

    def update_hearing_status(
        self,
        hearing_id: int,
        new_status: str,
        notes: str | None = None,
    ) -> bool:
        """Atajo para cambiar solo el estado de una audiencia (y opcionalmente
        sus notas) desde la agenda. Equivalente a:
            update_hearing(hearing_id, HearingScheduleUpdate(status=new_status, notes=notes))
        Se mantiene como conveniencia para la UI de agenda, que solo necesita
        actualizar el estado sin construir un ``HearingScheduleUpdate`` completo.

        Returns:
            True si la audiencia fue actualizada; False si no existe.
        """
        with session_scope(self._db_path) as session:
            hearing = session.get(HearingSchedule, hearing_id)
            if hearing is None:
                return False
            hearing.status = new_status
            if notes is not None:
                hearing.notes = notes
            session.add(hearing)
            return True

    def delete_hearing(self, hearing_id: int) -> bool:
        """Elimina una audiencia individual por su clave primaria.

        Returns:
            True si la audiencia fue eliminada; False si no se encontró.
        """
        with session_scope(self._db_path) as session:
            hearing = session.get(HearingSchedule, hearing_id)
            if hearing is None:
                return False
            session.delete(hearing)
            return True
