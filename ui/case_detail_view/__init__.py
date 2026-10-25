"""
Guilliman Frontend - Detalles de un expediente.

Muestra los datos del expediente, la tabla de acusados y la de audiencias, con
botones para editar/eliminar el expediente y exportar el PDF. El alta/edición
de acusados y audiencias se hace con diálogos (``DefendantDialog`` /
``HearingDialog``); la exportación usa ``QFileDialog`` (diálogo nativo del SO).

Para mantener el archivo manejable, las secciones de personas y registros
(acusados, víctimas, testigos, documentales, expertos y audiencias) se definen
como mixins en ``ui.case_detail_view._*`` y se combinan aquí en
``CaseDetailView``.
"""

from __future__ import annotations

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from qfluentwidgets import (
    BodyLabel,
    PlainTextEdit,
    PrimaryPushButton,
    PushButton,
    SettingCardGroup,
    StrongBodyLabel,
    SubtitleLabel,
)

from db import CaseFileRead

from ui.dialogs import confirm_delete, pick_save_pdf
from ui.exporters import export_case_pdf
from ui.shared import (
    HEARING_STATUS_LABELS,
    HEARING_TYPE_LABELS,
    ORIGIN_TYPE_LABELS,
    format_date,
    translate,
)
from ui.widgets import show_error, show_info

from ._acting_officials import _ActingOfficialsSection
from ._attachments import _AttachmentsSection
from ._defendants import _DefendantsSection
from ._documentaries import _DocumentariesSection
from ._experts import _ExpertsSection
from ._hearings import _HearingsSection, _split_hearings
from ._victims import _VictimsSection
from ._witnesses import _WitnessesSection

logger = logging.getLogger("guilliman")


