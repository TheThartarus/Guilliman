"""
Guilliman Backend - Esquemas de datos (DTOs).

Modelos Pydantic usados como frontera limpia y validada entre la capa de
servicio del db y el frontend PyQt. El frontend solo maneja estos DTOs;
nunca objetos ORM crudos.

Convención de nombres: los esquemas ``*Create`` validan las cargas de
entrada; los esquemas simples representan modelos de lectura/salida.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# Vocabulario de dominio definido por el negocio para el estado del acusado.
# Los valores legacy ("Detained", "Custody", "Conditional release") se
# traducen automáticamente en la migración 1 (ver migrations.py).
DefendantStatusValue = Literal[
    "En Libertad",
    "Detenido",
    "Arresto Domiciliario",
]

CrimeTypeValue = Literal[
    "Ordinario",
    "Violencia",
    "Droga",
    "Armas",
]

DrugTypeValue = Literal[
    "Marihuana",
    "Cocaína",
    "Crack",
    "Metanfetamina",
    "LSD",
    "Heroína",
]

WeaponTypeValue = Literal[
    "Arma de Fuego",
    "Arma Blanca",
    "Arma Contundente",
    "Arma Improvisada",
    "Explosivo",
    "Otra",
]


def _compute_age(birth_date: date | None) -> int | None:
    """Calcula la edad en años a partir de una fecha de nacimiento."""
    if birth_date is None:
        return None
    today = date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def _compute_days_detained(arrest_date: date | None, status: str | None) -> int | None:
    """Calcula los días detenido para un acusado con estado ``Detenido``."""
    if arrest_date is None or status != "Detenido":
        return None
    return max(0, (date.today() - arrest_date).days)


# --------------------------------------------------------------------------- #
# Acusados
# --------------------------------------------------------------------------- #
class DefendantCreate(BaseModel):
    """Carga de entrada para crear/actualizar un acusado."""

    full_name: str = Field(..., min_length=1, max_length=200)
    national_id: str | None = Field(None, max_length=50)
    birth_date: date | None = None
    arrest_date: date | None = None
    presentation_hearing_date: date | None = None
    status: DefendantStatusValue | None = None
    verdict_status: str | None = Field(None, max_length=100)
    arresting_agency: str | None = Field(None, max_length=200)
    additional_notes: str | None = None
    address: str | None = Field(None, max_length=300)
    phone: str | None = Field(None, max_length=50)


class DefendantRead(BaseModel):
    """Representación de un acusado devuelta al frontend."""

    id: int
    case_file_id: int
    full_name: str
    national_id: str | None = None
    birth_date: date | None = None
    age: int | None = None
    arrest_date: date | None = None
    days_detained: int | None = None
    presentation_hearing_date: date | None = None
    status: str | None = None
    verdict_status: str | None = None
    arresting_agency: str | None = None
    additional_notes: str | None = None
    address: str | None = None
    phone: str | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def _compute_age_from_birth_date(self) -> "DefendantRead":
        self.age = _compute_age(self.birth_date)
        self.days_detained = _compute_days_detained(self.arrest_date, self.status)
        return self


class DetentionAlertItem(BaseModel):
    """Acusado detenido que alcanza o supera el umbral configurado."""

    case_file_id: int
    case_number: str
    defendant_id: int
    full_name: str
    arrest_date: date
    days_detained: int
    status: str


# --------------------------------------------------------------------------- #
# Víctimas
# --------------------------------------------------------------------------- #
class VictimCreate(BaseModel):
    """Carga de entrada para crear/actualizar una víctima."""

    full_name: str = Field(..., min_length=1, max_length=200)
    national_id: str | None = Field(None, max_length=50)
    birth_date: date | None = None
    appeared: bool = False
    appearance_date: date | None = None
    address: str | None = Field(None, max_length=300)
    phone: str | None = Field(None, max_length=50)
    additional_notes: str | None = None


class VictimRead(BaseModel):
    """Representación de una víctima devuelta al frontend."""

    id: int
    case_file_id: int
    full_name: str
    national_id: str | None = None
    birth_date: date | None = None
    age: int | None = None
    appeared: bool = False
    appearance_date: date | None = None
    address: str | None = None
    phone: str | None = None
    additional_notes: str | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def _compute_age_from_birth_date(self) -> "VictimRead":
        self.age = _compute_age(self.birth_date)
        return self


# --------------------------------------------------------------------------- #
# Testigos
# --------------------------------------------------------------------------- #
class WitnessCreate(BaseModel):
    """Carga de entrada para crear/actualizar un testigo."""

    full_name: str = Field(..., min_length=1, max_length=200)
    national_id: str | None = Field(None, max_length=50)
    appeared: bool = False
    appearance_date: date | None = None
    address: str | None = Field(None, max_length=300)
    phone: str | None = Field(None, max_length=50)
    additional_notes: str | None = None


class WitnessRead(BaseModel):
    """Representación de un testigo devuelta al frontend."""

    id: int
    case_file_id: int
    full_name: str
    national_id: str | None = None
    appeared: bool = False
    appearance_date: date | None = None
    address: str | None = None
    phone: str | None = None
    additional_notes: str | None = None

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------- #
# Documentales (pruebas documentales)
# --------------------------------------------------------------------------- #
class DocumentaryCreate(BaseModel):
    """Carga de entrada para crear/actualizar un documental (prueba documental)."""

    name: str = Field(..., min_length=1, max_length=200)
    in_possession: bool = False
    possession_date: date | None = None
    evacuated: bool = False
    evacuation_date: date | None = None
    additional_notes: str | None = None


class DocumentaryRead(BaseModel):
    """Representación de un documental devuelta al frontend."""

    id: int
    case_file_id: int
    name: str
    in_possession: bool = False
    possession_date: date | None = None
    evacuated: bool = False
    evacuation_date: date | None = None
    additional_notes: str | None = None

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------- #
# Expertos (funcionarios)
# --------------------------------------------------------------------------- #
class ExpertCreate(BaseModel):
    """Carga de entrada para crear/actualizar un experto/funcionario."""

    name: str = Field(..., min_length=1, max_length=200)
    appeared: bool = False
    appearance_date: date | None = None
    additional_notes: str | None = None


class ExpertRead(BaseModel):
    """Representación de un experto devuelta al frontend."""

    id: int
    case_file_id: int
    name: str
    appeared: bool = False
    appearance_date: date | None = None
    additional_notes: str | None = None

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------- #
# Funcionarios actuantes / aprehensores
# --------------------------------------------------------------------------- #
class ActingOfficialCreate(BaseModel):
    """Carga de entrada para crear/actualizar un funcionario actuante."""

    name: str = Field(..., min_length=1, max_length=200)
    appeared: bool = False
    appearance_date: date | None = None
    additional_notes: str | None = None


class ActingOfficialRead(BaseModel):
    """Representación de un funcionario actuante devuelta al frontend."""

    id: int
    case_file_id: int
    name: str
    appeared: bool = False
    appearance_date: date | None = None
    additional_notes: str | None = None

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------- #
# Audiencias programadas
# --------------------------------------------------------------------------- #
class HearingScheduleCreate(BaseModel):
    """Carga de entrada para crear una audiencia."""

    scheduled_at: datetime
    hearing_type: str | None = Field(None, max_length=100)
    status: str = Field("Scheduled", max_length=50)
    notes: str | None = None
    transcription: str | None = None
    audio_path: str | None = None
    audio_filename: str | None = None


class HearingScheduleUpdate(BaseModel):
    """Carga de entrada para actualizar una audiencia (semántica PATCH):
    solo se aplican los campos provistos explícitamente. Permite corregir
    fecha/hora, tipo, estado y notas sin reenviar el resto."""

    scheduled_at: datetime | None = None
    hearing_type: str | None = Field(None, max_length=100)
    status: str | None = Field(None, max_length=50)
    notes: str | None = None
    transcription: str | None = None
    audio_path: str | None = None
    audio_filename: str | None = None


class HearingScheduleRead(BaseModel):
    """Representación de una audiencia devuelta al frontend."""

    id: int
    case_file_id: int
    scheduled_at: datetime
    hearing_type: str | None = None
    status: str
    notes: str | None = None
    transcription: str | None = None
    audio_path: str | None = None
    audio_filename: str | None = None

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------- #
# Delitos por expediente
# --------------------------------------------------------------------------- #
class CrimeCreate(BaseModel):
    """Carga de entrada para un delito imputado."""

    crime_type: CrimeTypeValue
    drug_quantity: float | None = None
    drug_type: DrugTypeValue | None = None
    weapon_quantity: int | None = None
    weapon_type: WeaponTypeValue | None = None


class CrimeRead(BaseModel):
    """Representación de un delito imputado devuelta al frontend."""

    id: int
    case_file_id: int
    crime_type: str
    drug_quantity: float | None = None
    drug_type: str | None = None
    weapon_quantity: int | None = None
    weapon_type: str | None = None

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------- #
# Documentos adjuntos
# --------------------------------------------------------------------------- #
class AttachmentCreate(BaseModel):
    """Carga de entrada para adjuntar un documento a un expediente."""

    name: str = Field(..., min_length=1, max_length=200)


class AttachmentRead(BaseModel):
    """Representación de un documento adjunto devuelta al frontend."""

    id: int
    case_file_id: int
    name: str
    original_filename: str | None = None
    rel_path: str
    uploaded_at: datetime | None = None

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------- #
# Expedientes
# --------------------------------------------------------------------------- #
class CaseFileCreate(BaseModel):
    """Carga de entrada para crear un expediente."""

    case_number: str = Field(..., min_length=1, max_length=100)
    prosecutor_file_number: str | None = Field(None, max_length=100)
    prosecutor_name: str | None = Field(None, max_length=200)
    defense_attorney: str | None = Field(None, max_length=200)
    current_hearing_type: str | None = Field(None, max_length=100)
    offense_description: str | None = None
    facts_summary: str | None = None
    origin_type: str | None = Field(None, max_length=50)
    indictment_date: date | None = None
    preliminary_hearing_date: date | None = None
    trial_transfer_date: date | None = None
    trial_entry_date: date | None = None
    trial_opening_date: date | None = None
    anticipated_proof_date: date | None = None
    # Control de seguimiento.
    control_entry_date: date | None = None
    control_exit_date: date | None = None
    # Procedencia y ubicación.
    origin_location: str | None = Field(None, max_length=100)
    location: str | None = Field(None, max_length=100)
    # Campos adicionales de clasificación del expediente.
    is_emblematic: bool = False
    pseudonym: str | None = Field(None, max_length=100)
    piece_count: int | None = None


class CaseFileUpdate(BaseModel):
    """Carga de actualización parcial. Todos los campos son opcionales;
    solo se aplican los provistos explícitamente (semántica PATCH)."""

    case_number: str | None = Field(None, min_length=1, max_length=100)
    prosecutor_file_number: str | None = Field(None, max_length=100)
    prosecutor_name: str | None = Field(None, max_length=200)
    defense_attorney: str | None = Field(None, max_length=200)
    current_hearing_type: str | None = Field(None, max_length=100)
    offense_description: str | None = None
    facts_summary: str | None = None
    origin_type: str | None = Field(None, max_length=50)
    indictment_date: date | None = None
    preliminary_hearing_date: date | None = None
    trial_transfer_date: date | None = None
    trial_entry_date: date | None = None
    trial_opening_date: date | None = None
    anticipated_proof_date: date | None = None
    # Control de seguimiento.
    control_entry_date: date | None = None
    control_exit_date: date | None = None
    # Procedencia y ubicación.
    origin_location: str | None = Field(None, max_length=100)
    location: str | None = Field(None, max_length=100)
    # Campos adicionales de clasificación del expediente.
    is_emblematic: bool | None = None
    pseudonym: str | None = Field(None, max_length=100)
    piece_count: int | None = None


class CaseFileRead(BaseModel):
    """Representación completa de un expediente devuelta al frontend,
    incluyendo todos sus acusados y audiencias relacionados."""

    id: int
    case_number: str
    prosecutor_file_number: str | None = None
    prosecutor_name: str | None = None
    defense_attorney: str | None = None
    current_hearing_type: str | None = None
    offense_description: str | None = None
    facts_summary: str | None = None
    origin_type: str | None = None
    indictment_date: date | None = None
    preliminary_hearing_date: date | None = None
    trial_transfer_date: date | None = None
    trial_entry_date: date | None = None
    trial_opening_date: date | None = None
    anticipated_proof_date: date | None = None
    # Control de seguimiento.
    control_entry_date: date | None = None
    control_exit_date: date | None = None
    # Procedencia y ubicación.
    origin_location: str | None = None
    location: str | None = None
    # Campos adicionales de clasificación del expediente.
    is_emblematic: bool = False
    pseudonym: str | None = None
    piece_count: int | None = None
    archived_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    defendants: list[DefendantRead] = []
    victims: list[VictimRead] = []
    witnesses: list[WitnessRead] = []
    documentaries: list[DocumentaryRead] = []
    experts: list[ExpertRead] = []
    acting_officials: list[ActingOfficialRead] = []
    hearings: list[HearingScheduleRead] = []
    attachments: list[AttachmentRead] = []
    crimes: list[CrimeRead] = []

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------- #
# Filas para la vista de calendario
# --------------------------------------------------------------------------- #
class ScheduledHearingItem(BaseModel):
    """Fila plana para vistas de calendario/agenda: información de la
    audiencia más el número de expediente padre, para que la UI pueda
    etiquetar las entradas sin consultas adicionales."""

    hearing_id: int
    case_file_id: int
    case_number: str
    scheduled_at: datetime
    hearing_type: str | None = None
    status: str
    notes: str | None = None
    has_audio: bool = False
    has_transcription: bool = False


class HearingClashItem(BaseModel):
    """Otra audiencia programada en la misma fecha y hora (posible choque)."""

    hearing_id: int
    case_file_id: int
    case_number: str
    scheduled_at: datetime
    hearing_type: str | None = None
    status: str


class DuplicateNationalIdItem(BaseModel):
    """Persona con cédula repetida en otro expediente activo."""

    entity_type: str  # "defendant" | "victim" | "witness"
    entity_id: int
    full_name: str
    national_id: str
    case_file_id: int
    case_number: str


class AttachmentIntegrityIssue(BaseModel):
    """Inconsistencia detectada en el almacén local de adjuntos."""

    attachment_id: int
    case_file_id: int
    case_number: str
    name: str
    rel_path: str
    original_filename: str | None = None
    reason: str  # "missing" | "outside_store"


class AudioIntegrityIssue(BaseModel):
    """Inconsistencia detectada en el almacén local de audios."""

    case_file_id: int
    case_number: str
    hearing_id: int
    scheduled_at: datetime
    audio_path: str
    audio_filename: str | None = None
    reason: str  # "missing" | "outside_store"


class CountItem(BaseModel):
    """Par etiqueta/recuento para reportes estadísticos."""

    label: str
    count: int


class StatisticsSummary(BaseModel):
    """Resumen estadístico del sistema para la vista y los reportes."""

    total_cases: int
    active_cases: int
    archived_cases: int
    cases_by_crime_type: list[CountItem] = []
    cases_by_prosecutor: list[CountItem] = []
    hearings_by_month: list[CountItem] = []
    hearings_by_status: list[CountItem] = []
    cases_by_verdict_status: list[CountItem] = []
    emblematic_cases: int = 0
    cases_missing_audio: int = 0
    cases_missing_transcription: int = 0
    detention_alerts_count: int = 0
