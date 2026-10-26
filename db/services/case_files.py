"""Operaciones de lectura/escritura de expedientes (CaseFile)."""

from __future__ import annotations

import logging
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from pathlib import Path

from ..database import get_app_data_dir, session_scope
from ..exceptions import CaseFileNotFoundError, DuplicateCaseNumberError
from ..models import (
    CaseFile,
    Crime,
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
    CrimeCreate,
    DefendantCreate,
    DefendantRead,
    DuplicateNationalIdItem,
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
        crime_type: str | None = None,
        origin_location: str | None = None,
        indictment_date_from: date | None = None,
        indictment_date_to: date | None = None,
        hearing_from: datetime | None = None,
        hearing_to: datetime | None = None,
        include_archived: bool = False,
    ):
        """Aplica filtros AND combinables sobre un statement de CaseFile.

        Extrae la lógica de filtrado compartida entre ``search_case_files``
        y ``count_case_files`` para evitar duplicación. El filtro de texto
        libre (``query``) solo se aplica si no está vacío. Los expedientes
        archivados se excluyen salvo que ``include_archived`` sea True.

        Returns:
            El statement con los filtros aplicados.
        """
        if not include_archived:
            statement = statement.where(CaseFile.archived_at.is_(None))
        if query.strip():
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                (CaseFile.case_number.ilike(pattern))
                | (CaseFile.prosecutor_file_number.ilike(pattern))
                | (CaseFile.offense_description.ilike(pattern))
                | (CaseFile.facts_summary.ilike(pattern))
                | (CaseFile.location.ilike(pattern))
            )
        if defendant_status is not None:
            sub = select(Defendant.case_file_id).where(Defendant.status == defendant_status)
            statement = statement.where(CaseFile.id.in_(sub))
        if verdict_status is not None:
            sub = select(Defendant.case_file_id).where(Defendant.verdict_status == verdict_status)
            statement = statement.where(CaseFile.id.in_(sub))
        if crime_type is not None:
            sub = select(Crime.case_file_id).where(Crime.crime_type == crime_type)
            statement = statement.where(CaseFile.id.in_(sub))
        if origin_location:
            statement = statement.where(
                CaseFile.origin_location.ilike(f"%{origin_location.strip()}%")
            )
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
        crime_type: str | None = None,
        origin_location: str | None = None,
        indictment_date_from: date | None = None,
        indictment_date_to: date | None = None,
        hearing_from: datetime | None = None,
        hearing_to: datetime | None = None,
        include_archived: bool = False,
    ) -> list[CaseFileRead]:
        """Busca expedientes con filtros combinables (AND).

        Filtros:
            - ``query``: texto libre sobre número de expediente, nomenclatura
              del MP, descripción del delito, resumen de hechos o ubicación
              (``""`` retorna todos los que cumplan el resto).
            - ``defendant_name`` / ``victim_name`` / ``witness_name``: substring
              (LIKE) insensible a mayúsculas sobre el nombre de la persona.
            - ``defendant_status`` / ``verdict_status``: coincidencia exacta.
            - ``crime_type``: coincidencia exacta sobre el tipo de delito
              (``Ordinario``, ``Violencia``, ``Droga``, ``Armas``).
            - ``origin_location``: substring sobre la procedencia del expediente.
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
            crime_type=crime_type,
            origin_location=origin_location,
            indictment_date_from=indictment_date_from,
            indictment_date_to=indictment_date_to,
            hearing_from=hearing_from,
            hearing_to=hearing_to,
            include_archived=include_archived,
        )
        statement = statement.order_by(CaseFile.case_number).limit(limit).offset(offset)
        with session_scope(self._db_path) as session:
            results = session.execute(statement).scalars().unique().all()
            return [self._to_case_file_read(case_file) for case_file in results]

    def find_duplicate_national_id(
        self,
        national_id: str,
        exclude_case_file_id: int | None = None,
    ) -> list[DuplicateNationalIdItem]:
        """Busca acusados, víctimas y testigos con la misma cédula en expedientes activos.

        Se ignora la cédula vacía o nula. Se excluye el expediente indicado (útil
        al editar una persona dentro de su propio expediente).

        Returns:
            Lista de ``DuplicateNationalIdItem`` ordenada por tipo de entidad,
            expediente y nombre. Vacía si no hay coincidencias.
        """
        target = national_id.strip()
        if not target:
            return []

        def _rows(model, entity_type: str) -> list[DuplicateNationalIdItem]:
            sub = (
                select(model, CaseFile.case_number)
                .join(CaseFile, model.case_file_id == CaseFile.id)
                .where(model.national_id == target)
                .where(CaseFile.archived_at.is_(None))
            )
            if exclude_case_file_id is not None:
                sub = sub.where(CaseFile.id != exclude_case_file_id)
            rows: list[DuplicateNationalIdItem] = []
            with session_scope(self._db_path) as session:
                for person, case_number in session.execute(sub).all():
                    rows.append(
                        DuplicateNationalIdItem(
                            entity_type=entity_type,
                            entity_id=person.id,
                            full_name=person.full_name,
                            national_id=target,
                            case_file_id=person.case_file_id,
                            case_number=case_number,
                        )
                    )
            return rows

        duplicates: list[DuplicateNationalIdItem] = []
        duplicates.extend(_rows(Defendant, "defendant"))
        duplicates.extend(_rows(Victim, "victim"))
        duplicates.extend(_rows(Witness, "witness"))
        duplicates.sort(
            key=lambda d: (d.entity_type, d.case_number, d.full_name)
        )
        return duplicates

    def count_case_files(
        self,
        query: str = "",
        defendant_name: str | None = None,
        victim_name: str | None = None,
        witness_name: str | None = None,
        defendant_status: str | None = None,
        verdict_status: str | None = None,
        crime_type: str | None = None,
        origin_location: str | None = None,
        indictment_date_from: date | None = None,
        indictment_date_to: date | None = None,
        hearing_from: datetime | None = None,
        hearing_to: datetime | None = None,
        include_archived: bool = False,
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
            crime_type=crime_type,
            origin_location=origin_location,
            indictment_date_from=indictment_date_from,
            indictment_date_to=indictment_date_to,
            hearing_from=hearing_from,
            hearing_to=hearing_to,
            include_archived=include_archived,
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
        crimes_list: list[CrimeCreate] | None = None,
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
            for crime_data in crimes_list or []:
                case_file.crimes.append(Crime(**crime_data.model_dump()))
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

    def archive_case_file(self, case_file_id: int) -> bool:
        """Archiva lógicamente un expediente (no borra datos ni audios).

        Returns:
            True si fue archivado; False si no existe o ya estaba archivado.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None or case_file.archived_at is not None:
                return False
            case_file.archived_at = datetime.now()
            session.add(case_file)
            return True

    def unarchive_case_file(self, case_file_id: int) -> bool:
        """Reactiva un expediente archivado.

        Returns:
            True si fue restaurado; False si no existe o no estaba archivado.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None or case_file.archived_at is None:
                return False
            case_file.archived_at = None
            session.add(case_file)
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
            # Recolectar antes de eliminar: la cascada borra las filas de
            # audiencias y perderíamos sus audio_path.
            audio_paths = [h.audio_path for h in case_file.hearings if h.audio_path]
            attachment_paths = [
                a.rel_path for a in case_file.attachments if a.rel_path
            ]
            session.delete(case_file)
            for rel_path in audio_paths:
                self._delete_stored_audio(rel_path)
            for rel_path in attachment_paths:
                self._delete_stored_attachment(rel_path)
            return True


    def case_portable_files(
        self, case: CaseFileRead
    ) -> tuple[list[tuple[str, str]], list[str]]:
        """Archivos del expediente que pueden viajar en el zip.

        Returns:
            ``(incluidos, omitidos)``. Cada incluido es
            ``(ruta_absoluta, nombre_en_zip)``. Se omiten rutas fuera de
            ``audios/`` o ``attachments/`` y archivos que ya no están en disco.
        """
        data_dir = get_app_data_dir().resolve()
        included: list[tuple[str, str]] = []
        missing: list[str] = []

        def consider(rel: str, store: str, arc: str) -> None:
            target = (data_dir / rel).resolve()
            try:
                target.relative_to((data_dir / store).resolve())
            except ValueError:
                missing.append(arc)
                return
            if not target.is_file():
                missing.append(arc)
                return
            included.append((str(target), arc))

        for hearing in case.hearings:
            if not hearing.audio_path:
                continue
            name = _portable_arc_name(
                hearing.audio_filename or Path(hearing.audio_path).name
            )
            consider(hearing.audio_path, "audios", f"audios/{hearing.id}_{name}")
        for attachment in case.attachments:
            name = _portable_arc_name(attachment.original_filename or attachment.name)
            consider(attachment.rel_path, "attachments", f"attachments/{attachment.id}_{name}")
        return included, missing



def _portable_arc_name(name: str) -> str:
    """Nombre de archivo seguro para meter en el zip."""
    cleaned = "".join(ch if ch not in '\\/:*?"<>|' else "_" for ch in name).strip()
    return cleaned or "archivo"

