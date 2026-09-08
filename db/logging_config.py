"""Configuración de logging de la aplicación Guilliman.

Centraliza la escritura de errores en ``guilliman.log`` dentro del directorio de
datos de la app (misma precedencia ``Guilliman_DATA_DIR`` que la base de datos),
para que en los PCs objetivo de 32 bits (donde no se ejecuta el código fuente)
cualquier fallo inesperado quede registrado en archivo.

El frontend (y el resto del db) debe consumir únicamente
``logging.getLogger("guilliman")``.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from .database import get_app_data_dir

_LOG_FILE_NAME = "guilliman.log"


def setup_logging(level: int = logging.INFO, *, to_console: bool = False) -> logging.Logger:
    """Configura y devuelve el logger raíz de la app ``"guilliman"``.

    Escribe en ``<data_dir>/guilliman.log`` (``data_dir`` = ``get_app_data_dir()``,
    misma precedencia ``Guilliman_DATA_DIR`` que la base de datos). La función es
    idempotente: si ya fue configurada, no añade handlers duplicados.

    Args:
        level: Nivel de log (por defecto ``logging.INFO``).
        to_console: Si ``True``, también registra en consola (útil en dev).

    Returns:
        ``logging.getLogger("guilliman")`` para que el frontend lo consuma.
    """
    logger = logging.getLogger("guilliman")
    logger.setLevel(level)

    if getattr(logger, "_guilliman_configured", False):
        return logger

    log_path = Path(get_app_data_dir()) / _LOG_FILE_NAME
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        # No bloqueamos el arranque si no se puede crear el directorio.
        pass

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if to_console:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    logger.propagate = False
    logger._guilliman_configured = True  # type: ignore[attr-defined]

    # Registrar excepciones no capturadas en el logger (arranque, hilos propios).
    _install_excepthook(logger)
    logger.info("Logging Guilliman inicializado en %s", log_path)
    return logger


def _install_excepthook(logger: logging.Logger) -> None:
    """Redirige ``sys.excepthook`` al logger para no perder errores irrecuperables."""
    original = sys.excepthook

    def _hook(exc_type, exc_value, exc_tb) -> None:
        logger.error("Excepción no capturada", exc_info=(exc_type, exc_value, exc_tb))
        if callable(original):
            original(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook
