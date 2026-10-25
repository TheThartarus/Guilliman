"""
Guilliman Frontend - Formulario de creación/edición de expedientes (PyQt5).

Reutiliza ``db.service.CaseFileService``. En modo edición precarga los
datos y aplica actualización parcial (PATCH) con ``CaseFileUpdate``; en modo
creación construye ``CaseFileCreate``.
"""

from __future__ import annotations

import logging

from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QScrollArea,
    QSpinBox,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtCore import Qt

from qfluentwidgets import (
    ComboBox,
    FluentIcon,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    SettingCard,
    SettingCardGroup,
    SubtitleLabel,
    SwitchButton,
    TableWidget,
    TextEdit,
)

from db import (
    CaseFileCreate,
    CaseFileRead,
    CaseFileUpdate,
    CrimeCreate,
    DuplicateCaseNumberError,
)
from pydantic import ValidationError

from ui.dialogs import CrimeDialog
from ui.dialogs._cards import _DateCard
from ui.shared import (
    CRIME_TYPE_LABELS,
    DRUG_TYPE_LABELS,
    ORIGIN_TYPE_LABELS,
    WEAPON_TYPE_LABELS,
    field_errors,
)
from ui.settings import load_theme_mode
from ui.widgets import (
    combo_current_data,
    combo_set_data,
    restrict_input,
    show_error,
    show_info,
)

_DARK_SPINBOX_SS = (
    "QSpinBox, QDoubleSpinBox {"
    "  background: #2d2d2d; color: #dedede; border: 1px solid #3d3d3d;"
    "  border-radius: 4px; padding: 4px 8px; min-height: 24px;"
    "}"
    "QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid #0078d4; }"
    "QSpinBox::up-button, QDoubleSpinBox::up-button,"
    "QSpinBox::down-button, QDoubleSpinBox::down-button {"
    "  background: #3d3d3d; border: none; width: 16px;"
    "}"
    "QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,"
    "QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {"
    "  background: #505050;"
    "}"
    "QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {"
    "  image: none; border-left: 4px solid transparent;"
    "  border-right: 4px solid transparent; border-bottom: 5px solid #dedede;"
    "  width: 0; height: 0;"
    "}"
    "QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {"
    "  image: none; border-left: 4px solid transparent;"
    "  border-right: 4px solid transparent; border-top: 5px solid #dedede;"
    "  width: 0; height: 0;"
    "}"
)

_LIGHT_SPINBOX_SS = (
    "QSpinBox, QDoubleSpinBox {"
    "  background: #ffffff; color: #1a1a1a; border: 1px solid #e0e0e0;"
    "  border-radius: 4px; padding: 4px 8px; min-height: 24px;"
    "}"
    "QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid #0078d4; }"
    "QSpinBox::up-button, QDoubleSpinBox::up-button,"
    "QSpinBox::down-button, QDoubleSpinBox::down-button {"
    "  background: #f0f0f0; border: none; width: 16px;"
    "}"
    "QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,"
    "QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {"
    "  background: #e0e0e0;"
    "}"
    "QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {"
    "  image: none; border-left: 4px solid transparent;"
    "  border-right: 4px solid transparent; border-bottom: 5px solid #1a1a1a;"
    "  width: 0; height: 0;"
    "}"
    "QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {"
    "  image: none; border-left: 4px solid transparent;"
    "  border-right: 4px solid transparent; border-top: 5px solid #1a1a1a;"
    "  width: 0; height: 0;"
    "}"
)

logger = logging.getLogger("guilliman")

class _LineEditCard(SettingCard):
    """Campo de texto libre presentado como tarjeta Fluent (estilo coherente con _DateCard)."""

    def __init__(self, title: str, kind: str = "text",
                 parent: QWidget | None = None) -> None:
        super().__init__(FluentIcon.EDIT, title, parent=parent)
        self.titleLabel.setMinimumWidth(200)
        self._edit = LineEdit(self)
        self._edit.setPlaceholderText(title)
        # El LineEdit ocupa el ancho disponible a la derecha del título:
        # se elimina el addStretch(1) final de SettingCard y se inserta el edit.
        self.hBoxLayout.takeAt(self.hBoxLayout.count() - 1)
        self.hBoxLayout.addWidget(self._edit, 1)
        self.hBoxLayout.addSpacing(16)
        restrict_input(self._edit, kind)


