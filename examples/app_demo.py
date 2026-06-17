"""Show off the high-level widget layer: toggles, momentaries, a radio group.

    .venv/bin/python examples/app_demo.py
"""

from staunchpad import App, Momentary, RadioGroup, Toggle, color


def main():
    app = App()

    # A column of latching toggles (green when on).
    for y in range(1, 5):
        Toggle(app, 0, y, on_color=color.GREEN, off_color=color.RED_DIM,
               on_change=lambda w: print(f"toggle {w.x},{w.y} -> {w.state}"))

    # A couple of momentary buttons (bright while held).
    Momentary(app, 2, 1, color=color.AMBER,
              on_press=lambda w: print("momentary down"),
              on_release=lambda w: print("momentary up"))

    # A radio group along the bottom row: exactly one selected.
    RadioGroup(app, cells=[(x, 8) for x in range(8)],
               on_color=color.GREEN, off_color=color.RED_DIM,
               on_select=lambda i: print(f"selected {i}"))

    print("Widget demo running. Ctrl-C to quit.")
    app.run()


if __name__ == "__main__":
    main()
