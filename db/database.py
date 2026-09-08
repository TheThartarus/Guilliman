"""
Guilliman Backend - Configuración de base de datos.

Provee el engine de SQLite, la fábrica de sesiones y los helpers de
transacción para la base de datos local ``case_files.db``. La capa de
servicio (``service.py``) consume este módulo; el frontend nunca lo toca
directamente.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, close_all_sessions, sessionmaker


def get_app_data_dir() -> Path:
    """Resuelve el directorio donde la app guarda sus datos persistentes.

    Precedencia:
        1. Variable de entorno ``Guilliman_DATA_DIR`` (ruta explícita, útil para
           pruebas y despliegues portables).
        2. Modo congelado (exe empaquetado con PyInstaller):
           ``%LOCALAPPDATA%/Guilliman`` en Windows, ``~/.guilliman`` en otros SO.
           No se usa ``__file__`` porque bajo un exe apunta a la carpeta
           temporal ``_MEIPASS``, que se borra al cerrar la aplicación.
        3. Desarrollo (no congelado): la raíz del proyecto
           (``parent.parent`` de este archivo), para no romper tests y dev.

    Returns:
        Ruta absoluta del directorio de datos de la app.
    """
    explicit = os.environ.get("Guilliman_DATA_DIR")
    if explicit:
        return Path(explicit).resolve()

    if getattr(sys, "frozen", False):
        if os.name == "nt":
            base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
            return Path(base) / "Guilliman"
        return Path.home() / ".guilliman"

    return Path(__file__).resolve().parent.parent


# El archivo de base de datos por defecto vive dentro del directorio de datos
# de la app (ver get_app_data_dir), de modo que sobrevive al empaquetado.
DEFAULT_DB_PATH = get_app_data_dir() / "case_files.db"

# Cachés por ruta resuelta. Reutilizar el mismo engine para la misma base de
# datos evita fugas de conexiones y bloqueos del archivo SQLite en Windows
# (un engine sin disponer mantiene un handle abierto sobre el archivo).
_engines: dict[str, Engine] = {}
_session_factories: dict[str, sessionmaker[Session]] = {}


def _resolve_cache_key(db_path: str | Path | None) -> str:
    """Resuelve la ruta absoluta usada como clave de caché."""
    path = Path(db_path).resolve() if db_path else DEFAULT_DB_PATH.resolve()
    return str(path)


def get_db_path(db_path: str | Path | None = None) -> str:
    """Resuelve la URL de conexión de SQLite.

    Args:
        db_path: Ruta de archivo personalizada opcional. Si se omite se usa
            ``case_files.db``, ubicado junto a la raíz del proyecto.

    Returns:
        Una cadena de URL de conexión SQLAlchemy tal como
        ``sqlite:///C:/.../case_files.db``.
    """
    path = Path(db_path).resolve() if db_path else DEFAULT_DB_PATH
    # Crea el directorio contenedor (p. ej. %LOCALAPPDATA%/Guilliman) de forma
    # automática para que el primer arranque no falle por carpeta inexistente.
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path.as_posix()}"


def get_engine(db_path: str | Path | None = None) -> Engine:
    """Devuelve el engine cacheado para la ruta indicada (lo crea si no existe).

    Args:
        db_path: Ruta personalizada opcional; None usa la base por defecto.

    Returns:
        El engine SQLAlchemy asociado a esa ruta. Llamar repetidamente con
        la misma ruta siempre retorna EL MISMO engine (no se crean duplicados
        ni se descartan engines sin disponer).
    """
    key = _resolve_cache_key(db_path)
    if key not in _engines:
        _engines[key] = create_engine(
            get_db_path(db_path),
            echo=False,
            connect_args={"check_same_thread": False},
        )
    return _engines[key]


def get_session_factory(db_path: str | Path | None = None) -> sessionmaker[Session]:
    """Devuelve la fábrica de sesiones cacheada para la ruta indicada."""
    key = _resolve_cache_key(db_path)
    if key not in _session_factories:
        _session_factories[key] = sessionmaker(
            bind=get_engine(db_path),
            autoflush=False,
            expire_on_commit=False,
        )
    return _session_factories[key]


@contextmanager
def session_scope(db_path: str | Path | None = None) -> Iterator[Session]:
    """Provee un ámbito transaccional alrededor de una serie de operaciones.

    Hace commit en caso de éxito, rollback ante cualquier excepción, y
    siempre cierra la sesión. Esto garantiza atomicidad en operaciones de
    negocio de varios pasos (p. ej., crear un expediente junto con sus
    acusados y audiencias).

    Uso:
        with session_scope() as session:
            session.add(some_object)
    """
    session = get_session_factory(db_path)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def dispose_engine(db_path: str | Path | None = None) -> bool:
    """Dispone el engine y la fábrica de sesiones de una ruta específica.

    Cierra todas las conexiones agrupadas, liberando el archivo SQLite
    (imprescindible en Windows para poder renombrar/borrar el .db).

    Args:
        db_path: Ruta cuya base se desea liberar; None libera la por defecto.

    Returns:
        True si existía un engine cacheado para esa ruta y fue dispuesto.
    """
    key = _resolve_cache_key(db_path)
    disposed = False
    factory = _session_factories.pop(key, None)
    engine = _engines.pop(key, None)
    if factory is not None:
        # ``sessionmaker.close_all()`` esta deprecado desde SQLAlchemy 1.4; el
        # reemplazo es la funcion de modulo ``close_all_sessions()``, que en
        # 2.0 no recibe argumentos y cierra todas las sesiones activas (en esta
        # app hay un unico engine, asi que es equivalente y seguro).
        close_all_sessions()
        disposed = True
    if engine is not None:
        engine.dispose()
        disposed = True
    return disposed


def reset_session_factory() -> None:
    """Dispone TODOS los engines/fábricas cacheados (útil sobre todo para tests)."""
    for key in list(_engines):
        dispose_engine(key)
