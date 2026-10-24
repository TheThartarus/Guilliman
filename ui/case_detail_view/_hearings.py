"""Sección de audiencias del detalle de expediente (tabla, alta/edición/borrado)."""

from __future__ import annotations

import logging
import os
from datetime import datetime

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QBrush, QColor, QDesktopServices
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QMenu,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from qfluentwidgets import PushButton, SubtitleLabel, TableWidget

from db import CaseFileRead

from ui.dialogs import HearingDialog, confirm_delete
from ui.shared import (
    HEARING_STATUS_LABELS,
    HEARING_TYPE_LABELS,
    format_datetime,
    translate,
)
from ui.widgets import show_error, show_info

logger = logging.getLogger("guilliman")


def _split_hearings(hearings, now=None) -> list[tuple]:
    """Separa audiencias en activas (arriba) y pasadas (abajo), en su orden.

    Activas = fecha futura/hoy y estado Programada/Diferida, orden asc.
    Pasadas = el resto, orden desc (más reciente primero). Devuelve una lista
    de tuplas ``(hearing, is_past)`` en el orden de visualización.
    """
    now = now or datetime.now()
    active = [
        h for h in hearings
        if h.scheduled_at >= now and h.status in ("Scheduled", "Deferred")
    ]
    past = [h for h in hearings if h not in active]
    active.sort(key=lambda h: h.scheduled_at)
    past.sort(key=lambda h: h.scheduled_at, reverse=True)
    return [(h, False) for h in active] + [(h, True) for h in past]


class _HearingsSection:
    """Métodos de la sección de audiencias del ``CaseDetailView``."""

    def _selected_hearing_id(self) -> int | None:
        row = self.hearings_table.currentRow()
        if 0 <= row < len(self._hearing_rows):
            return self._hearing_rows[row]
        return None

    def _fill_hearings(self, case: CaseFileRead) -> None:
        rows = _split_hearings(case.hearings)
        self._hearing_rows = [h.id for h, _ in rows]
        self.hearings_table.setRowCount(len(rows))
        gray = QBrush(QColor(150, 150, 150))
        for row, (h, is_past) in enumerate(rows):
            id_item = QTableWidgetItem(str(h.id))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.hearings_table.setItem(row, 0, id_item)
            self.hearings_table.setItem(
                row, 1, QTableWidgetItem(format_datetime(h.scheduled_at))
            )
            self.hearings_table.setItem(
                row, 2, QTableWidgetItem(translate(h.hearing_type, HEARING_TYPE_LABELS))
            )
            self.hearings_table.setItem(
                row, 3, QTableWidgetItem(translate(h.status, HEARING_STATUS_LABELS))
            )
            self.hearings_table.setItem(row, 4, QTableWidgetItem(h.notes or ""))
            self.hearings_table.setItem(
                row, 5, QTableWidgetItem(h.audio_filename or "")
            )
            if is_past:
                for col in range(6):
                    self.hearings_table.item(row, col).setForeground(gray)

    def _on_add_hearing(self) -> None:
        dialog = HearingDialog(self, self.app, self.case_file_id)
        if dialog.exec():
            self.load()

    def _on_edit_hearing(self) -> None:
        hearing_id = self._selected_hearing_id()
        if hearing_id is None:
            show_error(self, "Seleccione una audiencia de la tabla.")
            return
        hearing = next(
            (h for h in self._case.hearings if h.id == hearing_id), None
        )
        dialog = HearingDialog(self, self.app, self.case_file_id, hearing)
        if dialog.exec():
            self.load()

    def _on_hearing_context_menu(self, pos) -> None:
        """Menú contextual: abrir el audio asociado a la audiencia."""
        row = self.hearings_table.rowAt(pos.y())
        if not (0 <= row < len(self._hearing_rows)):
            return
        hearing = next(
            (h for h in self._case.hearings if h.id == self._hearing_rows[row]), None
        )
        if hearing is None or not hearing.audio_path:
            return
        menu = QMenu(self.hearings_table)
        menu.addAction(
            "Abrir audio", lambda: self._open_hearing_audio(hearing.audio_path)
        )
        menu.exec_(self.hearings_table.viewport().mapToGlobal(pos))

    def _open_hearing_audio(self, rel_path: str) -> None:
        abs_path = self.app.service.get_audio_abs_path(rel_path)
        if not os.path.isfile(abs_path):
            show_error(self, "El archivo de audio no se encuentra en este equipo.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(abs_path))

    def _on_hearing_double(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._hearing_rows):
            hearing = next(
                (h for h in self._case.hearings if h.id == self._hearing_rows[row]), None
            )
            dialog = HearingDialog(self, self.app, self.case_file_id, hearing)
            if dialog.exec():
                self.load()

    def _build_hearings_section(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(SubtitleLabel("Audiencias"))

        row = QHBoxLayout()
        self.add_hearing_btn = PushButton("Agregar audiencia")
        self.add_hearing_btn.clicked.connect(self._on_add_hearing)
        self.edit_hearing_btn = PushButton("Editar audiencia")
        self.edit_hearing_btn.clicked.connect(self._on_edit_hearing)
        self.del_hearing_btn = PushButton("Eliminar audiencia")
        self.del_hearing_btn.clicked.connect(self._on_del_hearing)
        row.addWidget(self.add_hearing_btn)
        row.addWidget(self.edit_hearing_btn)
        row.addWidget(self.del_hearing_btn)
        vbox.addLayout(row)

        from PyQt5.QtWidgets import QAbstractItemView, QHeaderView

        self.hearings_table = TableWidget()
        self.hearings_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.hearings_table.setColumnCount(6)
        self.hearings_table.setHorizontalHeaderLabels(
            ["ID", "Fecha/Hora", "Tipo", "Estado", "Notas", "Audio"]
        )
        self.hearings_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.hearings_table.cellDoubleClicked.connect(self._on_hearing_double)
        self.hearings_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.hearings_table.customContextMenuRequested.connect(
            self._on_hearing_context_menu
        )
        vbox.addWidget(self.hearings_table, 1)
        return container

    def _on_del_hearing(self) -> None:
        hearing_id = self._selected_hearing_id()
        if hearing_id is None:
            show_error(self, "Seleccione una audiencia de la tabla.")
            return
        if not confirm_delete(self, "¿Eliminar esta audiencia?"):
            return
        try:
            ok = self.app.service.delete_hearing(hearing_id)
        except ValueError as exc:
            logger.exception("Error al eliminar audiencia %s", hearing_id)
            show_error(self, f"Error al eliminar: {exc}")
            return
        if ok:
            show_info(self, "Audiencia eliminada.")
            self.load()
        else:
            show_error(self, "La audiencia no existe.")
