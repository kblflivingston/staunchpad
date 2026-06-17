"""A prompt console: grid buttons that signal prompts to your always-on agent,
with press/running/complete/error colour feedback and a pretty ambient region.

Run this, then run examples/dispatcher.py in another terminal (the "agent" side).

    .venv/bin/python examples/prompt_console.py
"""

from staunchpad import Console, PromptButton, ActionButton, color
from staunchpad.animations import Twinkle, RainbowWave, rect

# Each prompt button signals a job to the queue; the dispatcher runs it and
# reports back, which drives the LED from pulsing -> green/red -> idle.
PROMPTS = [
    ("standup",  "Summarise what I worked on today from my git log."),
    ("relnote",  "Draft release notes from the latest diff."),
    ("triage",   "Triage my unread email and list what needs a reply."),
    ("plan",     "Plan my next 3 hours around my calendar."),
]

# distinct idle hue per button so they're easy to tell apart
HUES = [color.rgb(0, 30, 45), color.rgb(30, 0, 40),
        color.rgb(40, 20, 0), color.rgb(0, 40, 20)]


def main():
    con = Console()

    for i, (label, prompt) in enumerate(PROMPTS):
        PromptButton(con, x=i, y=1, prompt=prompt, label=label, color=HUES[i])

    # a local (non-prompt) action button, just to show the synchronous path
    ActionButton.shell(con, 7, 1, "osascript -e 'display notification \"hi\" with title \"staunchpad\"'",
                       color=color.rgb(40, 40, 40), label="notify")

    # ambient eye-candy on the bottom rows — kept clear of the buttons above
    con.animate(Twinkle(rect(0, 6, 7, 7)))
    con.animate(RainbowWave(rect(0, 8, 7, 8), period=8.0, value=0.6))

    print("Console up. Row 1 = prompt buttons; press one (start the dispatcher too).")
    print("Bottom two rows are ambient. Ctrl-C to quit.")
    con.run()


if __name__ == "__main__":
    main()
