"""Persistencia ligera de preferencias de la app (solo frontend).

Se almacena en un archivo JSON junto al proyecto; no depende del
db ni de la base de datos de expedientes.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

_KEY = "theme_mode"
_DEFAULT = "LIGHT"
_LAST_BACKUP_KEY = "last_backup_at"
_SEARCH_FILTERS_KEY = "search_filters"
_WINDOW_STATE_KEY = "window_state"


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


def _read_data() -> dict:
    """Lee el JSON de preferencias; devuelve un dict vacío si falta o es inválido."""
    path = get_settings_path()
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001 - preferencias no críticas
        pass
    return {}


def _write_data(data: dict) -> None:
    """Escribe las preferencias, ignorando errores de I/O."""
    try:
        path = get_settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:  # noqa: BLE001 - si no se puede guardar, se ignora
        pass


def load_theme_mode() -> str:
    """Retorna el modo de tema guardado ('LIGHT' | 'DARK'); LIGHT por omisión."""
    return _read_data().get(_KEY, _DEFAULT)


def save_theme_mode(mode: str) -> None:
    """Guarda el modo de tema para conservarlo entre ejecuciones."""
    data = _read_data()
    data[_KEY] = mode
    _write_data(data)


def load_last_backup_at() -> datetime | None:
    """Retorna la fecha/hora del último respaldo registrado (o None)."""
    value = _read_data().get(_LAST_BACKUP_KEY)
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def save_last_backup_at(value: datetime | None = None) -> None:
    """Registra el momento del último respaldo (por defecto, ahora)."""
    data = _read_data()
    data[_LAST_BACKUP_KEY] = (value or datetime.now()).isoformat(timespec="seconds")
    _write_data(data)


def load_search_filters() -> dict:
    """Retorna los filtros de búsqueda guardados (dict vacío si no hay)."""
    value = _read_data().get(_SEARCH_FILTERS_KEY)
    return value if isinstance(value, dict) else {}


def save_search_filters(filters: dict) -> None:
    """Persiste los filtros de búsqueda entre ejecuciones."""
    data = _read_data()
    data[_SEARCH_FILTERS_KEY] = filters
    _write_data(data)


def load_window_state() -> dict:
    """Retorna el estado guardado de la ventana (dict vacío si no hay)."""
    value = _read_data().get(_WINDOW_STATE_KEY)
    return value if isinstance(value, dict) else {}


def save_window_state(maximized: bool, width: int, height: int) -> None:
    """Persiste si la ventana estaba maximizada y su tamaño normal."""
    data = _read_data()
    data[_WINDOW_STATE_KEY] = {
        "maximized": bool(maximized),
        "width": int(width),
        "height": int(height),
    }
    _write_data(data)
