# Guilliman — AGENTS.md

Compact guidance for agents working in this repo. Signals only.

## What this is
- Windows-only desktop app (PyQt5 + qfluentwidgets) for managing penal case files,
  including per-hearing audio recordings stored locally. Backend is pure Python over
  SQLAlchemy 2.0 + SQLite (local `case_files.db`).
- Build target is **32-bit Windows PCs**; the packaged exe must run offline with no Python install.

## Commands
- Run (dev): `python main.py` → opens a native window. In dev mode the app writes
  `case_files.db` and `settings.json` **into the repo root** (both gitignored).
- Tests: `python -m pytest tests`. `tests/conftest.py` adds the repo root to
  `sys.path`; PyQt tests run headless via `QT_QPA_PLATFORM=offscreen` (set inside the test).
  Single file: `python -m pytest tests/test_backend.py`. Verbose: add `-v`.
- Build 32-bit exe: `build.bat` (uses the embedded **Python 3.12 32-bit**; by default
  `py -3.12-32`, or pass an explicit interpreter: `build.bat python312\python.exe`).
  Output: `dist/Guilliman/Guilliman.exe`.
- CI: GitHub Actions runs `python -m pytest tests -v` on Ubuntu with Python 3.12
  (`.github/workflows/test.yml`). Tests pass headless; no Windows-specific behavior tested.

## Architecture
- `db/` — business logic + persistence. Public API is re-exported in
  `db/__init__.py` (`CaseFileService`, pydantic schemas `CaseFileCreate/Read/Update`, etc.).
  The UI must import only from `db`, never touch `db.database` directly.
- `CaseFileService` (`db/service.py`) is composed of **mixins** from
  `db/services/` (one per entity: `case_files`, `defendants`, `victims`,
  etc.). To add a new entity, create a mixin in `db/services/`, add a
  schema in `db/schemas.py`, and mix it into `CaseFileService`.
- `ui/` — views, dialogs, exporters, settings, and the app shell
  (`ui.app_shell.AppShell` is the main `FluentWindow`).
  Sub-views are split into private modules (e.g. `ui/case_detail_view/_defendants.py`).
- `main.py` — entry point: builds `QApplication`, applies the saved theme, calls
  `service.init_db()`, constructs `AppShell`, `showMaximized()`.
- Data dir resolution (`db.database.get_app_data_dir`), in precedence:
  `Guilliman_DATA_DIR` env → frozen exe (`%LOCALAPPDATA%/Guilliman` on Win, `~/.guilliman` elsewhere)
  → dev (repo root). Tests override via `Guilliman_DATA_DIR` or an explicit DB path to
  `CaseFileService(...)`. Never point data at `_MEIPASS` (temp dir of the frozen exe).
- **Hearing audio**: each `HearingSchedule` carries `audio_path` (relative to
  `get_app_data_dir()`) + `audio_filename`. Files live in `<data_dir>/audios/`
  (gitignored; in dev that is the repo root). Public API: `store_audio_file(src) ->
  (rel_path, filename)` and `get_audio_abs_path(rel)`. Cleanup is automatic when the
  audio is replaced/cleared, a hearing is deleted, or its parent case file is deleted.

## Quirks / gotchas
- `.opencode/node_modules` and `.opencode/package.json` are **OpenCode's own plugin
  tooling**, NOT application code. This repo is pure Python/PyQt — there is no JS/Node
  frontend. Do not treat `.opencode/` as part of the app or look for a web client.
- **Build Python is pinned to 3.12 32-bit**. SQLAlchemy 2.0 declares `greenlet>=1`, but
  `greenlet` publishes **no 32-bit wheel at all** (neither 3.11 nor 3.12); `build.bat`
  therefore installs SQLAlchemy with `--no-deps` (the app is fully synchronous and never
  imports `greenlet`). Do NOT build with 3.13-32, and do not `pip install -r requirements.txt`
  on a 32-bit interpreter (it would try to compile `greenlet` from source and fail).
- PyInstaller needs the `--hidden-import` flags already in `build.bat`
  (`qfluentwidgets`, `qframelesswindow`, `reportlab`). If you add a new runtime import,
  add its `--hidden-import` or the frozen exe fails at startup.
- **Migrations** are sequential integer versions in `db/migrations.py`, applied by
  `init_db()` only for versions newer than the recorded `schema_version`. Never edit a
  released migration; append a new entry to `MIGRATIONS` instead.
- **Backups**: the user-facing "Respaldar datos" flow uses `backup_data()` /
  `restore_data()`, which zip the `.db` **and** `audios/` together. `backup_db()` /
  `restore_db()` remain DB-only (legacy). `restore_data()` validates the zip (rejects
  zip-slip) and replaces both the DB and the whole `audios/` folder; Settings calls
  `backup_data()` first as a safety net before restoring.
- Input convention: text fields are uppercased on collection
  (`ui/shared.make_uppercase`, `combo_set_data`). Tests assert uppercase output
  (e.g. `form._collect_kwargs()` returns `"FISCALIA TEST"`); preserve this behavior.
- No lint / typecheck / CI config exists in this repo — do not assume those commands.
- **Test isolation**: Tests create temp DBs and clean them up via `db.database.dispose_engine(path)`
  and `reset_session_factory()`. On Windows, an undisposed engine keeps a file handle that blocks
  deleting/renaming `.db` files. Always call `service.close()` or `dispose_engine()` in test teardown.
- **QApplication lifecycle**: Tests keep QApplication module-level (`APP = QApplication.instance() or QApplication([])`)
  because destroying it before widgets aborts Qt (segfault). Do not create per-test apps.

## Deeper docs
- Area-specific guidance lives in `.opencode/BACKEND.md` (persistence/service/migrations)
  and `.opencode/FRONTEND.md` (PyQt views, navigation, conventions). Read them before
  touching the respective layer.
