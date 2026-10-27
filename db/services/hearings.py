"""Operaciones de audiencias (HearingSchedule) y vista de agenda."""

from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select

from ..database import get_app_data_dir, session_scope
from ..exceptions import CaseFileNotFoundError
from ..models import CaseFile, HearingSchedule
from ..schemas import (
    AudioIntegrityIssue,
    HearingClashItem,
    HearingScheduleCreate,
    HearingScheduleUpdate,
    ScheduledHearingItem,
)
from ._base import _ServiceMixin


class HearingMethods(_ServiceMixin):
    """Métodos de audiencias y listado de agenda."""

    def _resolve_audio_dir(self) -> Path:
        """Retorna ``<data_dir>/audios/``, creándola si no existe."""
        audio_dir = get_app_data_dir() / "audios"
        audio_dir.mkdir(parents=True, exist_ok=True)
        return audio_dir

    def store_audio_file(self, src_path: str) -> tuple[str, str]:
        """Copia un archivo de audio al almacén local con nombre único.

        Args:
            src_path: Ruta al archivo de origen.

        Returns:
            Tupla ``(ruta_relativa, nombre_original)`` donde ``ruta_relativa`` es
            relativa al directorio de datos de la app (idónea para guardar en BD)
            y ``nombre_original`` es el nombre del archivo de origen para mostrar
            al usuario.

        Raises:
            FileNotFoundError: Si el archivo de origen no existe.
        """
        src = Path(src_path)
        if not src.exists():
            raise FileNotFoundError(f"No se encontró el archivo de audio: {src_path}")
        audio_dir = self._resolve_audio_dir()
        unique_name = f"{uuid.uuid4().hex}_{src.name}"
        dest = audio_dir / unique_name
        shutil.copy2(src, dest)
        rel_path = dest.relative_to(get_app_data_dir()).as_posix()
        return rel_path, src.name

    def get_audio_abs_path(self, rel_path: str) -> str:
        """Retorna la ruta absoluta de un audio del store (para reproducción)."""
        return str((get_app_data_dir() / rel_path).resolve())

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
            .where(CaseFile.archived_at.is_(None))
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
                        has_audio=bool(hearing.audio_path),
                        has_transcription=bool(hearing.transcription),
                    )
                )
        return items

    def count_hearings_missing_audio(self) -> int:
        """Cuenta las audiencias (de expedientes activos) sin audio asociado."""
        statement = (
            select(func.count())
            .select_from(HearingSchedule)
            .join(CaseFile, HearingSchedule.case_file_id == CaseFile.id)
            .where(HearingSchedule.audio_path.is_(None))
            .where(CaseFile.archived_at.is_(None))
        )
        with session_scope(self._db_path) as session:
            return session.execute(statement).scalar_one()

    def count_hearings_missing_transcription(self) -> int:
        """Cuenta las audiencias (de expedientes activos) sin transcripción registrada."""
        statement = (
            select(func.count())
            .select_from(HearingSchedule)
            .join(CaseFile, HearingSchedule.case_file_id == CaseFile.id)
            .where(HearingSchedule.transcription.is_(None))
            .where(CaseFile.archived_at.is_(None))
        )
        with session_scope(self._db_path) as session:
            return session.execute(statement).scalar_one()

    def find_hearing_clashes(
        self,
        scheduled_at: datetime,
        exclude_hearing_id: int | None = None,
    ) -> list[HearingClashItem]:
        """Busca otras audiencias (de expedientes activos) con la misma fecha/hora.

        Útil para detectar choques de agenda antes de crear o mover una audiencia.

        Args:
            scheduled_at: Fecha/hora de la audiencia a validar.
            exclude_hearing_id: Audiencia a excluir del resultado (útil al editar
                una audiencia existente para no chocar contra sí misma).

        Returns:
            Lista de ``HearingClashItem`` ordenada por expediente y fecha.
        """
        statement = (
            select(HearingSchedule, CaseFile.case_number)
            .join(CaseFile, HearingSchedule.case_file_id == CaseFile.id)
            .where(HearingSchedule.scheduled_at == scheduled_at)
            .where(CaseFile.archived_at.is_(None))
        )
        if exclude_hearing_id is not None:
            statement = statement.where(HearingSchedule.id != exclude_hearing_id)
        statement = statement.order_by(CaseFile.case_number, HearingSchedule.id)
        clashes: list[HearingClashItem] = []
        with session_scope(self._db_path) as session:
            for hearing, case_number in session.execute(statement).all():
                clashes.append(
                    HearingClashItem(
                        hearing_id=hearing.id,
                        case_file_id=hearing.case_file_id,
                        case_number=case_number,
                        scheduled_at=hearing.scheduled_at,
                        hearing_type=hearing.hearing_type,
                        status=hearing.status,
                    )
                )
        return clashes

    def check_audio_integrity(self) -> list[AudioIntegrityIssue]:
        """Lista audios referenciados que faltan o viven fuera del almacén.

        Returns:
            Lista de ``AudioIntegrityIssue`` ordenada por expediente y fecha.
            Vacía si todos los audios referenciados existen dentro de
            ``<data_dir>/audios/``.
        """
        statement = (
            select(HearingSchedule, CaseFile.case_number)
            .join(CaseFile, HearingSchedule.case_file_id == CaseFile.id)
            .where(HearingSchedule.audio_path.is_not(None))
            .order_by(CaseFile.case_number, HearingSchedule.scheduled_at)
        )
        data_dir = get_app_data_dir().resolve()
        audio_dir = (data_dir / "audios").resolve()
        issues: list[AudioIntegrityIssue] = []
        with session_scope(self._db_path) as session:
            for hearing, case_number in session.execute(statement).all():
                target = (data_dir / hearing.audio_path).resolve()
                try:
                    target.relative_to(audio_dir)
                except ValueError:
                    reason = "outside_store"
                else:
                    reason = None if target.is_file() else "missing"
                if reason is None:
                    continue
                issues.append(
                    AudioIntegrityIssue(
                        case_file_id=hearing.case_file_id,
                        case_number=case_number,
                        hearing_id=hearing.id,
                        scheduled_at=hearing.scheduled_at,
                        audio_path=hearing.audio_path,
                        audio_filename=hearing.audio_filename,
                        reason=reason,
                    )
                )
        return issues

    def add_hearing(self, case_file_id: int, hearing_data: HearingScheduleCreate) -> int:
        """Agrega una audiencia a un expediente existente.

        Se permite cualquier fecha (incluidas pasadas): las audiencias suelen
        registrarse o completarse después de realizarse.

        Returns:
            El ID de la audiencia creada.

        Raises:
            CaseFileNotFoundError: Si el expediente padre no existe.
        """
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
            old_audio = hearing.audio_path
            self._apply_hearing_update(hearing, update)
            # Si el audio cambió (o pasó a None), el archivo viejo queda huérfano.
            if old_audio and old_audio != hearing.audio_path:
                self._delete_stored_audio(old_audio)
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

    def duplicate_hearing(self, hearing_id: int, days: int = 7) -> int | None:
        """Duplica una audiencia programándola ``days`` días después.

        Copia tipo y notas; el estado vuelve a ``Scheduled`` y no copia audio
        ni transcripción (son propios de la audiencia original).

        Returns:
            El ID de la nueva audiencia, o ``None`` si la original no existe.
        """
        with session_scope(self._db_path) as session:
            original = session.get(HearingSchedule, hearing_id)
            if original is None:
                return None
            copy = HearingSchedule(
                case_file_id=original.case_file_id,
                scheduled_at=original.scheduled_at + timedelta(days=days),
                hearing_type=original.hearing_type,
                status="Scheduled",
                notes=original.notes,
            )
            session.add(copy)
            session.flush()
            return copy.id

    def delete_hearing(self, hearing_id: int) -> bool:
        """Elimina una audiencia individual por su clave primaria.

        Returns:
            True si la audiencia fue eliminada; False si no se encontró.
        """
        with session_scope(self._db_path) as session:
            hearing = session.get(HearingSchedule, hearing_id)
            if hearing is None:
                return False
            self._delete_stored_audio(hearing.audio_path)
            session.delete(hearing)
            return True
