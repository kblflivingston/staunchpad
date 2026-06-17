"""Turn the grid into a launcher that fires shell commands / workflows.

Each grid button runs a command. The button glows its idle colour, flashes
while the command runs, then flashes red briefly on failure.

Edit BINDINGS below, then:

    .venv/bin/python examples/soundboard.py
"""

import subprocess
import threading

from launchpad import App, Launchpad, color
from launchpad.device import ButtonEvent

# (x, y) -> (idle_color, shell command)
BINDINGS = {
    (0, 1): (color.GREEN, "say 'hello from the launchpad'"),
    (1, 1): (color.AMBER, "open -a 'Visual Studio Code'"),
    (2, 1): (color.ORANGE, "date | say"),
    (7, 8): (color.RED, "osascript -e 'display notification \"ping\" with title \"Launchpad\"'"),
}


def run_command(lp: Launchpad, x: int, y: int, cmd: str):
    lp.pulse(x, y, color.GREEN)          # pulse while the command runs
    try:
        subprocess.run(cmd, shell=True, check=True)
        ok = True
    except subprocess.CalledProcessError:
        ok = False
    # a channel-1 (static) message stops the pulse
    lp.set(x, y, BINDINGS[(x, y)][0] if ok else color.RED)


def main():
    app = App()
    lp = app.lp

    # paint idle colours
    for (x, y), (c, _cmd) in BINDINGS.items():
        lp.set(x, y, c)

    @lp.on
    def handle(ev: ButtonEvent):
        if ev.pressed and ev.pos in BINDINGS:
            _, cmd = BINDINGS[ev.pos]
            threading.Thread(target=run_command, args=(lp, ev.x, ev.y, cmd),
                             daemon=True).start()

    print("Soundboard running. Press the lit buttons. Ctrl-C to quit.")
    lp.run()


if __name__ == "__main__":
    main()
