"""The :class:`Launchpad` device handle for the Launchpad MK2: I/O, LEDs,
flash/pulse, RGB, scenes, text, and button events."""

from __future__ import annotations

import threading
import time
from typing import Callable, Iterable, Mapping

import mido

from . import layout as L
from . import protocol as P
from .color import Color, OFF, parse as parse_color

Handler = Callable[["ButtonEvent"], None]


class LaunchpadNotFound(RuntimeError):
    """Raised when no Launchpad MIDI port can be located."""


class ButtonEvent:
    """A button press or release.

    Attributes:
        x, y:     surface coordinates (see :mod:`launchpad.layout`).
        pressed:  ``True`` on press, ``False`` on release.
        velocity: raw MIDI velocity/value (127 on press, 0 on release).
        kind:     ``"note"`` (grid/scene) or ``"cc"`` (top row).
        number:   the raw MIDI note or CC number.
    """

    __slots__ = ("x", "y", "pressed", "velocity", "kind", "number")

    def __init__(self, x, y, pressed, velocity, kind, number):
        self.x, self.y = x, y
        self.pressed = pressed
        self.velocity = velocity
        self.kind, self.number = kind, number

    @property
    def released(self) -> bool:
        return not self.pressed

    @property
    def pos(self) -> tuple[int, int]:
        return (self.x, self.y)

    def __repr__(self) -> str:
        what = "press" if self.pressed else "release"
        return f"<ButtonEvent ({self.x},{self.y}) {what}>"


def list_ports() -> dict[str, list[str]]:
    """Return ``{"inputs": [...], "outputs": [...]}`` of all MIDI ports."""
    return {"inputs": mido.get_input_names(), "outputs": mido.get_output_names()}


