"""Operaciones de lectura/escritura de expedientes (CaseFile)."""

from __future__ import annotations

import logging
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ..database import session_scope
from ..exceptions import CaseFileNotFoundError, DuplicateCaseNumberError
from ..models import (
    CaseFile,
    Defendant,
    Documentary,
    Expert,
    HearingSchedule,
    Victim,
    Witness,
)
from ..schemas import (
    CaseFileCreate,
    CaseFileRead,
    CaseFileUpdate,
    DefendantCreate,
    DocumentaryCreate,
    ExpertCreate,
    HearingScheduleCreate,
    VictimCreate,
    WitnessCreate,
)
from ._base import _ServiceMixin

logger = logging.getLogger("guilliman")


class CaseFileMethods(_ServiceMixin):
    """Métodos de búsqueda, lectura y CRUD de expedientes."""

    # ------------------------------------------------------------------ #
    # Helper compartido de filtros (usa search y count)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _build_case_file_filters(
        statement,
        *,
        query: str = "",
        defendant_name: str | None = None,
        victim_name: str | None = None,
        witness_name: str | None = None,
        defendant_status: str | None = None,
        verdict_status: str | None = None,
        indictment_date_from: date | None = None,
        indictment_date_to: date | None = None,
        hearing_from: datetime | None = None,
        hearing_to: datetime | None = None,
    ):
        """Aplica filtros AND combinables sobre un statement de CaseFile.

        Extrae la lógica de filtrado compartida entre ``search_case_files``
        y ``count_case_files`` para evitar duplicación. El filtro de texto
        libre (``query``) solo se aplica si no está vacío.

        Returns:
            El statement con los filtros aplicados.
        """
        if query.strip():
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                (CaseFile.case_number.ilike(pattern))
                | (CaseFile.prosecutor_file_number.ilike(pattern))
            )
        if defendant_status is not None:
            sub = select(Defendant.case_file_id).where(Defendant.status == defendant_status)
            statement = statement.where(CaseFile.id.in_(sub))
        if verdict_status is not None:
            sub = select(Defendant.case_file_id).where(Defendant.verdict_status == verdict_status)
            statement = statement.where(CaseFile.id.in_(sub))
        if indictment_date_from is not None:
            statement = statement.where(CaseFile.indictment_date >= indictment_date_from)
        if indictment_date_to is not None:
            statement = statement.where(CaseFile.indictment_date <= indictment_date_to)
        if defendant_name:
            sub = select(Defendant.case_file_id).where(
                Defendant.full_name.ilike(f"%{defendant_name.strip()}%")
            )
            statement = statement.where(CaseFile.id.in_(sub))
        if victim_name:
            sub = select(Victim.case_file_id).where(
                Victim.full_name.ilike(f"%{victim_name.strip()}%")
            )
            statement = statement.where(CaseFile.id.in_(sub))
        if witness_name:
            sub = select(Witness.case_file_id).where(
                Witness.full_name.ilike(f"%{witness_name.strip()}%")
            )
            statement = statement.where(CaseFile.id.in_(sub))
        if hearing_from is not None or hearing_to is not None:
            sub = select(HearingSchedule.case_file_id)
            if hearing_from is not None:
                sub = sub.where(HearingSchedule.scheduled_at >= hearing_from)
            if hearing_to is not None:
                sub = sub.where(HearingSchedule.scheduled_at <= hearing_to)
            statement = statement.where(CaseFile.id.in_(sub))
        return statement

    # ------------------------------------------------------------------ #
    # Búsqueda y lectura
    # ------------------------------------------------------------------ #
    def search_case_files(
        self,
        query: str,
        limit: int = 100,
        offset: int = 0,
        defendant_name: str | None = None,
        victim_name: str | None = None,
        witness_name: str | None = None,
        defendant_status: str | None = None,
        verdict_status: str | None = None,
        indictment_date_from: date | None = None,
        indictment_date_to: date | None = None,
        hearing_from: datetime | None = None,
        hearing_to: datetime | None = None,
    ) -> list[CaseFileRead]:
        """Busca expedientes con filtros combinables (AND).

        Filtros:
            - ``query``: texto libre sobre número de expediente O nomenclatura
              del MP (``""`` retorna todos los que cumplan el resto).
            - ``defendant_name`` / ``victim_name`` / ``witness_name``: substring
              (LIKE) insensible a mayúsculas sobre el nombre de la persona.
            - ``defendant_status`` / ``verdict_status``: coincidencia exacta.
            - ``indictment_date_from`` / ``indictment_date_to``: rango sobre la
              fecha de acusación del expediente.
            - ``hearing_from`` / ``hearing_to``: rango sobre la fecha/hora de
              audiencias (cualquiera del expediente).

        Los filtros sobre hijos usan subqueries ``IN (SELECT ...)`` para no
        generar producto cartesiano al unir las tablas.

        Returns:
            Lista de ``CaseFileRead`` que coinciden con los filtros.
            Una lista vacía si no hay resultados.

        Raises:
            ValueError: Si ``limit`` < 1 o ``offset`` < 0.
        """
        if limit < 1:
            raise ValueError("limit must be greater than or equal to 1.")
        if offset < 0:
            raise ValueError("offset must be greater than or equal to 0.")

        statement = select(CaseFile)
        statement = self._build_case_file_filters(
            statement,
            query=query,
            defendant_name=defendant_name,
            victim_name=victim_name,
            witness_name=witness_name,
            defendant_status=defendant_status,
            verdict_status=verdict_status,
            indictment_date_from=indictment_date_from,
            indictment_date_to=indictment_date_to,
            hearing_from=hearing_from,
            hearing_to=hearing_to,
        )
        statement = statement.order_by(CaseFile.case_number).limit(limit).offset(offset)
        with session_scope(self._db_path) as session:
            results = session.execute(statement).scalars().unique().all()
            return [self._to_case_file_read(case_file) for case_file in results]

    def count_case_files(
        self,
        query: str = "",
        defendant_name: str | None = None,
        victim_name: str | None = None,
        witness_name: str | None = None,
        defendant_status: str | None = None,
        verdict_status: str | None = None,
        indictment_date_from: date | None = None,
        indictment_date_to: date | None = None,
        hearing_from: datetime | None = None,
        hearing_to: datetime | None = None,
    ) -> int:
        """Cuenta expedientes que coinciden con los filtros de búsqueda.

        Misma lógica de filtros que ``search_case_files`` pero retorna
        únicamente el recuento (para paginación en la UI).
        """
        statement = select(func.count()).select_from(CaseFile)
        statement = self._build_case_file_filters(
            statement,
            query=query,
            defendant_name=defendant_name,
            victim_name=victim_name,
            witness_name=witness_name,
            defendant_status=defendant_status,
            verdict_status=verdict_status,
            indictment_date_from=indictment_date_from,
            indictment_date_to=indictment_date_to,
            hearing_from=hearing_from,
            hearing_to=hearing_to,
        )
        with session_scope(self._db_path) as session:
            return session.execute(statement).scalar_one()

    def get_case_file_by_id(self, case_file_id: int) -> CaseFileRead | None:
        """Retorna el detalle completo de un expediente por su clave primaria.

        Returns:
            ``CaseFileRead`` si existe; ``None`` si no se encontró.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                return None
            return self._to_case_file_read(case_file)

    def create_case_file(
        self,
        case_file_data: CaseFileCreate,
        defendants_list: list[DefendantCreate] | None = None,
        victims_list: list[VictimCreate] | None = None,
        witnesses_list: list[WitnessCreate] | None = None,
        documentaries_list: list[DocumentaryCreate] | None = None,
        experts_list: list[ExpertCreate] | None = None,
        hearings_list: list[HearingScheduleCreate] | None = None,
    ) -> int:
        """Registra un expediente completo (con sus hijos) de forma atómica.

        Returns:
            El ID del expediente creado.

        Raises:
            DuplicateCaseNumberError: Si ya existe un expediente con el mismo
                ``case_number``.
        """
        with session_scope(self._db_path) as session:
            case_file = CaseFile(**case_file_data.model_dump())
            for defendant_data in defendants_list or []:
                case_file.defendants.append(Defendant(**defendant_data.model_dump()))
            for victim_data in victims_list or []:
                case_file.victims.append(Victim(**victim_data.model_dump()))
            for witness_data in witnesses_list or []:
                case_file.witnesses.append(Witness(**witness_data.model_dump()))
            for documentary_data in documentaries_list or []:
                case_file.documentaries.append(Documentary(**documentary_data.model_dump()))
            for expert_data in experts_list or []:
                case_file.experts.append(Expert(**expert_data.model_dump()))
            for hearing_data in hearings_list or []:
                case_file.hearings.append(HearingSchedule(**hearing_data.model_dump()))
            session.add(case_file)
            try:
                session.flush()  # Asigna la PK antes del commit.
            except IntegrityError as error:
                logger.warning(
                    "Duplicate case_number attempted: %r",
                    case_file_data.case_number,
                )
                raise DuplicateCaseNumberError(case_file_data.case_number) from error
            return case_file.id

    def update_case_file(self, case_file_id: int, updated_data: CaseFileUpdate) -> bool:
        """Actualiza un expediente existente (semántica de actualización parcial).

        Returns:
            True si el expediente fue actualizado; False si no existe.

        Raises:
            DuplicateCaseNumberError: Si el ``case_number`` actualizado ya
                pertenece a otro expediente.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                return False
            self._apply_case_file_update(case_file, updated_data)
            session.add(case_file)
            try:
                session.flush()
            except IntegrityError as error:
                logger.warning(
                    "Duplicate case_number on update: %r",
                    updated_data.case_number,
                )
                raise DuplicateCaseNumberError(updated_data.case_number or "") from error
            return True

    def delete_case_file(self, case_file_id: int) -> bool:
        """Elimina un expediente y, vía cascada, todos sus registros relacionados.

        Returns:
            True si el expediente fue eliminado; False si no existe.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                return False
            session.delete(case_file)
            return True
