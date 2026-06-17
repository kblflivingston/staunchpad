"""Find the Launchpad, identify it, and run a quick LED self-test.

Run this first whenever you plug the device in:

    .venv/bin/python examples/detect.py
"""

import sys
import time

from launchpad import Launchpad, LaunchpadNotFound, list_ports


def main():
    ports = list_ports()
    print("MIDI inputs :", ports["inputs"] or "(none)")
    print("MIDI outputs:", ports["outputs"] or "(none)")

    if not any("launchpad" in n.lower() for n in ports["outputs"]):
        print(
            "\nNo Launchpad output port found.\n"
            "  • Make sure it's plugged in.\n"
            "  • The ORIGINAL (non-S) Launchpad is not class-compliant and needs\n"
            "    Novation's USB driver to appear here on macOS. If it never shows\n"
            "    up, that's the most likely reason.",
        )
        return 1

    lp = Launchpad()
    print("\nConnected.")
    info = lp.identify()
    print("Identity   :", info["model"], "(responds to inquiry:", info["responds"], ")")
    print("Input port :", "yes" if lp.has_input else "NO — button events unavailable")

    print("\nLighting all LEDs amber for 1s...")
    lp.all_on(2)
    time.sleep(1)
    lp.reset()

    print("Lighting the four corners (red / green / amber / orange)...")
    from launchpad import color
    lp.set(0, 1, color.RED)
    lp.set(7, 1, color.GREEN)
    lp.set(0, 8, color.AMBER)
    lp.set(7, 8, color.ORANGE)
    time.sleep(2)
    lp.reset()
    lp.close()
    print("Done.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except LaunchpadNotFound as e:
        print("Error:", e)
        sys.exit(1)
