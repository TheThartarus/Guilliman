"""
Guilliman Frontend - Ventana principal y estado compartido.

``AppShell`` es una ``FluentWindow`` con una barra de navegación (índices:
Expedientes/Buscar, Nuevo, Agenda, Ajustes) y un widget central que intercambia
vistas mediante ``addSubInterface``/``switchTo``. El detalle y la edición de un
expediente se abren como sub-interfaces dinámicas.

``GuillimanApp`` es el contenedor de estado compartido: mantiene el ``CaseFileService``
y una referencia a la shell para navegar.
"""

from __future__ import annotations

import logging

from PyQt5.QtWidgets import QWidget

from qfluentwidgets import FluentIcon, FluentWindow, NavigationItemPosition

from db import CaseFileService

from ui.about_view import AboutView
from ui.agenda_view import AgendaView
from ui.case_detail_view import CaseDetailView
from ui.case_form_view import CaseFormView
from ui.case_search_view import CaseSearchView
from ui.widgets import show_error, show_info


class GuillimanApp:
    """Estado compartido entre las vistas (fachada del db + shell)."""

    def __init__(self, service: CaseFileService) -> None:
        self.service = service
        self.shell: AppShell | None = None


class SettingsView(QWidget):
    """Vista de ajustes: permite cambiar y persistir el tema de la app."""

    def __init__(self, app: GuillimanApp) -> None:
        super().__init__()
        from PyQt5.QtWidgets import QFormLayout, QHBoxLayout, QVBoxLayout

        from qfluentwidgets import (
            BodyLabel,
            ComboBox,
            PushButton,
            SubtitleLabel,
            TitleLabel,
        )

        from ui import settings as app_settings

        self.app = app

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(TitleLabel("Ajustes"))

        form = QFormLayout()
        form.setSpacing(12)

        self.theme_combo = ComboBox()
        self.theme_combo.addItems(["Claro", "Oscuro"])
        current = app_settings.load_theme_mode()
        self.theme_combo.setCurrentText("Oscuro" if current == "DARK" else "Claro")
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)

        form.addRow(BodyLabel("Tema de la interfaz:"), self.theme_combo)
        layout.addWidget(SubtitleLabel("Apariencia"))
        layout.addLayout(form)

        # Respaldo y restauración de la base de datos (integra B3).
        layout.addWidget(SubtitleLabel("Respaldo de datos"))
        backup_row = QHBoxLayout()
        self.backup_btn = PushButton("Respaldar datos (BD + audios)")
        self.backup_btn.clicked.connect(self._on_backup)
        self.restore_btn = PushButton("Restaurar datos")
        self.restore_btn.clicked.connect(self._on_restore)
        backup_row.addWidget(self.backup_btn)
        backup_row.addWidget(self.restore_btn)
        backup_row.addStretch(1)
        layout.addLayout(backup_row)

        layout.addStretch(1)

    def _on_theme_changed(self, text: str) -> None:
        from qfluentwidgets import Theme, setTheme

        from ui import settings as app_settings

        mode = "DARK" if text == "Oscuro" else "LIGHT"
        setTheme(Theme.DARK if mode == "DARK" else Theme.LIGHT)
        app_settings.save_theme_mode(mode)

    # ------------------------------------------------------------------ #
    # Respaldo / restauración (B3)
    # ------------------------------------------------------------------ #
    def _on_backup(self) -> None:
        from PyQt5.QtWidgets import QFileDialog

        dest, _ = QFileDialog.getSaveFileName(
            self, "Respaldar datos (BD + audios)", "guilliman_backup.zip",
            "Respaldo (*.zip)",
        )
        if not dest:
            return
        if not dest.lower().endswith(".zip"):
            dest += ".zip"
        try:
            path = self.app.service.backup_data(dest)
        except Exception as exc:  # noqa: BLE001 - fallo de I/O
            show_error(self, f"No se pudo crear el respaldo:\n{exc}")
            return
        show_info(self, f"Respaldo creado:\n{path}")

    def _on_restore(self) -> None:
        from PyQt5.QtWidgets import QFileDialog, QMessageBox

        src, _ = QFileDialog.getOpenFileName(
            self, "Restaurar datos", "", "Respaldo (*.zip)"
        )
        if not src:
            return
        reply = QMessageBox.question(
            self, "Restaurar",
            "¿Restaurar la base de datos y los audios desde el respaldo?\n"
            "Se reemplazará la información actual. Se hará un respaldo automático previo.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            self.app.service.backup_db()  # respaldo automático previo de la BD
            self.app.service.restore_data(src)
        except Exception as exc:  # noqa: BLE001 - fallo de I/O
            show_error(self, f"No se pudo restaurar:\n{exc}")
            return
        # La restauración reemplaza el .db: cerramos vistas dinámicas y refrescamos.
        if self.app.shell is not None:
            self.app.shell._close_all_dynamic_routes()
            self.app.shell.search_view.refresh()
            self.app.shell.agenda_view.refresh()
        show_info(self, "Datos restaurados.")


class AppShell(FluentWindow):
    """Ventana principal con navegación y vistas intercambiables."""

    def __init__(self, service: CaseFileService) -> None:
        super().__init__()
        self.setWindowTitle("Guilliman")
        self.resize(1120, 740)

        self.app = GuillimanApp(service)
        self.app.shell = self

        # Vistas principales (sub-interfaces fijas). addSubInterface usa el
        # objectName del widget como route key.
        self.search_view = CaseSearchView(self.app)
        self.new_view = CaseFormView(self.app, None)
        self.agenda_view = AgendaView(self.app)
        self.settings_view = SettingsView(self.app)
        self.about_view = AboutView()

        self.search_view.setObjectName("search")
        self.new_view.setObjectName("new")
        self.agenda_view.setObjectName("agenda")
        self.settings_view.setObjectName("settings")
        self.about_view.setObjectName("about")

        self.addSubInterface(self.search_view, FluentIcon.SEARCH, "Expedientes", NavigationItemPosition.TOP)
        self.addSubInterface(self.new_view, FluentIcon.ADD, "Nuevo", NavigationItemPosition.TOP)
        self.addSubInterface(self.agenda_view, FluentIcon.CALENDAR, "Agenda", NavigationItemPosition.TOP)
        self.addSubInterface(self.about_view, FluentIcon.INFO, "Acerca de", NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.settings_view, FluentIcon.SETTING, "Ajustes", NavigationItemPosition.BOTTOM)

        self.stackedWidget.currentChanged.connect(self._on_current_changed)
        self.switchTo(self.search_view)
        # Carga inicial: al arrancar la pestaña activa ya es Expedientes, pero
        # currentChanged no se dispara en el primer switchTo, así que refrescamos
        # explícitamente para que los expedientes aparezcan sin pulsar "Buscar".
        self.search_view.refresh()

        # Sub-interfaces dinámicas abiertas (detalle / edición de expediente).
        self._dynamic: dict[str, QWidget] = {}

    # ------------------------------------------------------------------ #
    # Navegación
    # ------------------------------------------------------------------ #
    def _on_current_changed(self, index: int) -> None:
        """Refresca la vista activa al cambiar de pestaña/vista."""
        widget = self.stackedWidget.widget(index)
        if widget is not None and hasattr(widget, "refresh"):
            widget.refresh()

    def open_case_detail(self, case_file_id: int) -> None:
        """Abre (o enfoca) la vista de detalle de un expediente."""
        route = f"detail-{case_file_id}"
        widget = self._dynamic.get(route)
        if widget is None:
            widget = CaseDetailView(self.app, case_file_id, on_close=self._close_route)
            widget.setObjectName(route)
            self._dynamic[route] = widget
            self.addSubInterface(widget, FluentIcon.INFO, "Detalle", NavigationItemPosition.TOP)
        self.switchTo(widget)

    def open_case_form(self, case_file_id: int | None = None) -> None:
        """Abre el formulario para crear (None) o editar un expediente."""
        if case_file_id is None:
            self.new_view.reset()
            self.switchTo(self.new_view)
            return
        route = f"edit-{case_file_id}"
        widget = self._dynamic.get(route)
        if widget is None:
            widget = CaseFormView(
                self.app, case_file_id, on_saved=self._close_route, on_cancel=self._close_route
            )
            widget.setObjectName(route)
            self._dynamic[route] = widget
            self.addSubInterface(widget, FluentIcon.EDIT, "Editar", NavigationItemPosition.TOP)
        self.switchTo(widget)

    def _close_route(self, route_key: str) -> None:
        """Cierra una sub-interfaz dinámica y regresa a Expedientes."""
        widget = self._dynamic.pop(route_key, None)
        if widget is not None:
            try:
                self.stackedWidget.removeWidget(widget)
                self.navigationInterface.removeWidget(route_key)
            except Exception:  # noqa: BLE001 - API defensiva
                logging.getLogger("guilliman").exception(
                    "fallo al cerrar ruta dinámica %s", route_key
                )
        self.search_view.refresh()
        self.switchTo(self.search_view)

    def _close_all_dynamic_routes(self) -> None:
        """Cierra todas las sub-interfaces dinámicas abiertas (tras restaurar BD)."""
        for key in list(self._dynamic.keys()):
            self._close_route(key)
