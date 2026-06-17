"""High-level building blocks: an :class:`App` runloop and reusable widgets.

This is the "let creativity run wild" layer. Compose widgets onto a surface and
let the App route events to them::

    from launchpad import App, Toggle, Momentary, RadioGroup, color

    app = App()
    Toggle(app, 0, 1, on_color=color.GREEN, on_change=lambda w: print(w.state))
    Momentary(app, 1, 1, on_press=lambda w: fire_thing())
    RadioGroup(app, cells=[(x, 8) for x in range(8)],
               on_select=lambda i: switch_page(i))
    app.run()
"""

from __future__ import annotations

from typing import Callable, Iterable, Sequence

from .color import AMBER, GREEN, OFF, RED, Color
from .device import ButtonEvent, Launchpad


class Widget:
    """Base class. A widget owns a set of coordinates and reacts to events."""

    def __init__(self, app: "App"):
        self.app = app
        app.add(self)

    @property
    def lp(self) -> Launchpad:
        return self.app.lp

    def cells(self) -> Iterable[tuple[int, int]]:
        raise NotImplementedError

    def contains(self, x: int, y: int) -> bool:
        return (x, y) in set(self.cells())

    def draw(self) -> None:  # pragma: no cover - hardware side effect
        pass

    def handle(self, ev: ButtonEvent) -> None:  # pragma: no cover
        pass


class Button(Widget):
    """A single momentary cell that fires on press and lights while held."""

    def __init__(self, app, x, y, color: Color = GREEN,
                 on_press: Callable[["Button"], None] | None = None):
        self.x, self.y = x, y
        self.color = color
        self._on_press = on_press
        super().__init__(app)

    def cells(self):
        return [(self.x, self.y)]

    def draw(self):
        self.lp.set(self.x, self.y, self.color)

    def handle(self, ev: ButtonEvent):
        if ev.pressed and self._on_press:
            self._on_press(self)


class Momentary(Widget):
    """Lights bright while held, dim otherwise; fires on press and release."""

    def __init__(self, app, x, y, color: Color = AMBER, idle: Color = OFF,
                 on_press=None, on_release=None):
        self.x, self.y = x, y
        self.color, self.idle = color, idle
        self._on_press, self._on_release = on_press, on_release
        super().__init__(app)

    def cells(self):
        return [(self.x, self.y)]

    def draw(self):
        self.lp.set(self.x, self.y, self.idle)

    def handle(self, ev: ButtonEvent):
        if ev.pressed:
            self.lp.set(self.x, self.y, self.color)
            if self._on_press:
                self._on_press(self)
        else:
            self.lp.set(self.x, self.y, self.idle)
            if self._on_release:
                self._on_release(self)


class Toggle(Widget):
    """A latching on/off button."""

    def __init__(self, app, x, y, on_color: Color = GREEN, off_color: Color = OFF,
                 state: bool = False, on_change: Callable[["Toggle"], None] | None = None):
        self.x, self.y = x, y
        self.on_color, self.off_color = on_color, off_color
        self.state = state
        self._on_change = on_change
        super().__init__(app)

    def cells(self):
        return [(self.x, self.y)]

    def draw(self):
        self.lp.set(self.x, self.y, self.on_color if self.state else self.off_color)

    def handle(self, ev: ButtonEvent):
        if ev.pressed:
            self.state = not self.state
            self.draw()
            if self._on_change:
                self._on_change(self)


class RadioGroup(Widget):
    """A row/column of cells where exactly one is selected at a time."""

    def __init__(self, app, cells: Sequence[tuple[int, int]],
                 selected: int = 0, on_color: Color = GREEN, off_color: Color = RED,
                 on_select: Callable[[int], None] | None = None):
        self._cells = list(cells)
        self.selected = selected
        self.on_color, self.off_color = on_color, off_color
        self._on_select = on_select
        super().__init__(app)

    def cells(self):
        return self._cells

    def draw(self):
        for i, (x, y) in enumerate(self._cells):
            self.lp.set(x, y, self.on_color if i == self.selected else self.off_color)

    def handle(self, ev: ButtonEvent):
        if not ev.pressed:
            return
        idx = self._cells.index((ev.x, ev.y))
        if idx != self.selected:
            self.selected = idx
            self.draw()
            if self._on_select:
                self._on_select(idx)


class ColorCycle(Widget):
    """A cell that steps through a palette on each press."""

    def __init__(self, app, x, y, palette: Sequence[Color],
                 index: int = 0, on_change: Callable[["ColorCycle"], None] | None = None):
        self.x, self.y = x, y
        self.palette = list(palette)
        self.index = index
        self._on_change = on_change
        super().__init__(app)

    @property
    def color(self) -> Color:
        return self.palette[self.index]

    def cells(self):
        return [(self.x, self.y)]

    def draw(self):
        self.lp.set(self.x, self.y, self.color)

    def handle(self, ev: ButtonEvent):
        if ev.pressed:
            self.index = (self.index + 1) % len(self.palette)
            self.draw()
            if self._on_change:
                self._on_change(self)


class App:
    """Owns a :class:`Launchpad`, a list of widgets, and the event router."""

    def __init__(self, lp: Launchpad | None = None, **launchpad_kwargs):
        self.lp = lp or Launchpad(**launchpad_kwargs)
        self.widgets: list[Widget] = []
        self.lp.on(self._route)

    def add(self, widget: Widget) -> Widget:
        self.widgets.append(widget)
        if self.lp.connected:
            widget.draw()
        return widget

    def redraw(self) -> None:
        for w in self.widgets:
            w.draw()

    def _route(self, ev: ButtonEvent) -> None:
        for w in self.widgets:
            if w.contains(ev.x, ev.y):
                w.handle(ev)

    def run(self) -> None:
        self.redraw()
        self.lp.run()
