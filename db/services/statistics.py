"""Estadísticas agregadas para la vista de reportes."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func, select

from ..database import session_scope
from ..models import CaseFile, Crime, HearingSchedule
from ..schemas import CountItem, StatisticsSummary
from ._base import _ServiceMixin


class StatisticsMethods(_ServiceMixin):
    """Cálculo de contadores y agrupaciones para estadísticas."""

    def get_statistics(self) -> StatisticsSummary:
        """Retorna el resumen estadístico de expedientes y audiencias.

        Los conteos por tipo de delito consideran expedientes activos y pueden
        sumar más que el total (un expediente puede tener varios delitos).
        """
        with session_scope(self._db_path) as session:
            total_cases = session.execute(
                select(func.count()).select_from(CaseFile)
            ).scalar_one()
            archived_cases = session.execute(
                select(func.count())
                .select_from(CaseFile)
                .where(CaseFile.archived_at.is_not(None))
            ).scalar_one()
            crime_rows = session.execute(
                select(
                    Crime.crime_type,
                    func.count(func.distinct(Crime.case_file_id)),
                )
                .join(CaseFile, Crime.case_file_id == CaseFile.id)
                .where(CaseFile.archived_at.is_(None))
                .group_by(Crime.crime_type)
                .order_by(
                    func.count(func.distinct(Crime.case_file_id)).desc(),
                    Crime.crime_type,
                )
            ).all()
            prosecutor_rows = session.execute(
                select(CaseFile.prosecutor_name, func.count())
                .where(CaseFile.archived_at.is_(None))
                .where(CaseFile.prosecutor_name.is_not(None))
                .group_by(CaseFile.prosecutor_name)
                .order_by(func.count().desc(), CaseFile.prosecutor_name)
                .limit(10)
            ).all()

            today = date.today()
            start_year, start_month = today.year, today.month - 11
            while start_month <= 0:
                start_month += 12
                start_year -= 1
            start = date(start_year, start_month, 1)
            hearing_dates = (
                session.execute(
                    select(HearingSchedule.scheduled_at)
                    .join(CaseFile, HearingSchedule.case_file_id == CaseFile.id)
                    .where(CaseFile.archived_at.is_(None))
                    .where(
                        HearingSchedule.scheduled_at
                        >= datetime.combine(start, datetime.min.time())
                    )
                )
                .scalars()
                .all()
            )

        keys: list[str] = []
        year, month = start_year, start_month
        for _ in range(12):
            keys.append(f"{year:04d}-{month:02d}")
            month += 1
            if month > 12:
                month = 1
                year += 1
        month_counts = {key: 0 for key in keys}
        for scheduled_at in hearing_dates:
            key = scheduled_at.strftime("%Y-%m")
            if key in month_counts:
                month_counts[key] += 1

        return StatisticsSummary(
            total_cases=total_cases,
            active_cases=total_cases - archived_cases,
            archived_cases=archived_cases,
            cases_by_crime_type=[
                CountItem(label=label or "—", count=count)
                for label, count in crime_rows
            ],
            cases_by_prosecutor=[
                CountItem(label=label or "—", count=count)
                for label, count in prosecutor_rows
            ],
            hearings_by_month=[
                CountItem(label=key, count=month_counts[key]) for key in keys
            ],
        )
