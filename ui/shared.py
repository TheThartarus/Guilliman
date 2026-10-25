"""
Guilliman Frontend - Utilidades puras compartidas entre las vistas.

Contiene helpers de formato de fechas y traducción de valores de dominio del
db a etiquetas legibles en español. Son helpers PUROS (sin dependencias
de ningún toolkit de UI): no dependen de PyQt ni construyen controles.

Los helpers dependientes de la UI (snackbars, diálogos de confirmación,
widgets compuestos, manejo de ``on_change`` de campos, etc.) viven en
``ui.widgets`` para mantener ``shared`` como una capa de presentación
desacoplada del db.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import ValidationError

# --------------------------------------------------------------------------- #
# Etiquetas legibles en español para los valores de dominio del db
# --------------------------------------------------------------------------- #
DEFENDANT_STATUS_LABELS: dict[str, str] = {
    # Valores vigentes (se almacenan tal cual en la base de datos).
    "En Libertad": "EN LIBERTAD",
    "Detenido": "DETENIDO",
    "Arresto Domiciliario": "ARRESTO DOMICILIARIO",
    # Valores legacy: expedientes creados antes del cambio de dominio.
    "Custody": "BAJO CUSTODIA",
    "Conditional release": "LIBERTAD CONDICIONAL",
}

# Opciones ofrecidas en los formularios para el estado del acusado.
DEFENDANT_STATUS_OPTIONS: list[str] = [
    "En Libertad",
    "Detenido",
    "Arresto Domiciliario",
]

VERDICT_STATUS_LABELS: dict[str, str] = {
    "Acquittal": "ABSOLUCIÓN",
    "Conviction": "CONDENA",
    "Pending": "PENDIENTE",
}
VERDICT_STATUS_OPTIONS: list[str] = [
    "Absolución",
    "Condena",
    "Pendiente",
]
VERDICT_STATUS_DOMAIN: dict[str, str] = {
    "Absolución": "Acquittal",
    "Condena": "Conviction",
    "Pendiente": "Pending",
}
ORIGIN_TYPE_LABELS: dict[str, str] = {
    "Local": "LOCAL",
    "TPM": "TPM",
}

# Tipos de delito ofrecidos en los formularios y en la búsqueda.
CRIME_TYPE_OPTIONS: list[str] = [
    "Ordinario",
    "Violencia",
    "Droga",
    "Armas",
]
CRIME_TYPE_LABELS: dict[str, str] = {value: value for value in CRIME_TYPE_OPTIONS}
DRUG_TYPE_LABELS: dict[str, str] = {
    "Marihuana": "Marihuana",
    "Cocaína": "Cocaína",
    "Crack": "Crack",
    "Metanfetamina": "Metanfetamina",
    "LSD": "LSD",
    "Heroína": "Heroína",
}
WEAPON_TYPE_LABELS: dict[str, str] = {
    "Arma de Fuego": "Arma de Fuego",
    "Arma Blanca": "Arma Blanca",
    "Arma Contundente": "Arma Contundente",
    "Arma Improvisada": "Arma Improvisada",
    "Explosivo": "Explosivo",
    "Otra": "Otra",
}

HEARING_STATUS_LABELS: dict[str, str] = {
    "Scheduled": "Programada",
    "Completed": "Realizada",
    "Deferred": "Diferida",
    "Cancelled": "Cancelada",
}

# Tipos de audiencia válidos: tuplas (etiqueta_visible, valor_almacenado).
HEARING_TYPE_OPTIONS: list[tuple[str, str]] = [
    ("Audiencia Preliminar", "Audiencia Preliminar"),
    ("Prueba Anticipada", "Prueba Anticipada"),
    ("Apertura de Juicio", "Apertura de Juicio"),
    ("Continuación de Juicio", "Continuación de Juicio"),
    ("Conclusión", "Conclusión"),
]

HEARING_TYPE_LABELS: dict[str, str] = {
    "Audiencia Preliminar": "Audiencia Preliminar",
    "Prueba Anticipada": "Prueba Anticipada",
    "Apertura de Juicio": "Apertura de Juicio",
    "Continuación de Juicio": "Continuación de Juicio",
    "Conclusión": "Conclusión",
    # Legacy (renombrados)
    "Apertura": "Apertura de Juicio",
    "Continuación": "Continuación de Juicio",
    # Legacy (inglés)
    "Opening": "Apertura de Juicio",
    "OPENING": "Apertura de Juicio",
    "Continuation": "Continuación de Juicio",
    "CONTINUATION": "Continuación de Juicio",
    "Preliminary": "Audiencia Preliminar",
    "PRELIMINARY": "Audiencia Preliminar",
    "Intermediate": "Etapa intermedia",
    "Trial": "Juicio oral",
    "Sentencia": "Sentencia",
    "Sentencing": "Sentencia",
}


# --------------------------------------------------------------------------- #
# Formato de fechas y horas
# --------------------------------------------------------------------------- #
def format_date(value: date | None) -> str:
    """Formatea una fecha como dd/mm/aaaa; devuelve un guion si es None."""
    return value.strftime("%d/%m/%Y") if value else "—"


def format_datetime(value: datetime | None) -> str:
    """Formatea una fecha/hora como dd/mm/aaaa hh:mm; guion si es None."""
    return value.strftime("%d/%m/%Y %H:%M") if value else "—"


def translate(value: str | None, labels: dict[str, str]) -> str:
    """Traduce un valor de dominio a su etiqueta en español."""
    if value is None or value == "":
        return "—"
    return labels.get(value, value)


# --------------------------------------------------------------------------- #
# Traducción de errores de validación (pydantic) a español
# --------------------------------------------------------------------------- #
def field_errors(exc: ValidationError) -> dict[str, str]:
    """Convierte un ``pydantic.ValidationError`` en {campo: primer mensaje}."""
    errors: dict[str, str] = {}
    for item in exc.errors():
        field = ".".join(str(part) for part in item.get("loc", []))
        if field not in errors:
            errors[field] = _humanize_pydantic_message(item)
    return errors


def _humanize_pydantic_message(item: dict) -> str:
    """Traduce los mensajes más frecuentes de Pydantic v2 al español."""
    message: str = item.get("msg", "Valor inválido")
    translations = {
        "String should have at least 1 character": "El campo es obligatorio",
        "Value error, El campo es obligatorio": "El campo es obligatorio",
        "Field required": "Campo requerido",
        "Input should be a valid string": "Debe ser texto válido",
        "Input should be a valid date": "Fecha inválida",
        "Input should be a valid datetime": "Fecha y hora inválidas",
    }
    for english, spanish in translations.items():
        if english in message:
            return spanish
    if "at least" in message or "less than" in message:
        ctx = item.get("ctx") or {}
        limit = ctx.get("min_length") or ctx.get("lt")
        if limit is not None:
            return f"Máximo/Mínimo de caracteres excedido ({limit})"
    return message


# --------------------------------------------------------------------------- #
# Parsers de texto a tipos de fecha/hora
# --------------------------------------------------------------------------- #
def parse_date_text(text: str) -> date | None:
    """Parsea texto dd/mm/aaaa; devuelve None si es vacío o inválido."""
    text = (text or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%d/%m/%Y").date()
    except ValueError:
        return None


def parse_time_text(text: str):
    """Parsea texto HH:MM; devuelve ``time`` o None si es inválido/vacío."""
    from datetime import time

    text = (text or "").strip()
    if not text:
        return None
    try:
        parts = [int(p) for p in text.split(":")]
        if len(parts) == 2 and 0 <= parts[0] <= 23 and 0 <= parts[1] <= 59:
            return time(parts[0], parts[1])
    except ValueError:
        return None
    return None


# --------------------------------------------------------------------------- #
# Patrones de caracteres permitidos
# --------------------------------------------------------------------------- #
ALPHANUMERIC_DASH_PATTERN = r"[A-Z0-9-]"
ALPHANUMERIC_SPACE_DASH_PATTERN = r"[A-Z0-9 -]"
DIGITS_ONLY_PATTERN = r"[0-9]"
DIGITS_AND_COLON_PATTERN = r"[0-9:]"
