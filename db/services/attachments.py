"""Operaciones de documentos adjuntos a expedientes."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from sqlalchemy import select

from ..database import get_app_data_dir, session_scope
from ..exceptions import CaseFileNotFoundError
from ..models import Attachment, CaseFile
from ..schemas import AttachmentCreate, AttachmentIntegrityIssue
from ._base import _ServiceMixin


class AttachmentMethods(_ServiceMixin):
    """Métodos de almacenamiento y CRUD de documentos adjuntos."""

    def _resolve_attachment_dir(self) -> Path:
        """Retorna ``<data_dir>/attachments/``, creándola si no existe."""
        attachment_dir = get_app_data_dir() / "attachments"
        attachment_dir.mkdir(parents=True, exist_ok=True)
        return attachment_dir

    def store_attachment_file(self, src_path: str) -> tuple[str, str]:
        """Copia un archivo al almacén de adjuntos con nombre único.

        Returns:
            Tupla ``(ruta_relativa, nombre_original)``.

        Raises:
            FileNotFoundError: Si el archivo de origen no existe.
        """
        src = Path(src_path)
        if not src.is_file():
            raise FileNotFoundError(f"No se encontró el documento: {src_path}")
        dest = self._resolve_attachment_dir() / f"{uuid.uuid4().hex}_{src.name}"
        shutil.copy2(src, dest)
        rel_path = dest.relative_to(get_app_data_dir()).as_posix()
        return rel_path, src.name

    def get_attachment_abs_path(self, rel_path: str) -> str:
        """Retorna la ruta absoluta de un documento del store."""
        return str((get_app_data_dir() / rel_path).resolve())

    def add_attachment(
        self,
        case_file_id: int,
        attachment_data: AttachmentCreate,
        src_path: str,
    ) -> int:
        """Copia un archivo y lo registra como adjunto del expediente.

        Returns:
            El ID del adjunto creado.

        Raises:
            CaseFileNotFoundError: Si el expediente padre no existe.
        """
        with session_scope(self._db_path) as session:
            case_file = session.get(CaseFile, case_file_id)
            if case_file is None:
                raise CaseFileNotFoundError(case_file_id)
            rel_path, original_filename = self.store_attachment_file(src_path)
            attachment = Attachment(
                case_file_id=case_file_id,
                name=attachment_data.name,
                original_filename=original_filename,
                rel_path=rel_path,
            )
            session.add(attachment)
            session.flush()
            return attachment.id

    def delete_attachment(self, attachment_id: int) -> bool:
        """Elimina un adjunto y su archivo del store.

        Returns:
            True si fue eliminado; False si no existe.
        """
        with session_scope(self._db_path) as session:
            attachment = session.get(Attachment, attachment_id)
            if attachment is None:
                return False
            rel_path = attachment.rel_path
            session.delete(attachment)
            self._delete_stored_attachment(rel_path)
            return True

    def check_attachment_integrity(self) -> list[AttachmentIntegrityIssue]:
        """Lista adjuntos referenciados que faltan o viven fuera del almacén.

        Returns:
            Lista de ``AttachmentIntegrityIssue`` ordenada por expediente y
            nombre del adjunto. Vacía si todos los adjuntos existen dentro de
            ``<data_dir>/attachments/``.
        """
        statement = (
            select(Attachment, CaseFile.case_number)
            .join(CaseFile, Attachment.case_file_id == CaseFile.id)
            .order_by(CaseFile.case_number, Attachment.name)
        )
        data_dir = get_app_data_dir().resolve()
        attachment_dir = (data_dir / "attachments").resolve()
        issues: list[AttachmentIntegrityIssue] = []
        with session_scope(self._db_path) as session:
            for attachment, case_number in session.execute(statement).all():
                target = (data_dir / attachment.rel_path).resolve()
                try:
                    target.relative_to(attachment_dir)
                except ValueError:
                    reason = "outside_store"
                else:
                    reason = None if target.is_file() else "missing"
                if reason is None:
                    continue
                issues.append(
                    AttachmentIntegrityIssue(
                        attachment_id=attachment.id,
                        case_file_id=attachment.case_file_id,
                        case_number=case_number,
                        name=attachment.name,
                        rel_path=attachment.rel_path,
                        original_filename=attachment.original_filename,
                        reason=reason,
                    )
                )
        return issues
