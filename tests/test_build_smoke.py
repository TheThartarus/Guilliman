"""Smoke test de empaquetado: verifica imports sin arrancar la UI.

Confirma que no hay errores de import circulares ni faltantes en el
entorno (los mismos que PyInstaller congelará). NO invoca la app
ni construye controles de PyQt.
"""

from __future__ import annotations

import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports_ok() -> None:
    """Importa los módulos clave del entrypoint, exportador y db."""
    # Entrypoint (no ejecuta ft.run: está tras `if __name__ == "__main__"`).
    main = importlib.import_module("main")
    assert hasattr(main, "main")

    # Exportador de PDF (reportlab).
    exporters = importlib.import_module("ui.exporters")
    assert hasattr(exporters, "export_case_pdf")
    assert hasattr(exporters, "export_agenda_pdf")

    # Backend (sqlalchemy + pydantic).
    db = importlib.import_module("db.database")
    assert hasattr(db, "get_app_data_dir")
    service_mod = importlib.import_module("db.service")
    assert hasattr(service_mod, "CaseFileService")

    schemas = importlib.import_module("db.schemas")
    assert hasattr(schemas, "CaseFileRead")


if __name__ == "__main__":
    test_imports_ok()
    print("BUILD SMOKE TEST OK")
