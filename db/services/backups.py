"""Backup y restauración de la base de datos local (``case_files.db``)."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from ..database import DEFAULT_DB_PATH, get_app_data_dir
from ._base import _ServiceMixin


class BackupMethods(_ServiceMixin):
    """Métodos de respaldo/restauración de la base de datos del expediente."""

    def _resolve_db_file(self) -> Path:
        """Ruta absoluta del archivo ``.db`` gestionado por este service."""
        if self._db_path is None:
            return DEFAULT_DB_PATH
        return Path(self._db_path).resolve()

    def backup_db(self, dest_path: str | None = None) -> str:
        """Copia segura de la base de datos a un archivo de respaldo.

        Cierra el engine para forzar el checkpoint de WAL (y liberar el handle
        en Windows), copia el archivo y reinicia la conexión para que la app
        siga operando. Por defecto guarda en
        ``<data_dir>/backups/case_files_backup_<timestamp>.db``.

        Args:
            dest_path: Ruta de destino opcional. Si es una carpeta, se genera
                dentro un nombre con timestamp; si es un archivo, se usa tal cual
                (creando la carpeta contenedora si hace falta).

        Returns:
            Ruta absoluta del respaldo creado.
        """
        src = self._resolve_db_file()
        dest = self._resolve_backup_dest(dest_path)
        # Disponer el engine asegura que WAL/-shm se vacíen al .db principal.
        self.close()
        shutil.copy2(src, dest)
        # Reiniciar para que la app continue usando la base tras el respaldo.
        self.init_db()
        return str(dest)

    def restore_db(self, src_path: str) -> None:
        """Restaura la base desde un respaldo, reemplazando la actual.

        Cierra el engine, reemplaza el ``.db`` por la copia indicada y reinicia
        la conexión. La UI debe recargar sus vistas tras invocar esto.

        Args:
            src_path: Ruta del respaldo a restaurar.

        Raises:
            FileNotFoundError: Si el archivo de respaldo no existe.
        """
        src = Path(src_path).resolve()
        if not src.is_file():
            raise FileNotFoundError(src)
        dest = self._resolve_db_file()
        self.close()
        shutil.copy2(src, dest)
        self.init_db()

    @staticmethod
    def _resolve_backup_dest(dest_path: str | None) -> Path:
        """Resuelve la ruta de destino de un respaldo (con timestamp por defecto)."""
        if dest_path is None:
            backups_dir = get_app_data_dir() / "backups"
            backups_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return backups_dir / f"case_files_backup_{stamp}.db"
        candidate = Path(dest_path).resolve()
        if candidate.is_dir():
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return candidate / f"case_files_backup_{stamp}.db"
        candidate.parent.mkdir(parents=True, exist_ok=True)
        return candidate
