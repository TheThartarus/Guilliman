"""
Guilliman Backend - Mecanismo de migraciones extensible.

El esquema de la base de datos se define en ``models.py`` y se crea con
``Base.metadata.create_all()`` dentro de ``init_db()``. La aplicación aún no está
en producción, por lo que los cambios de esquema se aplican recreando la base en
frío; ``MIGRATIONS`` arranca vacío.

Este modulo se mantiene como andamiaje funcional para EVOLUCIONAR bases ya
existentes cuando el proyecto se despliegue (o cambie el modelo y exista una
base con datos que no se quiera borrar). Cada migracion es una funcion
``(Session) -> None`` idempotente; ``init_db()`` aplica solo las versiones
mayores a las registradas en ``schema_version``.

Para agregar una migracion futura:
    1. Define ``def _migration_001_xxx(session: Session) -> None: ...`` usando
       ``_column_exists`` / ``_table_exists`` para hacer ALTER idempotentes.
    2. Registrala: ``MIGRATIONS[1] = _migration_001_xxx``.
Nunca edites una migracion ya liberada; agrega una nueva entrada.
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Tabla de control de versiones (creada si no existe).
SCHEMA_VERSION_TABLE = "schema_version"


def _column_exists(session: Session, table: str, column: str) -> bool:
    """Retorna True si ``column`` ya existe en ``table`` (SQLite)."""
    rows = session.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(row[1] == column for row in rows)


def _table_exists(session: Session, table: str) -> bool:
    """Retorna True si ``table`` ya existe en la base de datos (SQLite)."""
    row = session.execute(
        text(
            "SELECT name FROM sqlite_master "
            f"WHERE type='table' AND name='{table}'"
        )
    ).fetchone()
    return row is not None


def sync_missing_columns(engine: Engine, metadata) -> list[str]:
    """Agrega a tablas existentes las columnas que el modelo declara pero faltan.

    ``Base.metadata.create_all()`` solo crea tablas nuevas; no altera las que ya
    existen. Cuando ``models.py`` gana columnas, las bases de usuarios ya
    pobladas se quedan desactualizadas y las consultas fallan con
    ``no such column``. Esta funcion autocura el esquema: por cada tabla existente
    inspecciona las columnas presentes y hace ``ALTER TABLE ... ADD COLUMN`` por
    las que falten. Es idempotente (no toca columnas existentes) y solo agrega,
    nunca borra ni renombra.

    Para evitar el limite de SQLite (no permite ``ADD COLUMN`` con ``NOT NULL``
    sin valor por defecto), las columnas nuevas se agregan siempre como
    ``NULL``; la nulidad a nivel de aplicacion la sigue garantizando el modelo
    para filas nuevas.

    Args:
        engine: Engine SQLAlchemy de la base a sincronizar.
        metadata: ``Base.metadata`` con las definiciones actuales de los modelos.

    Returns:
        Lista de ``"tabla.columna"`` agregadas en esta llamada (vacia si ya
        estaba al dia).
    """
    added: list[str] = []
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in metadata.tables.values():
            if not inspector.has_table(table.name):
                continue
            existing = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                sql = text(
                    f'ALTER TABLE "{table.name}" '
                    f'ADD COLUMN "{column.name}" {col_type} NULL'
                )
                conn.execute(sql)
                added.append(f"{table.name}.{column.name}")
    if added:
        logger.info("Esquema sincronizado, columnas agregadas: %s", ", ".join(added))
    return added


# Registro global de migraciones: {version: funcion}. Vacio: el esquema actual
# vive en models.py y la base se crea en frío con ``create_all``.
MIGRATIONS: dict[int, callable] = {}


def _ensure_version_table(session: Session) -> None:
    """Crea la tabla ``schema_version`` si aún no existe."""
    session.execute(
        text(
            f"CREATE TABLE IF NOT EXISTS {SCHEMA_VERSION_TABLE} ("
            "version INTEGER PRIMARY KEY,"
            "applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
    )


def get_current_version(engine) -> int:  # noqa: ANN001
    """Retorna la última versión de migración aplicada (0 si nunca se migró)."""
    with engine.connect() as connection:
        # La tabla puede no existir todavía en bases muy antiguas.
        exists = connection.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name=:table_name"
            ),
            {"table_name": SCHEMA_VERSION_TABLE},
        ).fetchone()
        if exists is None:
            return 0
        row = connection.execute(
            text(f"SELECT MAX(version) AS max_version FROM {SCHEMA_VERSION_TABLE}")
        ).fetchone()
        return int(row.max_version or 0)


def apply_migrations(engine) -> list[int]:  # noqa: ANN001
    """Aplica todas las migraciones pendientes de forma transaccional.

    Returns:
        Lista de números de versión aplicados en esta llamada (vacía si la
        base de datos ya estaba al día).
    """
    applied: list[int] = []
    current = get_current_version(engine)
    for version in sorted(MIGRATIONS):
        if version <= current:
            continue
        # Cada migración corre en su propia transacción para que un fallo
        # no deje la tabla schema_version apuntando a una versión incompleta.
        with Session(engine) as session:
            _ensure_version_table(session)
            MIGRATIONS[version](session)
            session.execute(
                text(f"INSERT INTO {SCHEMA_VERSION_TABLE} (version) VALUES (:v)"),
                {"v": version},
            )
            session.commit()
        applied.append(version)
    return applied


__all__ = [
    "SCHEMA_VERSION_TABLE",
    "MIGRATIONS",
    "get_current_version",
    "apply_migrations",
    "sync_missing_columns",
]
