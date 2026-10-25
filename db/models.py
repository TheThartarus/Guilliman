"""
Guilliman Backend - Modelos ORM.

Define el esquema relacional de la base de datos SQLite local
(``case_files.db``) usando el estilo declarativo de SQLAlchemy 2.0.

Entidades:
    - CaseFile:        Un expediente judicial penal.
    - Defendant:       Un acusado relacionado con un expediente.
    - HearingSchedule: Una audiencia programada relacionada con un expediente.

Ambas tablas hijas están configuradas con ON DELETE CASCADE, de modo que al
eliminar un CaseFile se eliminan automáticamente todos sus acusados y
audiencias.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Clase base declarativa para todos los modelos ORM del proyecto."""


class CaseFile(Base):
    """Un expediente judicial penal (tabla: ``case_files``)."""

    __tablename__ = "case_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Número de expediente único - campo principal de búsqueda.
    case_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    # Referencia de la fiscalía (Nomenclatura del MP).
    prosecutor_file_number: Mapped[str | None] = mapped_column(String(100), index=True)
    prosecutor_name: Mapped[str | None] = mapped_column(String(200))
    defense_attorney: Mapped[str | None] = mapped_column(String(200))
    current_hearing_type: Mapped[str | None] = mapped_column(String(100))
    offense_description: Mapped[str | None] = mapped_column(Text)
    facts_summary: Mapped[str | None] = mapped_column(Text)
    # p. ej. "Local", "TPM".
    origin_type: Mapped[str | None] = mapped_column(String(50))
    indictment_date: Mapped[date | None] = mapped_column(Date)
    preliminary_hearing_date: Mapped[date | None] = mapped_column(Date)
    trial_transfer_date: Mapped[date | None] = mapped_column(Date)
    trial_entry_date: Mapped[date | None] = mapped_column(Date)
    trial_opening_date: Mapped[date | None] = mapped_column(Date)
    # "Prueba Anticipada" (dato del expediente, como los demás trial_* dates).
    anticipated_proof_date: Mapped[date | None] = mapped_column(Date)

    # Control de seguimiento del expediente.
    control_entry_date: Mapped[date | None] = mapped_column(Date)
    control_exit_date: Mapped[date | None] = mapped_column(Date)

    # Procedencia y ubicación del expediente.
    origin_location: Mapped[str | None] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(100))

    # Campos adicionales de clasificación del expediente (los delitos viven en
    # la tabla ``crimes``).
    is_emblematic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pseudonym: Mapped[str | None] = mapped_column(String(100))
    piece_count: Mapped[int | None] = mapped_column(Integer)  # N° de piezas del expediente

    # Archivo lógico (soft delete): NULL = activo, fecha = archivado.
    archived_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    # Relaciones 1 a N. ``cascade="all, delete-orphan"`` combinado con el
    # ondelete="CASCADE" de la FK garantiza la limpieza de huérfanos tanto a
    # nivel ORM como a nivel de base de datos.
    defendants: Mapped[list["Defendant"]] = relationship(
        back_populates="case_file",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    victims: Mapped[list["Victim"]] = relationship(
        back_populates="case_file",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    witnesses: Mapped[list["Witness"]] = relationship(
        back_populates="case_file",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    documentaries: Mapped[list["Documentary"]] = relationship(
        back_populates="case_file",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    experts: Mapped[list["Expert"]] = relationship(
        back_populates="case_file",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    acting_officials: Mapped[list["ActingOfficial"]] = relationship(
        back_populates="case_file",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    hearings: Mapped[list["HearingSchedule"]] = relationship(
        back_populates="case_file",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="case_file",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    crimes: Mapped[list["Crime"]] = relationship(
        back_populates="case_file",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<CaseFile id={self.id} case_number={self.case_number!r}>"


class Defendant(Base):
    """Un acusado vinculado a un expediente (tabla: ``defendants``)."""

    __tablename__ = "defendants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_file_id: Mapped[int] = mapped_column(
        ForeignKey("case_files.id", ondelete="CASCADE"), index=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    national_id: Mapped[str | None] = mapped_column(String(50), index=True)
    birth_date: Mapped[date | None] = mapped_column(Date)
    arrest_date: Mapped[date | None] = mapped_column(Date)
    # "Audiencia de Presentación" (dato del acusado, como arrest_date).
    presentation_hearing_date: Mapped[date | None] = mapped_column(Date)
    # Estado del acusado: "En Libertad", "Detenido", "Arresto Domiciliario".
    status: Mapped[str | None] = mapped_column(String(100))
    # p. ej. "Acquittal", "Conviction", "Pending".
    verdict_status: Mapped[str | None] = mapped_column(String(100), default="Pending")
    # Organismo que aprehendió al acusado.
    arresting_agency: Mapped[str | None] = mapped_column(String(200))
    additional_notes: Mapped[str | None] = mapped_column(Text)
    # Campos de contacto del acusado.
    address: Mapped[str | None] = mapped_column(String(300))
    phone: Mapped[str | None] = mapped_column(String(50))

    case_file: Mapped[CaseFile] = relationship(back_populates="defendants")

    def __repr__(self) -> str:
        return f"<Defendant id={self.id} full_name={self.full_name!r}>"


class Victim(Base):
    """Una víctima vinculada a un expediente (tabla: ``victims``)."""

    __tablename__ = "victims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_file_id: Mapped[int] = mapped_column(
        ForeignKey("case_files.id", ondelete="CASCADE"), index=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    national_id: Mapped[str | None] = mapped_column(String(50), index=True)
    birth_date: Mapped[date | None] = mapped_column(Date)
    appeared: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    appearance_date: Mapped[date | None] = mapped_column(Date)
    address: Mapped[str | None] = mapped_column(String(300))
    phone: Mapped[str | None] = mapped_column(String(50))
    additional_notes: Mapped[str | None] = mapped_column(Text)

    case_file: Mapped[CaseFile] = relationship(back_populates="victims")

    def __repr__(self) -> str:
        return f"<Victim id={self.id} full_name={self.full_name!r}>"


class Witness(Base):
    """Un testigo vinculado a un expediente (tabla: ``witnesses``)."""

    __tablename__ = "witnesses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_file_id: Mapped[int] = mapped_column(
        ForeignKey("case_files.id", ondelete="CASCADE"), index=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    national_id: Mapped[str | None] = mapped_column(String(50), index=True)
    appeared: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    appearance_date: Mapped[date | None] = mapped_column(Date)
    address: Mapped[str | None] = mapped_column(String(300))
    phone: Mapped[str | None] = mapped_column(String(50))
    additional_notes: Mapped[str | None] = mapped_column(Text)

    case_file: Mapped[CaseFile] = relationship(back_populates="witnesses")

    def __repr__(self) -> str:
        return f"<Witness id={self.id} full_name={self.full_name!r}>"


class Documentary(Base):
    """Un documental/prueba documental vinculado a un expediente (tabla: ``documentaries``)."""

    __tablename__ = "documentaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_file_id: Mapped[int] = mapped_column(
        ForeignKey("case_files.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # ¿Se encuentra ya en posesión del expediente? Si es True, la UI fija
    # ``possession_date`` (cuándo se entregó/recibió).
    in_possession: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    possession_date: Mapped[date | None] = mapped_column(Date)
    # ¿Ya fue evacuada (presentada) la prueba? Si es True, la UI fija
    # ``evacuation_date`` (cuándo se entregó).
    evacuated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evacuation_date: Mapped[date | None] = mapped_column(Date)
    additional_notes: Mapped[str | None] = mapped_column(Text)

    case_file: Mapped[CaseFile] = relationship(back_populates="documentaries")

    def __repr__(self) -> str:
        return f"<Documentary id={self.id} name={self.name!r}>"


class Expert(Base):
    """Un experto/funcionario vinculado a un expediente (tabla: ``experts``)."""

    __tablename__ = "experts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_file_id: Mapped[int] = mapped_column(
        ForeignKey("case_files.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # ¿Ya compareció el experto? Si es True, la UI fija ``appearance_date``
    # (cuándo compareció).
    appeared: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    appearance_date: Mapped[date | None] = mapped_column(Date)
    additional_notes: Mapped[str | None] = mapped_column(Text)

    case_file: Mapped[CaseFile] = relationship(back_populates="experts")

    def __repr__(self) -> str:
        return f"<Expert id={self.id} name={self.name!r}>"


class ActingOfficial(Base):
    """Un funcionario actuante/aprehensor vinculado a un expediente (tabla: ``acting_officials``)."""

    __tablename__ = "acting_officials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_file_id: Mapped[int] = mapped_column(
        ForeignKey("case_files.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # ¿Ya compareció el funcionario? Si es True, la UI fija ``appearance_date``
    # (cuándo compareció).
    appeared: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    appearance_date: Mapped[date | None] = mapped_column(Date)
    additional_notes: Mapped[str | None] = mapped_column(Text)

    case_file: Mapped[CaseFile] = relationship(back_populates="acting_officials")

    def __repr__(self) -> str:
        return f"<ActingOfficial id={self.id} name={self.name!r}>"


class HearingSchedule(Base):
    """Una audiencia programada vinculada a un expediente (tabla: ``hearing_schedules``)."""

    __tablename__ = "hearing_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_file_id: Mapped[int] = mapped_column(
        ForeignKey("case_files.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # p. ej. "Opening", "Continuation", "Preliminary".
    hearing_type: Mapped[str | None] = mapped_column(String(100))
    # p. ej. "Scheduled", "Completed", "Deferred", "Cancelled".
    status: Mapped[str] = mapped_column(String(50), default="Scheduled", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    # Acta / transcripción de la audiencia (texto libre, tal como se redacta).
    transcription: Mapped[str | None] = mapped_column(Text)
    # Ruta relativa (al directorio de datos de la app) del archivo de audio
    # copiado al almacén local. No se uppercacea: es una ruta de archivo.
    audio_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Nombre original del archivo de audio, solo para mostrar al usuario.
    audio_filename: Mapped[str | None] = mapped_column(String(300), nullable=True)

    case_file: Mapped[CaseFile] = relationship(back_populates="hearings")

    def __repr__(self) -> str:
        return f"<HearingSchedule id={self.id} scheduled_at={self.scheduled_at!r}>"


class Attachment(Base):
    """Un documento adjunto a un expediente (tabla: ``attachments``)."""

    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_file_id: Mapped[int] = mapped_column(
        ForeignKey("case_files.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Título visible del documento (p. ej. "Cédula del acusado").
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Nombre original del archivo, para mostrar al usuario.
    original_filename: Mapped[str | None] = mapped_column(String(300))
    # Ruta relativa (al directorio de datos) del archivo copiado.
    rel_path: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )

    case_file: Mapped[CaseFile] = relationship(back_populates="attachments")

    def __repr__(self) -> str:
        return f"<Attachment id={self.id} name={self.name!r}>"


class Crime(Base):
    """Un delito imputado en un expediente (tabla: ``crimes``)."""

    __tablename__ = "crimes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_file_id: Mapped[int] = mapped_column(
        ForeignKey("case_files.id", ondelete="CASCADE"), index=True, nullable=False
    )
    crime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    drug_quantity: Mapped[float | None] = mapped_column(Float)
    drug_type: Mapped[str | None] = mapped_column(String(50))
    weapon_quantity: Mapped[int | None] = mapped_column(Integer)
    weapon_type: Mapped[str | None] = mapped_column(String(50))

    case_file: Mapped[CaseFile] = relationship(back_populates="crimes")

    def __repr__(self) -> str:
        return f"<Crime id={self.id} crime_type={self.crime_type!r}>"
