"""staunchpad — a programming interface for the Novation Launchpad MK2.

Quick start::

    from staunchpad import Launchpad, color

    lp = Launchpad()                  # auto-detects the device
    lp.set(0, 1, color.RED)           # palette colour (one MIDI message)
    lp.set(7, 8, color.rgb(0, 0, 63)) # exact RGB (SysEx)
    lp.pulse(4, 4, color.GREEN)       # hardware pulse
    lp.fill(color.BLUE)               # flood the whole surface
    lp.scroll_text("hi", color.YELLOW)

    @lp.on_press(0, 0)
    def _(ev):
        print("top-left mode button pressed!")

    lp.run()                          # block and dispatch events
"""

from . import animations, color, layout, protocol, scenes
from .color import Color, palette, rgb
from .console import (ActionButton, Console, PromptButton, State,
                      clipboard_runner, shell_runner)
from .device import ButtonEvent, Launchpad, LaunchpadNotFound, list_ports
from .dispatch import Job, JobQueue
from .widgets import App, Button, ColorCycle, Momentary, RadioGroup, Toggle, Widget

__all__ = [
    "Launchpad", "LaunchpadNotFound", "ButtonEvent", "list_ports",
    "App", "Widget", "Button", "Toggle", "Momentary", "RadioGroup", "ColorCycle",
    "Console", "ActionButton", "PromptButton", "State",
    "clipboard_runner", "shell_runner",
    "JobQueue", "Job",
    "Color", "palette", "rgb",
    "color", "layout", "protocol", "scenes", "animations",
]

__version__ = "0.1.0"
