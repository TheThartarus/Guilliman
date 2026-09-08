"""
Bump de versión de Guilliman.

Uso:
    python bump.py            # interactivo (elige patch/minor/major)
    python bump.py patch      # directo, sin preguntar
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

VERSION_FILE = Path(__file__).resolve().parent / "version.py"

# ── Helpers ────────────────────────────────────────────────────────────

_VERSION_RE = re.compile(r'__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"')


def _read_version() -> tuple[int, int, int]:
    text = VERSION_FILE.read_text(encoding="utf-8")
    m = _VERSION_RE.search(text)
    if m is None:
        sys.exit("No se encontró __version__ en version.py")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _write_version(major: int, minor: int, patch: int) -> None:
    text = VERSION_FILE.read_text(encoding="utf-8")
    text = _VERSION_RE.sub(f'__version__ = "{major}.{minor}.{patch}"', text)
    # Actualizar fecha de compilación
    from datetime import date

    today = date.today().isoformat()
    text = re.sub(
        r'__build_date__\s*=\s*"[^"]*"',
        f'__build_date__ = "{today}"',
        text,
    )
    VERSION_FILE.write_text(text, encoding="utf-8")


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, cwd=Path(__file__).resolve().parent)


# ── Main ───────────────────────────────────────────────────────────────

def main() -> None:
    major, minor, patch = _read_version()
    current = f"{major}.{minor}.{patch}"

    # Determinar tipo de bump
    if len(sys.argv) > 1:
        bump = sys.argv[1].strip().lower()
    else:
        print(f"Versión actual: {current}\n")
        print("  1) patch  (1.0.0 → 1.0.1)  — correcciones")
        print("  2) minor  (1.0.0 → 1.1.0)  — nuevas funcionalidades")
        print("  3) major  (1.0.0 → 2.0.0)  — cambios incompatibles\n")
        choice = input("¿Qué tipo de bump? [1/2/3]: ").strip()
        bump = {"1": "patch", "2": "minor", "3": "major"}.get(choice, "")

    if bump == "patch":
        patch += 1
    elif bump == "minor":
        minor += 1
        patch = 0
    elif bump == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        sys.exit(f"Tipo inválido: {bump!r}  (usa: patch, minor, major)")

    new_version = f"{major}.{minor}.{patch}"
    tag = f"v{new_version}"

    print(f"\n{current} → {new_version}")

    _write_version(major, minor, patch)

    _run(["git", "add", str(VERSION_FILE)])
    _run(["git", "commit", "-m", f"chore(release): bump version to {new_version}"])
    _run(["git", "tag", tag])

    print(f"\nCommit creado y tag {tag} generado.")


if __name__ == "__main__":
    main()
