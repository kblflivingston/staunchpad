"""A little light show that exercises most LED features.

    .venv/bin/python examples/hello_lights.py
"""

import time

from launchpad import Launchpad, color


def sweep(lp):
    """Walk a colour gradient across the grid, row by row."""
    palette = [color.RED, color.ORANGE, color.AMBER, color.YELLOW,
               color.LIME, color.GREEN]
    for y in range(1, 9):
        for x in range(8):
            lp.set(x, y, palette[(x + y) % len(palette)])
            time.sleep(0.01)


def full_refresh_animation(lp):
    """Use the fast rapid-update path to animate full-surface frames."""
    for frame in range(8):
        grid = {}
        for y in range(1, 9):
            for x in range(8):
                ring = (abs(x - 3.5) + abs(y - 4.5))
                on = int(ring) % 8 == frame % 8
                grid[(x, y)] = color.GREEN if on else color.OFF
        lp.render(grid)
        time.sleep(0.08)


def flashing_demo(lp):
    lp.reset()
    lp.begin_flash()
    for x in range(8):
        lp.set(x, 4, color.AMBER)            # solid row
        lp.flash(x, 5, color.RED)            # flashing row
    time.sleep(3)
    lp.end_flash()


def main():
    with Launchpad() as lp:
        info = lp.identify()
        print("Device:", info["model"])

        sweep(lp)
        time.sleep(0.5)
        full_refresh_animation(lp)
        flashing_demo(lp)

        if info["responds"]:  # S / Mini only
            lp.scroll_text("hello", color.GREEN, loop=False)
            time.sleep(3)

        lp.reset()


if __name__ == "__main__":
    main()
