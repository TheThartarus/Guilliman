"""Test del HTML imprimible de la transcripción (escape de texto)."""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import CaseFileRead, HearingScheduleRead  # noqa: E402
from ui.printing import hearing_minutes_html  # noqa: E402


def test_hearing_minutes_html_escapes_text() -> None:
    case = CaseFileRead(
        id=1,
        case_number="A-1",
        prosecutor_name="Fiscal <X>",
    )
    hearing = HearingScheduleRead(
        id=2,
        case_file_id=1,
        scheduled_at=datetime(2026, 1, 10, 9, 0),
        hearing_type="Apertura de Juicio",
        status="Scheduled",
        transcription="Línea 1\nLínea 2 & <b>",
    )

    html = hearing_minutes_html(case, hearing)

    assert "TRANSCRIPCIÓN DE AUDIENCIA" in html
    assert "A-1" in html
    assert "Fiscal &lt;X&gt;" in html
    assert "Línea 1<br>Línea 2 &amp; &lt;b&gt;" in html
