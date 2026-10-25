"""Test de la exportación de la agenda a iCalendar (.ics)."""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import ScheduledHearingItem  # noqa: E402
from ui.exporters import export_agenda_ics  # noqa: E402


def test_export_agenda_ics(tmp_path) -> None:
    items = [
        ScheduledHearingItem(
            hearing_id=1,
            case_file_id=2,
            case_number="A;1",
            scheduled_at=datetime(2026, 5, 1, 9, 0),
            hearing_type="Apertura de Juicio",
            status="Scheduled",
            notes="Línea 1\nLínea 2",
        )
    ]
    path = tmp_path / "agenda.ics"
    export_agenda_ics(items, str(path))

    assert path.is_file()
    raw = path.open("r", encoding="utf-8", newline="").read()
    assert raw.startswith("BEGIN:VCALENDAR\r\n")
    assert "BEGIN:VEVENT" in raw
    assert "DTSTART:20260501T090000" in raw
    assert "DTEND:20260501T100000" in raw
    assert "SUMMARY:Audiencia A\\;1 - Apertura de Juicio" in raw
    assert "DESCRIPTION:Programada\\nLínea 1\\nLínea 2" in raw
    assert raw.rstrip().endswith("END:VCALENDAR")
