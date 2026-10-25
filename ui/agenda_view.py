"""
Guilliman Frontend - Agenda de audiencias.

``QWidget`` con un rango de fechas (desde/hasta) y una ``QTableWidget`` de
audiencias. El botón Exportar PDF usa ``QFileDialog`` (diálogo nativo) para
elegir la ruta y llama a ``ui.exporters.export_agenda_pdf``.
"""

from __future__ import annotations

import logging
from datetime import datetime

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from qfluentwidgets import (
    Action,
    BodyLabel,
    DatePicker,
    PrimaryPushButton,
    PushButton,
    RoundMenu,
    SubtitleLabel,
    TableWidget,
)

from ui.date_pickers import apply_spanish_date_picker
from ui.dialogs import HearingDialog, confirm_delete, pick_save_pdf
from ui.exporters import export_agenda_ics, export_agenda_pdf
from ui.shared import (
    HEARING_STATUS_LABELS,
    HEARING_TYPE_LABELS,
    format_datetime,
    translate,
)
from ui.widgets import show_error, show_info

logger = logging.getLogger("guilliman")


class AgendaView(QWidget):
    """Vista de agenda de audiencias por rango de fechas."""

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self._rows: list[int] = []
        self._items: list = []
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)
        layout.addWidget(SubtitleLabel("Agenda de Audiencias"))

        range_row = QHBoxLayout()
        self.start_date = DatePicker()
        self.start_date.setDate(QDate.currentDate())
        apply_spanish_date_picker(self.start_date)
        self.end_date = DatePicker()
        self.end_date.setDate(QDate.currentDate())
        apply_spanish_date_picker(self.end_date)
        self.filter_btn = PrimaryPushButton("Filtrar")
        self.filter_btn.clicked.connect(self.refresh)
        self.clear_btn = PushButton("Limpiar filtros")
        self.clear_btn.clicked.connect(self._on_clear_filters)
        self.export_btn = PushButton("Exportar PDF")
        self.export_btn.clicked.connect(self._on_export)
        self.export_ics_btn = PushButton("Exportar .ics")
        self.export_ics_btn.clicked.connect(self._on_export_ics)
        range_row.addWidget(BodyLabel("Desde:"))
        range_row.addWidget(self.start_date, 1)
        range_row.addWidget(BodyLabel("Hasta:"))
        range_row.addWidget(self.end_date, 1)
        range_row.addWidget(self.filter_btn)
        range_row.addWidget(self.clear_btn)
        range_row.addWidget(self.export_btn)
        range_row.addWidget(self.export_ics_btn)
        layout.addLayout(range_row)

        self.table = TableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setBorderVisible(True)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Expediente", "Fecha/Hora", "Tipo", "Estado", "Notas"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellDoubleClicked.connect(self._on_row_double)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.table, 1)

    def refresh(self) -> None:
        """Carga las audiencias en el rango seleccionado."""
        start = datetime.combine(self.start_date.getDate().toPyDate(), datetime.min.time())
        end = datetime.combine(self.end_date.getDate().toPyDate(), datetime.max.time())
        try:
            items = self.app.service.list_scheduled_hearings(start, end)
        except ValueError as exc:
            logger.exception("Error al cargar audiencias")
            show_error(self, f"Error al cargar: {exc}")
            return

        self._items = items
        self._rows = [i.hearing_id for i in items]
        self.table.setRowCount(len(items))
        for row, item in enumerate(items):
            id_item = QTableWidgetItem(str(item.hearing_id))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, QTableWidgetItem(item.case_number or ""))
            self.table.setItem(row, 2, QTableWidgetItem(format_datetime(item.scheduled_at)))
            self.table.setItem(
                row, 3, QTableWidgetItem(translate(item.hearing_type, HEARING_TYPE_LABELS))
            )
            self.table.setItem(
                row, 4, QTableWidgetItem(translate(item.status, HEARING_STATUS_LABELS))
            )
            self.table.setItem(row, 5, QTableWidgetItem(item.notes or ""))

    def _on_clear_filters(self) -> None:
        """Restablece el rango de fechas al día de hoy y recarga la agenda."""
        today = QDate.currentDate()
        self.start_date.setDate(today)
        self.end_date.setDate(today)
        self.refresh()

    def _on_row_double(self, row: int, _col: int) -> None:
        """Doble clic en la agenda abre el detalle del expediente asociado."""
        if not (0 <= row < len(self._items)):
            return
        item = self._items[row]
        self.app.shell.open_case_detail(item.case_file_id)

    def _edit_hearing(self, row: int) -> None:
        if not (0 <= row < len(self._items)):
            return
        item = self._items[row]
        case = self.app.service.get_case_file_by_id(item.case_file_id)
        if case is None:
            show_error(self, "El expediente asociado no existe.")
            return
        hearing = next((h for h in case.hearings if h.id == item.hearing_id), None)
        if hearing is None:
            show_error(self, "La audiencia no existe.")
            return
        dlg = HearingDialog(self, self.app, item.case_file_id, hearing)
        if dlg.exec():
            self.refresh()

    def _delete_hearing(self, row: int) -> None:
        if not (0 <= row < len(self._items)):
            return
        item = self._items[row]
        if not confirm_delete(
            self, f"¿Eliminar la audiencia del expediente {item.case_number}?"
        ):
            return
        if not self.app.service.delete_hearing(item.hearing_id):
            show_error(self, "La audiencia no existe.")
            return
        show_info(self, "Audiencia eliminada.")
        self.refresh()

    def _set_status(self, row: int, new_status: str) -> None:
        """Cambia el estado de la audiencia usando el servicio de negocio.

        Se llama ``update_hearing_status`` (no ``update_hearing``) porque
        únicamente se transiciona el campo ``status`` y no se modifican los
        demás atributos de la audiencia.
        """
        if not (0 <= row < len(self._items)):
            return
        item = self._items[row]
        if not self.app.service.update_hearing_status(item.hearing_id, new_status):
            show_error(self, "No se pudo actualizar el estado.")
            return
        show_info(self, "Estado de la audiencia actualizado.")
        self.refresh()

    def _on_context_menu(self, pos) -> None:
        row = self.table.indexAt(pos).row()
        if not (0 <= row < len(self._items)):
            return
        menu = RoundMenu(parent=self)
        edit_action = Action("Editar")
        menu.addAction(edit_action)
        edit_action.triggered.connect(lambda *_, r=row: self._edit_hearing(r))
        delete_action = Action("Eliminar")
        menu.addAction(delete_action)
        delete_action.triggered.connect(lambda *_, r=row: self._delete_hearing(r))
        status_menu = RoundMenu("Cambiar estado", self)
        for key in ("Scheduled", "Completed", "Deferred", "Cancelled"):
            act = Action(HEARING_STATUS_LABELS[key])
            status_menu.addAction(act)
            act.triggered.connect(lambda *_, k=key, r=row: self._set_status(r, k))
        menu.addMenu(status_menu)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _on_export(self) -> None:
        if not self._rows:
            show_error(self, "No hay audiencias en el rango para exportar.")
            return
        path = pick_save_pdf(self, "agenda_de_audiencias.pdf")
        if not path:
            return
        start = self.start_date.getDate().toPyDate()
        end = self.end_date.getDate().toPyDate()
        items = self.app.service.list_scheduled_hearings(
            datetime.combine(start, datetime.min.time()),
            datetime.combine(end, datetime.max.time()),
        )
        try:
            export_agenda_pdf(items, start, end, path)
        except Exception as exc:  # noqa: BLE001 - se informa al usuario
            logger.exception("Error al exportar PDF de agenda")
            show_error(self, f"Error al exportar: {exc}")
            return
        show_info(self, "PDF de la agenda generado.")

    def _on_export_ics(self) -> None:
        """Exporta las audiencias del rango a un archivo iCalendar (.ics)."""
        if not self._rows:
            show_error(self, "No hay audiencias en el rango para exportar.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar agenda .ics",
            "agenda_de_audiencias.ics",
            "iCalendar (*.ics)",
        )
        if not path:
            return
        if not path.lower().endswith(".ics"):
            path += ".ics"
        start = self.start_date.getDate().toPyDate()
        end = self.end_date.getDate().toPyDate()
        items = self.app.service.list_scheduled_hearings(
            datetime.combine(start, datetime.min.time()),
            datetime.combine(end, datetime.max.time()),
        )
        try:
            export_agenda_ics(items, path)
        except Exception as exc:  # noqa: BLE001 - se informa al usuario
            logger.exception("Error al exportar .ics de agenda")
            show_error(self, f"Error al exportar: {exc}")
            return
        show_info(self, "Agenda .ics exportada.")
