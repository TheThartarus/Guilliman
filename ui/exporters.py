"""
Guilliman Frontend - Exportación de expedientes y agenda a PDF.

Genera documentos PDF con ``reportlab.platypus`` a partir de los DTOs del
db. No depende de ningún toolkit de UI: solo depende de ``reportlab``, los esquemas de
``db`` y las etiquetas/formato de ``ui.shared``.
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from xml.sax.saxutils import escape as _xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from db import CaseFileRead, ScheduledHearingItem

from ui.shared import (
    DEFENDANT_STATUS_LABELS,
    HEARING_STATUS_LABELS,
    HEARING_TYPE_LABELS,
    ORIGIN_TYPE_LABELS,
    VERDICT_STATUS_LABELS,
    format_date,
    format_datetime,
    translate,
)

# --------------------------------------------------------------------------- #
# Estilos de texto (Helvetica soporta acentos españoles en WinAnsi)
# --------------------------------------------------------------------------- #
_STYLES = getSampleStyleSheet()
_TITLE = ParagraphStyle(
    "GuillimanTitle", parent=_STYLES["Title"], fontName="Helvetica-Bold", fontSize=16
)
_SUBTITLE = ParagraphStyle(
    "GuillimanSubtitle",
    parent=_STYLES["Normal"],
    fontName="Helvetica",
    fontSize=10,
    textColor=colors.HexColor("#555555"),
)
_HEADING = ParagraphStyle(
    "GuillimanHeading",
    parent=_STYLES["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=12,
    spaceBefore=10,
    spaceAfter=4,
)
_CELL = ParagraphStyle(
    "GuillimanCell", parent=_STYLES["Normal"], fontName="Helvetica", fontSize=9, leading=11
)
_CELL_B = ParagraphStyle(
    "GuillimanCellBold",
    parent=_CELL,
    fontName="Helvetica-Bold",
)
_HEADER = ParagraphStyle(
    "GuillimanHeader",
    parent=_CELL,
    fontName="Helvetica-Bold",
    textColor=colors.white,
)


def _esc(value) -> str:
    """Escapa XML y normaliza None/cadena vacía a un guion largo."""
    if value is None or value == "":
        return "—"
    return _xml_escape(str(value))


def _p(text, style=_CELL) -> Paragraph:
    """Construye un párrafo con el texto ya escapado y normalizado."""
    return Paragraph(_esc(text), style)


def _grid_style(header: bool = False) -> TableStyle:
    """Estilo base de tabla: bordes, relleno y cabecera sombreada."""
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BBBBBB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F5F5F8")]),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3F51B5")))
    return TableStyle(commands)


# Ancho útil de A4 con márgenes de 15 mm a cada lado.
_PAGE = A4
_USABLE_WIDTH = _PAGE[0] - 2 * 15 * mm


# --------------------------------------------------------------------------- #
# Exportación de expediente
# --------------------------------------------------------------------------- #
def export_case_pdf(case: CaseFileRead, filepath: str) -> None:
    """Genera el PDF completo de un expediente en ``filepath``.

    Exporta **todos** los campos del expediente y de todas sus entidades
    relacionadas (acusados, víctimas, testigos, documentales, expertos,
    actuantes y audiencias), sin excepción.
    """
    story = []

    story.append(Paragraph(_esc(f"Guilliman - Expediente {case.case_number}"), _TITLE))
    story.append(Spacer(1, 4))

    # --- Datos generales ---
    story.append(Paragraph("Datos generales", _HEADING))
    general_rows = [
        [_p("Nº Expediente", _CELL_B), _p(case.case_number)],
        [_p("MP", _CELL_B), _p(case.prosecutor_file_number)],
        [_p("Fiscal", _CELL_B), _p(case.prosecutor_name)],
        [_p("Defensor", _CELL_B), _p(case.defense_attorney)],
        [_p("Audiencia Actual", _CELL_B), _p(case.current_hearing_type)],
        [_p("Origen", _CELL_B), _p(translate(case.origin_type, ORIGIN_TYPE_LABELS))],
        [_p("Procedencia", _CELL_B), _p(case.origin_location)],
        [_p("Ubicación", _CELL_B), _p(case.location)],
        [_p("Tipo de Delito", _CELL_B), _p(case.crime_type)],
        [_p("Emblemático", _CELL_B), _p("Sí" if case.is_emblematic else "No")],
        [_p("Seudónimo", _CELL_B), _p(case.pseudonym)],
        [_p("N° Piezas", _CELL_B), _p(case.piece_count)],
        [_p("Cantidad de Droga", _CELL_B), _p(case.drug_quantity)],
        [_p("Tipo de Droga", _CELL_B), _p(case.drug_type)],
        [_p("Cantidad de Armas", _CELL_B), _p(case.weapon_quantity)],
        [_p("Tipo de Armas", _CELL_B), _p(case.weapon_type)],
        [_p("Descripción del delito", _CELL_B), _p(case.offense_description)],
        [_p("Resumen de hechos", _CELL_B), _p(case.facts_summary)],
    ]
    story.append(
        Table(
            general_rows,
            colWidths=[_USABLE_WIDTH * 0.32, _USABLE_WIDTH * 0.68],
            style=_grid_style(),
        )
    )

    # --- Fechas ---
    story.append(Paragraph("Fechas", _HEADING))
    date_rows = [
        [_p("Acusación", _CELL_B), _p(format_date(case.indictment_date))],
        [_p("Audiencia Preliminar", _CELL_B),
         _p(format_date(case.preliminary_hearing_date))],
        [_p("Prueba Anticipada", _CELL_B),
         _p(format_date(case.anticipated_proof_date))],
        [_p("Apertura a Juicio", _CELL_B), _p(format_date(case.trial_opening_date))],
        [_p("Pase a Juicio", _CELL_B), _p(format_date(case.trial_transfer_date))],
        [_p("Ingreso a Juicio", _CELL_B), _p(format_date(case.trial_entry_date))],
        [_p("Entrada a Control", _CELL_B), _p(format_date(case.control_entry_date))],
        [_p("Salida de Control", _CELL_B), _p(format_date(case.control_exit_date))],
    ]
    story.append(
        Table(
            date_rows,
            colWidths=[_USABLE_WIDTH * 0.40, _USABLE_WIDTH * 0.60],
            style=_grid_style(),
        )
    )

    # --- Acusados ---
    story.append(Paragraph("Acusados", _HEADING))
    defendant_header = [
        _p("Nombre", _HEADER),
        _p("Cédula", _HEADER),
        _p("Fecha Nacimiento", _HEADER),
        _p("Fecha Aprehensión", _HEADER),
        _p("Audiencia Presentación", _HEADER),
        _p("Estado", _HEADER),
        _p("Veredicto", _HEADER),
        _p("Organismo Aprehensor", _HEADER),
        _p("Dirección", _HEADER),
        _p("Teléfono", _HEADER),
        _p("Notas", _HEADER),
    ]
    defendant_rows = [defendant_header]
    for d in case.defendants:
        defendant_rows.append(
            [
                _p(d.full_name),
                _p(d.national_id),
                _p(format_date(d.birth_date)),
                _p(format_date(d.arrest_date)),
                _p(format_date(d.presentation_hearing_date)),
                _p(d.status),
                _p(translate(d.verdict_status, VERDICT_STATUS_LABELS)),
                _p(d.arresting_agency),
                _p(d.address),
                _p(d.phone),
                _p(d.additional_notes),
            ]
        )
    story.append(
        Table(
            defendant_rows,
            colWidths=[
                _USABLE_WIDTH * 0.14,
                _USABLE_WIDTH * 0.09,
                _USABLE_WIDTH * 0.09,
                _USABLE_WIDTH * 0.09,
                _USABLE_WIDTH * 0.11,
                _USABLE_WIDTH * 0.07,
                _USABLE_WIDTH * 0.09,
                _USABLE_WIDTH * 0.10,
                _USABLE_WIDTH * 0.09,
                _USABLE_WIDTH * 0.06,
                _USABLE_WIDTH * 0.07,
            ],
            style=_grid_style(header=True),
            repeatRows=1,
        )
    )

    # --- Víctimas ---
    story.append(Paragraph("Víctimas", _HEADING))
    victim_header = [
        _p("Nombre", _HEADER),
        _p("Cédula", _HEADER),
        _p("Fecha Nacimiento", _HEADER),
        _p("Compareció", _HEADER),
        _p("Fecha Comparecencia", _HEADER),
        _p("Dirección", _HEADER),
        _p("Teléfono", _HEADER),
        _p("Notas", _HEADER),
    ]
    victim_rows = [victim_header]
    for v in case.victims:
        victim_rows.append(
            [
                _p(v.full_name),
                _p(v.national_id),
                _p(format_date(v.birth_date)),
                _p("SÍ" if v.appeared else "NO"),
                _p(format_date(v.appearance_date)),
                _p(v.address),
                _p(v.phone),
                _p(v.additional_notes),
            ]
        )
    story.append(
        Table(
            victim_rows,
            colWidths=[
                _USABLE_WIDTH * 0.18,
                _USABLE_WIDTH * 0.10,
                _USABLE_WIDTH * 0.10,
                _USABLE_WIDTH * 0.08,
                _USABLE_WIDTH * 0.11,
                _USABLE_WIDTH * 0.15,
                _USABLE_WIDTH * 0.10,
                _USABLE_WIDTH * 0.18,
            ],
            style=_grid_style(header=True),
            repeatRows=1,
        )
    )

    # --- Testigos ---
    story.append(Paragraph("Testigos", _HEADING))
    witness_header = [
        _p("Nombre", _HEADER),
        _p("Cédula", _HEADER),
        _p("Compareció", _HEADER),
        _p("Fecha Comparecencia", _HEADER),
        _p("Dirección", _HEADER),
        _p("Teléfono", _HEADER),
        _p("Notas", _HEADER),
    ]
    witness_rows = [witness_header]
    for w in case.witnesses:
        witness_rows.append(
            [
                _p(w.full_name),
                _p(w.national_id),
                _p("SÍ" if w.appeared else "NO"),
                _p(format_date(w.appearance_date)),
                _p(w.address),
                _p(w.phone),
                _p(w.additional_notes),
            ]
        )
    story.append(
        Table(
            witness_rows,
            colWidths=[
                _USABLE_WIDTH * 0.18,
                _USABLE_WIDTH * 0.10,
                _USABLE_WIDTH * 0.08,
                _USABLE_WIDTH * 0.11,
                _USABLE_WIDTH * 0.15,
                _USABLE_WIDTH * 0.10,
                _USABLE_WIDTH * 0.18,
            ],
            style=_grid_style(header=True),
            repeatRows=1,
        )
    )

    # --- Documentales ---
    story.append(Paragraph("Documentales", _HEADING))
    doc_header = [
        _p("Nombre", _HEADER),
        _p("En posesión", _HEADER),
        _p("Fecha recepción", _HEADER),
        _p("Evacuado", _HEADER),
        _p("Fecha evacuación", _HEADER),
        _p("Notas", _HEADER),
    ]
    doc_rows = [doc_header]
    for d in case.documentaries:
        doc_rows.append(
            [
                _p(d.name),
                _p("SÍ" if d.in_possession else "NO"),
                _p(format_date(d.possession_date)),
                _p("SÍ" if d.evacuated else "NO"),
                _p(format_date(d.evacuation_date)),
                _p(d.additional_notes),
            ]
        )
    story.append(
        Table(
            doc_rows,
            colWidths=[
                _USABLE_WIDTH * 0.26,
                _USABLE_WIDTH * 0.12,
                _USABLE_WIDTH * 0.16,
                _USABLE_WIDTH * 0.12,
                _USABLE_WIDTH * 0.18,
                _USABLE_WIDTH * 0.16,
            ],
            style=_grid_style(header=True),
            repeatRows=1,
        )
    )

    # --- Actuantes (funcionarios actuantes / aprehensores) ---
    story.append(Paragraph("Actuantes", _HEADING))
    acting_header = [
        _p("Nombre", _HEADER),
        _p("Compareció", _HEADER),
        _p("Fecha comparecencia", _HEADER),
        _p("Notas", _HEADER),
    ]
    acting_rows = [acting_header]
    for o in case.acting_officials:
        acting_rows.append(
            [
                _p(o.name),
                _p("SÍ" if o.appeared else "NO"),
                _p(format_date(o.appearance_date)),
                _p(o.additional_notes),
            ]
        )
    story.append(
        Table(
            acting_rows,
            colWidths=[
                _USABLE_WIDTH * 0.34,
                _USABLE_WIDTH * 0.15,
                _USABLE_WIDTH * 0.35,
                _USABLE_WIDTH * 0.16,
            ],
            style=_grid_style(header=True),
            repeatRows=1,
        )
    )

    # --- Expertos ---
    story.append(Paragraph("Expertos", _HEADING))
    exp_header = [
        _p("Nombre", _HEADER),
        _p("Compareció", _HEADER),
        _p("Fecha comparecencia", _HEADER),
        _p("Notas", _HEADER),
    ]
    exp_rows = [exp_header]
    for e in case.experts:
        exp_rows.append(
            [
                _p(e.name),
                _p("SÍ" if e.appeared else "NO"),
                _p(format_date(e.appearance_date)),
                _p(e.additional_notes),
            ]
        )
    story.append(
        Table(
            exp_rows,
            colWidths=[
                _USABLE_WIDTH * 0.34,
                _USABLE_WIDTH * 0.15,
                _USABLE_WIDTH * 0.35,
                _USABLE_WIDTH * 0.16,
            ],
            style=_grid_style(header=True),
            repeatRows=1,
        )
    )

    # --- Audiencias (cronológico ascendente) ---
    story.append(Paragraph("Audiencias", _HEADING))
    hearing_header = [
        _p("Fecha/Hora", _HEADER),
        _p("Tipo", _HEADER),
        _p("Estado", _HEADER),
        _p("Notas", _HEADER),
    ]
    hearing_rows = [hearing_header]
    for h in sorted(case.hearings, key=lambda hh: hh.scheduled_at):
        hearing_rows.append(
            [
                _p(format_datetime(h.scheduled_at)),
                _p(translate(h.hearing_type, HEARING_TYPE_LABELS)),
                _p(translate(h.status, HEARING_STATUS_LABELS)),
                _p(h.notes),
            ]
        )
    story.append(
        Table(
            hearing_rows,
            colWidths=[
                _USABLE_WIDTH * 0.23,
                _USABLE_WIDTH * 0.21,
                _USABLE_WIDTH * 0.19,
                _USABLE_WIDTH * 0.37,
            ],
            style=_grid_style(header=True),
            repeatRows=1,
        )
    )

    doc = SimpleDocTemplate(
        filepath,
        pagesize=_PAGE,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"Guilliman - Expediente {case.case_number}",
    )
    doc.build(story)


# --------------------------------------------------------------------------- #
# Exportación de agenda
# --------------------------------------------------------------------------- #
def export_agenda_pdf(
    items: list[ScheduledHearingItem],
    start: date,
    end: date,
    filepath: str,
) -> None:
    """Genera el PDF de la agenda de audiencias en el rango indicado."""
    story = []

    story.append(Paragraph("Guilliman - Agenda de Audiencias", _TITLE))
    story.append(
        Paragraph(
            f"Rango: {format_date(start)} - {format_date(end)}", _SUBTITLE
        )
    )
    story.append(Spacer(1, 6))

    header = [
        _p("Fecha/Hora", _HEADER),
        _p("Expediente", _HEADER),
        _p("Tipo", _HEADER),
        _p("Estado", _HEADER),
        _p("Notas", _HEADER),
    ]
    rows = [header]
    for item in sorted(items, key=lambda hh: hh.scheduled_at):
        rows.append(
            [
                _p(format_datetime(item.scheduled_at)),
                _p(item.case_number),
                _p(translate(item.hearing_type, HEARING_TYPE_LABELS)),
                _p(translate(item.status, HEARING_STATUS_LABELS)),
                _p(item.notes),
            ]
        )
    story.append(
        Table(
            rows,
            colWidths=[
                _USABLE_WIDTH * 0.21,
                _USABLE_WIDTH * 0.19,
                _USABLE_WIDTH * 0.18,
                _USABLE_WIDTH * 0.17,
                _USABLE_WIDTH * 0.25,
            ],
            style=_grid_style(header=True),
        )
    )

    doc = SimpleDocTemplate(
        filepath,
        pagesize=_PAGE,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Guilliman - Agenda de Audiencias",
    )
    doc.build(story)


# --------------------------------------------------------------------------- #
# Exportación de listado de expedientes
# --------------------------------------------------------------------------- #
def export_cases_pdf(cases: list[CaseFileRead], filepath: str) -> None:
    """Genera un PDF listado de varios expedientes en ``filepath``.

    Reutiliza los mismos helpers tipográficos que ``export_case_pdf``.
    """
    story = []
    story.append(Paragraph("Guilliman - Listado de Expedientes", _TITLE))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(_esc(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"), _SUBTITLE)
    )
    story.append(Spacer(1, 10))

    header = [
        _p("Nº Expediente", _HEADER),
        _p("MP", _HEADER),
        _p("Fiscal", _HEADER),
        _p("Fecha acusación", _HEADER),
    ]
    rows = [header]
    for c in cases:
        rows.append(
            [
                _p(c.case_number),
                _p(c.prosecutor_file_number),
                _p(c.prosecutor_name),
                _p(format_date(c.indictment_date)),
            ]
        )
    story.append(
        Table(
            rows,
            colWidths=[
                _USABLE_WIDTH * 0.28,
                _USABLE_WIDTH * 0.22,
                _USABLE_WIDTH * 0.25,
                _USABLE_WIDTH * 0.25,
            ],
            style=_grid_style(header=True),
            repeatRows=1,
        )
    )
    story.append(Spacer(1, 8))
    story.append(Paragraph(_esc(f"Total de expedientes: {len(cases)}"), _SUBTITLE))

    doc = SimpleDocTemplate(
        filepath,
        pagesize=_PAGE,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Guilliman - Listado de Expedientes",
    )
    doc.build(story)


def export_cases_csv(cases: list[CaseFileRead], filepath: str) -> None:
    """Genera un CSV plano del listado de expedientes en ``filepath``."""
    with open(filepath, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "case_number",
                "prosecutor_file_number",
                "prosecutor_name",
                "indictment_date",
            ]
        )
        for c in cases:
            writer.writerow(
                [
                    c.case_number or "",
                    c.prosecutor_file_number or "",
                    c.prosecutor_name or "",
                    format_date(c.indictment_date),
                ]
            )
