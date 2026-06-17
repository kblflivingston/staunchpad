"""``launchpad-detect`` console command: find, identify, and self-test a device.

Installed as a script entry point (see pyproject), and also used by
``examples/detect.py``. Run it the first time you plug a Launchpad in.
"""

from __future__ import annotations

import sys
import time


def main(argv: list[str] | None = None) -> int:
    from . import color
    from .device import Launchpad, LaunchpadNotFound, list_ports

    ports = list_ports()
    print("MIDI inputs :", ports["inputs"] or "(none)")
    print("MIDI outputs:", ports["outputs"] or "(none)")

    if not any("launchpad" in n.lower() for n in ports["outputs"]):
        print(
            "\nNo Launchpad MIDI port found. Things to check, in order:\n"
            "  1. Cable: use a known DATA cable, not a charge-only one. If the\n"
            "     unit shows a drifting light show ('Vegas mode'), it has power\n"
            "     but no data link to the computer — classic charge-only cable.\n"
            "  2. Connection: plug straight into the computer, not via a hub chain.\n"
            "  3. Driver: the ORIGINAL (non-S) Launchpad is not USB class-compliant\n"
            "     and may need Novation's USB driver to appear as a MIDI device.\n"
        )
        return 1

    try:
        lp = Launchpad()
    except LaunchpadNotFound as e:
        print("Error:", e)
        return 1

    print("\nConnected.")
    info = lp.identify()
    print("Identity   :", info["model"], "| responds to inquiry:", info["responds"])
    print("Input port :", "yes" if lp.has_input else "NO (button events unavailable)")

    print("\nAll LEDs amber for 1s...")
    lp.fill(color.AMBER)
    time.sleep(1)
    lp.clear()

    print("Corners: red / green / blue / yellow (2s)...")
    lp.set(0, 1, color.RED)
    lp.set(7, 1, color.GREEN)
    lp.set(0, 8, color.rgb(0, 0, 63))
    lp.set(7, 8, color.YELLOW)
    time.sleep(2)
    lp.clear()
    lp.close()
    print("Done. The device is working.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
