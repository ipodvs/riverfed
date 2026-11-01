---
name: studio-diagram
description: >
  Generate an Excalidraw diagram from the Riverfed wiki, matching the
  crisp wiki-atlas house style. Use whenever the user wants a "diagram",
  "excalidraw", "knowledge map", "visual", "flow chart", or "architecture
  picture" built from the wiki, or says a generated diagram looks "sketchy" or
  "off-style". Anchors the output on diagrams/wiki-atlas.excalidraw (roughness
  0, thin line-connectors, rounded rects, light-text labels) and drives node
  colours from the chosen design.
---

# Generate an Excalidraw diagram (atlas style)

The gold standard is [`diagrams/wiki-atlas.excalidraw`](../../../diagrams/wiki-atlas.excalidraw).
New diagrams must match *its* conventions, not the looser values older docs
once prescribed.

## Run it

From `/studio`, or CLI:

```powershell
py -3.13 wiki\scripts\studio_diagram.py --wiki wiki --prompt "..." --design designs\heritage.md
```

`--design` is optional (defaults to the house/atlas palette). The design's
palette drives the **node/accent colours**; the canvas stays a dark map.

## The house style (what "atlas style" means)

The generator's prompt already enforces this — it's here so you can spot when
output drifts:

- **`roughness: 0`** (clean/crisp) on essentially everything. Roughness 1
  everywhere is the sketchy look we avoid.
- **`strokeWidth: 1`** default, 2 for emphasis. Thin, elegant lines.
- **Connectors are thin `line` elements, NOT `arrow`s.** The atlas connects
  nodes with clean lines, not sketchy arrowheads.
- Rounded rectangles (`roundness.type: 3`), `fillStyle: solid`.
- `fontFamily: 4` (Excalifont) for headings/body, `3` (Cascadia) for eyebrows.
- Light-text labels (`#e6e8ee` body, `#cae3ff` soft); node strokes rotate the
  saber palette (blue/green/yellow/purple) for category coding.
- Map-like grid/radial layout with generous spacing — readable, not cramped.

If a generated diagram comes out sketchy/heavy/arrow-y, the fix is the
**prompt anchoring on the atlas** (already in `studio_diagram.py`), not
hand-editing the JSON.

## Viewing

`.excalidraw` files open at [excalidraw.com](https://excalidraw.com) (drag the
file in) or in the Excalidraw VS Code extension.

## References (read on demand)

- [`wiki/training/design.md`](../../../wiki/training/design.md) →
  "Excalidraw conventions" — the full element-defaults table + palette
- [`diagrams/wiki-atlas.excalidraw`](../../../diagrams/wiki-atlas.excalidraw)
  — the exemplar to replicate
