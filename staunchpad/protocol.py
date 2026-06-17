"""Low-level MIDI / SysEx message builders for the Novation Launchpad MK2.

This module is the single source of truth for the wire protocol. Everything
here is pure: each function returns a ``list[int]`` of MIDI bytes. The
:class:`~staunchpad.device.Launchpad` class is the only thing that puts these on
the wire, which keeps the protocol fully unit-testable without hardware.

References ("PRM p.N") point at Novation's *Launchpad MK2 Programmer's Reference
Manual* v1.03.

The MK2 has 80 addressable LEDs:
  * 8x8 grid + the 8 right-hand "scene" buttons -> Note On messages
  * 8 top round "mode" buttons                  -> Control Change 104..111

Note/CC numbers use the *Session* layout (PRM p.6-7): a decimal scheme where
``note = row*10 + column``, row 1 = bottom, column 1 = left, and column 9 = the
right-hand scene buttons. So bottom-left grid = 11, top-left = 81, top-right
grid = 88, scene buttons = 19,29,...,89.

Channels carry meaning (PRM p.8-10):
  * channel 1 -> set a static colour
  * channel 2 -> flash between the current colour and the sent colour
  * channel 3 -> pulse the sent colour
Sending a channel-1 message stops a flash/pulse.
"""

from __future__ import annotations

# --- SysEx framing (PRM p.15) ----------------------------------------------
SYSEX_START = 0xF0
SYSEX_END = 0xF7
#: Every Launchpad MK2 SysEx command starts with this 6-byte header.
HEADER = (0x00, 0x20, 0x29, 0x02, 0x18)  # Novation id (00 20 29) + MK2 (02 18)

# --- SysEx command bytes (the 6th byte; PRM p.15-16) -----------------------
CMD_SET_LED = 0x0A          # <LED> <colour>            (repeat up to 80)
CMD_SET_LED_RGB = 0x0B      # <LED> <r> <g> <b>         (repeat up to 80)
CMD_SET_COLUMN = 0x0C       # <column 0-8> <colour>     (repeat up to 9)
CMD_SET_ROW = 0x0D          # <row 0-8> <colour>        (repeat up to 9)
CMD_SET_ALL = 0x0E          # <colour>
CMD_FLASH_LED = 0x23        # <mode=0> <LED> <colour>   (repeat up to 80)
CMD_PULSE_LED = 0x28        # <mode=0> <LED> <colour>   (repeat up to 80)
CMD_SCROLL_TEXT = 0x14      # <colour> <loop> <text...>
CMD_LAYOUT = 0x22           # <layout>
CMD_FADER_SETUP = 0x2B      # <number> <type> <colour> <value>

# --- layouts (PRM p.6) ------------------------------------------------------
LAYOUT_SESSION = 0x00       # the default; this library drives Session
LAYOUT_USER1 = 0x01         # drum rack
LAYOUT_USER2 = 0x02
LAYOUT_VOLUME = 0x04        # volume faders
LAYOUT_PAN = 0x05           # pan faders

# --- channels for static / flash / pulse (PRM p.8-10) ----------------------
CH_STATIC = 1
CH_FLASH = 2
CH_PULSE = 3

# --- top round button CC numbers (PRM p.7) ---------------------------------
TOP_CC_FIRST = 0x68  # 104
TOP_CC_LAST = 0x6F   # 111

# --- value ranges -----------------------------------------------------------
PALETTE_MAX = 0x7F   # palette colour index 0..127 (0 = off)
RGB_MAX = 0x3F       # each R/G/B element 0..63

DEVICE_INQUIRY = [0xF0, 0x7E, 0x7F, 0x06, 0x01, 0xF7]


# ---------------------------------------------------------------------------
# framing helpers
# ---------------------------------------------------------------------------
def sysex(*body: int) -> list[int]:
    """Wrap ``body`` bytes in the MK2 SysEx header/terminator."""
    return [SYSEX_START, *HEADER, *body, SYSEX_END]


def _status(base: int, channel: int) -> int:
    if not 1 <= channel <= 16:
        raise ValueError("channel must be 1..16")
    return base + (channel - 1)


# ---------------------------------------------------------------------------
# direct channel messages (static / flash / pulse via channel)
# ---------------------------------------------------------------------------
def note_msg(note: int, velocity: int, channel: int = CH_STATIC) -> list[int]:
    """Note On. ``velocity`` is a palette index; channel selects static/flash/pulse."""
    return [_status(0x90, channel), note & 0x7F, velocity & 0x7F]


