"""A high-level console: programmable prompt/action buttons with state-driven
colour feedback, plus ambient animations on chosen regions.

Typical use — buttons that *signal* prompts to an always-on agent::

    from staunchpad import Console, PromptButton, color
    from staunchpad.animations import Twinkle, rect

    con = Console()                                   # opens the device + a JobQueue

    PromptButton(con, 0, 1, "Summarise today's commits", label="standup",
                 color=color.rgb(0, 30, 45))
    PromptButton(con, 1, 1, "Draft a release note from the diff", label="relnote",
                 color=color.rgb(30, 0, 40))

    con.animate(Twinkle(rect(0, 6, 7, 8)))            # pretty ambient region

    con.run()

Pressing a PromptButton drops a job in the queue (LED pulses = running). A
separate dispatcher (see ``examples/dispatcher.py``) hands the prompt to a
subagent and writes the result back, which flips the LED to green (done) or red
(error) before it fades back to idle.

For buttons that just run something locally, use :class:`ActionButton`.
"""

from __future__ import annotations

import subprocess
import threading
import time
from enum import Enum
from typing import Callable

from . import color as _c
from .color import GREEN, ORANGE, RED, WHITE, Color, parse
from . import dispatch
from .dispatch import JobQueue
from .widgets import App, Widget


class State(Enum):
    IDLE = "idle"
    PRESSED = "pressed"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"


class ActionButton(Widget):
    """A single button with a press → running → complete/error → idle lifecycle.

    ``action`` is called (with this button) in a background thread when pressed;
    returning normally means success, raising means error. The LED reflects each
    state. Colours are configurable; ``running`` and ``error`` use the hardware
    pulse/flash when given palette colours (RGB colours fall back to static).
    """

    def __init__(self, console: "Console", x: int, y: int,
                 action: Callable[["ActionButton"], None] | None = None, *,
                 color=Color(rgb=(0, 30, 45)), idle_level: float = 0.45,
                 pressed=WHITE, running=ORANGE, complete=GREEN, error=RED,
                 complete_hold: float = 1.0, error_hold: float = 1.6,
                 label: str | None = None):
        self.x, self.y = x, y
        self.label = label
        self.action = action
        self.idle_color = parse(color).dimmed(idle_level)
        self.colors = {
            State.PRESSED: parse(pressed),
            State.RUNNING: parse(running),
            State.COMPLETE: parse(complete),
            State.ERROR: parse(error),
        }
        self.complete_hold = complete_hold
        self.error_hold = error_hold
        self.state = State.IDLE
        self._busy = False
        super().__init__(console)

    def cells(self):
        return [(self.x, self.y)]

    def draw(self):
        self._apply(State.IDLE)

    # -- LED for a state ----------------------------------------------------
    def _apply(self, state: State) -> None:
        self.state = state
        lp = self.app.lp
        if state is State.IDLE:
            lp.set(self.x, self.y, self.idle_color)
            return
        c = self.colors[state]
        if state is State.RUNNING and not c.is_rgb:
            lp.pulse(self.x, self.y, c)
        elif state is State.ERROR and not c.is_rgb:
            lp.flash(self.x, self.y, c)
        else:
            lp.set(self.x, self.y, c)

    # -- events -------------------------------------------------------------
    def handle(self, ev):
        if ev.pressed and not self._busy:
            self._busy = True
            self._apply(State.PRESSED)
            threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        time.sleep(0.1)               # let the PRESSED flash register
        self._apply(State.RUNNING)
        ok = True
        try:
            if self.action:
                self.action(self)
        except Exception as exc:       # noqa: BLE001 - surface any failure on the LED
            ok = False
            print(f"[staunchpad] action {self.label or (self.x, self.y)} failed: {exc}")
        self._apply(State.COMPLETE if ok else State.ERROR)
        time.sleep(self.complete_hold if ok else self.error_hold)
        self._apply(State.IDLE)
        self._busy = False

    # -- convenience constructor -------------------------------------------
    @classmethod
    def shell(cls, console, x, y, command: str, **kw) -> "ActionButton":
        """A button that runs a shell ``command`` (non-zero exit = error)."""
        def action(_btn):
            subprocess.run(command, shell=True, check=True)
        return cls(console, x, y, action=action, **kw)


