"""Persistencia ligera de preferencias de la app (solo frontend).

Se almacena en un archivo JSON junto al proyecto; no depende del
db ni de la base de datos de expedientes.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_KEY = "theme_mode"
_DEFAULT = "LIGHT"


def get_settings_path() -> Path:
    """Resuelve la ruta del archivo de preferencias settings.json.

    Precedencia:
        1. Variable de entorno ``Guilliman_DATA_DIR`` -> ``<dir>/settings.json``.
        2. Modo congelado (exe empaquetado): ``%LOCALAPPDATA%/Guilliman/
           settings.json`` en Windows, ``~/.guilliman/settings.json`` en otros SO.
           Evita ``__file__`` para no apuntar a la temporal ``_MEIPASS``.
        3. Desarrollo (no congelado): ``parent.parent / "settings.json"``
           (junto al proyecto), para no romper el comportamiento actual.
    """
    explicit = os.environ.get("Guilliman_DATA_DIR")
    if explicit:
        return Path(explicit).resolve() / "settings.json"

    if getattr(sys, "frozen", False):
        if os.name == "nt":
            base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
            return Path(base) / "Guilliman" / "settings.json"
        return Path.home() / ".guilliman" / "settings.json"

    return Path(__file__).resolve().parent.parent / "settings.json"


# Mantenido por compatibilidad con el frontend existente.
SETTINGS_PATH = get_settings_path()


def load_theme_mode() -> str:
    """Retorna el modo de tema guardado ('LIGHT' | 'DARK'); LIGHT por omisión."""
    path = get_settings_path()
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get(_KEY, _DEFAULT)
    except Exception:  # noqa: BLE001 - preferencia no crítica
        pass
    return _DEFAULT


def save_theme_mode(mode: str) -> None:
    """Guarda el modo de tema para conservarlo entre ejecuciones."""
    try:
        path = get_settings_path()
        # Crea el directorio contenedor (p. ej. %LOCALAPPDATA%/Guilliman) si falta.
        path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, str] = {}
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001 - archivo corrupto -> sobrescribir
                data = {}
        data[_KEY] = mode
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:  # noqa: BLE001 - si no se puede guardar, se ignora
        pass
