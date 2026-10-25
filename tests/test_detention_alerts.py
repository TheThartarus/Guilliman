"""Test de las alertas por plazo de detención."""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (  # noqa: E402
    CaseFileCreate,
    CaseFileService,
    DefendantCreate,
)
from db.database import dispose_engine, reset_session_factory  # noqa: E402


def test_detention_alerts(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "detention.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        case_id = service.create_case_file(CaseFileCreate(case_number="DET-1"))
        long_ago = date.today() - timedelta(days=40)
        short_ago = date.today() - timedelta(days=5)
        service.add_defendant(
            case_id,
            DefendantCreate(
                full_name="Detenido Largo", arrest_date=long_ago, status="Detenido"
            ),
        )
        service.add_defendant(
            case_id,
            DefendantCreate(
                full_name="Detenido Corto", arrest_date=short_ago, status="Detenido"
            ),
        )
        service.add_defendant(
            case_id,
            DefendantCreate(
                full_name="En Libertad", arrest_date=long_ago, status="En Libertad"
            ),
        )

        by_name = {
            d.full_name: d
            for d in service.get_case_file_by_id(case_id).defendants
        }
        assert by_name["Detenido Largo"].days_detained >= 40
        assert by_name["Detenido Corto"].days_detained >= 5
        assert by_name["En Libertad"].days_detained is None

        alerts = service.list_detention_alerts(30)
        assert [alert.full_name for alert in alerts] == ["Detenido Largo"]
        assert alerts[0].days_detained >= 40
        assert alerts[0].case_number == "DET-1"

        # Un expediente archivado no genera alertas.
        service.archive_case_file(case_id)
        assert service.list_detention_alerts(30) == []
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
