"""Test de regresión para las rutas de guardado de los diálogos de víctimas/testigos.

Ejercita ``VictimDialog._on_save`` y ``WitnessDialog._on_save`` contra una base
de datos temporal con un ``CaseFileService`` real, parcheando
``ui.dialogs.show_info``/``show_error`` para capturar la llamada de éxito.

Espejo de ``test_dialogs_save.py`` para las dos entidades nuevas del handoff
Backend → Frontend.
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

from db import CaseFileCreate, CaseFileService  # noqa: E402
from db.database import dispose_engine, reset_session_factory  # noqa: E402
from ui import dialogs  # noqa: E402
from ui.dialogs import VictimDialog, WitnessDialog  # noqa: E402
from ui.dialogs import _person  # noqa: E402


def _make_service():
    db = os.path.join(tempfile.gettempdir(), "test_person_dialogs_save.db")
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


def test_victim_dialog_save_calls_show_info():
    svc, db = _make_service()
    try:
        case_id = svc.create_case_file(
            CaseFileCreate(
                case_number="MP-VICTIM",
                prosecutor_name="Fiscal",

                origin_type="Local",
            )
        )
        dlg = VictimDialog(None, _fake_app(svc), case_id)
        dlg._full_name.setText("Ana Pérez")
        dlg._national_id.setText("123")
        dlg._address.setText("Calle Falsa 123")
        dlg._phone.setText("0414-1234567")

        with mock.patch.object(_person, "show_info") as m_info, \
                mock.patch.object(_person, "show_error") as m_err:
            dlg._on_save()

        assert m_info.called, "show_info debió llamarse en guardado exitoso"
        assert not m_err.called, "show_error no debió llamarse en éxito"
        case = svc.get_case_file_by_id(case_id)
        assert any(v.full_name == "ANA PÉREZ" for v in case.victims)
        victim = next(v for v in case.victims if v.full_name == "ANA PÉREZ")
        # phone NO debe estar en mayúsculas; address SÍ.
        assert victim.address == "CALLE FALSA 123"
        assert victim.phone == "0414-1234567"
    finally:
        _cleanup(db)


def test_witness_dialog_save_calls_show_info():
    svc, db = _make_service()
    try:
        case_id = svc.create_case_file(
            CaseFileCreate(
                case_number="MP-WITNESS",
                prosecutor_name="Fiscal",

                origin_type="Local",
            )
        )
        dlg = WitnessDialog(None, _fake_app(svc), case_id)
        dlg._full_name.setText("Carlos Gomez")
        dlg._phone.setText("0212-9998888")

        with mock.patch.object(_person, "show_info") as m_info, \
                mock.patch.object(_person, "show_error") as m_err:
            dlg._on_save()

        assert m_info.called, "show_info debió llamarse en guardado exitoso"
        assert not m_err.called, "show_error no debió llamarse en éxito"
        case = svc.get_case_file_by_id(case_id)
        assert any(w.full_name == "CARLOS GOMEZ" for w in case.witnesses)
    finally:
        _cleanup(db)


def test_person_dialog_input_validators():
    """Los validadores de direccion/telefono en victimas y testigos."""
    svc, db = _make_service()
    try:
        case_id = svc.create_case_file(
            CaseFileCreate(
                case_number="MP-VICTIM-VAL",
                prosecutor_name="Fiscal",

                origin_type="Local",
            )
        )
        dlg = VictimDialog(None, _fake_app(svc), case_id)
        # Direccion: mayusculas, conserva alfanumericos/espacio/guion/punto/comma,
        # borra lo demas (@ y # desaparecen; el espacio y la coma se conservan).
        dlg._address.setText("av. 1-a, b@#")
        assert dlg._address.text() == "AV. 1-A, B"
        # Telefono: solo digitos y guion.
        dlg._phone.setText("0424-123.45x")
        assert dlg._phone.text() == "0424-12345"
    finally:
        _cleanup(db)


def test_victim_dialog_validation_error_shows_error():
    svc, db = _make_service()
    try:
        case_id = svc.create_case_file(
            CaseFileCreate(
                case_number="MP-VICTIM-VAL",
                prosecutor_name="Fiscal",

                origin_type="Local",
            )
        )
        dlg = VictimDialog(None, _fake_app(svc), case_id)
        # Nombre vacío -> ValidationError (full_name requerido).
        dlg._full_name.setText("")

        with mock.patch.object(_person, "show_info") as m_info, \
                mock.patch.object(_person, "show_error") as m_err:
            dlg._on_save()

        assert m_err.called, "show_error debió llamarse con nombre vacío"
        assert not m_info.called, "show_info no debió llamarse con error de validación"
        case = svc.get_case_file_by_id(case_id)
        assert len(case.victims) == 0
    finally:
        _cleanup(db)


if __name__ == "__main__":
    test_victim_dialog_save_calls_show_info()
    test_witness_dialog_save_calls_show_info()
    test_victim_dialog_validation_error_shows_error()
    print("PERSON DIALOGS SAVE TEST OK")