class _SwitchCard(SettingCard):
    """Campo booleano presentado como tarjeta Fluent con SwitchButton."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(FluentIcon.INFO, title, parent=parent)
        self.titleLabel.setMinimumWidth(200)
        self._switch = SwitchButton()
        self._switch.setChecked(False)
        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self._switch)
        self.hBoxLayout.addSpacing(16)

    @property
    def check(self) -> SwitchButton:
        return self._switch

    def get(self) -> bool:
        return self._switch.isChecked()

    def set(self, value: bool) -> None:
        self._switch.setChecked(bool(value))


class _SpinBoxCard(SettingCard):
    """Campo numérico entero presentado como tarjeta Fluent."""

    def __init__(self, title: str, suffix: str = "", parent: QWidget | None = None) -> None:
        super().__init__(FluentIcon.INFO, title, parent=parent)
        self.titleLabel.setMinimumWidth(200)
        self._spin = QSpinBox()
        self._spin.setRange(0, 99999)
        self._spin.setSpecialValueText("—")
        if suffix:
            self._spin.setSuffix(suffix)
        self.hBoxLayout.takeAt(self.hBoxLayout.count() - 1)
        self.hBoxLayout.addWidget(self._spin, 1)
        self.hBoxLayout.addSpacing(16)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        ss = _DARK_SPINBOX_SS if load_theme_mode() == "DARK" else _LIGHT_SPINBOX_SS
        self._spin.setStyleSheet(ss)

    def value(self) -> int:
        return self._spin.value()

    def setValue(self, val: int) -> None:
        self._spin.setValue(val)


class _ComboBoxCard(SettingCard):
    """ComboBox presentado como tarjeta Fluent."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(FluentIcon.INFO, title, parent=parent)
        self.titleLabel.setMinimumWidth(200)
        self._combo = ComboBox()
        self.hBoxLayout.takeAt(self.hBoxLayout.count() - 1)
        self.hBoxLayout.addWidget(self._combo, 1)
        self.hBoxLayout.addSpacing(16)

    @property
    def combo(self) -> ComboBox:
        return self._combo


