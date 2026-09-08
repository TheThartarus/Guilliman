"""
Smoke test de la UI PyQt (sin abrir ventana).

Construye el ``AppShell`` de qfluentwidgets y todas las vistas/formularios/
diálogos contra una base de datos temporal, crea datos de prueba a través del
db y valida flujos completos de creación/edición. Elimina la BD temporal
al final.

La ventana no se muestra (plataforma "offscreen"), pero se construye el árbol
de widgets completo, lo que detecta errores de API de PyQt/qfluentwidgets.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import date, datetime, timedelta

from PyQt5.QtWidgets import QApplication

# QApplication debe vivir hasta el cierre del intérprete; si es local de la
# función de test, se destruye antes que los widgets y Qt aborta (segfault).
APP = QApplication.instance() or QApplication([])

from db import (
    CaseFileCreate,
    CaseFileService,
    DefendantCreate,
    HearingScheduleCreate,
)
from db.database import dispose_engine, reset_session_factory

import ui.app_shell as app_shell
import ui.case_detail_view as case_detail_view
import ui.case_form_view as case_form_view
import ui.case_search_view as case_search_view
import ui.dialogs as dialogs
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtCore import QDate

from ui.widgets import combo_set_data, make_uppercase


DB_PATH = "test_pyqt_smoke.db"


def _cleanup() -> None:
    reset_session_factory()
    try:
        dispose_engine(DB_PATH)
    except Exception:
        pass
    for suffix in ("", "-wal", "-shm"):
        p = DB_PATH + suffix
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


def test_pyqt_ui_builds() -> None:
    _cleanup()

    service = CaseFileService(DB_PATH)
    service.init_db()

    # Crea un expediente con todo para ejercitar la carga de detalle/edición.
    case_id = service.create_case_file(
        CaseFileCreate(
            case_number="MP-2026-SMOKE",
            prosecutor_file_number="MP-999",
            prosecutor_name="Fiscalia Test",
            current_hearing_type="Apertura",
            offense_description="Hechos de prueba",
            indictment_date=date(2026, 1, 10),
            preliminary_hearing_date=date(2026, 2, 1),
            anticipated_proof_date=date(2026, 2, 15),
            trial_opening_date=date(2026, 3, 1),
            trial_transfer_date=date(2026, 4, 1),
            trial_entry_date=date(2026, 5, 1),
            origin_type="Local",
        ),
        defendants_list=[
            DefendantCreate(
                full_name="Juana Prueba",
                national_id="12345678",
                arrest_date=date(2026, 1, 5),
                additional_notes="Sin antecedentes",
            )
        ],
        hearings_list=[
            HearingScheduleCreate(
                scheduled_at=datetime(2026, 3, 1, 9, 30),
                hearing_type="Apertura de Juicio",
                status="Scheduled",
                notes="Audiencia inicial",
            ),
            HearingScheduleCreate(
                scheduled_at=datetime(2026, 4, 15, 11, 0),
                hearing_type="Continuación de Juicio",
                status="Deferred",
                notes="",
            ),
        ],
    )

    shell = app_shell.AppShell(service)
    assert shell.windowTitle().startswith("Guilliman")
    assert shell.search_view is not None
    assert shell.new_view is not None
    assert shell.agenda_view is not None
    assert shell.settings_view is not None

    agenda = shell.agenda_view
    agenda.start_date.setDate(QDate(2020, 1, 1))
    agenda.end_date.setDate(QDate(2020, 12, 31))
    agenda._on_clear_filters()
    assert agenda.start_date.getDate() == QDate.currentDate()
    assert agenda.end_date.getDate() == QDate.currentDate()

    search = case_search_view.CaseSearchView(shell.app)
    search.refresh()
    form = case_form_view.CaseFormView(shell.app, None)
    form.reset()
    form._case_number.setText("MP-2026-SMOKE")
    form._prosecutor_name.setText("Fiscalia Test")
    form._offense_description.setPlainText("Hechos")
    form._indictment_date.check.setChecked(True)
    form._indictment_date.edit.setDate(QDate(2026, 1, 10))
    form._preliminary_hearing_date.edit.setDate(QDate(2026, 2, 1))
    form._anticipated_proof_date.check.setChecked(True)
    form._anticipated_proof_date.edit.setDate(QDate(2026, 2, 15))
    form._trial_opening_date.edit.setDate(QDate(2026, 3, 1))
    form._trial_transfer_date.edit.setDate(QDate(2026, 4, 1))
    form._trial_entry_date.edit.setDate(QDate(2026, 5, 1))
    kwargs = form._collect_kwargs()
    assert kwargs["case_number"] == "MP-2026-SMOKE"
    assert kwargs["prosecutor_name"] == "FISCALIA TEST"
    assert kwargs["anticipated_proof_date"] == date(2026, 2, 15)

    detail = case_detail_view.CaseDetailView(shell.app, case_id, on_close=lambda: None)
    detail.load()
    assert detail._case is not None
    assert detail._case.id == case_id
    assert detail._fields["anticipated_proof_date"].text() == "15/02/2026"

    shell.open_case_detail(case_id)
    shell.open_case_form(case_id)
    shell._close_route(f"detail-{case_id}")
    shell._close_route(f"edit-{case_id}")

    dlg_def = dialogs.DefendantDialog(None, shell.app, case_id)
    dlg_def._full_name.setText("Otro Acusado")
    dlg_def._national_id.setText("87654321")
    ddata = dlg_def._collect()
    assert ddata["full_name"] == "OTRO ACUSADO"
    assert ddata["national_id"] == "87654321"

    dlg_hear = dialogs.HearingDialog(None, shell.app, case_id)
    dlg_hear._scheduled_card.set(datetime(2026, 6, 1, 10, 0))
    combo_set_data(dlg_hear._hearing_type, "Apertura de Juicio")
    combo_set_data(dlg_hear._status, "Scheduled")
    hdata = dlg_hear._collect()
    assert hdata["hearing_type"] == "Apertura de Juicio"
    assert hdata["status"] == "Scheduled"

    le = QLineEdit()
    make_uppercase(le)
    le.setText("mp-999")
    assert le.text() == "MP-999"

    shell.close()
    _cleanup()


if __name__ == "__main__":
    test_pyqt_ui_builds()
    print("PYQT SMOKE TEST OK")
