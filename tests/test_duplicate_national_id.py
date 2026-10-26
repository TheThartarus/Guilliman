"""Test de detección de cédula repetida entre expedientes activos."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import (  # noqa: E402
    CaseFileCreate,
    CaseFileService,
    DefendantCreate,
    DuplicateNationalIdItem,
    VictimCreate,
    WitnessCreate,
)
from db.database import dispose_engine, reset_session_factory  # noqa: E402


def test_duplicate_national_id_across_entities(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "dup_id.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        case_1 = service.create_case_file(CaseFileCreate(case_number="DI-1"))
        case_2 = service.create_case_file(CaseFileCreate(case_number="DI-2"))
        cedula = "V-12345678"

        # Sin personas con esa cédula, no hay duplicados.
        assert service.find_duplicate_national_id(cedula) == []

        service.add_defendant(
            case_1,
            DefendantCreate(full_name="Acusado Uno", national_id=cedula, status="Detenido"),
        )
        # Una persona con esa cédula: la consulta la devuelve (ella misma).
        dups = service.find_duplicate_national_id(cedula)
        assert len(dups) == 1
        assert dups[0].entity_type == "defendant"
        assert dups[0].case_number == "DI-1"

        # Excluyendo el propio expediente no hay otro con esa cédula.
        dups_excl = service.find_duplicate_national_id(cedula, exclude_case_file_id=case_1)
        assert dups_excl == []

        # Misma cédula como víctima en otro expediente: ahora hay dos.
        service.add_victim(
            case_2,
            VictimCreate(full_name="Víctima Dos", national_id=cedula),
        )

        dups = service.find_duplicate_national_id(cedula)
        assert len(dups) == 2
        types = {d.entity_type for d in dups}
        assert types == {"defendant", "victim"}
        assert all(isinstance(d, DuplicateNationalIdItem) for d in dups)
        assert all(d.national_id == cedula for d in dups)
        case_numbers = {d.case_number for d in dups}
        assert case_numbers == {"DI-1", "DI-2"}

        # Excluir el expediente 1: solo queda el de caso_2.
        dups_excl = service.find_duplicate_national_id(cedula, exclude_case_file_id=case_1)
        assert len(dups_excl) == 1
        assert dups_excl[0].entity_type == "victim"
        assert dups_excl[0].case_number == "DI-2"

        # Cédula vacía o nula no busca nada.
        assert service.find_duplicate_national_id("") == []
        assert service.find_duplicate_national_id("  ") == []
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()


def test_duplicate_national_id_includes_witness(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "dup_id_wit.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        case_1 = service.create_case_file(CaseFileCreate(case_number="DIW-1"))
        case_2 = service.create_case_file(CaseFileCreate(case_number="DIW-2"))
        cedula = "E-87654321"

        service.add_defendant(
            case_1, DefendantCreate(full_name="Acusado A", national_id=cedula)
        )
        service.add_witness(
            case_2, WitnessCreate(full_name="Testigo B", national_id=cedula)
        )

        dups = service.find_duplicate_national_id(cedula)
        assert len(dups) == 2
        types = {d.entity_type for d in dups}
        assert types == {"defendant", "witness"}
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()


def test_duplicate_national_id_ignores_archived_cases(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("Guilliman_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir()
    db_path = str(tmp_path / "dup_id_arch.db")
    service = CaseFileService(db_path)
    service.init_db()
    try:
        case_1 = service.create_case_file(CaseFileCreate(case_number="DIA-1"))
        case_2 = service.create_case_file(CaseFileCreate(case_number="DIA-2"))
        cedula = "J-11223344"

        service.add_defendant(
            case_1, DefendantCreate(full_name="Acusado A", national_id=cedula)
        )
        service.add_defendant(
            case_2, DefendantCreate(full_name="Acusado B", national_id=cedula)
        )
        service.archive_case_file(case_1)

        dups = service.find_duplicate_national_id(cedula)
        assert len(dups) == 1
        assert dups[0].case_number == "DIA-2"
    finally:
        service.close()
        dispose_engine(db_path)
        reset_session_factory()
