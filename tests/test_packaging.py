"""
Guilliman Backend - Test de preparación para empaquetado (PyInstaller).

Verifica que la resolución de rutas de datos persistentes sea correcta tanto
en desarrollo como en modo congelado (exe), evitando que la BD y el
settings.json apunten a la carpeta temporal ``_MEIPASS`` (que se borra al
cerrar la app).

No modifica lógica de negocio; solo valida las funciones de resolución de
rutas de ``db.database`` y ``ui.settings``.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import get_app_data_dir
from ui.settings import get_settings_path


def _assert_under(path: Path, parent: Path, label: str) -> None:
    """Asegura que ``path`` no contiene _MEIPASS y cae bajo ``parent``."""
    assert "_MEIPASS" not in str(path), f"Ruta contaminada por _MEIPASS: {path}"
    resolved = path.resolve()
    expected_parent = parent.resolve()
    assert expected_parent in resolved.parents or resolved == expected_parent, (
        f"{label} debe estar bajo {expected_parent}, pero fue: {resolved}"
    )


def test_frozen_uses_localappdata_not_meipass(monkeypatch) -> None:
    """En modo congelado la ruta debe estar bajo LOCALAPPDATA/HOME y no en _MEIPASS."""
    orig_frozen = getattr(sys, "frozen", None)
    orig_meipass = getattr(sys, "_MEIPASS", None)
    orig_localappdata = os.environ.pop("LOCALAPPDATA", None)
    orig_data_dir = os.environ.pop("Guilliman_DATA_DIR", None)

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", "C:/fake/_MEIPASS", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", "C:/Users/Test/AppData/Local")

    try:
        data_dir = get_app_data_dir()
        settings_path = get_settings_path()

        if os.name == "nt":
            expected_root = Path(os.environ["LOCALAPPDATA"])
            _assert_under(data_dir, expected_root / "Guilliman", "get_app_data_dir")
            _assert_under(settings_path, expected_root / "Guilliman", "get_settings_path")
        else:
            expected_root = Path.home()
            _assert_under(data_dir, expected_root / ".guilliman", "get_app_data_dir")
            _assert_under(settings_path, expected_root / ".guilliman", "get_settings_path")
    finally:
        # Limpieza de los monkeypatches y la env.
        if orig_frozen is None:
            monkeypatch.delattr(sys, "frozen", raising=False)
        else:
            monkeypatch.setattr(sys, "frozen", orig_frozen, raising=False)
        if orig_meipass is None:
            monkeypatch.delattr(sys, "_MEIPASS", raising=False)
        else:
            monkeypatch.setattr(sys, "_MEIPASS", orig_meipass, raising=False)
        if orig_localappdata is not None:
            os.environ["LOCALAPPDATA"] = orig_localappdata
        if orig_data_dir is not None:
            os.environ["Guilliman_DATA_DIR"] = orig_data_dir


def test_guilliman_data_dir_override(tmp_path: Path, monkeypatch) -> None:
    """Si Guilliman_DATA_DIR está seteado, ambas rutas caen dentro de ese directorio."""
    orig_frozen = getattr(sys, "frozen", None)
    orig_data_dir = os.environ.pop("Guilliman_DATA_DIR", None)

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path))

    try:
        data_dir = get_app_data_dir()
        settings_path = get_settings_path()

        assert data_dir == tmp_path.resolve(), f"Debe usar Guilliman_DATA_DIR: {data_dir}"
        assert settings_path.parent == tmp_path.resolve(), (
            f"settings.json debe estar en Guilliman_DATA_DIR: {settings_path}"
        )
        assert settings_path.name == "settings.json"
    finally:
        if orig_frozen is None:
            monkeypatch.delattr(sys, "frozen", raising=False)
        else:
            monkeypatch.setattr(sys, "frozen", orig_frozen, raising=False)
        if orig_data_dir is not None:
            os.environ["Guilliman_DATA_DIR"] = orig_data_dir


if __name__ == "__main__":
    # Ejecutable de forma aislada sin pytest: usa un tmp_path y monkeypatch
    # mínimo implementado en línea para no acoplar la corrida a pytest.
    import tempfile

    class _Mono:
        def setattr(self, obj, name, val, raising=True):
            setattr(obj, "_orig_" + name, getattr(obj, name, None))
            setattr(obj, name, val)

        def setenv(self, k, v):
            self._old_env = getattr(self, "_old_env", {})
            if k in os.environ:
                self._old_env[k] = os.environ[k]
            os.environ[k] = v

        def delattr(self, obj, name, raising=True):
            orig = getattr(obj, "_orig_" + name, None)
            if orig is None:
                delattr(obj, name)
            else:
                setattr(obj, name, orig)

    print("Ejecutando validación manual de test_packaging...")
    m = _Mono()

    # frozen -> LOCALAPPDATA (Windows) / HOME (otros SO)
    os.environ.pop("LOCALAPPDATA", None)
    os.environ.pop("Guilliman_DATA_DIR", None)
    m.setattr(sys, "frozen", True)
    m.setattr(sys, "_MEIPASS", "C:/fake/_MEIPASS")
    if os.name == "nt":
        os.environ["LOCALAPPDATA"] = "C:/Users/Test/AppData/Local"
    try:
        d = get_app_data_dir()
        s = get_settings_path()
        if os.name == "nt":
            _assert_under(d, Path(os.environ["LOCALAPPDATA"]) / "Guilliman", "app_data")
            _assert_under(s, Path(os.environ["LOCALAPPDATA"]) / "Guilliman", "settings")
        else:
            _assert_under(d, Path.home() / ".guilliman", "app_data")
            _assert_under(s, Path.home() / ".guilliman", "settings")
        print("  OK frozen:", d, "|", s)
    finally:
        m.delattr(sys, "frozen")
        m.delattr(sys, "_MEIPASS")
        del os.environ["LOCALAPPDATA"]

    # Guilliman_DATA_DIR override
    with tempfile.TemporaryDirectory() as td:
        m.setattr(sys, "frozen", True)
        os.environ["Guilliman_DATA_DIR"] = td
        try:
            d = get_app_data_dir()
            s = get_settings_path()
            assert d == Path(td).resolve()
            assert s.parent == Path(td).resolve()
            print("  OK Guilliman_DATA_DIR:", d, "|", s)
        finally:
            m.delattr(sys, "frozen")
            del os.environ["Guilliman_DATA_DIR"]

    print("PACKAGING TEST OK")
