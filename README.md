# launchpad-controller

A clean, fully-featured Python interface for the **Novation Launchpad MK2**. It
turns the grid into a programmable surface for your own tools and workflows:
direct LED control with full **RGB**, the 128-colour palette, hardware
**flashing** and **pulsing**, single-message full-surface updates, button
events, scene save/recall, and a high-level widget layer for building things
fast.

Verified working against real hardware (firmware 0171). The wire protocol is
implemented straight from Novation's *Launchpad MK2 Programmer's Reference
Manual* and unit-tested against its documented byte sequences.

## Install

```bash
cd launchpad-controller
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"        # or: pip install -r requirements.txt
```

## First run

Plug the Launchpad in and run the detector — it lists MIDI ports, identifies the
model, and lights a test pattern:

```bash
.venv/bin/python examples/detect.py        # or: launchpad-detect
```

> **Not appearing?** If the unit shows a drifting light show ("Vegas mode"), it
> has power but no data link — almost always a charge-only USB cable or a flaky
> hub. Use a known data cable and plug straight into the computer. The MK2 is
> USB class-compliant, so once it enumerates no driver is needed.

## Hello, lights

```python
from launchpad import Launchpad, color

with Launchpad() as lp:                 # auto-detects the first "Launchpad" port
    lp.set(0, 1, color.RED)             # palette colour — one MIDI message
    lp.set(7, 8, color.rgb(0, 0, 63))   # exact RGB — SysEx, ~262k colours
    lp.pulse(4, 4, color.GREEN)         # hardware pulse
    lp.flash(0, 0, color.YELLOW)        # hardware flash
    lp.fill(color.BLUE)                 # flood the whole surface

    @lp.on_press(7, 0)
    def _(ev):
        print("pressed!", ev)

    lp.run()                            # block and dispatch button events (Ctrl-C)
```

## Coordinate system

One friendly grid for everything (Session layout, selected automatically):

```
    x: 0  1  2  3  4  5  6  7     8
  y
  0  ●  ●  ●  ●  ●  ●  ●  ●          <- top "mode" buttons  (Control Change 104..111)
  1  □  □  □  □  □  □  □  □    ●     <- scene buttons live at x=8
  2  □  □  □  □  □  □  □  □    ●
  …                                  the 8x8 grid is x:0..7, y:1..8 (Note On)
  8  □  □  □  □  □  □  □  □    ●
```

`launchpad.layout.xy_to_midi(x, y)` / `midi_to_xy(kind, num)` convert both ways.
(The MK2's own "decimal" note numbering — 11 bottom-left … 88 top-right — is
hidden behind this so y increases downward and x rightward.)

## Colour

Two ways to light an LED, and you can mix them freely:

```python
from launchpad import color

# palette: a preset index 0..127 (one MIDI message; flash/pulse use these)
color.RED, color.ORANGE, color.YELLOW, color.GREEN, color.BLUE
color.PINK, color.PURPLE, color.OFF
color.palette(45)

# RGB: any colour, each element 0..63 (SysEx; cannot flash/pulse)
color.rgb(63, 20, 0)
color.WHITE, color.CYAN, color.AMBER, color.RED_DIM        # exact-RGB conveniences

# parse() accepts all of these anywhere a colour is expected:
color.parse("green"); color.parse(45); color.parse([0, 0, 63]); color.parse("#ff8800")
```

## What you can do

| Capability | API |
|---|---|
| Light one LED (palette or RGB) | `lp.set(x, y, color)` / `lp.off(x, y)` |
| Flash between two colours | `lp.flash(x, y, color)` (palette) |
| Pulse a colour | `lp.pulse(x, y, color)` (palette) |
| Flood / clear | `lp.fill(color)` / `lp.clear()` |
| Light a whole row / column | `lp.set_row(y, color)` / `lp.set_column(x, color)` |
| Full-surface repaint | `lp.render({(x, y): color, ...})` (1–2 SysEx msgs) |
| Scrolling text | `lp.scroll_text("hi", color.GREEN, loop=True)` |
| Identify model + firmware | `lp.identify()` |
| Button events | `@lp.on`, `@lp.on_press(x, y)`, `@lp.on_release(x, y)`, `@lp.on_button(x, y)` |
| Save / recall scenes | `scenes.save(path, grid)` / `scenes.load(path)` |
| Raw escape hatch | `lp.set_note`, `lp.set_cc`, `lp.send_raw([...])` |

### High-level widgets

```python
from launchpad import App, Toggle, Momentary, RadioGroup, ColorCycle, color

app = App()
Toggle(app, 0, 1, on_color=color.GREEN, on_change=lambda w: print(w.state))
Momentary(app, 1, 1, on_press=lambda w: do_thing())
RadioGroup(app, cells=[(x, 8) for x in range(8)], on_select=lambda i: page(i))
ColorCycle(app, 2, 1, palette=[color.RED, color.YELLOW, color.GREEN])
app.run()
```

## Examples

| File | What it shows |
|---|---|
| `examples/detect.py` | Port discovery, model identification, LED self-test |
| `examples/hello_lights.py` | RGB gradient render, pulsing, flashing, text |
| `examples/app_demo.py` | The widget layer: toggles, momentaries, radio group |
| `examples/soundboard.py` | Grid buttons fire shell commands, with run/fail feedback |
| `examples/scene_recall.py` | Edit grid patterns; save/recall to the scene buttons |

## Tests

Pure-protocol logic is fully unit-tested without hardware:

```bash
.venv/bin/python -m pytest -q
```

## Architecture

```
launchpad/
  protocol.py   pure MIDI/SysEx byte builders (the wire spec; the source of truth)
  color.py      Color model: palette index OR RGB, named palette, parse()
  layout.py     (x, y) <-> note/CC mapping for the Session layout
  device.py     Launchpad: I/O, LEDs, flash/pulse, RGB, render, events, identify
  scenes.py     save/recall full-surface snapshots (JSON)
  widgets.py    App runloop + Toggle/Momentary/RadioGroup/ColorCycle/Button
```

`protocol.py`, `color.py`, and `layout.py` are pure and hardware-free; `device.py`
is the only module that touches MIDI.

## Supported hardware

This library targets the **Launchpad MK2** (the 2015 RGB model). The legacy
Launchpad / S / Mini and the newer X / Mini MK3 / Pro use different protocols and
are out of scope, but the layered design (a pure `protocol` module behind a
`device` facade) makes a separate backend the natural way to add them.

## Protocol notes (Launchpad MK2)

Distilled from Novation's *Launchpad MK2 Programmer's Reference Manual* v1.03:

- **Grid + scene buttons:** Note On. Session layout note = `row*10 + col`, row 1
  at the bottom, col 9 = scene buttons (bottom-left 11 … top-right 88).
- **Top mode buttons:** Control Change 104..111.
- **Channels carry intent:** channel 1 = static, channel 2 = flash (between the
  current colour and the sent one), channel 3 = pulse. A channel-1 message stops
  a flash/pulse. Flash/pulse use palette colours and run on MIDI beat clock
  (default 120 BPM).
- **Colour:** palette index 0..127 via velocity (0 = off), or RGB via SysEx with
  each element 0..63.
- **SysEx** (header `F0 00 20 29 02 18 … F7`): set LED `0A`, set LED RGB `0B`,
  set column `0C`, set row `0D`, set all `0E`, flash `23`, pulse `28`, text `14`,
  layout `22`. The LED-set commands accept up to 80 LEDs in one message.
- **Device inquiry** `F0 7E 7F 06 01 F7` → reply contains `00 20 29 69` and a
  4-byte firmware revision.
```
