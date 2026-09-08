"""
Guilliman Backend - Servicio de lógica de negocio.

``CaseFileService`` es el único punto de entrada público para el frontend
PyQt. Su implementación se compone de mixins por entidad en el paquete
``db.services`` (expedientes, acusados, víctimas, testigos, documentales,
expertos y audiencias), de modo que este módulo solo orquesta la herencia y el
ciclo de vida de la base de datos. El frontend solo necesita hacer:

    from db.service import CaseFileService
    service = CaseFileService()          # opcional: CaseFileService("mi.db")
    service.init_db()

Notas de comportamiento:
    - ``search_case_files("")`` retorna TODOS los expedientes (el patrón LIKE
      vacío coincide con cualquier valor), útil para listados sin filtro.
    - Los errores de negocio son tipados (ver ``exceptions.py``): todos
      heredan de ``ValueError`` para retrocompatibilidad.
    - Llamar ``close()`` al cerrar la aplicación libera el archivo SQLite
      (necesario en Windows para copiar/borrar la base con la app abierta).
    - ``backup_db()`` / ``restore_db()`` permiten respaldar y restaurar la base
      de datos local (por defecto en ``<data_dir>/backups/``).
"""

from __future__ import annotations

from sqlalchemy import Engine, event

from .database import dispose_engine, get_engine
from .migrations import apply_migrations, sync_missing_columns
from .models import Base
from .services.backups import BackupMethods
from .services.case_files import CaseFileMethods
from .services.defendants import DefendantMethods
from .services.documentaries import DocumentaryMethods
from .services.experts import ExpertMethods
from .services.hearings import HearingMethods
from .services.victims import VictimMethods
from .services.witnesses import WitnessMethods
from .services.acting_officials import ActingOfficialMethods


class CaseFileService(
    CaseFileMethods,
    DefendantMethods,
    VictimMethods,
    WitnessMethods,
    DocumentaryMethods,
    ExpertMethods,
    ActingOfficialMethods,
    HearingMethods,
    BackupMethods,
):
    """Fachada de servicio de alto nivel para la aplicación Guilliman.

    Todas las operaciones de escritura se ejecutan dentro de transacciones
    atómicas. Cada método público retorna DTOs de Pydantic (o ints/bools
    simples), por lo que el frontend nunca maneja sesiones de SQLAlchemy ni
    objetos ORM directamente.
    """

    def __init__(self, db_path: str | None = None) -> None:
        """
        Args:
            db_path: Ruta de archivo SQLite personalizada opcional. Si se omite,
                se usa el ``case_files.db`` por defecto junto a la raíz del
                proyecto. Varios servicios sobre la misma ruta comparten el
                mismo engine (sin fugas de conexiones).
        """
        self._db_path = db_path

    # ------------------------------------------------------------------ #
    # Ciclo de vida del servicio / base de datos
    # ------------------------------------------------------------------ #
    def init_db(self) -> None:
        """Crea todas las tablas si aún no existen y aplica migraciones pendientes.

        Llamar una sola vez al arrancar la aplicación antes de usar cualquier
        otro método. También habilita el cumplimiento de llaves foráneas de
        SQLite (desactivado por defecto) para que ON DELETE CASCADE funcione
        de forma confiable.

        Las bases existentes se actualizan mediante migraciones secuenciales
        registradas en ``db.migrations`` (tabla ``schema_version``),
        de modo que los datos de los usuarios nunca se pierdan entre versiones.
        """
        engine: Engine = get_engine(self._db_path)
        # Fuerza las FK por conexión mediante un listener PRAGMA
        # (registrado una sola vez por engine).
        if not getattr(engine, "_guilliman_fk_listener_attached", False):

            @event.listens_for(engine, "connect")
            def _enable_sqlite_fk(dbapi_connection, _connection_record):  # noqa: ANN001
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

            engine._guilliman_fk_listener_attached = True

        Base.metadata.create_all(engine)
        # Autocura columnas faltantes en bases ya pobladas (ver sync_missing_columns).
        sync_missing_columns(engine, Base.metadata)
        apply_migrations(engine)

    def close(self) -> None:
        """Libera las conexiones del engine asociado a la ruta de este servicio.

        Debe llamarse al cerrar la aplicación (o al terminar pruebas que usen
        una BD temporal): en Windows un handle abierto impide borrar/renombrar
        el archivo .db.
        """
        dispose_engine(self._db_path)


__all__ = ["CaseFileService"]
