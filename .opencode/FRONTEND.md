# Guilliman — FRONTEND

Desktop UI: PyQt5 + qfluentwidgets (FluentWindow). Windows-only, 32-bit target.

## Entry point
- `main.py` builds `QApplication`, applies the saved theme (`ui.settings.load_theme_mode`),
  calls `service.init_db()`, constructs `AppShell`, `showMaximized()`.
- One `QApplication` per process. Tests keep it module-level (`APP = QApplication.instance() or QApplication([])`)
  because destroying it before widgets aborts Qt. Do not create per-test apps.

## Structure (`ui/`)
- `app_shell.py` — `AppShell(FluentWindow)` + `GuillimanApp` (shared state: `service` + `shell`)
  + `SettingsView` (theme combo + "Respaldar datos (BD + audios)" / "Restaurar datos",
  both operating on a `.zip` via `service.backup_data()` / `service.restore_data()`).
- `case_search_view.py` — search / list of case files.
- `case_form_view.py` — create / edit form for a case file and its child entities.
- `case_detail_view/` — read-only detail of a case file (package, not single file).
  Split into mixins per entity: `_defendants.py`, `_victims.py`, `_witnesses.py`,
  `_documentaries.py`, `_experts.py`, `_hearings.py`. All combined in
  `CaseDetailView` via multiple inheritance. `_hearings.py` shows an "Audio" column and
  offers "Abrir audio" in the table context menu (resolves via `service.get_audio_abs_path`).
- `agenda_view.py` — calendar / agenda of scheduled hearings.
- `settings.py` — theme persistence (light / dark) to `settings.json`.
- `dialogs/` — entity dialogs, split into private modules:
  `_defendant.py` (`DefendantDialog`), `_person.py` (`VictimDialog`, `WitnessDialog`),
  `_record.py` (`DocumentaryDialog`, `ExpertDialog`), `_hearing.py` (`HearingDialog`),
  `_cards.py` (`_DateCard`, `_DateTimeCard`, `_FlaggedDateCard`), `_misc.py` (`confirm_delete`, `pick_save_pdf`),
  `_sizes.py` (dialog dimension constants). All re-exported from `dialogs/__init__.py`.
  `HearingDialog` also attaches audio: it copies the file (via `service.store_audio_file`)
  only on save, so cancelling leaves no orphan, and can open/clear an existing audio.
- `exporters.py` — PDF generation (reportlab), pure (no PyQt dependency).
- `shared.py` — pure helpers (labels, date format/parse, validators, uppercase + input
  restriction, InfoBar wrappers). Safe to import without PyQt present.
- `date_pickers.py` — Spanish month localization for qfluentwidgets `DatePicker`.

## Navigation (`AppShell`)
- Fixed sub-interfaces (objectName = route key): `search`, `new`, `agenda`, `settings`.
- Dynamic routes for case detail / edit are added via `addSubInterface` with keys
  `detail-{case_id}` / `edit-{case_id}` and removed by `_close_route`. When adding a
  new dynamic view, follow this key + `on_close=self._close_route` pattern.
- Switching tabs triggers `refresh()` on the active view (via `_on_current_changed`).
- `_close_all_dynamic_routes()` closes all dynamic views (used after DB restore).

## State & data flow
- UI talks to the db only through `CaseFileService` (passed via `GuillimanApp.service`).
  No direct SQLAlchemy usage in `ui/`.
- Hearing audio paths are stored relative to the data dir; the UI must resolve them with
  `service.get_audio_abs_path(rel)` and never build `<data_dir>` paths itself.
- `ui.settings` persists prefs (`theme_mode`) to `get_settings_path()`:
  `Guilliman_DATA_DIR` → frozen (`%LOCALAPPDATA%/Guilliman/settings.json`) → **dev: repo root
  `settings.json`** (gitignored). In dev, running the app writes `settings.json` to the repo root.

## Conventions (enforced — tests assert these)
- Text inputs are normalized to UPPERCASE (`shared.make_uppercase`, `shared.restrict_input`).
  Form collection returns uppercase (e.g. `form._collect_kwargs()["prosecutor_name"] == "FISCALIA TEST"`).
  Preserve this; don't strip uppercasing. Recommendation: apply uppercase to names / addresses /
  ids; leave `phone` as typed (uppercasing numbers adds no value).
- `shared.restrict_input(widget, kind)` filters characters by kind:
  - `"code"`: alphanumeric + `-` (case number, MP reference).
  - `"agency"`: alphanumeric + space + `-` (arresting agency).
  - `"letters"`: letters + space (person names).
  - `"digits"`: digits only (national id / cedula).
  - `"address"`: alphanumeric + space + `-` + `.` + `,` (addresses).
  - `"phone"`: digits + `-` (phones).
  - `"text"`: alphanumeric + space (default; names, descriptions, notes).
  - `"text_ext"`: alphanumeric + space + `.` + `,` (descriptions and summaries with punctuation).
  Used across forms and dialogs.
- Comboboxes store domain values in `userData`; use `combo_set_data(combo, value)` /
  `combo_current_data(combo)` — not by display text.

## Domain labels (`shared.py`)
- Spanish display labels for db domain values live here: `DEFENDANT_STATUS_LABELS`,
  `HEARING_TYPE_LABELS`, `HEARING_STATUS_LABELS`, `ORIGIN_TYPE_LABELS`, `VERDICT_STATUS_LABELS`.
- These maps intentionally include LEGACY English keys (`Opening`, `Custody`, …) so old
  DB rows still render. When adding a new domain value, add the Spanish label here AND the
  option in `DEFENDANT_STATUS_OPTIONS` / `HEARING_TYPE_OPTIONS` as needed.
- `translate(value, labels)` renders a stored value to its label (or `—` for None/empty).
  `field_errors(exc)` translates a pydantic `ValidationError` to Spanish for user-facing
  messages. Date helpers: `format_date`, `format_datetime`, `parse_date_text`, `parse_time_text`.

## Date handling (`_DateCard` in `ui/case_form_view.py`)
- Optional dates use the `_DateCard(SettingCard)` pattern: a `SwitchButton` toggles
  the date on/off (off = `NULL` in DB), and a `DatePicker` is disabled when off.
- `date_pickers.py` injects `SpanishMonthFormatter` into qfluentwidgets' `DatePicker`
  so month names display in Spanish.

## PDF export (`exporters.py`)
- `export_case_pdf(case: CaseFileRead, filepath)`, `export_agenda_pdf(items, start, end, filepath)`
  use reportlab.
- Pure (no PyQt dependency) — takes db DTOs + `ui.shared` labels.
- Uses Helvetica (WinAnsi) deliberately for Spanish accents; keep it unless you switch to a
  Unicode font with a registered face.

## Tests (`tests/`)
- Run headless via `QT_QPA_PLATFORM=offscreen` (set inside the test file).
- `conftest.py` adds repo root to `sys.path`; tests import `db`/`ui`/`main` directly.
- Some tests create temp DBs in the repo root and clean them up (`test_pyqt_smoke.py`
  removes `test_pyqt_smoke.db` + `-wal`/`-shm`). `test_packaging.py` validates that data/settings
  paths never resolve under PyInstaller's `_MEIPASS`.
- Test teardown MUST call `service.close()` or `dispose_engine()` to release the SQLite
  file handle on Windows. `reset_session_factory()` clears all cached engines/factories.
- `test_hearing_audio.py` covers the audio lifecycle (store → persist → clear/delete →
  default `backup_data()`); it isolates `audios/` via `Guilliman_DATA_DIR`.
