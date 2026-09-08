"""Test de la separación de audiencias activas/pasadas en el detalle.

Verifica que ``_split_hearings`` coloca las audiencias pendientes (futuras y
estado Programada/Diferida) en orden ascendente arriba, y las pasadas (hechas,
canceladas o ya vencidas) en orden descendente abajo, marcadas como ``is_past``.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from datetime import datetime  # noqa: E402

from ui.case_detail_view import _split_hearings  # noqa: E402


class _FakeHearing:
    def __init__(self, scheduled_at, status, hid):
        self.scheduled_at = scheduled_at
        self.status = status
        self.id = hid


def test_split_hearings_orders_active_then_past():
    now = datetime(2026, 8, 28, 12, 0)
    done_past = _FakeHearing(datetime(2026, 8, 1, 10, 0), "Completed", 1)
    missed_past = _FakeHearing(datetime(2026, 8, 27, 10, 0), "Scheduled", 2)
    upcoming_a = _FakeHearing(datetime(2026, 8, 29, 9, 0), "Scheduled", 3)
    upcoming_b = _FakeHearing(datetime(2026, 8, 30, 9, 0), "Deferred", 4)

    rows = _split_hearings(
        [done_past, missed_past, upcoming_a, upcoming_b], now=now
    )
    ids = [h.id for h, _ in rows]
    is_past = [past for _, past in rows]

    assert ids == [3, 4, 2, 1]
    assert is_past == [False, False, True, True]


if __name__ == "__main__":
    test_split_hearings_orders_active_then_past()
    print("HEARING SPLIT TEST OK")
