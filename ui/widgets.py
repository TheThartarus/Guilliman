"""
Guilliman Frontend - Helpers de UI que dependen de PyQt5 / qfluentwidgets.

Funciones de presentación (snackbars, conversión a mayúsculas, manejo de
ComboBoxes y restricción de caracteres) que requieren ``PyQt5`` o
``qfluentwidgets`` en tiempo de ejecución.  Se separan de ``ui.shared``
(que es puro y no depende de ningún toolkit) para mantener la capa de
presentación desacoplada y facilitar pruebas.
"""

from __future__ import annotations


# --------------------------------------------------------------------------- #
# Snackbars (InfoBar de qfluentwidgets)
# --------------------------------------------------------------------------- #
try:  # pragma: no cover - qfluentwidgets se instala en el frontend
    from qfluentwidgets import InfoBar, InfoBarPosition
except Exception:  # noqa: BLE001 - el frontend nativo puede no estar presente
    InfoBar = None
    InfoBarPosition = None


def show_info(parent, message: str, title: str = "Guilliman") -> None:
    """Muestra un mensaje de éxito (InfoBar de qfluentwidgets)."""
    if InfoBar is not None and parent is not None:
        InfoBar.success(
            title=title, content=message, parent=parent, position=InfoBarPosition.TOP
        )
    else:
        print(f"[INFO] {message}")


def show_error(parent, message: str, title: str = "Error") -> None:
    """Muestra un mensaje de error (InfoBar de qfluentwidgets)."""
    if InfoBar is not None and parent is not None:
        InfoBar.error(
            title=title, content=message, parent=parent, position=InfoBarPosition.TOP
        )
    else:
        print(f"[ERROR] {message}")


# --------------------------------------------------------------------------- #
# Conversión a mayúsculas
# --------------------------------------------------------------------------- #
def make_uppercase(widget) -> None:
    """Fuerza mayúsculas en un campo de texto preservando la posición del cursor.

    Soporta ``QLineEdit`` y ``QTextEdit`` (detección por duck typing). Todos los
    campos de texto del formulario se normalizan a MAYÚSCULAS, igual que en la
    versión anterior de la app.
    """
    if widget is None:
        return

    def _on_text_changed() -> None:
        if hasattr(widget, "toPlainText"):
            text = widget.toPlainText()
            upper = text.upper()
            if upper != text:
                pos = widget.textCursor().position()
                widget.blockSignals(True)
                widget.setPlainText(upper)
                widget.blockSignals(False)
                cursor = widget.textCursor()
                cursor.setPosition(min(pos, len(upper)))
                widget.setTextCursor(cursor)
        else:
            text = widget.text()
            upper = text.upper()
            if upper != text:
                pos = widget.cursorPosition()
                widget.setText(upper)
                widget.setCursorPosition(pos)

    widget.textChanged.connect(_on_text_changed)


# --------------------------------------------------------------------------- #
# Helpers de ComboBox (QComboBox)
# --------------------------------------------------------------------------- #
def combo_set_data(combo, value) -> None:
    """Selecciona en un ``QComboBox`` el ítem cuyo ``userData`` coincide."""
    if combo is None:
        return
    idx = combo.findData(value)
    if idx >= 0:
        combo.setCurrentIndex(idx)


def combo_current_data(combo):
    """Devuelve el ``userData`` del ítem seleccionado (None si no hay)."""
    if combo is None:
        return None
    val = combo.currentData
    if callable(val):  # PyQt5 lo expone como propiedad; por si acaso
        val = val()
    return val


# --------------------------------------------------------------------------- #
# Restriccion de caracteres de entrada
# --------------------------------------------------------------------------- #
def _allowed_char(ch: str, kind: str) -> bool:
    """True si ``ch`` es valido para el tipo de campo.

    - "code":    alfanumerico + guion (-).  Ej.: N Expediente, MP.
    - "agency":  alfanumerico + espacio + guion (-).  Ej.: Organismo Aprehensor.
    - "text":    alfanumerico + espacio.    Ej.: nombres, descripciones.
    - "text_ext": alfanumerico + espacio + punto (.) + coma (,).
              Ej.: descripciones y resumenes con puntuacion.
    - "letters": solo letras (+ espacio).   Ej.: nombre del acusado.
    - "digits":  solo digitos.              Ej.: cedula.
    - "address": alfanumericos (letras en mayusculas) + espacio + guion (-)
              + punto (.) + coma (,).  Ej.: direccion de victimas/testigos.
    - "phone":   digitos + guion (-).       Ej.: telefono de victimas/testigos.
    """
    if kind == "code":
        return ch.isalnum() or ch == "-"
    if kind == "agency":
        return ch.isalnum() or ch == " " or ch == "-"
    if kind == "letters":
        return ch.isalpha() or ch == " "
    if kind == "digits":
        return ch.isdigit()
    if kind == "text_ext":
        return ch.isalnum() or ch in (" ", ".", ",")
    if kind == "address":
        return ch.isalnum() or ch in (" ", "-", ".", ",")
    if kind == "phone":
        return ch.isdigit() or ch == "-"
    return ch.isalnum() or ch == " "


def _widget_get_text(widget) -> str:
    if hasattr(widget, "toPlainText"):
        return widget.toPlainText()
    return widget.text()


def _widget_set_text(widget, text: str, pos: int) -> None:
    if hasattr(widget, "toPlainText"):
        widget.blockSignals(True)
        widget.setPlainText(text)
        widget.blockSignals(False)
        cursor = widget.textCursor()
        cursor.setPosition(min(pos, len(text)))
        widget.setTextCursor(cursor)
    else:
        widget.blockSignals(True)
        widget.setText(text)
        widget.blockSignals(False)
        widget.setCursorPosition(min(pos, len(text)))


def restrict_input(widget, kind: str = "text", uppercase: bool = True) -> None:
    """Restringe un campo de texto a alfanumericos (+ guion/espacio segun
    ``kind``) y, opcionalmente, convierte a mayusculas automaticamente.

    Funciona con ``QLineEdit`` y ``QTextEdit`` (deteccion por duck typing, sin
    importar PyQt directamente). Filtra tanto la escritura como el pegado.
    """
    if widget is None:
        return

    def _sanitize() -> None:
        text = _widget_get_text(widget)
        out = "".join(c for c in text if _allowed_char(c, kind))
        if uppercase:
            out = out.upper()
        if out != text:
            pos = 0
            if hasattr(widget, "toPlainText"):
                pos = widget.textCursor().position()
            else:
                pos = widget.cursorPosition()
            _widget_set_text(widget, out, pos)

    if hasattr(widget, "textChanged"):
        widget.textChanged.connect(_sanitize)
