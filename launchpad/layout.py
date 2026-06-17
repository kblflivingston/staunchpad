"""Coordinate system <-> MIDI mapping for the X-Y layout.

This library uses a single, friendly coordinate system::

        x: 0   1   2   3   4   5   6   7      8
      y ┌───────────────────────────────┐
      0 │  ●   ●   ●   ●   ●   ●   ●   ●  │        <- top "mode" buttons (CC)
        ├───────────────────────────────┤  ┌───┐
      1 │  □   □   □   □   □   □   □   □  │  │ ● │  <- scene button (note)
      2 │  □   □   □   □   □   □   □   □  │  │ ● │
      …                                     …
      8 │  □   □   □   □   □   □   □   □  │  │ ● │
        └───────────────────────────────┘  └───┘

* ``y == 0`` is the top row of 8 round "mode" buttons -> Control Change 104..111.
* ``y`` 1..8, ``x`` 0..7 is the 8x8 grid -> Note On, note = (y-1)*16 + x.
* ``x == 8``, ``y`` 1..8 are the right-hand "scene" buttons -> note = (y-1)*16 + 8.
* The top-right corner (x=8, y=0) does not exist on the hardware.

All of this assumes the **X-Y layout** is active (the library selects it on
connect). Drum-rack users should drive the device with raw note APIs instead.
"""

from __future__ import annotations

from .protocol import LAYOUT_DRUM, LAYOUT_XY, TOP_CC_FIRST  # re-export for convenience

__all__ = ["LAYOUT_XY", "LAYOUT_DRUM", "xy_to_midi", "midi_to_xy", "rapid_order",
           "is_valid", "all_coords"]


def is_valid(x: int, y: int) -> bool:
    """True if (x, y) addresses a real button/LED."""
    if y == 0:
        return 0 <= x <= 7              # top mode buttons
    if 1 <= y <= 8:
        return 0 <= x <= 8             # grid (0..7) + scene button (8)
    return False


def xy_to_midi(x: int, y: int) -> tuple[str, int]:
    """Map (x, y) to ``("cc", number)`` or ``("note", number)``."""
    if not is_valid(x, y):
        raise ValueError(f"({x}, {y}) is not a valid Launchpad coordinate")
    if y == 0:
        return ("cc", TOP_CC_FIRST + x)
    return ("note", (y - 1) * 16 + x)


def midi_to_xy(kind: str, number: int) -> tuple[int, int] | None:
    """Inverse of :func:`xy_to_midi`. Returns ``None`` for anything off-surface."""
    if kind == "cc":
        if TOP_CC_FIRST <= number <= TOP_CC_FIRST + 7:
            return (number - TOP_CC_FIRST, 0)
        return None
    if kind == "note":
        x, row = number % 16, number // 16
        y = row + 1
        if 1 <= y <= 8 and 0 <= x <= 8:
            return (x, y)
        return None
    raise ValueError(f"kind must be 'cc' or 'note', got {kind!r}")


def all_coords() -> list[tuple[int, int]]:
    """Every addressable coordinate, top row first then grid rows."""
    coords = [(x, 0) for x in range(8)]
    for y in range(1, 9):
        coords += [(x, y) for x in range(9)]
    return coords


def rapid_order() -> list[tuple[int, int]]:
    """The 80 coordinates in the exact order the rapid-update stream expects.

    Grid horizontally then vertically (64), then the 8 scene buttons, then the
    8 top mode buttons (PRM p.14).
    """
    order: list[tuple[int, int]] = []
    for y in range(1, 9):                 # 64 grid LEDs, row by row
        order += [(x, y) for x in range(8)]
    order += [(8, y) for y in range(1, 9)]  # 8 scene buttons
    order += [(x, 0) for x in range(8)]     # 8 top mode buttons
    return order
