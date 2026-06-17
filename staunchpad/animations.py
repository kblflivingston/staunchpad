"""Passive ambient animations for chosen regions of the grid.

Pick a region with :func:`rect` / :func:`row` / :func:`col` / :func:`cells`, hand
an :class:`Animation` to :meth:`Console.animate`, and the console's render loop
will paint just those cells each frame (diffed, so only changed LEDs are sent).

Animations use RGB so they fade smoothly. Keep animation regions and your action
buttons on *separate* cells — the console paints them independently.
"""

from __future__ import annotations

import math
import random
from typing import Iterable

from .color import Color, rgb

TWO_PI = math.pi * 2


# --- region helpers ---------------------------------------------------------
def rect(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
    """All cells in the inclusive rectangle (x0,y0)..(x1,y1)."""
    xs = range(min(x0, x1), max(x0, x1) + 1)
    ys = range(min(y0, y1), max(y0, y1) + 1)
    return [(x, y) for y in ys for x in xs]


def row(y: int) -> list[tuple[int, int]]:
    return [(x, y) for x in range(8)]


def col(x: int) -> list[tuple[int, int]]:
    return [(x, y) for y in range(1, 9)]


def cells(seq: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    return list(seq)


def hsv(h: float, s: float = 1.0, v: float = 1.0) -> Color:
    """HSV (h in 0..1) -> an MK2 RGB Color (each element 0..63)."""
    i = int(h * 6) % 6
    f = h * 6 - int(h * 6)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r, g, b = [(v, t, p), (q, v, p), (p, v, t),
               (p, q, v), (t, p, v), (v, p, q)][i]
    return rgb(round(r * 63), round(g * 63), round(b * 63))


# --- animations -------------------------------------------------------------
class Animation:
    """Base class. Override :meth:`frame` to return ``{(x, y): Color}`` for time ``t``."""

    def __init__(self, region: Iterable[tuple[int, int]]):
        self.region = list(region)
        self._last: dict[tuple[int, int], Color] = {}

    def frame(self, t: float) -> dict[tuple[int, int], Color]:
        raise NotImplementedError


class Breathe(Animation):
    """The whole region fades in and out together."""

    def __init__(self, region, color: Color = rgb(0, 0, 40), period: float = 4.0,
                 low: float = 0.04, high: float = 1.0):
        super().__init__(region)
        self.color, self.period, self.low, self.high = color, period, low, high

    def frame(self, t):
        s = 0.5 + 0.5 * math.sin(TWO_PI * t / self.period)
        level = self.low + (self.high - self.low) * s
        c = self.color.dimmed(level)
        return {cell: c for cell in self.region}


class Twinkle(Animation):
    """Each cell shimmers on its own random phase, like quiet stars."""

    def __init__(self, region, palette=None, period: float = 2.6,
                 low: float = 0.0, high: float = 1.0):
        super().__init__(region)
        palette = palette or [rgb(0, 10, 24), rgb(0, 20, 40), rgb(8, 0, 28)]
        self.period, self.low, self.high = period, low, high
        self._phase = {cell: random.random() for cell in self.region}
        self._color = {cell: random.choice(palette) for cell in self.region}

    def frame(self, t):
        out = {}
        for cell in self.region:
            s = 0.5 + 0.5 * math.sin(TWO_PI * (t / self.period + self._phase[cell]))
            level = self.low + (self.high - self.low) * s
            out[cell] = self._color[cell].dimmed(level)
        return out


class RainbowWave(Animation):
    """A hue gradient that drifts across the region."""

    def __init__(self, region, period: float = 6.0, spread: float = 1.0,
                 value: float = 0.7):
        super().__init__(region)
        self.period, self.spread, self.value = period, spread, value
        xs = [c[0] for c in self.region] or [0]
        self._span = (max(xs) - min(xs)) or 1
        self._x0 = min(xs)

    def frame(self, t):
        out = {}
        for (x, y) in self.region:
            h = ((x - self._x0) / self._span * self.spread + t / self.period) % 1.0
            out[(x, y)] = hsv(h, 1.0, self.value)
        return out
