"""The :class:`Launchpad` device handle: I/O, LEDs, scenes, and events."""

from __future__ import annotations

import threading
import time
from typing import Callable, Iterable, Mapping

import mido

from . import layout as L
from . import protocol as P
from .color import OFF, Color, FLAG_CLEAR, FLAG_COPY, parse as parse_color

Handler = Callable[["ButtonEvent"], None]


class LaunchpadNotFound(RuntimeError):
    """Raised when no Launchpad MIDI port can be located."""


class ButtonEvent:
    """A button press or release.

    Attributes:
        x, y:      surface coordinates (see :mod:`launchpad.layout`).
        pressed:   ``True`` on press, ``False`` on release.
        velocity:  raw MIDI velocity/value (127 on press, 0 on release).
        kind:      ``"note"`` (grid/scene) or ``"cc"`` (top row).
        number:    the raw MIDI note or CC number.
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
    """A connection to a legacy Launchpad.

    Open it directly (auto-detects the first port whose name contains
    ``name``)::

        lp = Launchpad()
        lp.set(0, 1, color.RED)

    or as a context manager, which resets the surface on the way out::

        with Launchpad() as lp:
            lp.fill(color.GREEN)
            lp.run()
    """

    def __init__(self, name: str = "Launchpad", layout: int = L.LAYOUT_XY,
                 auto_open: bool = True):
        self.name = name
        self._layout = layout
        self._out = None
        self._in = None
        self._global_handlers: list[Handler] = []
        # (x, y) -> list of (when, handler); when in {"press","release","both"}
        self._button_handlers: dict[tuple[int, int], list[tuple[str, Handler]]] = {}
        self._flashing = False
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
        self.reset()
        return self

    def close(self) -> None:
        try:
            if self._out:
                self.reset()
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
    def reset(self) -> None:
        """All LEDs off, settings back to defaults."""
        self._send(P.reset_msg())
        self._flashing = False

    def set_layout(self, layout: int) -> None:
        self._layout = layout
        self._send(P.layout_msg(layout))

    def all_on(self, intensity: int = 2) -> None:
        """Light every LED amber (a quick hardware sanity check)."""
        self._send(P.all_leds_on_msg(intensity))

    def set_brightness(self, numerator: int, denominator: int) -> None:
        """Scale overall brightness to the fraction ``numerator/denominator``."""
        self._send(P.brightness_msg(numerator, denominator))

    # -- single LED ---------------------------------------------------------
    def set(self, x: int, y: int, color, flag: int = FLAG_COPY) -> None:
        """Light the LED at (x, y). ``color`` may be a Color, name, or [r,g]."""
        color = parse_color(color)
        kind, number = L.xy_to_midi(x, y)
        vel = color.velocity(flag)
        if kind == "cc":
            self._send(P.led_cc_msg(number, vel))
        else:
            self._send(P.led_note_msg(number, vel))

    def off(self, x: int, y: int) -> None:
        self.set(x, y, OFF)

    def set_note(self, note: int, velocity: int) -> None:
        """Raw note LED (use with the drum-rack layout or custom maps)."""
        self._send(P.led_note_msg(note, velocity))

    def set_cc(self, cc: int, velocity: int) -> None:
        self._send(P.led_cc_msg(cc, velocity))

    # -- bulk -------------------------------------------------------------
    def fill(self, color) -> None:
        """Set the whole surface to one colour via a fast rapid update."""
        self.render({pos: color for pos in L.rapid_order()})

    def clear(self) -> None:
        self.reset()

    def render(self, grid: Mapping[tuple[int, int], object], flag: int = FLAG_COPY,
               fast: bool = True) -> None:
        """Paint the whole surface from a ``{(x, y): color}`` mapping.

        Missing coordinates default to off. With ``fast=True`` (default) this
        uses the channel-3 rapid-update stream (40 messages for all 80 LEDs);
        ``fast=False`` sends one message per LED (handy when debugging).
        """
        if fast:
            # A ch.1 message first resets the rapid cursor to the top-left.
            self._send(P.layout_msg(self._layout))
            vels = []
            for pos in L.rapid_order():
                c = grid.get(pos, OFF)
                vels.append(parse_color(c).velocity(flag))
            for msg in P.rapid_msgs(vels):
                self._send(msg)
        else:
            for x, y in L.rapid_order():
                self.set(x, y, grid.get((x, y), OFF), flag)

    # -- flashing -----------------------------------------------------------
    def begin_flash(self) -> None:
        """Enter hardware flash mode (display swaps every 280 ms)."""
        self._send(P.buffer_msg(P.BUF_FLASH))
        self._flashing = True

    def end_flash(self) -> None:
        self._send(P.buffer_msg(P.BUF_SIMPLE))
        self._flashing = False

    def flash(self, x: int, y: int, color) -> None:
        """Make one LED flash ``color``. Enters flash mode automatically.

        Other LEDs set with :meth:`set` stay solid while flash mode is on.
        Call :meth:`end_flash` to stop.
        """
        if not self._flashing:
            self.begin_flash()
        self.set(x, y, color, flag=FLAG_CLEAR)

    # -- double buffering ---------------------------------------------------
    def double_buffer(self) -> "DoubleBuffer":
        """Return a context manager for flicker-free scene swaps.

        ::

            with lp.double_buffer() as db:
                db.draw(scene_a)   # invisible
                db.swap()          # appears instantly
                db.draw(scene_b)
                db.swap()
        """
        return DoubleBuffer(self)

    # -- text (S / Mini only) ----------------------------------------------
    def scroll_text(self, text: str, color=Color(0, 3), loop: bool = False) -> None:
        """Scroll text across the pads. **Launchpad S/Mini only** (original ignores)."""
        self._send(P.text_scroll_msg(text, parse_color(color).velocity(FLAG_COPY), loop))

    def stop_text(self) -> None:
        self._send(P.text_stop_msg())

    # -- identity -----------------------------------------------------------
    def identify(self, timeout: float = 0.4) -> dict:
        """Probe the device. An S/Mini answers a device inquiry; the original
        stays silent, which is itself the tell.

        Returns a dict like ``{"model": "Launchpad S", "responds": True, ...}``.
        """
        self.identity = {"model": "original Launchpad (or no MIDI input)",
                         "responds": False, "raw": None}
        if not self._in:
            return self.identity
        self._inquiry_event.clear()
        self._inquiry_data = None
        self._send(P.device_inquiry_msg())
        if self._inquiry_event.wait(timeout) and self._inquiry_data:
            data = self._inquiry_data
            model = "Launchpad S / Mini (class-compliant)"
            self.identity = {"model": model, "responds": True, "raw": data}
        return self.identity

    # -- events -------------------------------------------------------------
    def on(self, handler: Handler) -> Handler:
        """Register a handler for *every* button event. Usable as a decorator."""
        self._global_handlers.append(handler)
        return handler

    def on_press(self, x: int, y: int) -> Callable[[Handler], Handler]:
        """Decorator: run the handler when (x, y) is pressed."""
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
        # device-inquiry reply (S/Mini): capture and signal identify()
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
                return None  # ignore config CCs echoed back
            return ButtonEvent(xy[0], xy[1], msg.value > 0, msg.value, "cc", msg.control)
        return None

    def run(self, poll: float = 0.05) -> None:
        """Block forever, dispatching events, until Ctrl-C."""
        if not self._in:
            raise RuntimeError(
                "No MIDI input port; cannot receive button events. "
                "(The original Launchpad needs Novation's USB driver to expose one.)"
            )
        try:
            while True:
                time.sleep(poll)
        except KeyboardInterrupt:
            pass


class DoubleBuffer:
    """Helper for :meth:`Launchpad.double_buffer`. Tracks which buffer is hidden."""

    def __init__(self, lp: Launchpad):
        self.lp = lp
        self._write_to_1 = True  # next draw goes to buffer 1 (hidden)

    def __enter__(self) -> "DoubleBuffer":
        # display buffer 0, write to buffer 1 (hidden)
        self.lp._send(P.buffer_msg(P.BUF_DISPLAY0_WRITE1))
        return self

    def draw(self, grid: Mapping[tuple[int, int], object]) -> None:
        """Draw a ``{(x, y): color}`` mapping into the *hidden* buffer."""
        from .color import FLAG_IGNORE
        for (x, y), c in grid.items():
            self.lp.set(x, y, c, flag=FLAG_IGNORE)

    def swap(self) -> None:
        """Reveal the hidden buffer instantly and start drawing the other."""
        if self._write_to_1:
            self.lp._send(P.buffer_msg(P.BUF_DISPLAY1_WRITE0))
        else:
            self.lp._send(P.buffer_msg(P.BUF_DISPLAY0_WRITE1))
        self._write_to_1 = not self._write_to_1

    def __exit__(self, *exc) -> None:
        self.lp._send(P.buffer_msg(P.BUF_SIMPLE))
