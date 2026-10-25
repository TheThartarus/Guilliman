"""Test del ciclo de vida de los documentos adjuntos."""

import os
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (  # noqa: E402
    AttachmentCreate,
    CaseFileCreate,
    CaseFileService,
)
from db.database import dispose_engine, reset_session_factory  # noqa: E402


def test_attachment_lifecycle(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "attachments.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        case_id = service.create_case_file(CaseFileCreate(case_number="ATT-1"))
        src = tmp_path / "cedula.pdf"
        src.write_bytes(b"%PDF-fake")
        attachment_id = service.add_attachment(
            case_id, AttachmentCreate(name="Cédula"), str(src)
        )

        case = service.get_case_file_by_id(case_id)
        assert len(case.attachments) == 1
        attachment = case.attachments[0]
        assert attachment.id == attachment_id
        assert attachment.name == "Cédula"
        assert attachment.original_filename == "cedula.pdf"
        stored = tmp_path / "data" / attachment.rel_path
        assert stored.is_file()
        assert stored.read_bytes() == b"%PDF-fake"
        assert Path(service.get_attachment_abs_path(attachment.rel_path)).is_file()

        # El respaldo completo incluye la carpeta attachments/.
        backup = Path(service.backup_data(str(tmp_path / "backup.zip")))
        with zipfile.ZipFile(backup) as archive:
            names = archive.namelist()
        assert any(name.startswith("attachments/") for name in names)

        # Eliminar el adjunto borra el archivo del store.
        assert service.delete_attachment(attachment_id)
        assert not stored.exists()
        assert service.get_case_file_by_id(case_id).attachments == []

        # Eliminar el expediente también borra los adjuntos.
        second_src = tmp_path / "oficio.pdf"
        second_src.write_bytes(b"oficio")
        second_id = service.add_attachment(
            case_id, AttachmentCreate(name="Oficio"), str(second_src)
        )
        second = next(
            a for a in service.get_case_file_by_id(case_id).attachments
            if a.id == second_id
        )
        second_stored = tmp_path / "data" / second.rel_path
        assert second_stored.is_file()
        assert service.delete_case_file(case_id)
        assert not second_stored.exists()

        # Restaurar el respaldo previo recupera el expediente y su adjunto.
        service.restore_data(str(backup))
        restored_case = service.get_case_file_by_id(case_id)
        assert restored_case is not None and len(restored_case.attachments) == 1
        restored_path = (
            tmp_path / "data" / restored_case.attachments[0].rel_path
        )
        assert restored_path.is_file()
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
