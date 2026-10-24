"""
Guilliman Backend - Test del soporte de audio en audiencias.

Cubre el ciclo de vida completo del audio de una audiencia, sin UI ni
transcripción:
    - Crear expediente + audiencia sin audio.
    - ``store_audio_file`` copia el archivo al store y devuelve ruta + nombre.
    - ``update_hearing`` persiste el ``audio_path`` (visible en el detalle).
    - ``update_hearing`` a ``None`` borra el archivo del store.
    - ``delete_hearing`` con audio borra el archivo.

Usa ``Guilliman_DATA_DIR`` (para aislar ``audios/``) y una BD temporal.
"""

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (  # noqa: E402
    CaseFileCreate,
    CaseFileService,
    HearingScheduleCreate,
    HearingScheduleUpdate,
)
from db.database import dispose_engine, reset_session_factory  # noqa: E402


def _find_hearing(service: CaseFileService, case_id: int, hearing_id: int):
    detail = service.get_case_file_by_id(case_id)
    return next(h for h in detail.hearings if h.id == hearing_id)


def _exercise_lifecycle(service: CaseFileService, data_dir: Path, work_dir: Path) -> None:
    """Recorre el ciclo de vida del audio sobre un service ya inicializado."""
    case_id = service.create_case_file(CaseFileCreate(case_number="01001-2026-AUDIO"))
    hearing_id = service.add_hearing(
        case_id,
        HearingScheduleCreate(
            scheduled_at=datetime(2030, 1, 1, 9, 0),
            hearing_type="Apertura",
        ),
    )

    # Sin audio todavía.
    hearing = _find_hearing(service, case_id, hearing_id)
    assert hearing.audio_path is None and hearing.audio_filename is None

    # store_audio_file copia y devuelve (ruta_relativa, nombre_original).
    src = work_dir / "evidencia.mp3"
    src.write_bytes(b"audio-bytes")
    rel_path, filename = service.store_audio_file(str(src))
    assert filename == "evidencia.mp3"
    assert rel_path.startswith("audios/")
    stored = Path(data_dir) / rel_path
    assert stored.is_file() and stored.read_bytes() == b"audio-bytes"

    # update_hearing persiste el audio y el detalle lo devuelve.
    assert service.update_hearing(
        hearing_id,
        HearingScheduleUpdate(audio_path=rel_path, audio_filename=filename),
    )
    hearing = _find_hearing(service, case_id, hearing_id)
    assert hearing.audio_path == rel_path
    assert hearing.audio_filename == filename

    # update_hearing a None borra el archivo viejo del store.
    assert service.update_hearing(
        hearing_id,
        HearingScheduleUpdate(audio_path=None, audio_filename=None),
    )
    assert _find_hearing(service, case_id, hearing_id).audio_path is None
    assert not stored.exists(), "update a None debe borrar el archivo del store"

    # delete_hearing con audio borra el archivo.
    rel_path2, filename2 = service.store_audio_file(str(src))
    assert service.update_hearing(
        hearing_id,
        HearingScheduleUpdate(audio_path=rel_path2, audio_filename=filename2),
    )
    stored2 = Path(data_dir) / rel_path2
    assert stored2.is_file()
    assert service.delete_hearing(hearing_id)
    assert not stored2.exists(), "delete_hearing debe borrar el archivo del store"

    # backup_data() sin argumentos usa <data_dir>/backups/ y devuelve ruta existente.
    backup_path = service.backup_data()
    assert Path(backup_path).is_file() and backup_path.endswith(".zip")


def test_hearing_audio_lifecycle(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("Guilliman_DATA_DIR", str(data_dir))
    db_path = str(tmp_path / "test_hearing_audio.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        _exercise_lifecycle(service, data_dir, tmp_path)
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        data_dir = root / "data"
        data_dir.mkdir()
        os.environ["Guilliman_DATA_DIR"] = str(data_dir)
        db_path = str(root / "test_hearing_audio.db")
        service = CaseFileService(db_path)
        service.init_db()
        try:
            _exercise_lifecycle(service, data_dir, root)
            print("HEARING AUDIO TEST OK")
        finally:
            service.close()
            dispose_engine(db_path)
            reset_session_factory()
            os.environ.pop("Guilliman_DATA_DIR", None)
