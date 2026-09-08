"""Guilliman DB package - business logic and persistence layer.

Public API for the PyQt frontend:

    from db import CaseFileService
"""

from .exceptions import (
    CaseFileNotFoundError,
    DefendantNotFoundError,
    DuplicateCaseNumberError,
    HearingNotFoundError,
    GuillimanBackendError,
    VictimNotFoundError,
    WitnessNotFoundError,
)
from .schemas import (
    ActingOfficialCreate,
    ActingOfficialRead,
    CaseFileCreate,
    CaseFileRead,
    CaseFileUpdate,
    CrimeTypeValue,
    DefendantCreate,
    DefendantRead,
    DefendantStatusValue,
    DocumentaryCreate,
    DocumentaryRead,
    DrugTypeValue,
    ExpertCreate,
    ExpertRead,
    HearingScheduleCreate,
    HearingScheduleRead,
    HearingScheduleUpdate,
    ScheduledHearingItem,
    VictimCreate,
    VictimRead,
    WitnessCreate,
    WitnessRead,
)
from .logging_config import setup_logging
from .service import CaseFileService

__all__ = [
    "ActingOfficialCreate",
    "ActingOfficialRead",
    "CaseFileService",
    "setup_logging",
    "CaseFileCreate",
    "CaseFileRead",
    "CaseFileUpdate",
    "CrimeTypeValue",
    "DefendantCreate",
    "DefendantRead",
    "DefendantStatusValue",
    "DrugTypeValue",
    "VictimCreate",
    "VictimRead",
    "WitnessCreate",
    "WitnessRead",
    "DocumentaryCreate",
    "DocumentaryRead",
    "ExpertCreate",
    "ExpertRead",
    "HearingScheduleCreate",
    "HearingScheduleRead",
    "HearingScheduleUpdate",
    "ScheduledHearingItem",
    "GuillimanBackendError",
    "CaseFileNotFoundError",
    "DefendantNotFoundError",
    "HearingNotFoundError",
    "DuplicateCaseNumberError",
    "VictimNotFoundError",
    "WitnessNotFoundError",
]
