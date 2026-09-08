"""Confirmaciones nativas y selección de ruta de PDF (QMessageBox / QFileDialog)."""

from PyQt5.QtWidgets import QFileDialog, QMessageBox


def confirm_delete(parent, message: str) -> bool:
    """Muestra un diálogo de confirmación; True si el usuario acepta."""
    reply = QMessageBox.question(
        parent,
        "Confirmar",
        message,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    return reply == QMessageBox.Yes


def pick_save_pdf(parent, default_name: str) -> str | None:
    """Abre el diálogo nativo de guardado y devuelve la ruta (con .pdf)."""
    path, _ = QFileDialog.getSaveFileName(
        parent, "Guardar PDF", default_name, "PDF (*.pdf)"
    )
    if not path:
        return None
    if not path.lower().endswith(".pdf"):
        path += ".pdf"
    return path
