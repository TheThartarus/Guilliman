# Guilliman — DB

Persistence + business logic. Pure Python (SQLAlchemy 2.0 + SQLite, pydantic). No PyQt here.

## Public API (use this, not internals)
- Re-exported in `db/__init__.py`. The UI imports only from `db`:
  `CaseFileService`, schemas, exceptions, and `setup_logging`.
- Schemas:
  - Case file: `CaseFileCreate`, `CaseFileRead`, `CaseFileUpdate`
  - Defendant: `DefendantCreate`, `DefendantRead`
  - Victim: `VictimCreate`, `VictimRead`
  - Witness: `WitnessCreate`, `WitnessRead`
  - Documentary: `DocumentaryCreate`, `DocumentaryRead`
  - Expert: `ExpertCreate`, `ExpertRead`
  - Hearing: `HearingScheduleCreate`, `HearingScheduleRead`, `HearingScheduleUpdate`
  - Agenda: `ScheduledHearingItem` (flat row for calendar views: hearing + parent case_number)
  - Domain: `DefendantStatusValue`
- The UI never touches `db.database` or ORM objects directly — it only
  receives pydantic DTOs. Keep that boundary; add new surface to `service.py`
  and re-export it in `__init__.py`.

## Service lifecycle (`service.py`)
- `CaseFileService(db_path=None)` — `None` → default `case_files.db` (see data dir
  rules below). Multiple services on the same path share one engine.
- `init_db()` MUST be called once before any other method. It:
  1. attaches a per-connection `PRAGMA foreign_keys=ON` listener (SQLite FK off by
     default — required for `ON DELETE CASCADE` to work),
  2. `Base.metadata.create_all`, then
  3. `sync_missing_columns(engine, Base.metadata)` — auto-heals existing DBs by
     adding columns that `models.py` declares but the DB is missing (idempotent,
     only adds, never drops). Uses `ALTER TABLE ... ADD COLUMN` with nullable type
     to work around SQLite's NOT NULL limitation.
  4. `apply_migrations(engine)` (see below).
- `close()` MUST be called on shutdown / after tests using a temp DB. On Windows an
  undisposed engine keeps a file handle that blocks deleting/renaming `case_files.db`.
  Tests clean up via `db.database.dispose_engine(path)`.

## Database (`database.py`)
- Engine + session factory are cached per resolved DB path (`_engines`/`_session_factories`)
  to avoid connection leaks and SQLite file locks on Windows.
- `session_scope(path)` is the context manager for transactions; service methods use it.
- Data dir resolution (`get_app_data_dir`): `Guilliman_DATA_DIR` env → frozen exe
  (`%LOCALAPPDATA%/Guilliman` on Win, `~/.guilliman` elsewhere) → dev (repo root).
  Do NOT point to `_MEIPASS`.

## Models (`models.py`)
- `CaseFile` (1) — children (N): `Defendant`, `Victim`, `Witness`, `Documentary`,
  `Expert`, `HearingSchedule`.
  Tables: `case_files`, `defendants`, `victims`, `witnesses`, `documentaries`,
  `experts`, `hearing_schedules`.
- All child FKs use `ondelete="CASCADE"` and relationships use
  `cascade="all, delete-orphan"`, `passive_deletes=True`, `lazy="selectin"`.
  Deleting a `CaseFile` removes all its children automatically.
- `case_number` is `unique` (drives `DuplicateCaseNumberError`).
- `CaseFile.archived_at` is the soft-delete marker (`NULL` = active). Hard delete
  (`delete_case_file`) still cascades and removes audio files.
- Domain fields per child entity:
  - `Defendant`: `full_name`, `national_id`, `arrest_date`, `presentation_hearing_date`,
    `address`, `phone`, `additional_notes`.
  - `Victim` / `Witness`: `full_name`, `national_id`, `address`, `phone`, `additional_notes`.
  - `Documentary`: `name`, `in_possession` (bool), `possession_date`, `evacuated` (bool),
    `evacuation_date`, `additional_notes`.
  - `Expert`: `name`, `appeared` (bool), `appearance_date`, `additional_notes`.
  - `HearingSchedule`: `scheduled_at` (datetime), `hearing_type`, `status`, `notes`,
    `transcription` (acta, free text), `audio_path` (relative to `get_app_data_dir()`),
    `audio_filename` (original name).

