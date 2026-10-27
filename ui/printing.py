"""Impresión directa de la transcripción de una audiencia (sin pasar por el PDF)."""

from __future__ import annotations

from html import escape

from PyQt5.QtGui import QTextDocument
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter

from db import CaseFileRead, HearingScheduleRead

from ui.shared import (
    HEARING_STATUS_LABELS,
    HEARING_TYPE_LABELS,
    format_datetime,
    translate,
)


def _text(value) -> str:
    if value is None or value == "":
        return "—"
    return escape(str(value))


def _multiline(value) -> str:
    return _text(value).replace("\n", "<br>")


def hearing_minutes_html(case: CaseFileRead, hearing: HearingScheduleRead) -> str:
    """Construye el HTML imprimible de la transcripción (texto escapado)."""
    parties: list[tuple[str, str]] = []
    parties.extend(("Acusado", d.full_name) for d in case.defendants)
    parties.extend(("Víctima", v.full_name) for v in case.victims)
    parties.extend(("Testigo", w.full_name) for w in case.witnesses)
    party_rows = "".join(
        f"<tr><td>{escape(kind)}</td><td>{_text(name)}</td></tr>"
        for kind, name in parties
    ) or '<tr><td colspan="2">—</td></tr>'

    return f"""
    <html><head><meta charset="utf-8"></head>
    <body style="font-family: Calibri, Arial; font-size: 11pt;">
      <h2 style="text-align:center;">TRANSCRIPCIÓN DE AUDIENCIA</h2>
      <table cellspacing="0" cellpadding="4" width="100%">
        <tr><td><b>Expediente:</b></td><td>{_text(case.case_number)}</td></tr>
        <tr><td><b>MP:</b></td><td>{_text(case.prosecutor_file_number)}</td></tr>
        <tr><td><b>Fiscal:</b></td><td>{_text(case.prosecutor_name)}</td></tr>
        <tr><td><b>Defensor:</b></td><td>{_text(case.defense_attorney)}</td></tr>
        <tr><td><b>Fecha y hora:</b></td><td>{_text(format_datetime(hearing.scheduled_at))}</td></tr>
        <tr><td><b>Tipo:</b></td><td>{_text(translate(hearing.hearing_type, HEARING_TYPE_LABELS))}</td></tr>
        <tr><td><b>Estado:</b></td><td>{_text(translate(hearing.status, HEARING_STATUS_LABELS))}</td></tr>
      </table>
      <h3>Partes</h3>
      <table cellspacing="0" cellpadding="3" border="1" width="100%">
        <tr><th align="left">Tipo</th><th align="left">Nombre</th></tr>
        {party_rows}
      </table>
      <h3>Transcripción</h3>
      <p>{_multiline(hearing.transcription)}</p>
    </body></html>
    """


def print_hearing_minutes(parent, case: CaseFileRead, hearing: HearingScheduleRead) -> bool:
    """Abre el diálogo de impresión y envía la transcripción directamente.

    Returns:
        True si el usuario confirmó la impresión; False si canceló.
    """
    printer = QPrinter(QPrinter.HighResolution)
    dialog = QPrintDialog(printer, parent)
    if dialog.exec_() != QPrintDialog.Accepted:
        return False
    document = QTextDocument()
    document.setHtml(hearing_minutes_html(case, hearing))
    document.print_(printer)
    return True
