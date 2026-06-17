# launchpad-controller

A clean, fully-featured Python interface for the **legacy Novation Launchpad**
(the original 2009 model, the Launchpad S, and the Launchpad Mini). It turns the
grid into a programmable surface for your own tools and workflows: direct
LED/button/event control, colour helpers, hardware flashing, double-buffered
scene recall, rapid full-surface repaint, brightness control, plus a high-level
widget/event layer for building things fast.

> **Your unit:** an original Launchpad (orange backplate, non-Pro). It shares the
> legacy MIDI core with the S/Mini, so everything here applies — with two
> caveats called out below (`scroll_text` and `identify` are S/Mini-only, and the
> original needs Novation's USB driver on macOS to appear as a MIDI device).

## Install

```bash
cd ~/developer/repos/launchpad-controller
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"        # or: pip install -r requirements.txt
```

## First run

Plug the Launchpad in and run the detector — it lists MIDI ports, identifies the
model, and lights a test pattern:

```bash
.venv/bin/python examples/detect.py
```

If no Launchpad output port appears: the **original** Launchpad is *not* USB
class-compliant and historically needs Novation's USB driver on macOS to show up
in CoreMIDI. That's the first thing to check if it never enumerates.

## Hello, lights

```python
from launchpad import Launchpad, color

with Launchpad() as lp:            # auto-detects the first "Launchpad" port
    lp.set(0, 1, color.RED)        # light the top-left GRID cell red
    lp.set(0, 0, color.GREEN)      # light the top-left MODE (round) button green
    lp.fill(color.AMBER)           # flood the whole surface (fast rapid update)

    @lp.on_press(7, 8)             # bottom-right grid cell
    def _(ev):
        print("pressed!", ev)

    lp.run()                       # block and dispatch button events (Ctrl-C)
```

## Coordinate system

One friendly grid for everything (X-Y layout, selected automatically on connect):

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

## Colour

The legacy Launchpad has **no RGB**. Each LED is a red element + a green element,
each 0..3, packed into a velocity byte: `velocity = (green << 4) | red | flags`.
The practical palette is red / amber / green plus a few orange/yellow shades.

```python
from launchpad import color
color.RED, color.GREEN, color.AMBER, color.ORANGE, color.YELLOW, color.LIME
color.RED_LOW, color.GREEN_MED, color.AMBER_LOW, color.OFF
color.Color(red=3, green=1)          # build your own (0..3 each)
color.parse("amber"); color.parse([3, 3])   # names / pairs accepted everywhere
```

## What you can do

| Capability | API |
|---|---|
| Light one LED | `lp.set(x, y, color)` / `lp.off(x, y)` |
| Flood / clear | `lp.fill(color)` / `lp.clear()` |
| Full-surface repaint (fast) | `lp.render({(x, y): color, ...})` |
| Hardware flashing (280 ms) | `lp.flash(x, y, color)` … `lp.end_flash()` |
| Flicker-free scene swap | `with lp.double_buffer() as db: db.draw(scene); db.swap()` |
| Brightness / fades | `lp.set_brightness(numerator, denominator)` |
| All-LED test | `lp.all_on(intensity=0..2)` |
| Layout | `lp.set_layout(layout.LAYOUT_XY | LAYOUT_DRUM)` |
| Raw escape hatch | `lp.set_note(note, vel)`, `lp.set_cc(cc, vel)`, `lp.send_raw([...])` |
| Scrolling text *(S/Mini only)* | `lp.scroll_text("hi", color.GREEN, loop=True)` |
| Identify model *(S/Mini reply)* | `lp.identify()` |
| Button events | `@lp.on`, `@lp.on_press(x, y)`, `@lp.on_release(x, y)`, `@lp.on_button(x, y)` |
| Save / recall scenes | `scenes.save(path, grid)` / `scenes.load(path)` |

### High-level widgets

```python
from launchpad import App, Toggle, Momentary, RadioGroup, ColorCycle, color

app = App()
Toggle(app, 0, 1, on_color=color.GREEN, on_change=lambda w: print(w.state))
Momentary(app, 1, 1, on_press=lambda w: do_thing())
RadioGroup(app, cells=[(x, 8) for x in range(8)], on_select=lambda i: page(i))
ColorCycle(app, 2, 1, palette=[color.RED, color.AMBER, color.GREEN])
app.run()
```

## Examples

| File | What it shows |
|---|---|
| `examples/detect.py` | Port discovery, model identification, LED self-test |
| `examples/hello_lights.py` | Colour sweep, rapid-update animation, flashing, text |
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
  protocol.py   pure MIDI byte builders (the wire spec; the source of truth)
  color.py      Color model + named palette + velocity packing
  layout.py     (x, y) <-> note/CC mapping, rapid-update scan order
  device.py     Launchpad: I/O, LEDs, flashing, double buffer, events, identify
  scenes.py     save/recall full-surface snapshots (JSON)
  widgets.py    App runloop + Toggle/Momentary/RadioGroup/ColorCycle/Button
```

`protocol.py`, `color.py`, and `layout.py` are pure and hardware-free; `device.py`
is the only module that touches MIDI.

## Protocol notes (legacy Launchpad)

Distilled from Novation's *Launchpad S Programmer's Reference Manual* v1.02:

- **Grid + scene buttons:** Note On, channel 1. Note = `(y-1)*16 + x` in X-Y layout.
  Press = velocity 127, release = velocity 0 (a Note On with velocity 0).
- **Top mode buttons:** Control Change, channel 1, CC 104..111.
- **Colour:** velocity `(green<<4) | red | flags`; flag bits 2–3 select the
  double-buffer behaviour (`copy` = both buffers, `clear` = flash, `ignore`).
- **Config:** `B0 00 00` reset · `B0 00 01/02` layout · `B0 00 7D–7F` all-LEDs ·
  `B0 00 28` flash mode · `B0 00 31/34` buffer swap · `B0 1E/1F xx` brightness.
- **Rapid update:** channel 3 Note On pairs repaint all 80 LEDs in 40 messages.
- **SysEx (S/Mini only):** device inquiry `F0 7E 7F 06 01 F7`; scrolling text
  `F0 00 20 29 09 <colour> <ascii…> F7`. The **original** Launchpad ignores both.
```
