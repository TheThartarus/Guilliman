"""
Guilliman Frontend - Búsqueda de expedientes (búsqueda rica + exportar lista).

``QWidget`` con panel de filtros combinables que llama a
``service.search_case_files`` (texto libre, estado del acusado, veredicto,
nombres de personas) y muestra los resultados en una tabla.
Doble clic abre el detalle; hay botones para exportar la lista (PDF/CSV).
"""

from __future__ import annotations

import logging

from PyQt5.QtCore import Qt, QTimer
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
    CheckBox,
    ComboBox,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    RoundMenu,
    SubtitleLabel,
    TableWidget,
)

from db import CaseFileRead

from ui import settings as app_settings
from ui.dialogs import confirm_delete, pick_save_pdf
from ui.exporters import export_cases_csv, export_cases_pdf
from ui.shared import (
    CRIME_TYPE_OPTIONS,
    DEFENDANT_STATUS_OPTIONS,
    VERDICT_STATUS_DOMAIN,
    VERDICT_STATUS_OPTIONS,
    parse_date_text,
)
from ui.widgets import (
    combo_current_data,
    combo_set_data,
    show_error,
    show_info,
)

logger = logging.getLogger("guilliman")


class CaseSearchView(QWidget):
    """Vista de búsqueda/listado de expedientes con filtros combinables."""

    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self._last_cases: list[CaseFileRead] = []  # resultados de la última búsqueda
        self._page = 0  # página actual (0-indexed)
        self._page_size = 50
        self._total = 0  # total de resultados de la última búsqueda
        self._last_saved_filters: dict = {}
        self._build()
        self._restore_filters()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        # Debounce de la búsqueda instantánea.
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._do_search)

        layout.addWidget(SubtitleLabel("Expedientes"))

        # --- Panel de filtros ---
        f_widget = QWidget()
        f_layout = QVBoxLayout(f_widget)
        f_layout.setSpacing(10)

        # Fila 1: texto libre + estado del acusado + veredicto.
        row1 = QHBoxLayout()
        self.query = LineEdit()
        self.query.setPlaceholderText("Búsqueda libre (nº expediente / nomenclatura MP)")
        self.defendant_status = ComboBox()
        self.defendant_status.addItem("Cualquiera", userData="")
        for opt in DEFENDANT_STATUS_OPTIONS:
            self.defendant_status.addItem(opt, userData=opt)
        self.verdict_status = ComboBox()
        self.verdict_status.addItem("Cualquiera", userData="")
        for opt in VERDICT_STATUS_OPTIONS:
            self.verdict_status.addItem(opt, userData=opt)
        self.crime_type = ComboBox()
        self.crime_type.addItem("Cualquiera", userData="")
        for opt in CRIME_TYPE_OPTIONS:
            self.crime_type.addItem(opt, userData=opt)
        row1.addWidget(BodyLabel("Texto:"))
        row1.addWidget(self.query, 2)
        row1.addWidget(BodyLabel("Estado acusado:"))
        row1.addWidget(self.defendant_status, 1)
        row1.addWidget(BodyLabel("Veredicto:"))
        row1.addWidget(self.verdict_status, 1)
        row1.addWidget(BodyLabel("Tipo de Delito:"))
        row1.addWidget(self.crime_type, 1)
        f_layout.addLayout(row1)

        # Fila 2: nombres de personas (substring, insensible a mayúsculas en db).
        row2 = QHBoxLayout()
        self.defendant_name = LineEdit()
        self.defendant_name.setPlaceholderText("Nombre")
        self.victim_name = LineEdit()
        self.victim_name.setPlaceholderText("Nombre")
        self.witness_name = LineEdit()
        self.witness_name.setPlaceholderText("Nombre")
        row2.addWidget(BodyLabel("Acusado:"))
        row2.addWidget(self.defendant_name, 1)
        row2.addWidget(BodyLabel("Víctima:"))
        row2.addWidget(self.victim_name, 1)
        row2.addWidget(BodyLabel("Testigo:"))
        row2.addWidget(self.witness_name, 1)
        f_layout.addLayout(row2)

        # Fila 3: rango de fechas de acusación + procedencia.
        row_dates = QHBoxLayout()
        self.indictment_from = LineEdit()
        self.indictment_from.setPlaceholderText("dd/mm/aaaa")
        self.indictment_to = LineEdit()
        self.indictment_to.setPlaceholderText("dd/mm/aaaa")
        self.origin_location = LineEdit()
        self.origin_location.setPlaceholderText("Procedencia")
        row_dates.addWidget(BodyLabel("Acusación desde:"))
        row_dates.addWidget(self.indictment_from, 1)
        row_dates.addWidget(BodyLabel("hasta:"))
        row_dates.addWidget(self.indictment_to, 1)
        row_dates.addWidget(BodyLabel("Procedencia:"))
        row_dates.addWidget(self.origin_location, 2)
        f_layout.addLayout(row_dates)

        # Fila 4: acciones.
        row3 = QHBoxLayout()
        self.search_btn = PrimaryPushButton("Buscar")
        self.search_btn.clicked.connect(self._do_search)
        self.clear_btn = PushButton("Limpiar filtros")
        self.clear_btn.clicked.connect(self._clear_filters)
        self.export_pdf_btn = PushButton("Exportar PDF")
        self.export_pdf_btn.clicked.connect(self._on_export_pdf)
        self.export_csv_btn = PushButton("Exportar CSV")
        self.export_csv_btn.clicked.connect(self._on_export_csv)
        row3.addWidget(self.search_btn)
        row3.addWidget(self.clear_btn)
        row3.addWidget(self.export_pdf_btn)
        row3.addWidget(self.export_csv_btn)
        self.include_archived = CheckBox("Incluir archivados")
        row3.addWidget(self.include_archived)
        row3.addStretch(1)
        f_layout.addLayout(row3)

        # Búsqueda instantánea: cualquier cambio en filtros programa la consulta.
        for field in (
            self.query,
            self.defendant_name,
            self.victim_name,
            self.witness_name,
            self.indictment_from,
            self.indictment_to,
            self.origin_location,
        ):
            field.textChanged.connect(self._schedule_search)
        for combo in (self.defendant_status, self.verdict_status, self.crime_type):
            combo.currentIndexChanged.connect(self._schedule_search)
        self.include_archived.stateChanged.connect(self._schedule_search)

        layout.addWidget(f_widget)

        # --- Resultados ---
        self.table = TableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setBorderVisible(True)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Número", "MP", "Fiscal", "Estado"]
        )
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table.verticalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSortingEnabled(True)
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.table, 1)

        # --- Paginación ---
        pager = QHBoxLayout()
        self.prev_btn = PushButton("Anterior")
        self.prev_btn.clicked.connect(self._prev_page)
        self.next_btn = PushButton("Siguiente")
        self.next_btn.clicked.connect(self._next_page)
        self.status_label = BodyLabel("")
        pager.addWidget(self.prev_btn)
        pager.addWidget(self.next_btn)
        pager.addStretch(1)
        pager.addWidget(self.status_label)
        layout.addLayout(pager)

    def refresh(self) -> None:
        """Recarga la tabla con los filtros actuales (vacío = todos)."""
        self._do_search()

    def _collect_filters(self) -> dict:
        return {
            "query": self.query.text(),
            "defendant_status": combo_current_data(self.defendant_status) or "",
            "verdict_status": combo_current_data(self.verdict_status) or "",
            "crime_type": combo_current_data(self.crime_type) or "",
            "defendant_name": self.defendant_name.text(),
            "victim_name": self.victim_name.text(),
            "witness_name": self.witness_name.text(),
            "indictment_from": self.indictment_from.text(),
            "indictment_to": self.indictment_to.text(),
            "origin_location": self.origin_location.text(),
            "include_archived": self.include_archived.isChecked(),
        }

    def _save_filters(self) -> None:
        """Persiste los filtros si cambiaron desde el último guardado."""
        data = self._collect_filters()
        if data != self._last_saved_filters:
            app_settings.save_search_filters(data)
            self._last_saved_filters = data

    def _restore_filters(self) -> None:
        """Restaura los filtros guardados de la última ejecución."""
        data = app_settings.load_search_filters()
        self._last_saved_filters = data
        if not data:
            return
        self.query.setText(str(data.get("query", "")))
        self.defendant_name.setText(str(data.get("defendant_name", "")))
        self.victim_name.setText(str(data.get("victim_name", "")))
        self.witness_name.setText(str(data.get("witness_name", "")))
        self.indictment_from.setText(str(data.get("indictment_from", "")))
        self.indictment_to.setText(str(data.get("indictment_to", "")))
        self.origin_location.setText(str(data.get("origin_location", "")))
        combo_set_data(self.defendant_status, data.get("defendant_status") or "")
        combo_set_data(self.verdict_status, data.get("verdict_status") or "")
        combo_set_data(self.crime_type, data.get("crime_type") or "")
        self.include_archived.setChecked(bool(data.get("include_archived", False)))

    def _clear_filters(self) -> None:
        self.query.clear()
        self.defendant_status.setCurrentIndex(0)
        self.verdict_status.setCurrentIndex(0)
        self.crime_type.setCurrentIndex(0)
        self.defendant_name.clear()
        self.victim_name.clear()
        self.witness_name.clear()
        self.indictment_from.clear()
        self.indictment_to.clear()
        self.origin_location.clear()
        self.include_archived.setChecked(False)
        self._page = 0
        self._do_search()

    def _schedule_search(self, *_args) -> None:
        """Programa una búsqueda tras una pausa de tecleo (debounce)."""
        self._page = 0
        self._search_timer.start()

    def _do_search(self) -> None:
        self._search_timer.stop()
        query = (self.query.text() or "").strip()
        defendant_status = combo_current_data(self.defendant_status) or None
        verdict_status_display = combo_current_data(self.verdict_status) or None
        verdict_status = (
            VERDICT_STATUS_DOMAIN.get(verdict_status_display, verdict_status_display)
            if verdict_status_display
            else None
        )
        defendant_name = (self.defendant_name.text() or "").strip() or None
        victim_name = (self.victim_name.text() or "").strip() or None
        witness_name = (self.witness_name.text() or "").strip() or None
        crime_type = combo_current_data(self.crime_type) or None
        include_archived = self.include_archived.isChecked()
        indictment_from = parse_date_text(self.indictment_from.text())
        indictment_to = parse_date_text(self.indictment_to.text())
        origin_location = (self.origin_location.text() or "").strip() or None

        # Obtener total para paginación.
        self._total = self.app.service.count_case_files(
            query,
            defendant_name=defendant_name,
            victim_name=victim_name,
            witness_name=witness_name,
            defendant_status=defendant_status,
            verdict_status=verdict_status,
            crime_type=crime_type,
            origin_location=origin_location,
            indictment_date_from=indictment_from,
            indictment_date_to=indictment_to,
            include_archived=include_archived,
        )
        max_page = max(0, (self._total - 1) // self._page_size)
        self._page = min(self._page, max_page)

        offset = self._page * self._page_size
        try:
            cases = self.app.service.search_case_files(
                query,
                limit=self._page_size,
                offset=offset,
                defendant_name=defendant_name,
                victim_name=victim_name,
                witness_name=witness_name,
                defendant_status=defendant_status,
                verdict_status=verdict_status,
                crime_type=crime_type,
                origin_location=origin_location,
                indictment_date_from=indictment_from,
                indictment_date_to=indictment_to,
                include_archived=include_archived,
            )
        except ValueError as exc:
            logger.exception("Error al buscar expedientes")
            show_error(self, f"Error al buscar: {exc}")
            return

        self._last_cases = cases
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(cases))
        for row, case in enumerate(cases):
            id_item = QTableWidgetItem()
            id_item.setData(Qt.DisplayRole, case.id)
            id_item.setData(Qt.UserRole, case.id)
            id_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, id_item)
            for col, value in enumerate(
                (
                    case.case_number or "",
                    case.prosecutor_file_number or "",
                    case.prosecutor_name or "",
                    "Archivado" if case.archived_at else "Activo",
                ),
                start=1,
            ):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.table.setItem(row, col, item)
        self.table.setSortingEnabled(True)

        self._update_pager()
        self._save_filters()

    def _on_export_pdf(self) -> None:
        if not self._last_cases:
            show_error(self, "No hay resultados para exportar.")
            return
        path = pick_save_pdf(self, "listado_expedientes.pdf")
        if not path:
            return
        export_cases_pdf(self._last_cases, path)
        show_info(self, "Listado PDF exportado.")

    def _on_export_csv(self) -> None:
        if not self._last_cases:
            show_error(self, "No hay resultados para exportar.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar CSV", "listado_expedientes.csv", "CSV (*.csv)"
        )
        if not path:
            return
        export_cases_csv(self._last_cases, path)
        show_info(self, "Listado CSV exportado.")

    def _case_id_at(self, row: int) -> int | None:
        """Retorna el ID del expediente en una fila (robusto ante el ordenamiento)."""
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item is not None else None

    def _case_at(self, row: int):
        case_id = self._case_id_at(row)
        if case_id is None:
            return None
        return next((c for c in self._last_cases if c.id == case_id), None)

    def _on_row_double_clicked(self, row: int, _col: int) -> None:
        case_id = self._case_id_at(row)
        if case_id is not None:
            self.app.shell.open_case_detail(case_id)

    def _on_context_menu(self, pos) -> None:
        row = self.table.indexAt(pos).row()
        case = self._case_at(row)
        if case is None:
            return
        menu = RoundMenu(parent=self)
        if case.archived_at is not None:
            restore_action = Action("Restaurar")
            menu.addAction(restore_action)
            restore_action.triggered.connect(lambda *_, r=row: self._restore_case(r))
            delete_action = Action("Eliminar definitivamente")
            menu.addAction(delete_action)
            delete_action.triggered.connect(lambda *_, r=row: self._delete_case(r))
        else:
            edit_action = Action("Editar")
            menu.addAction(edit_action)
            edit_action.triggered.connect(lambda *_, r=row: self._edit_case(r))
            archive_action = Action("Archivar")
            menu.addAction(archive_action)
            archive_action.triggered.connect(lambda *_, r=row: self._archive_case(r))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _edit_case(self, row: int) -> None:
        case_id = self._case_id_at(row)
        if case_id is not None:
            self.app.shell.open_case_form(case_id)

    def _archive_case(self, row: int) -> None:
        case_id = self._case_id_at(row)
        if case_id is None:
            return
        if not confirm_delete(
            self,
            "¿Archivar este expediente? Podrás restaurarlo después; "
            "no se eliminan datos ni audios.",
        ):
            return
        try:
            ok = self.app.service.archive_case_file(case_id)
        except ValueError as exc:
            logger.exception("Error al archivar expediente %s", case_id)
            show_error(self, f"Error al archivar: {exc}")
            return
        if ok:
            show_info(self, "Expediente archivado.")
            self._do_search()
        else:
            show_error(self, "El expediente no existe o ya estaba archivado.")

    def _restore_case(self, row: int) -> None:
        case_id = self._case_id_at(row)
        if case_id is None:
            return
        try:
            ok = self.app.service.unarchive_case_file(case_id)
        except ValueError as exc:
            logger.exception("Error al restaurar expediente %s", case_id)
            show_error(self, f"Error al restaurar: {exc}")
            return
        if ok:
            show_info(self, "Expediente restaurado.")
            self._do_search()
        else:
            show_error(self, "El expediente no existe o no estaba archivado.")

    def _delete_case(self, row: int) -> None:
        case_id = self._case_id_at(row)
        if case_id is None:
            return
        if not confirm_delete(
            self,
            "¿Eliminar definitivamente este expediente y todos sus registros? "
            "Esta acción no se puede deshacer.",
        ):
            return
        try:
            ok = self.app.service.delete_case_file(case_id)
        except ValueError as exc:
            logger.exception("Error al eliminar expediente %s", case_id)
            show_error(self, f"Error al eliminar: {exc}")
            return
        if ok:
            show_info(self, "Expediente eliminado.")
            self._do_search()
        else:
            show_error(self, "El expediente no existe.")

    # --- Paginación ---

    def _update_pager(self) -> None:
        total_pages = max(1, (self._total + self._page_size - 1) // self._page_size)
        self.prev_btn.setEnabled(self._page > 0)
        self.next_btn.setEnabled(self._page < total_pages - 1)
        if self._total == 0:
            self.status_label.setText("Sin resultados")
        else:
            start = self._page * self._page_size + 1
            end = min(start + self._page_size - 1, self._total)
            self.status_label.setText(
                f"Mostrando {start}–{end} de {self._total} resultados"
                f"  (página {self._page + 1} de {total_pages})"
            )

    def _prev_page(self) -> None:
        if self._page > 0:
            self._page -= 1
            self._do_search()

    def _next_page(self) -> None:
        total_pages = max(1, (self._total + self._page_size - 1) // self._page_size)
        if self._page < total_pages - 1:
            self._page += 1
            self._do_search()
