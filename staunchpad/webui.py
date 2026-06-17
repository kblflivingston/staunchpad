"""A local web UI for laying out the board: assign prompts, pick colours,
paint animation regions — live-synced to the hardware.

Run ``staunchpad-ui`` (or ``python -m staunchpad.webui``), open the printed URL,
and design your surface visually. The page mirrors the device in real time and a
built-in dry-run dispatcher lets you watch the press/running/complete lifecycle
without wiring up an agent yet.

Dependency-free: stdlib ``http.server`` + a single static HTML page, JSON API,
~5 Hz polling. The layout persists to ``~/.staunchpad/layout.json``.
"""

from __future__ import annotations

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import animations as _anim
from . import color as _c
from .color import Color, rgb
from .console import ActionButton, Console, PromptButton
from .device import ButtonEvent, LaunchpadNotFound
from .dispatch import JobQueue

STATIC = Path(__file__).parent / "static"
CONFIG_PATH = Path(os.environ.get("STAUNCHPAD_CONFIG",
                                  Path.home() / ".staunchpad" / "layout.json"))

# representative hex for the palette colours we use (display only)
PALETTE_HEX = {0: "#0c0c10", 3: "#ffffff", 5: "#ff2a2a", 9: "#ff7a1a",
               13: "#ffe62e", 21: "#3aff3a", 45: "#2a6bff", 53: "#ff3aa0",
               81: "#a04bff"}
PRESETS = {"orange": _c.ORANGE, "red": _c.RED, "green": _c.GREEN,
           "yellow": _c.YELLOW, "blue": _c.BLUE, "pink": _c.PINK,
           "purple": _c.PURPLE, "white": _c.WHITE}


def color_to_hex(c: Color) -> str:
    if c.is_rgb:
        r, g, b = (min(255, v * 4) for v in c.rgb)
        return f"#{r:02x}{g:02x}{b:02x}"
    return PALETTE_HEX.get(c.index, "#888888")


def hex_to_rgb(h: str) -> Color:
    h = h.lstrip("#")
    return rgb(int(h[0:2], 16) // 4, int(h[2:4], 16) // 4, int(h[4:6], 16) // 4)


def state_color(v):
    """A button state colour: '#rrggbb' -> RGB, or a preset name (pulses/flashes)."""
    if isinstance(v, str) and v.startswith("#"):
        return hex_to_rgb(v)
    return PRESETS.get(v, _c.WHITE)


class WebUI:
    def __init__(self, dispatch_mode: str = "dry"):
        self.queue = JobQueue()
        self.con = Console(queue=self.queue)
        self.config = self._load()
        self.lock = threading.Lock()
        self.apply(self.config)
        self.dispatch_mode = dispatch_mode
        if dispatch_mode == "dry":
            threading.Thread(target=self._dry_dispatcher, daemon=True).start()

    # -- persistence --------------------------------------------------------
    def _load(self) -> dict:
        if CONFIG_PATH.exists():
            try:
                return json.loads(CONFIG_PATH.read_text())
            except json.JSONDecodeError:
                pass
        return {"buttons": [], "animations": []}

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(self.config, indent=2))

    # -- build the live console from a config -------------------------------
    def apply(self, config: dict) -> None:
        with self.lock:
            self.con.stop()
            self.con.clear_layout()
            for b in config.get("buttons", []):
                kw = {"label": b.get("label") or None,
                      "color": hex_to_rgb(b.get("color", "#003045")),
                      "idle_level": float(b.get("dim", 0.7))}
                for k in ("pressed", "running", "complete", "error"):
                    if b.get(k):
                        kw[k] = state_color(b[k])
                kind = b.get("type", "prompt")
                if kind == "shell":
                    ActionButton.shell(self.con, b["x"], b["y"], b.get("command", ""), **kw)
                elif kind == "prompt":
                    PromptButton(self.con, b["x"], b["y"], b.get("prompt", ""), **kw)
                else:
                    ActionButton(self.con, b["x"], b["y"], **kw)
            for a in config.get("animations", []):
                region = [tuple(c) for c in a.get("cells", [])]
                if not region:
                    continue
                kind = a.get("type", "twinkle")
                if kind == "breathe":
                    self.con.animate(_anim.Breathe(region, color=hex_to_rgb(a.get("color", "#0030ff"))))
                elif kind == "rainbow":
                    self.con.animate(_anim.RainbowWave(region))
                else:
                    self.con.animate(_anim.Twinkle(region))
            self.config = config
            self.con.start()

    # -- live state for the browser -----------------------------------------
    def state(self) -> dict:
        cells = {}
        for (x, y), c in self.con.snapshot().items():
            cells[f"{x},{y}"] = {"hex": color_to_hex(c)}
        for w in self.con.widgets:
            meta = cells.setdefault(f"{w.x},{w.y}", {"hex": "#0c0c10"})
            meta["state"] = w.state.name.lower()
            meta["label"] = getattr(w, "label", None)
            meta["kind"] = "prompt" if isinstance(w, PromptButton) else "action"
        return {"connected": self.con.lp.connected, "cells": cells,
                "dispatch": self.dispatch_mode}

    def press(self, x: int, y: int) -> None:
        self.con._route(ButtonEvent(x, y, True, 127, "note", 0))

    # -- built-in dry-run "agent" so the lifecycle is visible immediately ---
    def _dry_dispatcher(self) -> None:
        while True:
            for job in self.queue.pending():
                if self.queue.claim(job):
                    time.sleep(1.4)
                    self.queue.set_status(job.id, "done", result="(dry-run ok)")
            time.sleep(0.25)


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------
def make_handler(app: WebUI):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass  # quiet

        def _json(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_body(self) -> dict:
            n = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(n) or b"{}")

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                html = (STATIC / "index.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)
            elif self.path == "/api/state":
                self._json(app.state())
            elif self.path == "/api/config":
                self._json(app.config)
            else:
                self.send_error(404)

        def do_POST(self):
            try:
                if self.path == "/api/config":
                    cfg = self._read_body()
                    app.apply(cfg)
                    app.save()
                    self._json({"ok": True})
                elif self.path == "/api/press":
                    b = self._read_body()
                    app.press(int(b["x"]), int(b["y"]))
                    self._json({"ok": True})
                else:
                    self.send_error(404)
            except Exception as exc:  # surface errors to the client
                self._json({"ok": False, "error": str(exc)}, code=500)

    return Handler


def serve(host: str = "127.0.0.1", port: int = 8765, dispatch_mode: str = "dry",
          open_browser: bool = True) -> None:
    try:
        app = WebUI(dispatch_mode=dispatch_mode)
    except LaunchpadNotFound as e:
        print("Launchpad not found:", e)
        print("The UI still runs as an editor, but won't light the board.")
        raise SystemExit(1)
    httpd = ThreadingHTTPServer((host, port), make_handler(app))
    url = f"http://{host}:{port}"
    print(f"staunchpad UI → {url}   (dispatch: {dispatch_mode}; Ctrl-C to stop)")
    if open_browser:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.con.stop()


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="staunchpad web UI")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--dispatch", choices=["dry", "off"], default="dry",
                    help="dry = built-in fake agent (see lifecycle); off = none")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)
    serve(port=args.port, dispatch_mode=args.dispatch, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
