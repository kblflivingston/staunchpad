"""Save and recall full-surface colour snapshots ("scenes").

A scene is an app-side ``{(x, y): Color}`` mapping you build, persist, and push
back with :meth:`Launchpad.render`. Palette colours serialise as ``{"i": index}``
and RGB colours as ``{"rgb": [r, g, b]}``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from .color import Color, OFF, palette, rgb, parse as parse_color

Scene = dict[tuple[int, int], Color]


def new_scene(fill: Color = OFF) -> Scene:
    """An all-``fill`` scene covering every addressable coordinate."""
    from . import layout as L
    return {pos: fill for pos in L.all_coords()}


def to_json(scene: Mapping[tuple[int, int], object]) -> str:
    """Serialise a scene to JSON. Off LEDs are omitted to keep files small."""
    obj = {}
    for (x, y), c in scene.items():
        c = parse_color(c)
        if not c:
            continue
        obj[f"{x},{y}"] = {"rgb": list(c.rgb)} if c.is_rgb else {"i": c.index}
    return json.dumps(obj, indent=2, sort_keys=True)


def from_json(text: str) -> Scene:
    """Parse JSON produced by :func:`to_json`."""
    obj = json.loads(text)
    scene: Scene = {}
    for key, spec in obj.items():
        x, y = (int(p) for p in key.split(","))
        if "rgb" in spec:
            scene[(x, y)] = rgb(*spec["rgb"])
        else:
            scene[(x, y)] = palette(spec["i"])
    return scene


def save(path: str | Path, scene: Mapping[tuple[int, int], object]) -> None:
    Path(path).write_text(to_json(scene))


def load(path: str | Path) -> Scene:
    return from_json(Path(path).read_text())
