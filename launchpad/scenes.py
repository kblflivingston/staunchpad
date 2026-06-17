"""Save and recall full-surface colour snapshots ("scenes").

The hardware can't report its own LED state, so a scene is an app-side model:
a ``{(x, y): Color}`` mapping you build, persist, and push back with
:meth:`Launchpad.render`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from .color import Color, OFF, parse as parse_color

Scene = dict[tuple[int, int], Color]


def new_scene(fill: Color = OFF) -> Scene:
    """An all-``fill`` scene covering every addressable coordinate."""
    from . import layout as L
    return {pos: fill for pos in L.rapid_order()}


def to_json(scene: Mapping[tuple[int, int], object]) -> str:
    """Serialise a scene to JSON (keys ``"x,y"``, values ``[red, green]``)."""
    obj = {}
    for (x, y), c in scene.items():
        c = parse_color(c)
        if c:  # omit off LEDs to keep files small
            obj[f"{x},{y}"] = [c.red, c.green]
    return json.dumps(obj, indent=2, sort_keys=True)


def from_json(text: str) -> Scene:
    """Parse JSON produced by :func:`to_json`."""
    obj = json.loads(text)
    scene: Scene = {}
    for key, rg in obj.items():
        x, y = (int(p) for p in key.split(","))
        scene[(x, y)] = Color(int(rg[0]), int(rg[1]))
    return scene


def save(path: str | Path, scene: Mapping[tuple[int, int], object]) -> None:
    Path(path).write_text(to_json(scene))


def load(path: str | Path) -> Scene:
    return from_json(Path(path).read_text())
