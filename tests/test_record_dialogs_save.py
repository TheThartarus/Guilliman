"""Test de regresión para las rutas de guardado de los diálogos de documentales/expertos.

Ejercita ``DocumentaryDialog._on_save`` y ``ExpertDialog._on_save`` contra una
base de datos temporal con un ``CaseFileService`` real, parcheando
``ui.dialogs.show_info``/``show_error`` para capturar la llamada de éxito.

Espejo de ``test_person_dialogs_save.py`` para las dos entidades nuevas del
segundo handoff Backend → Frontend (documentales y expertos, con fechas
condicionadas por booleanos).
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import tempfile
from unittest import mock

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QApplication

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

APP = QApplication.instance() or QApplication([])

from db import CaseFileCreate, CaseFileService  # noqa: E402
from db.database import dispose_engine, reset_session_factory  # noqa: E402
from ui import dialogs  # noqa: E402
from ui.dialogs import DocumentaryDialog, ExpertDialog  # noqa: E402
from ui.dialogs import _record  # noqa: E402


def _make_service():
    db = os.path.join(tempfile.gettempdir(), "test_record_dialogs_save.db")
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


def test_documentary_dialog_save_calls_show_info():
    svc, db = _make_service()
    try:
        case_id = svc.create_case_file(
            CaseFileCreate(
                case_number="MP-DOC",
                prosecutor_name="Fiscal",

                origin_type="Local",
            )
        )
        dlg = DocumentaryDialog(None, _fake_app(svc), case_id)
        dlg._name.setText("Informe Pericial 123")
        # Marcar "en posesión" y fijar fecha de recepción.
        dlg._in_possession_card._switch.setChecked(True)
        dlg._in_possession_card._picker.setDate(QDate(2026, 3, 10))
        # "evacuado" queda apagado -> evacuation_date debe ser None.

        with mock.patch.object(_record, "show_info") as m_info, \
                mock.patch.object(_record, "show_error") as m_err:
            dlg._on_save()

        assert m_info.called, "show_info debió llamarse en guardado exitoso"
        assert not m_err.called, "show_error no debió llamarse en éxito"
        case = svc.get_case_file_by_id(case_id)
        assert any(d.name == "INFORME PERICIAL 123" for d in case.documentaries)
        doc = next(d for d in case.documentaries if d.name == "INFORME PERICIAL 123")
        assert doc.in_possession is True
        assert doc.possession_date is not None
        assert doc.evacuated is False
        assert doc.evacuation_date is None
    finally:
        _cleanup(db)


def test_expert_dialog_save_calls_show_info():
    svc, db = _make_service()
    try:
        case_id = svc.create_case_file(
            CaseFileCreate(
                case_number="MP-EXP",
                prosecutor_name="Fiscal",

                origin_type="Local",
            )
        )
        dlg = ExpertDialog(None, _fake_app(svc), case_id)
        dlg._name.setText("Carlos Gomez")
        dlg._appeared_card._switch.setChecked(True)
        dlg._appeared_card._picker.setDate(QDate(2026, 4, 1))

        with mock.patch.object(_record, "show_info") as m_info, \
                mock.patch.object(_record, "show_error") as m_err:
            dlg._on_save()

        assert m_info.called, "show_info debió llamarse en guardado exitoso"
        assert not m_err.called, "show_error no debió llamarse en éxito"
        case = svc.get_case_file_by_id(case_id)
        assert any(e.name == "CARLOS GOMEZ" for e in case.experts)
        expert = next(e for e in case.experts if e.name == "CARLOS GOMEZ")
        assert expert.appeared is True
        assert expert.appearance_date is not None
    finally:
        _cleanup(db)


def test_documentary_dialog_validation_error_empty_name():
    svc, db = _make_service()
    try:
        case_id = svc.create_case_file(
            CaseFileCreate(
                case_number="MP-DOC-VAL",
                prosecutor_name="Fiscal",

                origin_type="Local",
            )
        )
        dlg = DocumentaryDialog(None, _fake_app(svc), case_id)
        dlg._name.setText("")  # nombre vacío -> ValidationError

        with mock.patch.object(_record, "show_info") as m_info, \
                mock.patch.object(_record, "show_error") as m_err:
            dlg._on_save()

        assert m_err.called, "show_error debió llamarse con nombre vacío"
        assert not m_info.called, "show_info no debió llamarse con error de validación"
        case = svc.get_case_file_by_id(case_id)
        assert len(case.documentaries) == 0
    finally:
        _cleanup(db)


def test_record_dialog_additional_notes_round_trip():
    """El campo additional_notes se guarda y mayusculiza en documentales/expertos."""
    svc, db = _make_service()
    try:
        case_id = svc.create_case_file(
            CaseFileCreate(
                case_number="MP-DOC-NOTE",
                prosecutor_name="Fiscal",

                origin_type="Local",
            )
        )
        dlg = DocumentaryDialog(None, _fake_app(svc), case_id)
        dlg._name.setText("Doc Notas")
        dlg._notes.setPlainText("observacion del documental 123")
        with mock.patch.object(_record, "show_info") as m_info, \
                mock.patch.object(_record, "show_error") as m_err:
            dlg._on_save()
        assert m_info.called and not m_err.called
        case = svc.get_case_file_by_id(case_id)
        doc = next(d for d in case.documentaries if d.name == "DOC NOTAS")
        assert doc.additional_notes == "OBSERVACION DEL DOCUMENTAL 123"

        dlg_e = ExpertDialog(None, _fake_app(svc), case_id)
        dlg_e._name.setText("Exp Notas")
        dlg_e._notes.setPlainText("nota experto abc")
        with mock.patch.object(_record, "show_info") as m_info2, \
                mock.patch.object(_record, "show_error") as m_err2:
            dlg_e._on_save()
        case = svc.get_case_file_by_id(case_id)
        exp = next(e for e in case.experts if e.name == "EXP NOTAS")
        assert exp.additional_notes == "NOTA EXPERTO ABC"
    finally:
        _cleanup(db)


if __name__ == "__main__":
    test_documentary_dialog_save_calls_show_info()
    test_expert_dialog_save_calls_show_info()
    test_documentary_dialog_validation_error_empty_name()
    test_record_dialog_additional_notes_round_trip()
    print("RECORD DIALOGS SAVE TEST OK")