def cc_msg(cc: int, value: int, channel: int = CH_STATIC) -> list[int]:
    """Control Change for a top-row button. ``value`` is a palette index."""
    return [_status(0xB0, channel), cc & 0x7F, value & 0x7F]


# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------
def layout_msg(layout: int = LAYOUT_SESSION) -> list[int]:
    return sysex(CMD_LAYOUT, layout)


# ---------------------------------------------------------------------------
# LED SysEx (palette colour mode)
# ---------------------------------------------------------------------------
def set_led_msg(led: int, colour: int) -> list[int]:
    return sysex(CMD_SET_LED, led & 0x7F, colour & 0x7F)


def set_leds_msg(pairs: list[tuple[int, int]]) -> list[int]:
    """One SysEx that lights many LEDs by palette colour. ``pairs`` = (led, colour)."""
    if not 1 <= len(pairs) <= 80:
        raise ValueError("set_leds takes 1..80 (led, colour) pairs")
    body = [CMD_SET_LED]
    for led, colour in pairs:
        body += [led & 0x7F, colour & 0x7F]
    return sysex(*body)


def set_column_msg(column: int, colour: int) -> list[int]:
    if not 0 <= column <= 8:
        raise ValueError("column must be 0..8 (left to right; 8 = scene buttons)")
    return sysex(CMD_SET_COLUMN, column, colour & 0x7F)


def set_row_msg(row: int, colour: int) -> list[int]:
    if not 0 <= row <= 8:
        raise ValueError("row must be 0..8 (bottom to top; 8 = top buttons)")
    return sysex(CMD_SET_ROW, row, colour & 0x7F)


def set_all_msg(colour: int) -> list[int]:
    """Light every LED one palette colour (0 turns them all off)."""
    return sysex(CMD_SET_ALL, colour & 0x7F)


# ---------------------------------------------------------------------------
# LED SysEx (RGB mode) -- each element 0..63
# ---------------------------------------------------------------------------
def _rgb(r: int, g: int, b: int) -> tuple[int, int, int]:
    for v in (r, g, b):
        if not 0 <= v <= RGB_MAX:
            raise ValueError("R/G/B elements must be 0..63")
    return r, g, b


def set_led_rgb_msg(led: int, r: int, g: int, b: int) -> list[int]:
    return sysex(CMD_SET_LED_RGB, led & 0x7F, *_rgb(r, g, b))


def set_leds_rgb_msg(quads: list[tuple[int, int, int, int]]) -> list[int]:
    """One SysEx lighting many LEDs by RGB. ``quads`` = (led, r, g, b)."""
    if not 1 <= len(quads) <= 80:
        raise ValueError("set_leds_rgb takes 1..80 (led, r, g, b) quads")
    body = [CMD_SET_LED_RGB]
    for led, r, g, b in quads:
        body += [led & 0x7F, *_rgb(r, g, b)]
    return sysex(*body)


# ---------------------------------------------------------------------------
# flash / pulse via SysEx (palette colour). Note the unused mode byte (0).
# ---------------------------------------------------------------------------
def flash_led_sysex(led: int, colour: int) -> list[int]:
    return sysex(CMD_FLASH_LED, 0x00, led & 0x7F, colour & 0x7F)


def pulse_led_sysex(led: int, colour: int) -> list[int]:
    return sysex(CMD_PULSE_LED, 0x00, led & 0x7F, colour & 0x7F)


# ---------------------------------------------------------------------------
# text scrolling
# ---------------------------------------------------------------------------
def scroll_text_msg(text: str, colour: int, loop: bool = False) -> list[int]:
    """Scroll ASCII ``text``. Embed bytes 1..7 to change speed mid-string."""
    body = [b & 0x7F for b in text.encode("ascii", "replace")]
    return sysex(CMD_SCROLL_TEXT, colour & 0x7F, 1 if loop else 0, *body)


def scroll_stop_msg() -> list[int]:
    return sysex(CMD_SCROLL_TEXT)


# ---------------------------------------------------------------------------
# faders
# ---------------------------------------------------------------------------
def fader_setup_msg(number: int, kind: int, colour: int, value: int) -> list[int]:
    """``kind`` 0 = volume, 1 = pan (must match the active fader layout)."""
    if not 0 <= number <= 7:
        raise ValueError("fader number must be 0..7")
    return sysex(CMD_FADER_SETUP, number, kind, colour & 0x7F, value & 0x7F)


# ---------------------------------------------------------------------------
# device inquiry
# ---------------------------------------------------------------------------
def device_inquiry_msg() -> list[int]:
    return list(DEVICE_INQUIRY)