## Schemas (`schemas.py`)
- `*Create` = input validation.
- `*Update` semantics differ by entity — respect this:
  - `CaseFileUpdate` and `HearingScheduleUpdate` are **PATCH**: only supplied fields are
    applied (`model_dump(exclude_unset=True)`). Do NOT switch to full replace.
  - Child-entity updates (`update_defendant`, `update_victim`, `update_witness`,
    `update_documentary`, `update_expert`) are **FULL REPLACE**: always send the complete
    object. (Unlike case file / hearing PATCH.)
- `CaseFileRead` includes nested `defendants`, `victims`, `witnesses`, `documentaries`,
  `experts`, `hearings` lists (eager `selectin`). No extra calls needed to read them.
- `ScheduledHearingItem` is a flat DTO for calendar/agenda views: `hearing_id`,
  `case_file_id`, `case_number`, `scheduled_at`, `hearing_type`, `status`, `notes`,
  `has_audio`, `has_transcription` (booleans for dashboard/agenda indicators).
- `AudioIntegrityIssue` reports a broken audio reference: `case_file_id`, `case_number`,
  `hearing_id`, `scheduled_at`, `audio_path`, `audio_filename`, `reason`
  (`"missing"` | `"outside_store"`). Produced by `check_audio_integrity()`.
- `HearingScheduleCreate` / `HearingScheduleUpdate` / `HearingScheduleRead` carry
  `audio_path` + `audio_filename` (optional) and `transcription` (acta). The agenda
  item does not.
- Hearing `transcription` is free text; never uppercase or filter it. `HearingScheduleUpdate`
  PATCH semantics ensure editing other fields (or scheduling) does not clear it.
- `DefendantStatusValue` is a `Literal` of the *current* Spanish domain
  (`"En Libertad" | "Detenido" | "Arresto Domiciliario"`). Old English values
  (`"Detained"`, `"Custody"`, `"Conditional release"`) are legacy data, not valid input.

## Service methods (`service.py`)
- Case files: `create_case_file(case_file_data, defendants_list=None, victims_list=None,
  witnesses_list=None, documentaries_list=None, experts_list=None, hearings_list=None) -> int`,
  `search_case_files(...)`, `get_case_file_by_id(id) -> CaseFileRead | None`,
  `update_case_file(id, data) -> bool`, `delete_case_file(id) -> bool`.
- `search_case_files` accepts combinable filters (all optional, AND logic):
  `query` (free text on case_number, MP ref, offense description, facts summary and
  location), `defendant_name`, `victim_name`, `witness_name` (LIKE substring),
  `defendant_status`, `verdict_status`, `crime_type` (exact match), `origin_location`
  (LIKE), `indictment_date_from/to`, `hearing_from/to` (date ranges), and
  `include_archived` (default `False` excludes archived rows).
  Empty `query` returns all matching records.
- Case file lifecycle: `archive_case_file(id)` / `unarchive_case_file(id)` toggle
  `archived_at`. Both return `False` if the record is missing or already in that state.
  `delete_case_file(id)` remains the permanent delete.
- Children — each exposes `add_* -> int`, `update_* -> bool`, `delete_* -> bool`:
  defendants, victims, witnesses, documentaries, experts, hearings. Hearings also expose
  `update_hearing_status(...)`, `duplicate_hearing(hearing_id, days=7)` (copies type
  and notes, resets status, omits audio/acta), `count_hearings_missing_audio()` and
  `count_hearings_missing_transcription()` (dashboard counters).
