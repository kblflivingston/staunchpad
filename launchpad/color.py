"""Colour model for the Launchpad MK2.

The MK2 lights LEDs two ways (PRM p.5, p.11-12):

* **Palette** — a velocity/value byte 0..127 picks one of 128 preset colours
  (0 = off). One MIDI message per LED; this is also the only mode that supports
  hardware **flashing** and **pulsing**.
* **RGB** — a SysEx message gives explicit red/green/blue, each 0..63, for any
  of ~262 000 colours. Exact, but cannot flash/pulse and is SysEx-only.

A :class:`Color` is either a palette index *or* an RGB triple. Build them with
:func:`palette` / :func:`rgb`, or just pass an ``int`` (palette), ``"name"``,
``"#rrggbb"``, or ``[r, g, b]`` anywhere a colour is expected.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Color:
    """A palette colour (``index``) or an RGB colour (``rgb``). Exactly one."""

    index: int | None = None
    rgb: tuple[int, int, int] | None = None

    def __post_init__(self) -> None:
        if (self.index is None) == (self.rgb is None):
            raise ValueError("Color needs exactly one of index or rgb")
        if self.index is not None and not 0 <= self.index <= 127:
            raise ValueError("palette index must be 0..127")
        if self.rgb is not None:
            if len(self.rgb) != 3 or any(not 0 <= v <= 63 for v in self.rgb):
                raise ValueError("rgb must be three values each 0..63")

    @property
    def is_rgb(self) -> bool:
        return self.rgb is not None

    def velocity(self) -> int:
        """The palette index for channel/CC messages. Errors for RGB colours."""
        if self.index is None:
            raise ValueError("RGB colours can't be sent as a velocity; use SysEx RGB")
        return self.index

    def __bool__(self) -> bool:
        if self.is_rgb:
            return any(self.rgb)
        return self.index != 0


def palette(index: int) -> Color:
    """A colour from the 128-entry preset palette (0 = off)."""
    return Color(index=index)


def rgb(r: int, g: int, b: int) -> Color:
    """An exact colour; each element 0..63."""
    return Color(rgb=(r, g, b))


# --- named palette colours (indices verified from the PRM examples) ---------
OFF = palette(0)
RED = palette(5)
ORANGE = palette(9)
YELLOW = palette(13)
GREEN = palette(21)
BLUE = palette(45)
PINK = palette(53)
PURPLE = palette(81)

# --- a few exact RGB conveniences (no palette guessing) ---------------------
WHITE = rgb(63, 63, 63)
CYAN = rgb(0, 63, 63)
AMBER = rgb(48, 20, 0)
RED_DIM = rgb(16, 0, 0)
GREEN_DIM = rgb(0, 16, 0)
BLUE_DIM = rgb(0, 0, 16)
AMBER_DIM = rgb(14, 5, 0)

#: Name -> Color, handy for config files and the soundboard example.
NAMED: dict[str, Color] = {
    "off": OFF, "red": RED, "orange": ORANGE, "yellow": YELLOW, "green": GREEN,
    "blue": BLUE, "pink": PINK, "purple": PURPLE, "white": WHITE, "cyan": CYAN,
    "amber": AMBER, "red_dim": RED_DIM, "green_dim": GREEN_DIM,
    "blue_dim": BLUE_DIM, "amber_dim": AMBER_DIM,
}


def parse(value) -> Color:
    """Coerce a Color, palette ``int``, ``"name"``, ``"#rrggbb"``, or ``[r,g,b]``."""
    if isinstance(value, Color):
        return value
    if isinstance(value, bool):  # guard: bool is an int subclass
        raise ValueError("cannot interpret a bool as a colour")
    if isinstance(value, int):
        return palette(value)
    if isinstance(value, str):
        s = value.strip().lower()
        if s.startswith("#") and len(s) == 7:
            r, g, b = (int(s[i:i + 2], 16) for i in (1, 3, 5))
            return rgb(r >> 2, g >> 2, b >> 2)  # 0..255 -> 0..63
        try:
            return NAMED[s]
        except KeyError:
            raise ValueError(f"unknown colour name: {value!r}")
    if isinstance(value, (list, tuple)) and len(value) == 3:
        return rgb(int(value[0]), int(value[1]), int(value[2]))
    raise ValueError(f"cannot interpret {value!r} as a colour")
