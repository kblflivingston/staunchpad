"""A light show that exercises most MK2 LED features (RGB, pulse, flash, text).

    .venv/bin/python examples/hello_lights.py
"""

import time

from staunchpad import Launchpad, color


def rgb_sweep(lp):
    """Walk a smooth RGB hue gradient across the grid using one SysEx per frame."""
    for t in range(48):
        grid = {}
        for y in range(1, 9):
            for x in range(8):
                phase = (x + y + t) % 24
                r = max(0, 31 - abs(phase - 6) * 6)
                g = max(0, 31 - abs(phase - 14) * 6)
                b = max(0, 31 - abs(phase - 22) * 6)
                grid[(x, y)] = color.rgb(min(63, r), min(63, g), min(63, b))
        lp.render(grid)
        time.sleep(0.04)


def pulse_and_flash(lp):
    lp.clear()
    for x in range(8):
        lp.pulse(x, 3, color.GREEN)     # whole row pulses green
        lp.set(x, 5, color.BLUE)        # static base...
        lp.flash(x, 5, color.RED)       # ...flashing to red
    time.sleep(4)
    lp.clear()


def main():
    with Launchpad() as lp:
        info = lp.identify()
        print("Device:", info["model"], "| firmware:", info["firmware"])

        rgb_sweep(lp)
        pulse_and_flash(lp)

        lp.scroll_text("hello", color.GREEN, loop=False)
        time.sleep(3.5)
        lp.clear()


if __name__ == "__main__":
    main()