class CaseDetailView(
    _DefendantsSection,
    _VictimsSection,
    _WitnessesSection,
    _DocumentariesSection,
    _AttachmentsSection,
    _ExpertsSection,
    _ActingOfficialsSection,
    _HearingsSection,
    QWidget,
):
    """Vista de detalles de un expediente (solo lectura + acciones)."""

    def __init__(self, app, case_file_id: int, on_close=None) -> None:
        super().__init__()
        self.app = app
        self.case_file_id = case_file_id
        self.on_close = on_close
        self._case: CaseFileRead | None = None
        self._defendant_rows: list[int] = []
        self._victim_rows: list[int] = []
        self._witness_rows: list[int] = []
        self._documentary_rows: list[int] = []
        self._attachment_rows: list[int] = []
        self._expert_rows: list[int] = []
        self._official_rows: list[int] = []
        self._hearing_rows: list[int] = []
        self._build()

    def _build(self) -> None:
        # Contenido scrollable: el detalle es alto en pantallas de 720p y no
        # debe forzar un tamaño mínimo mayor que la pantalla del usuario.
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent}")
        content = QWidget()
        content.setAttribute(Qt.WA_StyledBackground, True)
        content.setStyleSheet("background:transparent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(SubtitleLabel("Detalles del Expediente"))
        header.addStretch(1)
        self.edit_btn = PrimaryPushButton("Editar")
        self.edit_btn.clicked.connect(self._on_edit)
        self.archive_btn = PushButton("Archivar")
        self.archive_btn.clicked.connect(self._on_archive)
        self.export_btn = PushButton("Exportar PDF")
        self.export_btn.clicked.connect(self._on_export)
        header.addWidget(self.edit_btn)
        header.addWidget(self.archive_btn)
        header.addWidget(self.export_btn)
        layout.addLayout(header)

        # Datos del expediente (identificación y estado)
        self.form = QFormLayout()
        self.form.setSpacing(6)
        self._fields: dict[str, BodyLabel] = {}
        for key, label in (
            ("case_number", "Número de Expediente"),
            ("prosecutor_file_number", "MP"),
            ("prosecutor_name", "Fiscal"),
            ("defense_attorney", "Defensor"),
            ("current_hearing_type", "Audiencia Actual"),
            ("origin_type", "Origen"),
            ("origin_location", "Procedencia"),
        ):
            lbl = BodyLabel("—")
            self._fields[key] = lbl
            self.form.addRow(StrongBodyLabel(label), lbl)
        layout.addLayout(self.form)

        # Fechas agrupadas en un SettingCardGroup (estilo Fluent Widgets)
        dates_group = SettingCardGroup("Fechas")
        dates_form = QFormLayout()
        dates_form.setSpacing(6)
        for key, label in (
            ("control_entry_date", "Entrada a Control"),
            ("indictment_date", "Escrito Acusatorio"),
            ("preliminary_hearing_date", "Audiencia Preliminar"),
            ("anticipated_proof_date", "Prueba Anticipada"),
            ("trial_opening_date", "Apertura a Juicio"),
            ("trial_transfer_date", "Pase a Juicio"),
            ("control_exit_date", "Salida de Control"),
            ("trial_entry_date", "Ingreso a Juicio"),
        ):
            lbl = BodyLabel("—")
            self._fields[key] = lbl
            dates_form.addRow(StrongBodyLabel(label), lbl)
        dates_holder = QWidget()
        dates_holder.setLayout(dates_form)
        dates_group.vBoxLayout.addWidget(dates_holder)
        layout.addWidget(dates_group)

        # Otros datos del expediente
        others_group = SettingCardGroup("Otros")
        others_form = QFormLayout()
        others_form.setSpacing(6)
        for key, label in (
            ("crime_type", "Tipo de Delito"),
            ("drug_quantity", "Cantidad de Droga"),
            ("drug_type", "Tipo de Droga"),
            ("weapon_quantity", "Cantidad de Armas"),
            ("weapon_type", "Tipo de Armas"),
            ("is_emblematic", "Emblemático"),
            ("pseudonym", "Seudónimo"),
            ("piece_count", "N.° de Piezas"),
            ("location", "Ubicación"),
        ):
            lbl = BodyLabel("—")
            self._fields[key] = lbl
            others_form.addRow(StrongBodyLabel(label), lbl)

        # Descripción y Resumen como cuadros de solo lectura
        self._text_fields: dict[str, PlainTextEdit] = {}
        for key, label in (
            ("offense_description", "Descripción"),
            ("facts_summary", "Resumen"),
        ):
            te = PlainTextEdit()
            te.setReadOnly(True)
            te.setPlaceholderText("—")
            te.setMaximumHeight(120)
            self._text_fields[key] = te
            others_form.addRow(StrongBodyLabel(label), te)

        others_holder = QWidget()
        others_holder.setLayout(others_form)
        others_group.vBoxLayout.addWidget(others_holder)
        layout.addWidget(others_group)

        # Secciones de entidades — cada mixin construye su propia UI.
        layout.addWidget(self._build_defendants_section())
        layout.addWidget(self._build_victims_section())
        layout.addWidget(self._build_witnesses_section())
        layout.addWidget(self._build_documentaries_section())
        layout.addWidget(self._build_attachments_section())
        layout.addWidget(self._build_experts_section())
        layout.addWidget(self._build_acting_officials_section())
        layout.addWidget(self._build_hearings_section())

        scroll.setWidget(content)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        self.load()

    # ------------------------------------------------------------------ #
    # Carga de datos
    # ------------------------------------------------------------------ #
    def load(self) -> None:
        """Carga (o recarga) los datos del expediente desde el db."""
        try:
            case = self.app.service.get_case_file_by_id(self.case_file_id)
        except ValueError as exc:
            logger.exception("Error al cargar expediente %s", self.case_file_id)
            show_error(self, f"Error al cargar: {exc}")
            return
        if case is None:
            show_error(self, f"El expediente {self.case_file_id} no existe.")
            if self.on_close:
                self.on_close(f"detail-{self.case_file_id}")
            return

        self._case = case
        archived = case.archived_at is not None
        self.archive_btn.setText("Restaurar" if archived else "Archivar")
        self.edit_btn.setEnabled(not archived)
        values = {
            "case_number": case.case_number,
            "prosecutor_file_number": case.prosecutor_file_number,
            "prosecutor_name": case.prosecutor_name,
            "defense_attorney": case.defense_attorney,
            "current_hearing_type": case.current_hearing_type,
            "origin_type": translate(case.origin_type, ORIGIN_TYPE_LABELS),
            "origin_location": case.origin_location,
            "crime_type": case.crime_type,
            "drug_quantity": str(case.drug_quantity) if case.drug_quantity is not None else None,
            "drug_type": case.drug_type,
            "weapon_quantity": str(case.weapon_quantity) if case.weapon_quantity is not None else None,
            "weapon_type": case.weapon_type,
            "is_emblematic": "Sí" if case.is_emblematic else "No",
            "piece_count": str(case.piece_count) if case.piece_count else None,
            "pseudonym": case.pseudonym,
            "location": case.location,
            "control_entry_date": format_date(case.control_entry_date),
            "indictment_date": format_date(case.indictment_date),
            "preliminary_hearing_date": format_date(case.preliminary_hearing_date),
            "anticipated_proof_date": format_date(case.anticipated_proof_date),
            "trial_opening_date": format_date(case.trial_opening_date),
            "trial_transfer_date": format_date(case.trial_transfer_date),
            "control_exit_date": format_date(case.control_exit_date),
            "trial_entry_date": format_date(case.trial_entry_date),
        }
        for key, value in values.items():
            self._fields[key].setText(value if value else "—")

        # Cuadros de texto de solo lectura
        text_values = {
            "offense_description": case.offense_description,
            "facts_summary": case.facts_summary,
        }
        for key, value in text_values.items():
            self._text_fields[key].setPlainText(value if value else "")

        self._fill_defendants(case)
        self._fill_victims(case)
        self._fill_witnesses(case)
        self._fill_documentaries(case)
        self._fill_attachments(case)
        self._fill_experts(case)
        self._fill_acting_officials(case)
        self._fill_hearings(case)

    def refresh(self) -> None:
        """Recarga al volver a esta vista."""
        self.load()

    # ------------------------------------------------------------------ #
    # Acciones del expediente
    # ------------------------------------------------------------------ #
    def _on_edit(self) -> None:
        self.app.shell.open_case_form(self.case_file_id)

    def _on_archive(self) -> None:
        if self._case is None:
            return
        if self._case.archived_at is not None:
            try:
                ok = self.app.service.unarchive_case_file(self.case_file_id)
            except ValueError as exc:
                logger.exception("Error al restaurar expediente %s", self.case_file_id)
                show_error(self, f"Error al restaurar: {exc}")
                return
            if ok:
                show_info(self, "Expediente restaurado.")
                self.load()
            else:
                show_error(self, "El expediente no existe o no estaba archivado.")
            return
        if not confirm_delete(
            self,
            "¿Archivar este expediente? Podrás restaurarlo después; "
            "no se eliminan datos ni audios.",
        ):
            return
        try:
            ok = self.app.service.archive_case_file(self.case_file_id)
        except ValueError as exc:
            logger.exception("Error al archivar expediente %s", self.case_file_id)
            show_error(self, f"Error al archivar: {exc}")
            return
        if ok:
            show_info(self, "Expediente archivado.")
            if self.on_close:
                self.on_close(f"detail-{self.case_file_id}")
        else:
            show_error(self, "El expediente no existe o ya estaba archivado.")

    def _on_export(self) -> None:
        if self._case is None:
            return
        path = pick_save_pdf(self, f"expediente_{self._case.case_number}.pdf")
        if not path:
            return
        try:
            export_case_pdf(self._case, path)
        except Exception as exc:  # noqa: BLE001 - se informa al usuario
            logger.exception("Error al exportar PDF del expediente")
            show_error(self, f"Error al exportar: {exc}")
            return
        show_info(self, "PDF del expediente generado.")
