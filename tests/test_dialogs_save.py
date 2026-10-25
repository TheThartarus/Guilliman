"""Test de regresión para las rutas de guardado de los diálogos.

Ejercita ``DefendantDialog._on_save`` y ``HearingDialog._on_save`` contra una
base de datos temporal con un ``CaseFileService`` real, parcheando
``ui.dialogs.show_info``/``show_error`` para capturar la llamada de éxito.

Esto habría fallado con ``NameError`` antes de importar ``show_info`` en
``ui.dialogs`` (el bug que se coló en la migración a PyQt).
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import tempfile
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt5.QtWidgets import QApplication

APP = QApplication.instance() or QApplication([])

from datetime import date, datetime, timedelta  # noqa: E402

from db import CaseFileCreate, CaseFileService, HearingScheduleCreate  # noqa: E402
from db.database import dispose_engine, reset_session_factory  # noqa: E402
from ui import dialogs  # noqa: E402
from ui.dialogs import CrimeDialog, DefendantDialog, HearingDialog, HearingTranscriptionDialog  # noqa: E402
from ui.dialogs import _defendant, _hearing, _transcription  # noqa: E402
from ui.widgets import combo_set_data  # noqa: E402


def _make_service():
    db = os.path.join(tempfile.gettempdir(), "test_dialogs_save.db")
    for suffix in ("", "-wal", "-shm"):
        p = db + suffix
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass
    reset_session_factory()
    svc = CaseFileService(db)
    svc.init_db()
    return svc, db


def _cleanup(db):
    reset_session_factory()
    try:
        dispose_engine(db)
    except Exception:
        pass
    for suffix in ("", "-wal", "-shm"):
        p = db + suffix
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


def _fake_app(svc):
    return type("App", (), {"service": svc, "shell": None})()


def test_defendant_dialog_save_calls_show_info():
    svc, db = _make_service()
    try:
        case_id = svc.create_case_file(
            CaseFileCreate(
                case_number="MP-TEST",
                prosecutor_name="Fiscal",
                origin_type="Local",
                indictment_date=date(2026, 1, 1),
            )
        )
        dlg = DefendantDialog(None, _fake_app(svc), case_id)
        dlg._full_name.setText("Juan Perez")
        dlg._national_id.setText("123")
        dlg._arrest_card.set(date(2026, 1, 5))

        with mock.patch.object(_defendant, "show_info") as m_info, \
                mock.patch.object(_defendant, "show_error") as m_err:
            dlg._on_save()

        assert m_info.called, "show_info debió llamarse en guardado exitoso"
        assert not m_err.called, "show_error no debió llamarse en éxito"
        case = svc.get_case_file_by_id(case_id)
        assert any(d.full_name == "JUAN PEREZ" for d in case.defendants)
    finally:
        _cleanup(db)


def test_hearing_dialog_save_calls_show_info():
    svc, db = _make_service()
    try:
        case_id = svc.create_case_file(
            CaseFileCreate(
                case_number="MP-TEST2",
                prosecutor_name="Fiscal",

                origin_type="Local",
            )
        )
        dlg = HearingDialog(None, _fake_app(svc), case_id)
        dlg._scheduled_card.set(datetime.now() + timedelta(days=1))
        dlg._hearing_type.setCurrentText("Apertura de Juicio")
        combo_set_data(dlg._status, "Scheduled")

        with mock.patch.object(_hearing, "show_info") as m_info, \
                mock.patch.object(_hearing, "show_error") as m_err:
            dlg._on_save()

        assert m_info.called, "show_info debió llamarse en guardado exitoso"
        assert not m_err.called, "show_error no debió llamarse en éxito"
        items = svc.list_scheduled_hearings(
            datetime(2000, 1, 1), datetime(2100, 12, 31, 23, 59)
        )
        assert any(i.case_number == "MP-TEST2" for i in items)
    finally:
        _cleanup(db)


def test_hearing_dialog_allows_past_date_on_create():
    svc, db = _make_service()
    try:
        case_id = svc.create_case_file(
            CaseFileCreate(
                case_number="MP-PAST",
                prosecutor_name="Fiscal",

                origin_type="Local",
            )
        )
        dlg = HearingDialog(None, _fake_app(svc), case_id)
        dlg._scheduled_card.set(datetime(2000, 1, 1, 10, 0))  # fecha pasada
        dlg._hearing_type.setCurrentText("Apertura de Juicio")
        combo_set_data(dlg._status, "Scheduled")

        with mock.patch.object(_hearing, "show_info") as m_info, \
                mock.patch.object(_hearing, "show_error") as m_err:
            dlg._on_save()

        assert m_info.called, "show_info debió llamarse con fecha pasada"
        assert not m_err.called, "show_error no debió llamarse con fecha pasada"
        items = svc.list_scheduled_hearings(
            datetime(1999, 1, 1), datetime(2100, 12, 31, 23, 59)
        )
        assert any(i.case_number == "MP-PAST" for i in items)
    finally:
        _cleanup(db)


def test_hearing_dialog_allows_unchanged_past_date_on_edit():
    svc, db = _make_service()
    try:
        case_id = svc.create_case_file(
            CaseFileCreate(
                case_number="MP-EDIT",
                prosecutor_name="Fiscal",

                origin_type="Local",
            )
        )
        # add_hearing ya permite registrar audiencias en fechas pasadas.
        svc.add_hearing(
            case_id,
            HearingScheduleCreate(
                scheduled_at=datetime(2000, 1, 1, 10, 0),
                hearing_type="Apertura de Juicio",
                status="Scheduled",
            ),
        )
        hearing_dto = svc.get_case_file_by_id(case_id).hearings[0]
        dlg = HearingDialog(None, _fake_app(svc), case_id, hearing=hearing_dto)
        # No se cambia la fecha (sigue en el pasado): la edición debe permitirse.
        dlg._hearing_type.setCurrentText("Apertura de Juicio")
        combo_set_data(dlg._status, "Scheduled")

        with mock.patch.object(_hearing, "show_info") as m_info, \
                mock.patch.object(_hearing, "show_error") as m_err:
            dlg._on_save()

        assert m_info.called, "editar una audiencia pasada debió permitirse"
        assert not m_err.called, "no debió dar error al editar una fecha pasada"
    finally:
        _cleanup(db)


def test_hearing_transcription_dialog_saves():
    svc, db = _make_service()
    try:
        case_id = svc.create_case_file(CaseFileCreate(case_number="MP-ACTA"))
        svc.add_hearing(
            case_id,
            HearingScheduleCreate(scheduled_at=datetime.now() + timedelta(days=1)),
        )
        hearing = svc.get_case_file_by_id(case_id).hearings[0]
        dlg = HearingTranscriptionDialog(None, _fake_app(svc), hearing)
        dlg._editor.setPlainText("  ACTA DE PRUEBA\nlínea 2  ")

        with mock.patch.object(_transcription, "show_info") as m_info, \
                mock.patch.object(_transcription, "show_error") as m_err:
            dlg._on_save()

        assert m_info.called, "show_info debió llamarse al guardar el acta"
        assert not m_err.called, "no debió dar error al guardar el acta"
        saved = svc.get_case_file_by_id(case_id).hearings[0].transcription
        assert saved == "ACTA DE PRUEBA\nlínea 2"
    finally:
        _cleanup(db)


def test_hearing_transcription_dialog_autosaves():
    svc, db = _make_service()
    try:
        case_id = svc.create_case_file(CaseFileCreate(case_number="MP-AUTOSAVE"))
        svc.add_hearing(
            case_id,
            HearingScheduleCreate(scheduled_at=datetime.now() + timedelta(days=1)),
        )
        hearing = svc.get_case_file_by_id(case_id).hearings[0]
        dlg = HearingTranscriptionDialog(None, _fake_app(svc), hearing)

        dlg._editor.setPlainText("ACTA AUTOGUARDADA")
        assert dlg._autosave()
        assert (
            svc.get_case_file_by_id(case_id).hearings[0].transcription
            == "ACTA AUTOGUARDADA"
        )

        # Cerrar sin pulsar "Guardar" también persiste los cambios pendientes.
        dlg._editor.setPlainText("SEGUNDA VERSION")
        dlg.reject()
        assert (
            svc.get_case_file_by_id(case_id).hearings[0].transcription
            == "SEGUNDA VERSION"
        )
    finally:
        _cleanup(db)


def test_crime_dialog_collapses_conditional_rows():
    dlg = CrimeDialog(None)
    assert dlg._drug_quantity.isHidden()
    assert dlg._weapon_quantity.isHidden()
    base_height = dlg.sizeHint().height()

    combo_set_data(dlg._type, "Droga")
    assert not dlg._drug_quantity.isHidden()
    assert dlg._weapon_quantity.isHidden()
    assert dlg.sizeHint().height() > base_height

    combo_set_data(dlg._type, "Armas")
    assert dlg._drug_quantity.isHidden()
    assert not dlg._weapon_quantity.isHidden()

    combo_set_data(dlg._type, "Ordinario")
    assert dlg._drug_quantity.isHidden()
    assert dlg._weapon_quantity.isHidden()
    assert dlg.sizeHint().height() == base_height


def test_defendant_dialog_input_validators():
    """El acusado usa los mismos validadores que victimas/testigos."""
    svc, db = _make_service()
    try:
        case_id = svc.create_case_file(
            CaseFileCreate(
                case_number="MP-DEF-VAL",
                prosecutor_name="Fiscal",

                origin_type="Local",
            )
        )
        dlg = DefendantDialog(None, _fake_app(svc), case_id)
        # Direccion: alfanumericos en mayusculas + espacio/guion/punto/comma.
        dlg._address.setText("av. 1-a, b@#")
        assert dlg._address.text() == "AV. 1-A, B"
        # Telefono: solo digitos y guion.
        dlg._phone.setText("0424-123.45x")
        assert dlg._phone.text() == "0424-12345"
    finally:
        _cleanup(db)


if __name__ == "__main__":
    test_defendant_dialog_save_calls_show_info()
    test_hearing_dialog_save_calls_show_info()
    print("DIALOGS SAVE TEST OK")
