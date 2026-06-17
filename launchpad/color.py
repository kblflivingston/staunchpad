"""Colour model for the legacy Launchpad.

The legacy Launchpad has **no RGB**. Each LED is one red element and one green
element, each with four brightness levels (0..3). The colour you want is packed
into the *velocity* byte of a note (or the *value* byte of a CC):

    velocity = (green << 4) | red | flags

``red`` occupies bits 0-1, ``green`` bits 4-5. Bits 2-3 are double-buffer
"flags" that decide what happens to the off-screen buffer (used for flashing and
flicker-free scene swaps). See PRM pp.12-16.

On the *original* Launchpad the usable palette is essentially red / amber /
green plus a couple of orange/yellow shades; on the S the separation is cleaner.
"""

from __future__ import annotations

from dataclasses import dataclass

# Double-buffer flag bits packed into the colour byte (PRM p.16).
FLAG_IGNORE = 0x00  # touch only the currently-addressed buffer
FLAG_CLEAR = 0x08   # set this buffer, clear the other -> flashes in flash mode
FLAG_COPY = 0x0C    # write to *both* buffers; the safe default (matches PRM fig.4)


@dataclass(frozen=True)
class Color:
    """A Launchpad colour: ``red`` and ``green`` each 0..3."""

    red: int = 0
    green: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.red <= 3 or not 0 <= self.green <= 3:
            raise ValueError(f"red/green must be 0..3, got {self.red},{self.green}")

    def velocity(self, flag: int = FLAG_COPY) -> int:
        """Pack into a MIDI velocity/value byte. ``flag`` is one of ``FLAG_*``."""
        return (self.green << 4) | self.red | flag

    @classmethod
    def from_velocity(cls, velocity: int) -> "Color":
        """Recover the colour from a velocity byte, discarding the flag bits."""
        return cls(red=velocity & 0x03, green=(velocity >> 4) & 0x03)

    def scaled(self, level: float) -> "Color":
        """Return this colour dimmed/brightened by ``level`` in 0..1 (rounded)."""
        level = max(0.0, min(1.0, level))
        return Color(round(self.red * level), round(self.green * level))

    def __bool__(self) -> bool:
        return self.red > 0 or self.green > 0


# --- named palette ----------------------------------------------------------
OFF = Color(0, 0)

RED = Color(3, 0)
RED_MED = Color(2, 0)
RED_LOW = Color(1, 0)

GREEN = Color(0, 3)
GREEN_MED = Color(0, 2)
GREEN_LOW = Color(0, 1)

AMBER = Color(3, 3)
AMBER_LOW = Color(1, 1)

ORANGE = Color(3, 1)   # red-leaning
YELLOW = Color(2, 3)   # green-leaning
LIME = Color(1, 3)

#: Name -> Color, handy for config files and the soundboard example.
NAMED: dict[str, Color] = {
    "off": OFF,
    "red": RED, "red_med": RED_MED, "red_low": RED_LOW,
    "green": GREEN, "green_med": GREEN_MED, "green_low": GREEN_LOW,
    "amber": AMBER, "amber_low": AMBER_LOW,
    "orange": ORANGE, "yellow": YELLOW, "lime": LIME,
}


def parse(value) -> Color:
    """Coerce a name, ``[red, green]`` pair, or :class:`Color` into a Color."""
    if isinstance(value, Color):
        return value
    if isinstance(value, str):
        try:
            return NAMED[value.lower()]
        except KeyError:
            raise ValueError(f"unknown colour name: {value!r}")
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return Color(int(value[0]), int(value[1]))
    raise ValueError(f"cannot interpret {value!r} as a colour")
