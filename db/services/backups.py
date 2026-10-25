"""Backup y restauración de la base de datos local (``case_files.db``)."""

from __future__ import annotations

import logging
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from ..database import DEFAULT_DB_PATH, get_app_data_dir
from ._base import _ServiceMixin

logger = logging.getLogger("guilliman")

# Nombres canónicos dentro del .zip de respaldo completo.
_ARCHIVE_DB_NAME = "case_files.db"
_ARCHIVE_STORE_DIRS = ("audios", "attachments")
_BACKUP_GLOB = "guilliman_backup_*.zip"


def _is_stored_member(name: str) -> bool:
    """Indica si una entrada del zip pertenece a un store local."""
    parts = Path(name).parts
    return bool(parts) and parts[0] in _ARCHIVE_STORE_DIRS


def _assert_safe_member(name: str) -> None:
    """Rechaza entradas con rutas absolutas o ``..`` (zip-slip)."""
    path = Path(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Ruta insegura en el respaldo: {name}")


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

    def backup_data(self, dest_zip_path: str | None = None, keep: int = 10) -> str:
        """Respaldo completo: la base ``.db`` y la carpeta ``audios/`` en un .zip.

        Args:
            dest_zip_path: Ruta del .zip a crear (su carpeta se crea si falta).
                Si es ``None``, se genera
                ``<data_dir>/backups/guilliman_backup_<timestamp>.zip`` y se
                aplica rotación (se conservan los ``keep`` más recientes).
            keep: Número de respaldos a conservar en la carpeta por defecto.

        Returns:
            Ruta absoluta del .zip creado.
        """
        backups_dir = get_app_data_dir() / "backups"
        if dest_zip_path is None:
            backups_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            dest = backups_dir / f"guilliman_backup_{stamp}.zip"
        else:
            dest = Path(dest_zip_path).resolve()
            dest.parent.mkdir(parents=True, exist_ok=True)
        src_db = self._resolve_db_file()
        # Disponer el engine vacía el WAL y libera el handle del .db (Windows).
        self.close()
        try:
            with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.write(src_db, arcname=_ARCHIVE_DB_NAME)
                for dir_name in _ARCHIVE_STORE_DIRS:
                    source_dir = get_app_data_dir() / dir_name
                    if not source_dir.is_dir():
                        continue
                    for file in sorted(source_dir.rglob("*")):
                        if file.is_file():
                            arcname = (
                                Path(dir_name)
                                / file.relative_to(source_dir)
                            ).as_posix()
                            archive.write(file, arcname=arcname)
        finally:
            self.init_db()
        if dest_zip_path is None:
            self._rotate_backups(backups_dir, keep)
        return str(dest)

    @staticmethod
    def _rotate_backups(backups_dir: Path, keep: int) -> None:
        """Elimina los respaldos más antiguos, conservando los últimos ``keep``.

        El nombre incluye un timestamp ordenable, así que el orden lexicográfico
        descendente equivale al cronológico (evita depender de la resolución de
        ``mtime`` del sistema de archivos).
        """
        if keep < 1:
            return
        files = sorted(
            backups_dir.glob(_BACKUP_GLOB), key=lambda path: path.name, reverse=True
        )
        for old in files[keep:]:
            try:
                old.unlink()
            except OSError as error:
                logger.warning(
                    "No se pudo borrar el respaldo antiguo %s: %s", old, error
                )

    def restore_data(self, src_zip_path: str) -> None:
        """Restaura la base y los stores locales desde un respaldo completo.

        Valida el .zip antes de tocar la base actual; luego cierra el engine,
        reemplaza el ``.db`` y las carpetas ``audios/`` y ``attachments/``, y
        reinicia la conexión.

        Args:
            src_zip_path: Ruta del .zip de respaldo.

        Raises:
            FileNotFoundError: Si el .zip no existe.
            ValueError: Si el .zip no contiene la base o trae rutas inseguras.
        """
        src = Path(src_zip_path).resolve()
        if not src.is_file():
            raise FileNotFoundError(src)

        # Validación previa: nada se toca si el respaldo es inválido.
        with zipfile.ZipFile(src) as archive:
            names = archive.namelist()
            if _ARCHIVE_DB_NAME not in names:
                raise ValueError("El respaldo no contiene la base de datos.")
            stored_members = [name for name in names if _is_stored_member(name)]
            for name in stored_members:
                _assert_safe_member(name)

        data_dir = get_app_data_dir()
        dest_db = self._resolve_db_file()
        self.close()
        dest_db.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(src) as archive:
            with archive.open(_ARCHIVE_DB_NAME) as member, open(dest_db, "wb") as out:
                shutil.copyfileobj(member, out)
            # Reemplaza los stores completos para no dejar archivos huérfanos.
            for dir_name in _ARCHIVE_STORE_DIRS:
                target_dir = data_dir / dir_name
                if target_dir.is_dir():
                    shutil.rmtree(target_dir)
                target_dir.mkdir(parents=True, exist_ok=True)
            for name in stored_members:
                target = data_dir / Path(name)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as member, open(target, "wb") as out:
                    shutil.copyfileobj(member, out)
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
