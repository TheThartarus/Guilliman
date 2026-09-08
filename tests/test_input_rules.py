"""Prueba de las reglas de restriccion de entrada (validadores de caracteres).

Valida que ``ui.widgets.restrict_input`` limita los campos a alfanumericos mas
guion (tipo "code") o alfanumericos mas espacio (tipo "text"), y que convierte
a mayusculas automaticamente, tanto en QLineEdit como en QTextEdit.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QLineEdit, QTextEdit

from ui.widgets import restrict_input


def test_restrict_code_lineedit() -> None:
    app = QApplication.instance() or QApplication([])
    le = QLineEdit()
    restrict_input(le, "code")
    le.setText("mp-2024-001 abc@#$%^&*()")
    assert le.text() == "MP-2024-001ABC"
    le.setText("con espacio")
    assert le.text() == "CONESPACIO"  # el espacio no es valido en "code"


def test_restrict_text_lineedit() -> None:
    app = QApplication.instance() or QApplication([])
    le = QLineEdit()
    restrict_input(le, "text")
    le.setText("Fiscalía 1@#$%")
    assert le.text() == "FISCALÍA 1"  # acentos y espacios permitidos, mayusculas


def test_restrict_text_textedit() -> None:
    app = QApplication.instance() or QApplication([])
    te = QTextEdit()
    restrict_input(te, "text")
    te.setPlainText("Resumen de hechos 123@#$%")
    assert te.toPlainText() == "RESUMEN DE HECHOS 123"


def test_restrict_agency_lineedit() -> None:
    app = QApplication.instance() or QApplication([])
    le = QLineEdit()
    restrict_input(le, "agency")
    le.setText("Cicpc-region 4@#$%")
    assert le.text() == "CICPC-REGION 4"  # guion y espacio permitidos, mayusculas


if __name__ == "__main__":
    test_restrict_code_lineedit()
    test_restrict_text_lineedit()
    test_restrict_text_textedit()
    print("INPUT RULES OK")
