"""Backup y restauración de la base de datos local (``case_files.db``)."""

from __future__ import annotations

import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from ..database import DEFAULT_DB_PATH, get_app_data_dir
from ._base import _ServiceMixin

# Nombres canónicos dentro del .zip de respaldo completo.
_ARCHIVE_DB_NAME = "case_files.db"
_ARCHIVE_AUDIO_DIR = "audios"


def _is_audio_member(name: str) -> bool:
    """Indica si una entrada del zip pertenece a la carpeta ``audios/``."""
    parts = Path(name).parts
    return bool(parts) and parts[0] == _ARCHIVE_AUDIO_DIR


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

    def backup_data(self, dest_zip_path: str) -> str:
        """Respaldo completo: la base ``.db`` y la carpeta ``audios/`` en un .zip.

        Args:
            dest_zip_path: Ruta del .zip a crear (su carpeta se crea si falta).

        Returns:
            Ruta absoluta del .zip creado.
        """
        dest = Path(dest_zip_path).resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        src_db = self._resolve_db_file()
        audio_dir = get_app_data_dir() / _ARCHIVE_AUDIO_DIR
        # Disponer el engine vacía el WAL y libera el handle del .db (Windows).
        self.close()
        try:
            with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.write(src_db, arcname=_ARCHIVE_DB_NAME)
                if audio_dir.is_dir():
                    for file in sorted(audio_dir.rglob("*")):
                        if file.is_file():
                            arcname = (
                                Path(_ARCHIVE_AUDIO_DIR)
                                / file.relative_to(audio_dir)
                            ).as_posix()
                            archive.write(file, arcname=arcname)
        finally:
            self.init_db()
        return str(dest)

    def restore_data(self, src_zip_path: str) -> None:
        """Restaura la base y la carpeta ``audios/`` desde un respaldo completo.

        Valida el .zip antes de tocar la base actual; luego cierra el engine,
        reemplaza el ``.db`` y la carpeta ``audios/``, y reinicia la conexión.

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
            audio_members = [name for name in names if _is_audio_member(name)]
            for name in audio_members:
                _assert_safe_member(name)

        data_dir = get_app_data_dir()
        audio_dir = data_dir / _ARCHIVE_AUDIO_DIR
        dest_db = self._resolve_db_file()
        self.close()
        dest_db.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(src) as archive:
            with archive.open(_ARCHIVE_DB_NAME) as member, open(dest_db, "wb") as out:
                shutil.copyfileobj(member, out)
            # Reemplaza el store completo para no dejar audios huérfanos.
            if audio_dir.is_dir():
                shutil.rmtree(audio_dir)
            audio_dir.mkdir(parents=True, exist_ok=True)
            for name in audio_members:
                target = audio_dir / Path(name).relative_to(_ARCHIVE_AUDIO_DIR)
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
