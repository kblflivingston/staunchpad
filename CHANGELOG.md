# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