class Launchpad:
    """A connection to a Launchpad MK2.

    ::

        lp = Launchpad()                 # auto-detects the first "Launchpad" port
        lp.set(0, 1, color.RED)          # palette colour (1 MIDI message)
        lp.set(7, 8, color.rgb(0, 0, 63))# exact RGB (SysEx)
        lp.pulse(4, 4, color.GREEN)      # hardware pulse

        @lp.on_press(0, 0)
        def _(ev): print("pressed", ev)

        lp.run()
    """

    def __init__(self, name: str = "Launchpad", layout: int = P.LAYOUT_SESSION,
                 auto_open: bool = True):
        self.name = name
        self._layout = layout
        self._out = None
        self._in = None
        self._global_handlers: list[Handler] = []
        self._button_handlers: dict[tuple[int, int], list[tuple[str, Handler]]] = {}
        self._inquiry_event = threading.Event()
        self._inquiry_data: list[int] | None = None
        self.identity: dict | None = None
        if auto_open:
            self.open()

    # -- connection ---------------------------------------------------------
    @staticmethod
    def _match(names: Iterable[str], needle: str) -> str | None:
        needle = needle.lower()
        for n in names:
            if needle in n.lower():
                return n
        return None

    def open(self) -> "Launchpad":
        out_name = self._match(mido.get_output_names(), self.name)
        if not out_name:
            raise LaunchpadNotFound(
                f"No MIDI output matching {self.name!r}. "
                f"Available: {mido.get_output_names()}"
            )
        self._out = mido.open_output(out_name)
        in_name = self._match(mido.get_input_names(), self.name)
        if in_name:
            self._in = mido.open_input(in_name, callback=self._dispatch)
        self.set_layout(self._layout)
        self.clear()
        return self

    def close(self) -> None:
        try:
            if self._out:
                self.clear()
        finally:
            if self._in:
                self._in.close()
            if self._out:
                self._out.close()
            self._in = self._out = None

    def __enter__(self) -> "Launchpad":
        if self._out is None:
            self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    @property
    def connected(self) -> bool:
        return self._out is not None

    @property
    def has_input(self) -> bool:
        return self._in is not None

    # -- raw send -----------------------------------------------------------
    def _send(self, data: list[int]) -> None:
        if self._out is None:
            raise RuntimeError("Launchpad is not open")
        self._out.send(mido.Message.from_bytes(bytes(data)))

    def send_raw(self, data: list[int]) -> None:
        """Escape hatch: put arbitrary MIDI bytes on the wire."""
        self._send(data)

    # -- configuration ------------------------------------------------------
    def set_layout(self, layout: int) -> None:
        self._layout = layout
        self._send(P.layout_msg(layout))

    # -- single LED ---------------------------------------------------------
    def set(self, x: int, y: int, color) -> None:
        """Light the LED at (x, y). Accepts a Color, palette int, name, or [r,g,b]."""
        color = parse_color(color)
        kind, number = L.xy_to_midi(x, y)
        if color.is_rgb:
            self._send(P.set_led_rgb_msg(number, *color.rgb))
        elif kind == "cc":
            self._send(P.cc_msg(number, color.velocity(), P.CH_STATIC))
        else:
            self._send(P.note_msg(number, color.velocity(), P.CH_STATIC))

    def off(self, x: int, y: int) -> None:
        self.set(x, y, OFF)

    def set_note(self, note: int, velocity: int, channel: int = P.CH_STATIC) -> None:
        """Raw note LED (use with non-Session layouts or custom maps)."""
        self._send(P.note_msg(note, velocity, channel))

    def set_cc(self, cc: int, value: int, channel: int = P.CH_STATIC) -> None:
        self._send(P.cc_msg(cc, value, channel))

    # -- flash / pulse (palette colours only) -------------------------------
    def _palette_channel(self, x, y, color, channel, what):
        color = parse_color(color)
        if color.is_rgb:
            raise ValueError(f"{what} needs a palette colour, not RGB "
                             f"(the MK2 can't {what} arbitrary RGB)")
        kind, number = L.xy_to_midi(x, y)
        if kind == "cc":
            self._send(P.cc_msg(number, color.velocity(), channel))
        else:
            self._send(P.note_msg(number, color.velocity(), channel))

    def flash(self, x: int, y: int, color) -> None:
        """Flash between the LED's current colour and ``color`` (palette only).

        Set a base colour first with :meth:`set` to flash *between two colours*;
        otherwise it flashes between off and ``color``. Stop with :meth:`set`/:meth:`off`.
        """
        self._palette_channel(x, y, color, P.CH_FLASH, "flash")

    def pulse(self, x: int, y: int, color) -> None:
        """Pulse ``color`` (palette only). Stop with :meth:`set`/:meth:`off`."""
        self._palette_channel(x, y, color, P.CH_PULSE, "pulse")

    # -- bulk ---------------------------------------------------------------
    def clear(self) -> None:
        """Turn every LED off in a single message."""
        self._send(P.set_all_msg(0))

    def fill(self, color) -> None:
        """Light the whole surface one colour."""
        color = parse_color(color)
        if color.is_rgb:
            quads = [(L.xy_to_midi(x, y)[1], *color.rgb) for x, y in L.all_coords()]
            self._send(P.set_leds_rgb_msg(quads))
        else:
            self._send(P.set_all_msg(color.velocity()))

    def set_column(self, x: int, color) -> None:
        """Light a whole column one palette colour (x 0..8; 8 = scene buttons)."""
        c = parse_color(color)
        self._send(P.set_column_msg(L.column_index(x), c.velocity()))

    def set_row(self, y: int, color) -> None:
        """Light a whole row one palette colour (y 0 = top buttons .. 8 = bottom)."""
        c = parse_color(color)
        self._send(P.set_row_msg(L.row_index(y), c.velocity()))

    def render(self, grid: Mapping[tuple[int, int], object]) -> None:
        """Paint the whole surface from a ``{(x, y): color}`` mapping.

        Palette and RGB cells are batched into (at most) one SysEx message each,
        so a full 80-LED refresh is one or two messages. Missing cells are left
        untouched -- call :meth:`clear` first for a clean repaint.
        """
        pairs: list[tuple[int, int]] = []
        quads: list[tuple[int, int, int, int]] = []
        for (x, y), c in grid.items():
            c = parse_color(c)
            _, number = L.xy_to_midi(x, y)
            if c.is_rgb:
                quads.append((number, *c.rgb))
            else:
                pairs.append((number, c.velocity()))
        for chunk in _chunks(pairs, 80):
            self._send(P.set_leds_msg(chunk))
        for chunk in _chunks(quads, 80):
            self._send(P.set_leds_rgb_msg(chunk))

    # -- text ---------------------------------------------------------------
    def scroll_text(self, text: str, color=Color(index=21), loop: bool = False) -> None:
        """Scroll ``text`` across the pads (palette colour). Embed bytes 1..7 for speed."""
        self._send(P.scroll_text_msg(text, parse_color(color).velocity(), loop))

    def stop_text(self) -> None:
        self._send(P.scroll_stop_msg())

    # -- identity -----------------------------------------------------------
    def identify(self, timeout: float = 0.5) -> dict:
        """Probe the device with a MIDI device inquiry and parse the reply."""
        self.identity = {"model": "unknown", "responds": False,
                         "firmware": None, "raw": None}
        if not self._in:
            return self.identity
        self._inquiry_event.clear()
        self._inquiry_data = None
        self._send(P.device_inquiry_msg())
        if self._inquiry_event.wait(timeout) and self._inquiry_data:
            data = self._inquiry_data  # excludes F0/F7
            # reply: 7E <id> 06 02 00 20 29 69 00 00 00 <fw0..3>
            is_mk2 = list(data[4:8]) == [0x00, 0x20, 0x29, 0x69]
            fw = list(data[-4:]) if len(data) >= 4 else None
            self.identity = {"model": "Launchpad MK2" if is_mk2 else "unknown Launchpad",
                             "responds": True, "firmware": fw, "raw": data}
        return self.identity

    # -- events -------------------------------------------------------------
    def on(self, handler: Handler) -> Handler:
        """Register a handler for *every* button event. Usable as a decorator."""
        self._global_handlers.append(handler)
        return handler

    def on_press(self, x: int, y: int) -> Callable[[Handler], Handler]:
        return self._register(x, y, "press")

    def on_release(self, x: int, y: int) -> Callable[[Handler], Handler]:
        return self._register(x, y, "release")

    def on_button(self, x: int, y: int) -> Callable[[Handler], Handler]:
        return self._register(x, y, "both")

    def _register(self, x, y, when) -> Callable[[Handler], Handler]:
        def deco(fn: Handler) -> Handler:
            self._button_handlers.setdefault((x, y), []).append((when, fn))
            return fn
        return deco

    def _dispatch(self, msg: "mido.Message") -> None:
        if msg.type == "sysex":
            self._inquiry_data = list(msg.data)
            self._inquiry_event.set()
            return
        ev = self._parse(msg)
        if ev is None:
            return
        for h in self._global_handlers:
            h(ev)
        for when, fn in self._button_handlers.get((ev.x, ev.y), ()):
            if when == "both" or (when == "press") == ev.pressed:
                fn(ev)

    @staticmethod
    def _parse(msg: "mido.Message") -> "ButtonEvent | None":
        if msg.type in ("note_on", "note_off"):
            xy = L.midi_to_xy("note", msg.note)
            if xy is None:
                return None
            pressed = msg.type == "note_on" and msg.velocity > 0
            return ButtonEvent(xy[0], xy[1], pressed, msg.velocity, "note", msg.note)
        if msg.type == "control_change":
            xy = L.midi_to_xy("cc", msg.control)
            if xy is None:
                return None
            return ButtonEvent(xy[0], xy[1], msg.value > 0, msg.value, "cc", msg.control)
        return None

    def run(self, poll: float = 0.05) -> None:
        """Block forever, dispatching events, until Ctrl-C."""
        if not self._in:
            raise RuntimeError("No MIDI input port; cannot receive button events.")
        try:
            while True:
                time.sleep(poll)
        except KeyboardInterrupt:
            pass


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]
