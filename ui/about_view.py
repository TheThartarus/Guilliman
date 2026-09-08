"""
Guilliman Frontend - Vista "Acerca de".

Muestra información institucional, versión, derechos de autor,
licencia y créditos del software.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QHBoxLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    HyperlinkButton,
    SubtitleLabel,
    TitleLabel,
)

from version import __build_date__, __copyright__, __email__, __license__, __version__

# ── Créditos / libs de terceros ────────────────────────────────────────
_THIRD_PARTY = [
    ("PyQt5", "https://riverbankcomputing.com/software/pyqt/"),
    ("QFluentWidgets", "https://github.com/zhiyiYo/PyQt-Fluent-Widgets"),
    ("SQLAlchemy", "https://www.sqlalchemy.org/"),
    ("ReportLab", "https://www.reportlab.com/"),
    ("Pydantic", "https://docs.pydantic.dev/"),
]


def _left_row(widget: QWidget) -> QHBoxLayout:
    """Envuelve *widget* en un ``QHBoxLayout`` alineado a la izquierda."""
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.addWidget(widget)
    row.addStretch(1)
    return row


class AboutView(QWidget):
    """Panel informativo del software Guilliman."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("about")

        # ── Layout raíz con scroll ─────────────────────────────────────
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.viewport().setAutoFillBackground(False)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        root_layout.addWidget(scroll)

        container = QWidget()
        container.setAutoFillBackground(False)
        container.setStyleSheet("QWidget { background: transparent; }")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)
        scroll.setWidget(container)

        # ── Título ─────────────────────────────────────────────────────
        layout.addWidget(TitleLabel("Guilliman"))
        layout.addWidget(SubtitleLabel("Sistema de Gestión de Expedientes Penales"))

        # ── Versión ────────────────────────────────────────────────────
        layout.addWidget(SubtitleLabel("Versión"))
        layout.addWidget(BodyLabel(f"Código: {__version__}"))
        layout.addWidget(BodyLabel(f"Fecha de compilación: {__build_date__}"))

        # ── Copyright ──────────────────────────────────────────────────
        layout.addWidget(SubtitleLabel("Derechos de autor"))
        layout.addWidget(BodyLabel(f"{__copyright__}. Todos los derechos reservados."))

        # ── Contacto ───────────────────────────────────────────────────
        layout.addWidget(SubtitleLabel("Contacto"))
        layout.addLayout(_left_row(HyperlinkButton(f"mailto:{__email__}", __email__)))

        # ── Licencia ───────────────────────────────────────────────────
        layout.addWidget(SubtitleLabel("Licencia de uso"))
        layout.addWidget(BodyLabel(f"Este software se distribuye bajo la licencia {__license__}."))
        layout.addLayout(_left_row(
            HyperlinkButton(
                "https://www.apache.org/licenses/LICENSE-2.0",
                "Ver licencia completa",
            )
        ))

        # ── Créditos ───────────────────────────────────────────────────
        layout.addWidget(SubtitleLabel("Créditos"))
        layout.addWidget(
            BodyLabel("Desarrollador principal: TheThartarus (David Canchica)")
        )
        layout.addWidget(
            BodyLabel("Colaborador: Galactus (Cristhofer Briceño)")
        )
        layout.addWidget(CaptionLabel("Librerías y herramientas de terceros:"))
        for name, url in _THIRD_PARTY:
            layout.addLayout(_left_row(HyperlinkButton(url, name)))

        # ── Espaciador final ───────────────────────────────────────────
        layout.addStretch(1)
