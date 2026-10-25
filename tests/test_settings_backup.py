"""Test de la persistencia del último respaldo en settings.json."""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui import settings  # noqa: E402


def test_last_backup_at_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path))
    assert settings.load_last_backup_at() is None

    stamp = datetime(2026, 1, 2, 3, 4, 5)
    settings.save_last_backup_at(stamp)
    assert settings.load_last_backup_at() == stamp

    # El tema sigue persistiendo en el mismo archivo sin pisar el respaldo.
    settings.save_theme_mode("DARK")
    assert settings.load_theme_mode() == "DARK"
    assert settings.load_last_backup_at() == stamp