- Hearing audio: `store_audio_file(src_path) -> (rel_path, filename)` copies the file
  into `<data_dir>/audios/` with a unique name and returns the DB-relative path;
  `get_audio_abs_path(rel_path) -> str` resolves it for playback. Passing
  `audio_path`/`audio_filename` through `add_hearing` / `update_hearing` persists or
  clears them. Stored files are deleted when the audio is replaced/cleared, the hearing
  is deleted, or the case file is deleted (cascade). Never uppercase these values.
- Backup: `backup_data(dest_zip_path=None, keep=10) -> str` zips the `.db` **and**
  `audios/` (default dest: `<data_dir>/backups/guilliman_backup_<timestamp>.zip`);
  with the default destination it rotates, keeping the newest `keep` zips.
  `restore_data(src_zip_path)` validates the zip (rejects zip-slip) and replaces both.
  `backup_db(dest_path=None)` / `restore_db(src_path)` are DB-only legacy helpers.
  All of them dispose the engine first (WAL checkpoint / Windows handle) and reinit after.
- `check_audio_integrity() -> list[AudioIntegrityIssue]` verifies every referenced
  audio exists inside `<data_dir>/audios/`; flags missing files and paths that resolve
  outside the store.
- Error / return semantics (relevant for the UI):
  - `add_*` / `update_*` raise `CaseFileNotFoundError` (subclass of `ValueError`) if the
    parent case file does not exist.
  - `update_*` / `delete_*` for children return `False` (do NOT raise) when the record is
    missing or does not belong to the given `case_file_id`. Treat `False` as "not found".
  - `create_case_file` raises `DuplicateCaseNumberError` on unique constraint violation.

## Mixin pattern (`db/services/`)
- `CaseFileService` inherits from entity-specific mixins in `db/services/`:
  `CaseFileMethods`, `DefendantMethods`, `VictimMethods`, `WitnessMethods`,
  `DocumentaryMethods`, `ExpertMethods`, `HearingMethods`, `BackupMethods`.
- All mixins inherit from `_ServiceMixin` (`_base.py`), which provides:
  - `db_path` property (from `self._db_path`)
  - `_to_case_file_read()` ORM→DTO converter
  - `_apply_case_file_update()` and `_apply_hearing_update()` PATCH applicators
  - `_delete_stored_audio(rel_path)` — deletes a file only if it lives inside
    `<data_dir>/audios/` (guards against path traversal); missing files are ignored
- To add a new entity: create mixin in `db/services/`, add schema in
  `db/schemas.py`, and mix it into `CaseFileService` in `service.py`.

## Migrations (`migrations.py`) — extensible stub
- The schema is the source of truth in `models.py` and is created by
  `Base.metadata.create_all()` inside `init_db()`. The migrations applied during
  development (new columns + legacy English→Spanish data translation) were
  consolidated into the models, and the dev database was reset — so `MIGRATIONS`
  starts **empty**.
- `migrations.py` is kept as a functional harness to evolve an *existing* database
  later (first deployment, or a model change over data you don't want to drop).
  `init_db()` applies only versions greater than the recorded `schema_version`;
  idempotent by design (`_column_exists` / `_table_exists` helpers available).
- To add a future migration:
  1. Define `def _migration_005_xxx(session: Session) -> None: ...` doing an
     idempotent ALTER (guard with `_column_exists` / `_table_exists`).
  2. Register it: `MIGRATIONS[5] = _migration_005_xxx`.
- **Never edit a released migration.** Append a new function + entry in `MIGRATIONS`.

## Errors (`exceptions.py`)
- Typed exceptions (`DuplicateCaseNumberError`, `CaseFileNotFoundError`,
  `DefendantNotFoundError`, `HearingNotFoundError`, `GuillimanBackendError`),
  all subclass `ValueError` for backwards compatibility. Catch/raise these, not raw SQLAlchemy.
- `VictimNotFoundError` and `WitnessNotFoundError` exist in `exceptions.py` and are
  re-exported in `__init__.py`, but victim/witness operations currently return `False`
  on miss rather than raising. Prefer the return-value pattern for new child entities.