class PromptButton(ActionButton):
    """A button that *signals* a prompt to an always-on agent via the job queue.

    On press it enqueues the prompt and goes to RUNNING; the console's queue
    watcher flips it to COMPLETE/ERROR when the dispatcher reports the job's
    outcome. The agent never has to know anything about MIDI.
    """

    def __init__(self, console: "Console", x: int, y: int, prompt: str, *,
                 label: str | None = None, **kw):
        self.prompt = prompt
        super().__init__(console, x, y, action=None, label=label, **kw)
        self.job_id: str | None = None

    def handle(self, ev):
        if ev.pressed and not self._busy:
            self._busy = True
            self._apply(State.PRESSED)
            self.job_id = self.app.queue.submit(self.prompt, button=(self.x, self.y),
                                                label=self.label)
            self.app._track(self.job_id, self)
            threading.Timer(0.12, lambda: self._apply(State.RUNNING)).start()

    def on_job_status(self, status: str) -> None:
        """Called by the console when the dispatcher updates this button's job."""
        if status == dispatch.RUNNING:
            self._apply(State.RUNNING)
        elif status == dispatch.DONE:
            self._finish(State.COMPLETE, self.complete_hold)
        elif status == dispatch.ERROR:
            self._finish(State.ERROR, self.error_hold)

    def _finish(self, state: State, hold: float) -> None:
        self._apply(state)
        threading.Timer(hold, self._reset).start()

    def _reset(self) -> None:
        self._apply(State.IDLE)
        self._busy = False
        self.job_id = None


class Console(App):
    """An :class:`App` plus a job queue, a queue watcher, and an animation loop."""

    def __init__(self, lp=None, queue: JobQueue | None = None, fps: int = 30,
                 archive_done: bool = True, **launchpad_kwargs):
        super().__init__(lp=lp, **launchpad_kwargs)
        self.queue = queue or JobQueue()
        self.fps = fps
        self.archive_done = archive_done
        self.animations: list = []
        self._jobs: dict[str, PromptButton] = {}
        self._seen: dict[str, str] = {}
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    # -- prompt-job tracking ------------------------------------------------
    def _track(self, job_id: str, button: PromptButton) -> None:
        self._jobs[job_id] = button
        self._seen[job_id] = dispatch.PENDING

    def _queue_loop(self) -> None:
        while not self._stop.is_set():
            for job_id, button in list(self._jobs.items()):
                status = self.queue.status(job_id)
                if status and status != self._seen.get(job_id):
                    self._seen[job_id] = status
                    button.on_job_status(status)
                    if status in dispatch.TERMINAL:
                        self._jobs.pop(job_id, None)
                        self._seen.pop(job_id, None)
                        if self.archive_done:
                            self.queue.archive(job_id)
            self._stop.wait(0.1)

    # -- animations ---------------------------------------------------------
    def animate(self, animation):
        """Register an ambient animation (see :mod:`staunchpad.animations`)."""
        self.animations.append(animation)
        return animation

    def _anim_loop(self) -> None:
        start = time.time()
        while not self._stop.is_set():
            t = time.time() - start
            changed: dict[tuple[int, int], Color] = {}
            for anim in self.animations:
                for cell, c in anim.frame(t).items():
                    if anim._last.get(cell) != c:
                        anim._last[cell] = c
                        changed[cell] = c
            if changed:
                self.lp.render(changed)
            self._stop.wait(1.0 / self.fps)

    # -- run ----------------------------------------------------------------
    def run(self) -> None:
        self.lp.clear()
        self.redraw()                          # paint every button's idle colour
        self._stop.clear()
        self._threads = [threading.Thread(target=self._queue_loop, daemon=True)]
        if self.animations:
            self._threads.append(threading.Thread(target=self._anim_loop, daemon=True))
        for th in self._threads:
            th.start()
        try:
            self.lp.run()
        finally:
            self._stop.set()
            self.lp.clear()


# --- prompt/action runner helpers (for ActionButton / manual use) -----------
def clipboard_runner(prompt: str) -> None:
    """Copy ``prompt`` to the macOS clipboard (and echo it)."""
    subprocess.run(["pbcopy"], input=prompt.encode(), check=True)
    print("[staunchpad] copied prompt to clipboard:", prompt)


def shell_runner(template: str) -> Callable[[str], None]:
    """Return a runner that executes ``template.format(prompt=...)`` in a shell."""
    def run(prompt: str) -> None:
        subprocess.run(template.format(prompt=prompt), shell=True, check=True)
    return run
