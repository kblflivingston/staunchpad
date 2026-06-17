"""Launch the visual web UI for laying out the board.

    .venv/bin/python examples/ui.py          # opens http://127.0.0.1:8765
    .venv/bin/staunchpad-ui                   # same thing, installed command

Edit buttons (assign prompts + colours), paint animation regions, and press
buttons — all live-synced to the hardware. A built-in dry-run dispatcher lets
you watch the press/running/complete lifecycle without an agent.
"""

from staunchpad.webui import main

if __name__ == "__main__":
    main()
