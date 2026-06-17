# Contributing

Thanks for your interest! This library targets the **Novation Launchpad MK2**,
whose MIDI/SysEx protocol is documented in Novation's *Launchpad MK2
Programmer's Reference Manual* v1.03.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest -q
```

## Ground rules

- **Keep `protocol.py`, `color.py`, and `layout.py` pure** (no MIDI I/O). All
  hardware access lives in `device.py`. This is what keeps the project
  unit-testable without a physical device.
- **Add a test for protocol changes.** New wire messages should be asserted
  against the reference manual's documented hex values.
- Match the existing style: type hints, short docstrings, and a comment citing
  the manual ("PRM p.N") when implementing a documented behaviour.

## Hardware testing

Behaviour that touches a real device can't run in CI. If you change `device.py`,
please note in your PR which model you tested on and what you observed.

## Other models

The legacy Launchpad / S / Mini and the newer X / Mini MK3 / Pro use different
protocols and are out of scope here. A separate `protocol` backend behind the
existing `device` facade is the right way to add one — open an issue to discuss
before starting.
