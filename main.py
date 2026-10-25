"""
Guilliman - Punto de entrada de la aplicación de escritorio (PyQt5 + qfluentwidgets).

Arranca ``QApplication``, construye la ``FluentWindow``, aplica el tema guardado
y muestra la interfaz.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt5.QtGui import QIcon
from PyQt5.QtNetwork import QLocalServer, QLocalSocket
from PyQt5.QtWidgets import QApplication, QMessageBox

from qfluentwidgets import Theme, setTheme

from db import CaseFileService, setup_logging
from db.database import reset_session_factory

from ui import settings as app_settings
from ui.app_shell import AppShell


def main() -> None:
    """Inicializa la base de datos, construye la UI y entra al loop de eventos."""
    # Logging temprano: los errores inesperados quedan en <data_dir>/guilliman.log
    # (misma precedencia Guilliman_DATA_DIR que la base de datos), ya que en los
    # PCs objetivo de 32 bits no se ejecuta el código fuente.
    setup_logging()

    # -- Single instance check ------------------------------------------------
    _SINGLE_INSTANCE_KEY = "Guilliman_SingleInstance"
    _socket = QLocalSocket()
    _socket.connectToServer(_SINGLE_INSTANCE_KEY)
    if _socket.waitForConnected(500):
        # Ya hay otra instancia corriendo.
        QMessageBox.critical(
            None,
            "Guilliman",
            "Ya existe una instancia de Guilliman abierta.\n\n"
            "No se permite ejecutar más de una instancia simultáneamente.",
        )
        sys.exit(1)
    _socket.disconnectFromServer()

    app = QApplication(sys.argv)
    app.setApplicationName("Guilliman")

    # -- Registrar el servidor de instancia única (bloquea futuras instancias).
    server = QLocalServer(app)
    # Si había un socket residual de un crash anterior, limpiarlo.
    QLocalServer.removeServer(_SINGLE_INSTANCE_KEY)
    server.listen(_SINGLE_INSTANCE_KEY)

    # -- AppUserModelID (Windows 7+): obligatorio para que la barra de tareas
    #    muestre el ícono del programa en vez de un ícono genérico. ----------
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "Guilliman.App"
            )
        except Exception:  # noqa: BLE001 - no crítico en dev
            pass

    # -- Ícono de la ventana (funciona en dev y en el exe empaquetado). ------
    if getattr(sys, "frozen", False):
        icon_path = Path(getattr(sys, "_MEIPASS")) / "assets" / "icon.ico"
    else:
        icon_path = Path(__file__).resolve().parent / "assets" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Tema guardado en la última ejecución (preferencia local del frontend).
    theme_mode = app_settings.load_theme_mode()
    setTheme(Theme.DARK if theme_mode == "DARK" else Theme.LIGHT)

    service = CaseFileService()
    try:
        service.init_db()
    except Exception as exc:  # noqa: BLE001 - fallo irrecuperable al arrancar
        QMessageBox.critical(None, "Guilliman", f"No se pudo inicializar la base de datos:\n{exc}")
        sys.exit(1)

    def _shutdown() -> None:
        """Libera el engine de SQLite al salir de la app.

        En Windows un engine no dispuesto deja el archivo .db bloqueado y
        archivos -wal/-shm colgando. Cerramos la sesión factory y el engine
        asociado al service, y vaciamos la caché global por si hubiera otros
        engines (p. ej. en tests o múltiples servicios).
        """
        service.close()
        reset_session_factory()

    # Disponer el engine en cualquier ruta de salida de la aplicación.
    app.aboutToQuit.connect(_shutdown)

    window = AppShell(service)
    state = app_settings.load_window_state()
    if state and not state.get("maximized", True):
        window.resize(int(state.get("width", 1120)), int(state.get("height", 740)))
        window.show()
    else:
        window.showMaximized()

    def _save_window_state() -> None:
        app_settings.save_window_state(
            window.isMaximized(), window.width(), window.height()
        )

    app.aboutToQuit.connect(_save_window_state)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
