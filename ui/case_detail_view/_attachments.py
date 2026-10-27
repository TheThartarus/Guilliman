"""Sección de documentos adjuntos del detalle de expediente."""

from __future__ import annotations

import logging
import os

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from qfluentwidgets import PushButton, SubtitleLabel, TableWidget

from db import AttachmentCreate, CaseFileRead

from ui.dialogs import confirm_delete
from ui.shared import format_datetime
from ui.widgets import show_error, show_info

logger = logging.getLogger("guilliman")


class _AttachmentsSection:
    """Métodos de la sección de documentos adjuntos del ``CaseDetailView``."""

    def _selected_attachment(self):
        row = self.attachments_table.currentRow()
        if 0 <= row < len(self._attachment_rows):
            attachment_id = self._attachment_rows[row]
            return next(
                (a for a in self._case.attachments if a.id == attachment_id), None
            )
        return None

    def _fill_attachments(self, case: CaseFileRead) -> None:
        self._attachment_rows = [a.id for a in case.attachments]
        self.attachments_table.setRowCount(len(case.attachments))
        for row, attachment in enumerate(case.attachments):
            id_item = QTableWidgetItem(str(attachment.id))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.attachments_table.setItem(row, 0, id_item)
            self.attachments_table.setItem(
                row, 1, QTableWidgetItem(attachment.name or "")
            )
            self.attachments_table.setItem(
                row, 2, QTableWidgetItem(attachment.original_filename or "")
            )
            self.attachments_table.setItem(
                row, 3, QTableWidgetItem(format_datetime(attachment.uploaded_at))
            )

    def _on_add_attachment(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Adjuntar documento", "", "Todos los archivos (*.*)"
        )
        if not path:
            return
        default_name = os.path.basename(path)
        name, accepted = QInputDialog.getText(
            self, "Nombre del documento", "Nombre:", text=default_name
        )
        if not accepted:
            return
        name = (name or "").strip() or default_name
        try:
            self.app.service.add_attachment(
                self.case_file_id, AttachmentCreate(name=name), path
            )
        except (OSError, ValueError) as exc:
            logger.exception("Error al adjuntar documento al expediente %s", self.case_file_id)
            show_error(self, f"No se pudo adjuntar el documento: {exc}")
            return
        show_info(self, "Documento adjuntado.")
        self.load()

    def _on_open_attachment(self) -> None:
        attachment = self._selected_attachment()
        if attachment is None:
            show_error(self, "Seleccione un documento de la tabla.")
            return
        abs_path = self.app.service.get_attachment_abs_path(attachment.rel_path)
        if not os.path.isfile(abs_path):
            show_error(self, "El archivo del documento no se encuentra en este equipo.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(abs_path))

    def _on_del_attachment(self) -> None:
        attachment = self._selected_attachment()
        if attachment is None:
            show_error(self, "Seleccione un documento de la tabla.")
            return
        if not confirm_delete(self, "¿Eliminar este documento adjunto?"):
            return
        try:
            ok = self.app.service.delete_attachment(attachment.id)
        except ValueError as exc:
            logger.exception("Error al eliminar documento %s", attachment.id)
            show_error(self, f"Error al eliminar: {exc}")
            return
        if ok:
            show_info(self, "Documento eliminado.")
            self.load()
        else:
            show_error(self, "El documento no existe.")

    def _build_attachments_section(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(SubtitleLabel("Documentos"))

        row = QHBoxLayout()
        self.add_attachment_btn = PushButton("Adjuntar documento")
        self.add_attachment_btn.clicked.connect(self._on_add_attachment)
        self.open_attachment_btn = PushButton("Abrir")
        self.open_attachment_btn.clicked.connect(self._on_open_attachment)
        self.del_attachment_btn = PushButton("Eliminar")
        self.del_attachment_btn.clicked.connect(self._on_del_attachment)
        row.addWidget(self.add_attachment_btn)
        row.addWidget(self.open_attachment_btn)
        row.addWidget(self.del_attachment_btn)
        vbox.addLayout(row)

        from PyQt5.QtWidgets import QAbstractItemView, QHeaderView

        self.attachments_table = TableWidget()
        self.attachments_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.attachments_table.setColumnCount(4)
        self.attachments_table.setHorizontalHeaderLabels(
            ["ID", "Nombre", "Archivo", "Fecha"]
        )
        self.attachments_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.attachments_table.cellDoubleClicked.connect(
            lambda *_: self._on_open_attachment()
        )
        vbox.addWidget(self.attachments_table, 1)
        return container
