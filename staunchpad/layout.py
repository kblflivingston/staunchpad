"""Coordinate system <-> MK2 note/CC mapping (Session layout).

This library uses one friendly coordinate system, origin top-left::

        x: 0   1   2   3   4   5   6   7      8
      y ┌───────────────────────────────┐
      0 │  ●   ●   ●   ●   ●   ●   ●   ●  │        <- top "mode" buttons (CC 104..111)
        ├───────────────────────────────┤  ┌───┐
      1 │  □   □   □   □   □   □   □   □  │  │ ● │  <- scene buttons (x = 8)
      2 │  □   □   □   □   □   □   □   □  │  │ ● │
      …                                     …
      8 │  □   □   □   □   □   □   □   □  │  │ ● │
        └───────────────────────────────┘  └───┘

The MK2 itself numbers grid notes "decimally" in Session layout: bottom-left = 11,
``note = row*10 + col`` with row 1 at the *bottom* and column 9 = scene buttons.
We hide that here so y always increases downward and x rightward.
"""

from __future__ import annotations

from .protocol import (LAYOUT_SESSION, LAYOUT_USER1, LAYOUT_USER2,  # re-exports
                       TOP_CC_FIRST)

__all__ = ["LAYOUT_SESSION", "LAYOUT_USER1", "LAYOUT_USER2",
           "xy_to_midi", "midi_to_xy", "is_valid", "all_coords",
           "column_index", "row_index"]


def is_valid(x: int, y: int) -> bool:
    """True if (x, y) addresses a real button/LED (the top-right corner doesn't)."""
    if y == 0:
        return 0 <= x <= 7              # top mode buttons
    if 1 <= y <= 8:
        return 0 <= x <= 8             # grid (0..7) + scene button (8)
    return False


def xy_to_midi(x: int, y: int) -> tuple[str, int]:
    """Map (x, y) to ``("cc", number)`` or ``("note", number)`` (Session layout)."""
    if not is_valid(x, y):
        raise ValueError(f"({x}, {y}) is not a valid Launchpad coordinate")
    if y == 0:
        return ("cc", TOP_CC_FIRST + x)
    row = 9 - y          # y=1 (top) -> row 8, y=8 (bottom) -> row 1
    col = x + 1          # x=0 -> col 1 ... x=8 -> col 9 (scene)
    return ("note", row * 10 + col)


def midi_to_xy(kind: str, number: int) -> tuple[int, int] | None:
    """Inverse of :func:`xy_to_midi`. Returns ``None`` for anything off-surface."""
    if kind == "cc":
        if TOP_CC_FIRST <= number <= TOP_CC_FIRST + 7:
            return (number - TOP_CC_FIRST, 0)
        return None
    if kind == "note":
        row, col = divmod(number, 10)
        if 1 <= row <= 8 and 1 <= col <= 9:
            return (col - 1, 9 - row)
        return None
    raise ValueError(f"kind must be 'cc' or 'note', got {kind!r}")


def column_index(x: int) -> int:
    """SysEx column number (0..8, left to right) for our x."""
    if not 0 <= x <= 8:
        raise ValueError("x must be 0..8")
    return x


def row_index(y: int) -> int:
    """SysEx row number (0..8, bottom to top) for our y (0 = top buttons row)."""
    if not 0 <= y <= 8:
        raise ValueError("y must be 0..8")
    return 8 - y


def all_coords() -> list[tuple[int, int]]:
    """Every addressable coordinate: top row, then grid rows with scene buttons."""
    coords = [(x, 0) for x in range(8)]
    for y in range(1, 9):
        coords += [(x, y) for x in range(9)]
    return coords
