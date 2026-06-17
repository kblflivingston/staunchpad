"""Low-level MIDI message builders for the legacy Novation Launchpad.

This module is the single source of truth for the wire protocol of the
*legacy* Launchpad generation (the original Launchpad, Launchpad S, and
Launchpad Mini). Everything here is pure: each function returns a ``list[int]``
of MIDI bytes (or a list of such lists). The :class:`~launchpad.device.Launchpad`
class is the only thing that actually puts these on the wire, which keeps the
protocol fully unit-testable without hardware.

All references below ("PRM p.N") point at Novation's *Launchpad S Programmer's
Reference Manual* v1.02, which documents the legacy protocol verbatim.

Channels (status bytes):
    0x90  Note On,  MIDI channel 1  -> grid + right "scene" buttons
    0x92  Note On,  MIDI channel 3  -> rapid LED update stream
    0xB0  Control Change, channel 1 -> top "mode" buttons + config commands
"""

from __future__ import annotations

# --- status bytes ----------------------------------------------------------
NOTE_ON_CH1 = 0x90  # grid + scene button LEDs / input
NOTE_ON_CH3 = 0x92  # rapid LED update
CC_CH1 = 0xB0       # top-row buttons + all configuration commands

# --- top-row "mode" buttons are CCs 104..111 (0x68..0x6F) -------------------
TOP_CC_FIRST = 0x68  # 104
TOP_CC_LAST = 0x6F   # 111

# --- the magic controller 0 commands (B0 00 xx) -----------------------------
RESET = 0x00            # B0 00 00 : all LEDs off, settings -> power-on defaults
LAYOUT_XY = 0x01        # B0 00 01 : X-Y note layout (this library's default)
LAYOUT_DRUM = 0x02      # B0 00 02 : drum-rack note layout
ALL_LEDS_LOW = 0x7D     # 125 : all LEDs amber, lowest intensity
ALL_LEDS_MED = 0x7E     # 126
ALL_LEDS_HIGH = 0x7F    # 127 : all LEDs amber, highest intensity

# Double-buffer / flash control values for controller 0 (PRM p.17).
BUF_SIMPLE = 0x20       # display & write buffer 0 (the default)
BUF_DISPLAY0_WRITE1 = 0x24
BUF_DISPLAY1_WRITE0 = 0x21
BUF_DISPLAY0_WRITE1_COPY = 0x34
BUF_DISPLAY1_WRITE0_COPY = 0x31
BUF_FLASH = 0x28        # write buffer 0, auto-swap display every 280 ms

# Brightness / "duty cycle" controllers (PRM p.10).
CC_BRIGHTNESS_LO = 0x1E  # 30, numerator < 9
CC_BRIGHTNESS_HI = 0x1F  # 31, numerator >= 9

# --- SysEx (Launchpad S / Mini only; the original Launchpad ignores these) --
NOVATION_ID = (0x00, 0x20, 0x29)
SYSEX_START = 0xF0
SYSEX_END = 0xF7
DEVICE_INQUIRY = [0xF0, 0x7E, 0x7F, 0x06, 0x01, 0xF7]
TEXT_SCROLL_CMD = 0x09   # F0 00 20 29 09 colour <text> F7
TEXT_LOOP_BIT = 0x40     # add to colour byte to loop the scroll


# ---------------------------------------------------------------------------
# configuration / command messages
# ---------------------------------------------------------------------------
def reset_msg() -> list[int]:
    """All LEDs off, every setting back to power-on defaults."""
    return [CC_CH1, 0x00, RESET]


def layout_msg(layout: int = LAYOUT_XY) -> list[int]:
    """Select the X-Y (``LAYOUT_XY``) or drum-rack (``LAYOUT_DRUM``) note map."""
    if layout not in (LAYOUT_XY, LAYOUT_DRUM):
        raise ValueError("layout must be LAYOUT_XY or LAYOUT_DRUM")
    return [CC_CH1, 0x00, layout]