class CaseFormView(QWidget):
    """Formulario completo de un expediente (crear o editar)."""

    def __init__(self, app, case_file_id: int | None = None, on_saved=None, on_cancel=None) -> None:
        super().__init__()
        self.app = app
        self.case_file_id = case_file_id
        self.on_saved = on_saved
        self.on_cancel = on_cancel
        self._current_case: CaseFileRead | None = None

        self._build_fields()
        if case_file_id is not None:
            self._load_existing(case_file_id)

        self._build_layout()

    # ------------------------------------------------------------------ #
    # Campos
    # ------------------------------------------------------------------ #
    def _build_fields(self) -> None:
        self._fields: dict = {}

        self._case_number_card = _LineEditCard("Número de Expediente *", "code", parent=self)
        self._case_number = self._case_number_card._edit
        self._fields["case_number"] = self._case_number_card

        self._prosecutor_number_card = _LineEditCard("MP", "code", parent=self)
        self._prosecutor_number = self._prosecutor_number_card._edit
        self._fields["prosecutor_file_number"] = self._prosecutor_number_card

        self._prosecutor_name_card = _LineEditCard("Fiscal", parent=self)
        self._prosecutor_name = self._prosecutor_name_card._edit
        self._fields["prosecutor_name"] = self._prosecutor_name_card

        self._defense_attorney_card = _LineEditCard("Defensor", parent=self)
        self._defense_attorney = self._defense_attorney_card._edit
        self._fields["defense_attorney"] = self._defense_attorney_card

        self._origin_type_card = _ComboBoxCard("Tipo de Origen", parent=self)
        self._origin_type = self._origin_type_card.combo
        for value, label in ORIGIN_TYPE_LABELS.items():
            self._origin_type.addItem(label, userData=value)
        self._fields["origin_type"] = self._origin_type_card

        self._origin_location_card = _LineEditCard("Procedencia", "address", parent=self)
        self._origin_location = self._origin_location_card._edit
        self._fields["origin_location"] = self._origin_location_card

        self._current_hearing_type_card = _LineEditCard("Audiencia Actual", parent=self)
        self._current_hearing_type = self._current_hearing_type_card._edit
        self._fields["current_hearing_type"] = self._current_hearing_type

        # Fechas del expediente, en el orden procesal requerido.
        self._control_entry_date = _DateCard("Entrada a Control", parent=self)
        self._fields["control_entry_date"] = self._control_entry_date
        self._indictment_date = _DateCard("Escrito Acusatorio", parent=self)
        self._fields["indictment_date"] = self._indictment_date
        self._preliminary_hearing_date = _DateCard("Audiencia Preliminar", parent=self)
        self._fields["preliminary_hearing_date"] = self._preliminary_hearing_date
        self._anticipated_proof_date = _DateCard("Prueba Anticipada", parent=self)
        self._fields["anticipated_proof_date"] = self._anticipated_proof_date
        self._trial_opening_date = _DateCard("Apertura a Juicio", parent=self)
        self._fields["trial_opening_date"] = self._trial_opening_date
        self._trial_transfer_date = _DateCard("Pase a Juicio", parent=self)
        self._fields["trial_transfer_date"] = self._trial_transfer_date
        self._control_exit_date = _DateCard("Salida de Control", parent=self)
        self._fields["control_exit_date"] = self._control_exit_date
        self._trial_entry_date = _DateCard("Ingreso a Juicio", parent=self)
        self._fields["trial_entry_date"] = self._trial_entry_date

        self._offense_description = TextEdit()
        self._offense_description.setPlaceholderText("Descripción del delito")
        restrict_input(self._offense_description, "text_ext")
        self._fields["offense_description"] = self._offense_description

        self._facts_summary = TextEdit()
        self._facts_summary.setPlaceholderText("Resumen de hechos")
        restrict_input(self._facts_summary, "text_ext")
        self._fields["facts_summary"] = self._facts_summary

        # -- Campos adicionales de clasificación --
        self._is_emblematic_card = _SwitchCard("Emblemático", parent=self)
        self._is_emblematic = self._is_emblematic_card
        self._fields["is_emblematic"] = self._is_emblematic_card

        self._piece_count_card = _SpinBoxCard("N° de Piezas", " piezas", parent=self)
        self._piece_count = self._piece_count_card
        self._fields["piece_count"] = self._piece_count_card

        self._pseudonym_card = _LineEditCard("Seudónimo del caso", parent=self)
        self._pseudonym = self._pseudonym_card._edit
        self._fields["pseudonym"] = self._pseudonym_card

        # -- Delitos imputados (lista dinámica; se edita con CrimeDialog) --
        self._crimes: list[CrimeCreate] = []
        self._crimes_table = TableWidget()
        self._crimes_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._crimes_table.setColumnCount(2)
        self._crimes_table.setHorizontalHeaderLabels(["Tipo", "Detalle"])
        self._crimes_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._crimes_table.setMinimumHeight(120)
        self._crimes_table.cellDoubleClicked.connect(lambda *_: self._on_edit_crime())

        self._crimes_buttons = QWidget()
        crimes_row = QHBoxLayout(self._crimes_buttons)
        crimes_row.setContentsMargins(0, 0, 0, 0)
        self.add_crime_btn = PushButton("Agregar delito")
        self.add_crime_btn.clicked.connect(self._on_add_crime)
        self.edit_crime_btn = PushButton("Editar delito")
        self.edit_crime_btn.clicked.connect(self._on_edit_crime)
        self.del_crime_btn = PushButton("Eliminar delito")
        self.del_crime_btn.clicked.connect(self._on_del_crime)
        crimes_row.addWidget(self.add_crime_btn)
        crimes_row.addWidget(self.edit_crime_btn)
        crimes_row.addWidget(self.del_crime_btn)
        crimes_row.addStretch(1)

        self._location_card = _LineEditCard("Ubicación", "address", parent=self)
        self._location = self._location_card._edit
        self._fields["location"] = self._location_card

    def _build_layout(self) -> None:
        # Contenido scrollable: evita que la ventana fuerce un tamaño mínimo
        # mayor que la pantalla (el formulario es alto en pantallas de 720p).
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent}")
        content = QWidget()
        content.setAttribute(Qt.WA_StyledBackground, True)
        content.setStyleSheet("background:transparent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)
        layout.addWidget(SubtitleLabel("Editar expediente" if self.case_file_id else "Nuevo expediente"))

        actions = QHBoxLayout()
        self.save_btn = PrimaryPushButton("Guardar")
        self.save_btn.clicked.connect(self._on_save)
        self.cancel_btn = PushButton("Cancelar")
        self.cancel_btn.clicked.connect(self._on_cancel)
        actions.addWidget(self.save_btn)
        actions.addWidget(self.cancel_btn)
        layout.addLayout(actions)

        layout.addWidget(self._section("Identificación", [
            self._case_number_card,
            self._prosecutor_number_card,
            self._prosecutor_name_card,
            self._defense_attorney_card,
            self._origin_type_card,
            self._origin_location_card,
        ]))
        layout.addWidget(self._section("Estado", [
            self._current_hearing_type_card,
        ]))
        layout.addWidget(self._section("Fechas", [
            self._control_entry_date,
            self._indictment_date,
            self._preliminary_hearing_date,
            self._anticipated_proof_date,
            self._trial_opening_date,
            self._trial_transfer_date,
            self._control_exit_date,
            self._trial_entry_date,
        ]))
        layout.addWidget(self._section("Descripción", [
            self._offense_description,
        ]))
        layout.addWidget(self._section("Resumen", [
            self._facts_summary,
        ]))
        layout.addWidget(self._section("Delitos", [
            self._crimes_buttons,
            self._crimes_table,
        ]))
        layout.addWidget(self._section("Otros", [
            self._is_emblematic_card,
            self._pseudonym_card,
            self._piece_count,
            self._location_card,
        ]))
        layout.addStretch(1)

        scroll.setWidget(content)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def _section(self, title: str, widgets: list) -> SettingCardGroup:
        """Sección agrupada con SettingCardGroup (estilo Fluent Widgets).

        Cada ``widget`` es un ``QHBoxLayout`` (par de campos) o un ``QWidget``
        (campo individual); se envuelve en un contenedor y se añade al grupo.
        """
        group = SettingCardGroup(title)
        for w in widgets:
            if isinstance(w, QHBoxLayout):
                holder = QWidget()
                holder.setLayout(w)
                group.vBoxLayout.addWidget(holder)
            else:
                group.vBoxLayout.addWidget(w)
        return group


    def _fill_crimes_table(self) -> None:
        self._crimes_table.setRowCount(len(self._crimes))
        for row, crime in enumerate(self._crimes):
            self._crimes_table.setItem(
                row, 0, QTableWidgetItem(CRIME_TYPE_LABELS.get(crime.crime_type, crime.crime_type))
            )
            self._crimes_table.setItem(
                row, 1, QTableWidgetItem(self._crime_detail(crime))
            )

    @staticmethod
    def _crime_detail(crime: CrimeCreate) -> str:
        parts: list[str] = []
        if crime.drug_quantity is not None or crime.drug_type:
            detail = DRUG_TYPE_LABELS.get(crime.drug_type, crime.drug_type) if crime.drug_type else "Droga"
            if crime.drug_quantity is not None:
                detail += f" — {crime.drug_quantity:g} g"
            parts.append(detail)
        if crime.weapon_quantity is not None or crime.weapon_type:
            detail = WEAPON_TYPE_LABELS.get(crime.weapon_type, crime.weapon_type) if crime.weapon_type else "Arma"
            if crime.weapon_quantity is not None:
                detail += f" — {crime.weapon_quantity} armas"
            parts.append(detail)
        return " | ".join(parts) if parts else "—"

    def _selected_crime_index(self) -> int | None:
        row = self._crimes_table.currentRow()
        return row if 0 <= row < len(self._crimes) else None

    def _on_add_crime(self) -> None:
        dialog = CrimeDialog(self)
        if dialog.exec() and dialog.result_crime is not None:
            self._crimes.append(dialog.result_crime)
            self._fill_crimes_table()

    def _on_edit_crime(self) -> None:
        index = self._selected_crime_index()
        if index is None:
            show_error(self, "Seleccione un delito de la tabla.")
            return
        dialog = CrimeDialog(self, self._crimes[index])
        if dialog.exec() and dialog.result_crime is not None:
            self._crimes[index] = dialog.result_crime
            self._fill_crimes_table()

    def _on_del_crime(self) -> None:
        index = self._selected_crime_index()
        if index is None:
            show_error(self, "Seleccione un delito de la tabla.")
            return
        del self._crimes[index]
        self._fill_crimes_table()

    # ------------------------------------------------------------------ #
    # Carga en edición
    # ------------------------------------------------------------------ #
    def _load_existing(self, case_file_id: int) -> None:
        try:
            case = self.app.service.get_case_file_by_id(case_file_id)
        except ValueError as exc:
            logger.exception("Error al cargar expediente %s", case_file_id)
            show_error(self, f"Error al cargar: {exc}")
            return
        if case is None:
            show_error(self, f"El expediente {case_file_id} no existe.")
            return

        self._current_case = case
        self._case_number.setText(case.case_number or "")
        self._prosecutor_number.setText(case.prosecutor_file_number or "")
        self._prosecutor_name.setText(case.prosecutor_name or "")
        self._defense_attorney.setText(case.defense_attorney or "")
        self._current_hearing_type.setText(case.current_hearing_type or "")
        if case.origin_type:
            combo_set_data(self._origin_type, case.origin_type)
        self._origin_location.setText(case.origin_location or "")
        self._control_entry_date.set(case.control_entry_date)
        self._indictment_date.set(case.indictment_date)
        self._preliminary_hearing_date.set(case.preliminary_hearing_date)
        self._anticipated_proof_date.set(case.anticipated_proof_date)
        self._trial_opening_date.set(case.trial_opening_date)
        self._trial_transfer_date.set(case.trial_transfer_date)
        self._control_exit_date.set(case.control_exit_date)
        self._trial_entry_date.set(case.trial_entry_date)
        self._offense_description.setPlainText(case.offense_description or "")
        self._facts_summary.setPlainText(case.facts_summary or "")
        self._is_emblematic.set(case.is_emblematic)
        self._pseudonym.setText(case.pseudonym or "")
        self._piece_count.setValue(case.piece_count or 0)
        self._crimes = [
            CrimeCreate(
                crime_type=crime.crime_type,
                drug_quantity=crime.drug_quantity,
                drug_type=crime.drug_type,
                weapon_quantity=crime.weapon_quantity,
                weapon_type=crime.weapon_type,
            )
            for crime in case.crimes
        ]
        self._fill_crimes_table()
        self._location.setText(case.location or "")

    def reset(self) -> None:
        """Limpia todos los campos para un alta nueva (vista persistente)."""
        self.case_file_id = None
        self._current_case = None
        self._case_number.clear()
        self._prosecutor_number.clear()
        self._prosecutor_name.clear()
        self._defense_attorney.clear()
        self._current_hearing_type.clear()
        self._origin_type.setCurrentIndex(0)
        self._origin_location.clear()
        for key in (
            "control_entry_date", "indictment_date", "preliminary_hearing_date",
            "anticipated_proof_date", "trial_opening_date", "trial_transfer_date",
            "control_exit_date", "trial_entry_date",
        ):
            self._fields[key].set(None)
        self._offense_description.clear()
        self._facts_summary.clear()
        self._is_emblematic.set(False)
        self._pseudonym.clear()
        self._piece_count.setValue(0)
        self._crimes = []
        self._fill_crimes_table()
        self._location.clear()

    # ------------------------------------------------------------------ #
    # Guardado
    # ------------------------------------------------------------------ #
    @staticmethod
    def _clean(value: str) -> str | None:
        value = (value or "").strip().upper()
        return value if value else None

    def _collect_kwargs(self) -> dict:
        piece_count = self._piece_count.value()

        return {
            "case_number": (self._case_number.text() or "").strip().upper(),
            "prosecutor_file_number": self._clean(self._prosecutor_number.text()),
            "prosecutor_name": self._clean(self._prosecutor_name.text()),
            "defense_attorney": self._clean(self._defense_attorney.text()),
            "origin_type": combo_current_data(self._origin_type),
            "origin_location": self._clean(self._origin_location.text()),
            "current_hearing_type": self._clean(self._current_hearing_type.text()),
            "offense_description": self._clean(self._offense_description.toPlainText()),
            "facts_summary": self._clean(self._facts_summary.toPlainText()),
            "control_entry_date": self._control_entry_date.get(),
            "indictment_date": self._indictment_date.get(),
            "preliminary_hearing_date": self._preliminary_hearing_date.get(),
            "anticipated_proof_date": self._anticipated_proof_date.get(),
            "trial_transfer_date": self._trial_transfer_date.get(),
            "control_exit_date": self._control_exit_date.get(),
            "trial_entry_date": self._trial_entry_date.get(),
            "trial_opening_date": self._trial_opening_date.get(),
            "location": self._clean(self._location.text()),
            "is_emblematic": self._is_emblematic.get(),
            "pseudonym": self._clean(self._pseudonym.text()),
            "piece_count": piece_count if piece_count > 0 else None,
        }

    def _mark_errors(self, errors: dict[str, str]) -> None:
        for key, message in errors.items():
            field = self._fields.get(key)
            if field is None:
                continue
            if hasattr(field, "setError"):
                field.setError(message)
            elif hasattr(field, "setToolTip"):
                field.setToolTip(message)

    def _on_save(self) -> None:
        kwargs = self._collect_kwargs()
        try:
            if self.case_file_id is None:
                new_id = self.app.service.create_case_file(
                    CaseFileCreate(**kwargs), crimes_list=self._crimes
                )
                show_info(self, f"Expediente creado (ID {new_id}).")
                saved_id = new_id
            else:
                updated = self.app.service.update_case_file(
                    self.case_file_id, CaseFileUpdate(**kwargs)
                )
                if not updated:
                    show_error(self, "El expediente no existe o fue eliminado.")
                    return
                if not self.app.service.set_case_crimes(
                    self.case_file_id, self._crimes
                ):
                    show_error(self, "No se pudieron guardar los delitos.")
                    return
                show_info(self, "Expediente actualizado.")
                saved_id = self.case_file_id
        except ValidationError as exc:
            logger.exception("Error de validación al guardar expediente")
            self._mark_errors(field_errors(exc))
            show_error(self, "Revise los campos marcados.")
            return
        except DuplicateCaseNumberError:
            logger.info("Número de expediente duplicado: %s", kwargs.get("case_number"))
            self._case_number.setError("Ya existe un expediente con ese Número de Expediente.")
            show_error(self, "Ya existe un expediente con ese Número de Expediente.")
            return
        except ValueError as exc:
            logger.exception("Error al guardar expediente")
            show_error(self, f"Error al guardar: {exc}")
            return

        if self.on_saved:
            self.on_saved(f"edit-{self.case_file_id}")
        else:
            self.reset()
            self.app.shell.search_view.refresh()
            self.app.shell.switchTo(self.app.shell.search_view)

    def _on_cancel(self) -> None:
        if self.on_cancel:
            self.on_cancel(f"edit-{self.case_file_id}")
        else:
            self.reset()
            self.app.shell.search_view.refresh()
            self.app.shell.switchTo(self.app.shell.search_view)
