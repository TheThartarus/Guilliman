"""Test de la exportación de la transcripción de audiencia a RTF y PDF."""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (  # noqa: E402
    CaseFileCreate,
    CaseFileService,
    CrimeCreate,
    DefendantCreate,
    HearingScheduleCreate,
    HearingScheduleUpdate,
    VictimCreate,
    WitnessCreate,
)
from db.database import dispose_engine, reset_session_factory  # noqa: E402
from ui.exporters import (  # noqa: E402
    export_hearing_minutes_pdf,
    export_hearing_minutes_rtf,
)


def test_minutes_export_rtf_and_pdf(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "minutes.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        case_id = service.create_case_file(
            CaseFileCreate(
                case_number="TRANSCRIPCION-1",
                prosecutor_name="Fiscal",
            ),
            crimes_list=[CrimeCreate(crime_type="Armas")],
            defendants_list=[
                DefendantCreate(full_name="Juan Perez", national_id="1-1")
            ],
            victims_list=[
                VictimCreate(full_name="Ana Victima", national_id="2-2")
            ],
            witnesses_list=[
                WitnessCreate(full_name="Luis Testigo", national_id="3-3")
            ],
            hearings_list=[
                HearingScheduleCreate(
                    scheduled_at=datetime(2026, 1, 10, 9, 0),
                    hearing_type="Apertura de Juicio",
                    status="Scheduled",
                    notes="Nota de la audiencia",
                )
            ],
        )
        hearing = service.get_case_file_by_id(case_id).hearings[0]
        service.update_hearing(
            hearing.id,
            HearingScheduleUpdate(
                transcription="TRANSCRIPCION DE PRUEBA\n\nSegunda línea con ñ, á, é."
            ),
        )
        case = service.get_case_file_by_id(case_id)
        hearing = case.hearings[0]

        rtf_path = tmp_path / "transcripcion.rtf"
        pdf_path = tmp_path / "transcripcion.pdf"
        export_hearing_minutes_rtf(case, hearing, str(rtf_path))
        export_hearing_minutes_pdf(case, hearing, str(pdf_path))

        assert rtf_path.is_file()
        rtf = rtf_path.read_text(encoding="ascii")
        assert rtf.startswith("{\\rtf1")
        assert "TRANSCRIPCION DE PRUEBA" in rtf
        assert "Juan Perez" in rtf

        assert pdf_path.is_file()
        assert pdf_path.stat().st_size > 0
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
