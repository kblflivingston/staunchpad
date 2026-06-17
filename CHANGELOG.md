# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `Console`: a high-level panel of programmable buttons with a press → running →
  complete/error → idle state machine, configurable per-state colours, and
  brightness dimming.
- `PromptButton` / `ActionButton`: buttons that signal a prompt to an always-on
  agent (via the job queue) or run a local action synchronously.
- `dispatch.JobQueue`: a tiny atomic file-based job queue — the "signal" between
  the board and your agent — plus a reference `examples/dispatcher.py`.
- `animations`: ambient `Breathe` / `Twinkle` / `RainbowWave` over `rect` / `row`
  / `col` / `cells` regions, diffed and rendered each frame.
- `Color.dimmed()` / `color.dim()` for smooth RGB brightness scaling.
- A MIDI write lock so the animation loop and action workers can share the device.

## [0.1.0]

Initial release. Full programming interface for the **Novation Launchpad MK2**,
verified against real hardware:

- `Launchpad`: auto-detecting connection, single-LED control (palette and RGB),
  hardware flash and pulse, whole row/column fills, single-message full-surface
  `render`, scrolling text, layout selection, and device identification.
- Event system: `@on_press` / `@on_release` / `@on_button` / `@on` handlers with
  a friendly `(x, y)` coordinate model.
- `color`: palette-index *or* RGB colour model, named palette, and a flexible
  `parse()` (names, ints, `[r,g,b]`, `#rrggbb`).
- `scenes`: save and recall full-surface snapshots as JSON.
- `widgets`: `App` runloop plus `Toggle`, `Momentary`, `RadioGroup`,
  `ColorCycle`, and `Button`.
- `staunchpad-detect` console command and five runnable examples.
- 21 hardware-free unit tests covering the protocol, colour, and layout layers.
