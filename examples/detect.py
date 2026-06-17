"""Find the Launchpad, identify it, and run a quick LED self-test.

Run this first whenever you plug the device in:

    .venv/bin/python examples/detect.py

(This is a thin wrapper around the installed ``staunchpad-detect`` command.)
"""

import sys

from staunchpad.cli import main

if __name__ == "__main__":
    sys.exit(main())
