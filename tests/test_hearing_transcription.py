"""Test de la transcripción de una audiencia.

Cubre:
    - La audiencia nace sin transcripción.
    - ``update_hearing`` persiste la transcripción y el detalle la devuelve.
    - Un PATCH que no toca la transcripción (p. ej. solo notas) la conserva.
    - ``update_hearing`` con ``transcription=None`` la limpia.
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (  # noqa: E402
    CaseFileCreate,
    CaseFileService,
    HearingScheduleCreate,
    HearingScheduleUpdate,
)
from db.database import dispose_engine, reset_session_factory  # noqa: E402


def _hearing(service: CaseFileService, case_id: int):
    return service.get_case_file_by_id(case_id).hearings[0]


def test_hearing_transcription_lifecycle(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "transcription.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        case_id = service.create_case_file(CaseFileCreate(case_number="ACT-1"))
        hearing_id = service.add_hearing(
            case_id,
            HearingScheduleCreate(scheduled_at=datetime(2026, 1, 10, 9, 0)),
        )
        assert _hearing(service, case_id).transcription is None

        transcripcion = "TRANSCRIPCIÓN DE AUDIENCIA\n\nSe dejó constancia de lo siguiente.\nFin."
        assert service.update_hearing(
            hearing_id, HearingScheduleUpdate(transcription=transcripcion)
        )
        assert _hearing(service, case_id).transcription == transcripcion

        # Un PATCH de otro campo no debe borrar la transcripción.
        assert service.update_hearing(
            hearing_id, HearingScheduleUpdate(notes="Nota posterior")
        )
        assert _hearing(service, case_id).transcription == transcripcion

        # Limpiar explícitamente la transcripción.
        assert service.update_hearing(
            hearing_id, HearingScheduleUpdate(transcription=None)
        )
        assert _hearing(service, case_id).transcription is None
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
