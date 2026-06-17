"""Paint patterns on the grid and recall them with the scene buttons.

* Grid buttons  : toggle the cell through off -> red -> amber -> green.
* Scene buttons (right column): tap to RECALL that saved scene; hold-press
  while the SAVE (top-left mode) button is lit to STORE the current grid.
* Top-left mode button (0,0): arm "save" mode (lit amber while armed).

Scenes persist to scenes/*.json next to this script.

    .venv/bin/python examples/scene_recall.py
"""

from pathlib import Path

from launchpad import Launchpad, color, scenes
from launchpad.device import ButtonEvent

SCENE_DIR = Path(__file__).parent / "scenes"
SCENE_DIR.mkdir(exist_ok=True)

CYCLE = [color.OFF, color.RED, color.AMBER, color.GREEN]

# in-memory model of the editable 8x8 grid
grid: dict[tuple[int, int], color.Color] = {}
save_armed = False


def scene_path(slot: int) -> Path:
    return SCENE_DIR / f"slot{slot}.json"


def main():
    global save_armed
    lp = Launchpad()
    lp.reset()
    lp.set(0, 0, color.AMBER_LOW)  # the "save" toggle, dim = disarmed

    # show which slots already have a saved scene
    for slot in range(8):
        lp.set(8, slot + 1, color.GREEN_LOW if scene_path(slot).exists() else color.RED_LOW)

    @lp.on
    def handle(ev: ButtonEvent):
        global save_armed
        if not ev.pressed:
            return

        # save-arm toggle
        if ev.pos == (0, 0):
            save_armed = not save_armed
            lp.set(0, 0, color.AMBER if save_armed else color.AMBER_LOW)
            return

        # scene buttons (right column)
        if ev.x == 8 and 1 <= ev.y <= 8:
            slot = ev.y - 1
            if save_armed:
                scenes.save(scene_path(slot), grid)
                lp.set(8, ev.y, color.GREEN_LOW)
                print(f"saved slot {slot}")
            elif scene_path(slot).exists():
                loaded = scenes.load(scene_path(slot))
                grid.clear()
                grid.update(loaded)
                lp.render(grid)
                lp.set(0, 0, color.AMBER if save_armed else color.AMBER_LOW)
                for s in range(8):
                    lp.set(8, s + 1, color.GREEN_LOW if scene_path(s).exists() else color.RED_LOW)
                print(f"recalled slot {slot}")
            return

        # editable grid: cycle the cell colour
        if 0 <= ev.x <= 7 and 1 <= ev.y <= 8:
            cur = grid.get(ev.pos, color.OFF)
            nxt = CYCLE[(CYCLE.index(cur) + 1) % len(CYCLE)] if cur in CYCLE else color.RED
            grid[ev.pos] = nxt
            lp.set(ev.x, ev.y, nxt)

    print("Scene editor running. Ctrl-C to quit.")
    lp.run()


if __name__ == "__main__":
    main()
