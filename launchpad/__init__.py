"""launchpad — a programming interface for the legacy Novation Launchpad.

Quick start::

    from launchpad import Launchpad, color

    lp = Launchpad()                 # auto-detects the device
    lp.set(0, 1, color.RED)          # light top-left grid LED red
    lp.fill(color.GREEN)             # flood the surface
    lp.scroll_text("hi", color.AMBER)  # S/Mini only

    @lp.on_press(0, 0)
    def _(ev):
        print("top-left mode button pressed!")

    lp.run()                         # block and dispatch events
"""

from . import color, layout, protocol, scenes
from .color import Color
from .device import ButtonEvent, Launchpad, LaunchpadNotFound, list_ports
from .widgets import App, Button, ColorCycle, Momentary, RadioGroup, Toggle, Widget

__all__ = [
    "Launchpad", "LaunchpadNotFound", "ButtonEvent", "list_ports",
    "App", "Widget", "Button", "Toggle", "Momentary", "RadioGroup", "ColorCycle",
    "Color", "color", "layout", "protocol", "scenes",
]

__version__ = "0.1.0"