def all_leds_on_msg(intensity: int = 2) -> list[int]:
    """Turn every LED amber. ``intensity`` 0..2 (low/med/high)."""
    if not 0 <= intensity <= 2:
        raise ValueError("intensity must be 0, 1 or 2")
    return [CC_CH1, 0x00, ALL_LEDS_LOW + intensity]


def buffer_msg(value: int) -> list[int]:
    """Raw double-buffer / flash control (one of the ``BUF_*`` constants)."""
    if not 0x20 <= value <= 0x3D:
        raise ValueError("buffer control value out of range 0x20..0x3D")
    return [CC_CH1, 0x00, value]


def brightness_msg(numerator: int, denominator: int) -> list[int]:
    """Set overall brightness as the fraction ``numerator/denominator``.

    Valid roughly between 1/18 and 6/1; the hardware default is 1/5. On the
    original Launchpad this is the "set duty cycle" command and very low
    fractions visibly flicker (that was, historically, the whole point).
    """
    if numerator < 1 or not 3 <= denominator <= 18:
        raise ValueError("denominator must be 3..18 and numerator >= 1")
    if numerator < 9:
        return [CC_CH1, CC_BRIGHTNESS_LO, 0x10 * (numerator - 1) + (denominator - 3)]
    return [CC_CH1, CC_BRIGHTNESS_HI, 0x10 * (numerator - 9) + (denominator - 3)]


# ---------------------------------------------------------------------------
# single-LED messages
# ---------------------------------------------------------------------------
def led_note_msg(note: int, velocity: int) -> list[int]:
    """Light a grid / scene-button LED. ``velocity`` is a packed colour byte."""
    return [NOTE_ON_CH1, note & 0x7F, velocity & 0x7F]


def led_cc_msg(cc: int, velocity: int) -> list[int]:
    """Light a top-row LED (``cc`` in 104..111). ``velocity`` is a colour byte."""
    return [CC_CH1, cc & 0x7F, velocity & 0x7F]


# ---------------------------------------------------------------------------
# rapid LED update (channel 3): note byte = LED A colour, velocity = LED B
# colour. PRM p.14. 80 LEDs -> 40 messages, in a fixed scan order.
# ---------------------------------------------------------------------------
def rapid_msgs(velocities: list[int]) -> list[list[int]]:
    """Pack a flat list of LED colour bytes into channel-3 update messages.

    ``velocities`` must follow the documented scan order (see
    :func:`launchpad.layout.rapid_order`) and have an even length (80 for a
    full surface refresh).
    """
    if len(velocities) % 2 != 0:
        raise ValueError("rapid update needs an even number of LED values")
    out = []
    for i in range(0, len(velocities), 2):
        out.append([NOTE_ON_CH3, velocities[i] & 0x7F, velocities[i + 1] & 0x7F])
    return out


# ---------------------------------------------------------------------------
# SysEx (Launchpad S / Mini only)
# ---------------------------------------------------------------------------
def device_inquiry_msg() -> list[int]:
    """Standard MIDI device-inquiry. Only an S/Mini replies; the original is mute."""
    return list(DEVICE_INQUIRY)


def text_scroll_msg(text: str, colour: int, loop: bool = False) -> list[int]:
    """Build a scrolling-text SysEx (S/Mini only).

    ``colour`` is a packed colour byte (see :mod:`launchpad.color`). Embed bytes
    1..7 inside ``text`` via the control characters ``\x01``..``\x07`` to change
    scroll speed mid-string (1 = slowest, 7 = fastest, default 4).
    """
    c = (colour & 0x7F) | (TEXT_LOOP_BIT if loop else 0)
    body = [b & 0x7F for b in text.encode("ascii", "replace")]
    return [SYSEX_START, *NOVATION_ID, TEXT_SCROLL_CMD, c, *body, SYSEX_END]


def text_stop_msg() -> list[int]:
    """Stop any in-progress scrolling text."""
    return [SYSEX_START, *NOVATION_ID, TEXT_SCROLL_CMD, 0x00, SYSEX_END]
