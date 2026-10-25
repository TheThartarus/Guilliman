"""Test de la rotación de respaldos automáticos."""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import CaseFileService  # noqa: E402
from db.database import dispose_engine, reset_session_factory  # noqa: E402


def test_backup_data_rotates_to_keep_limit(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "rotation.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        paths = [Path(service.backup_data(keep=2)) for _ in range(4)]
        backups_dir = tmp_path / "data" / "backups"
        backups = sorted(backups_dir.glob("guilliman_backup_*.zip"))
        assert len(backups) == 2
        assert set(backups) == set(paths[-2:])

        # Un destino explícito no participa en la rotación de la carpeta por defecto.
        custom = tmp_path / "custom.zip"
        service.backup_data(str(custom))
        assert custom.is_file()
        assert len(sorted(backups_dir.glob("guilliman_backup_*.zip"))) == 2
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
