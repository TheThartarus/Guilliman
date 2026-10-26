"""Test del zip de un solo expediente (PDF + audios + adjuntos)."""

import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime  # noqa: E402

from db import (  # noqa: E402
    AttachmentCreate,
    CaseFileCreate,
    CaseFileService,
    HearingScheduleCreate,
    HearingScheduleUpdate,
)
from db.database import dispose_engine, reset_session_factory, session_scope  # noqa: E402
from db.models import HearingSchedule  # noqa: E402
from ui.exporters import export_case_bundle  # noqa: E402


def test_case_bundle_includes_pdf_audio_and_attachment(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "bundle.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        case_id = service.create_case_file(CaseFileCreate(case_number="ZIP-1"))
        hearing_id = service.add_hearing(
            case_id,
            HearingScheduleCreate(scheduled_at=datetime(2026, 6, 1, 9, 0)),
        )
        src_audio = tmp_path / "audiencia.mp3"
        src_audio.write_bytes(b"audio")
        rel_audio, filename = service.store_audio_file(str(src_audio))
        service.update_hearing(
            hearing_id,
            HearingScheduleUpdate(audio_path=rel_audio, audio_filename=filename),
        )
        src_doc = tmp_path / "oficio.pdf"
        src_doc.write_bytes(b"%PDF")
        service.add_attachment(case_id, AttachmentCreate(name="Oficio"), str(src_doc))

        case = service.get_case_file_by_id(case_id)
        included, missing = service.case_portable_files(case)
        assert missing == []
        assert len(included) == 2

        dest = tmp_path / "llevar.zip"
        export_case_bundle(case, str(dest), included)
        with zipfile.ZipFile(dest) as archive:
            names = archive.namelist()
        assert "expediente_ZIP-1.pdf" in names
        assert any(name.startswith("audios/") and name.endswith("audiencia.mp3") for name in names)
        assert any(name.startswith("attachments/") and name.endswith("oficio.pdf") for name in names)

        # Fuera del almacén y archivo borrado no entran al zip.
        (tmp_path / "data" / rel_audio).unlink()
        with session_scope(db_path) as session:
            hearing = session.get(HearingSchedule, hearing_id)
            hearing.audio_path = "../evil.mp3"
            hearing.audio_filename = "evil.mp3"
        case = service.get_case_file_by_id(case_id)
        included, missing = service.case_portable_files(case)
        assert len(included) == 1
        assert any(name.startswith("audios/") for name in missing)
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
