"""Test de verificación de integridad del almacén de adjuntos."""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (  # noqa: E402
    AttachmentCreate,
    AttachmentIntegrityIssue,
    CaseFileCreate,
    CaseFileService,
)
from db.database import dispose_engine, reset_session_factory, session_scope  # noqa: E402
from db.models import Attachment  # noqa: E402


def test_attachment_integrity_detects_missing_and_outside(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "att_integrity.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        case_id = service.create_case_file(CaseFileCreate(case_number="AI-1"))
        src = tmp_path / "cedula.pdf"
        src.write_bytes(b"%PDF-fake")
        attachment_id = service.add_attachment(
            case_id, AttachmentCreate(name="Cédula"), str(src)
        )

        # Todo en orden: sin problemas.
        assert service.check_attachment_integrity() == []

        # Borrar el archivo del store ⇒ faltante.
        case = service.get_case_file_by_id(case_id)
        rel_path = case.attachments[0].rel_path
        (tmp_path / "data" / rel_path).unlink()
        issues = service.check_attachment_integrity()
        assert len(issues) == 1
        assert issues[0].reason == "missing"
        assert issues[0].attachment_id == attachment_id
        assert issues[0].case_number == "AI-1"
        assert isinstance(issues[0], AttachmentIntegrityIssue)

        # Ruta fuera del almacén ⇒ outside_store.
        with session_scope(db_path) as session:
            att = session.get(Attachment, attachment_id)
            att.rel_path = "../evil.pdf"

        issues = service.check_attachment_integrity()
        assert len(issues) == 1
        assert issues[0].reason == "outside_store"
        assert issues[0].attachment_id == attachment_id
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()


def test_attachment_integrity_empty_when_all_present(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "att_clean.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        case_id = service.create_case_file(CaseFileCreate(case_number="AC-1"))
        src = tmp_path / "doc.pdf"
        src.write_bytes(b"doc")
        service.add_attachment(case_id, AttachmentCreate(name="Doc"), str(src))
        assert service.check_attachment_integrity() == []
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
