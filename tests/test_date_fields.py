"""
Guilliman Backend - Test de los nuevos campos de fecha (presentación / prueba).

Valida en el db (sin tocar UI/PDF):
    1) Round-trip de ``Defendant.presentation_hearing_date`` y
       ``CaseFile.anticipated_proof_date`` (guardar y recuperar).
     2) Que ambos campos son opcionales (None) y no rompen la creación.
     3) Que el mecanismo de migraciones sigue funcional e idempotente para
        uso futuro (el esquema actual vive en models.py vía create_all).

Patrón de limpieza reutilizado de ``test_export_data.py``.
"""

import gc
import os
import sys
import tempfile
import time
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

from db import CaseFileCreate, CaseFileService, DefendantCreate
from db.database import reset_session_factory
from db.migrations import apply_migrations


def _cleanup(path: str) -> None:
    """Libera engines y borra la BD temporal con reintentos."""
    reset_session_factory()
    gc.collect()
    for suffix in ("", "-wal", "-shm"):
        p = path + suffix
        if not os.path.exists(p):
            continue
        for _attempt in range(10):
            try:
                os.remove(p)
                break
            except PermissionError:
                gc.collect()
                time.sleep(0.2)


def test_roundtrip() -> None:
    """Guarda y recupera los dos nuevos campos; verifica que son opcionales."""
    path = tempfile.mktemp(suffix=".db")
    service = CaseFileService(path)
    service.init_db()

    cf_id = service.create_case_file(
        CaseFileCreate(
            case_number="01001-2026-DATES",
            anticipated_proof_date=date(2026, 2, 1),
        ),
        defendants_list=[
            DefendantCreate(
                full_name="Pedro Gomez",
                presentation_hearing_date=date(2026, 2, 15),
            )
        ],
    )
    detail = service.get_case_file_by_id(cf_id)
    assert detail.anticipated_proof_date == date(2026, 2, 1), (
        f"anticipated_proof_date no round-trip: {detail.anticipated_proof_date}"
    )
    assert len(detail.defendants) == 1
    assert detail.defendants[0].presentation_hearing_date == date(2026, 2, 15), (
        "presentation_hearing_date no round-trip"
    )

    # Opcionalidad: crear sin los campos no debe fallar.
    cf_id2 = service.create_case_file(CaseFileCreate(case_number="01001-2026-NONE"))
    detail2 = service.get_case_file_by_id(cf_id2)
    assert detail2.anticipated_proof_date is None

    service.close()
    _cleanup(path)
    print("   -> round-trip OK (con y sin valores)")


def test_migration_harness_is_functional_and_idempotent() -> None:
    """El mecanismo de migraciones sigue funcional para uso futuro.

    Valida la maquinaria (schema_version, apply_migrations, idempotencia)
    registrando una migración temporal; no depende de migraciones ya
    aplicadas, ya que esas viven ahora en models.py vía create_all.
    """
    from db import migrations as mig

    path = tempfile.mktemp(suffix=".db")
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY)"))
        conn.execute(
            text(
                "CREATE TABLE schema_version "
                "(version INTEGER PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
        )

    applied_flag: list[int] = []

    def _temp_migration(session):
        applied_flag.append(1)
        session.execute(text("ALTER TABLE t ADD COLUMN note TEXT"))

    original = dict(mig.MIGRATIONS)
    try:
        mig.MIGRATIONS[5] = _temp_migration
        applied = mig.apply_migrations(engine)
        assert applied == [5], f"se esperaba [5], fue {applied}"
        assert len(applied_flag) == 1

        # Idempotencia: segunda corrida no aplica nada.
        applied2 = mig.apply_migrations(engine)
        assert applied2 == [], f"segunda corrida no debe aplicar nada, fue {applied2}"
        assert len(applied_flag) == 1

        # La columna se agregó y la versión quedó registrada.
        with engine.connect() as conn:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(t)")).fetchall()}
            assert "note" in cols
            assert mig.get_current_version(engine) == 5
    finally:
        mig.MIGRATIONS.clear()
        mig.MIGRATIONS.update(original)
        engine.dispose()
        _cleanup(path)
    print("   -> harness de migraciones funcional e idempotente")


def main() -> None:
    print("1) Round-trip de los nuevos campos de fecha...")
    test_roundtrip()
    print("2) Harness de migraciones funcional e idempotente (uso futuro)...")
    test_migration_harness_is_functional_and_idempotent()
    print("\nDATE FIELDS TEST OK")


if __name__ == "__main__":
    main()
