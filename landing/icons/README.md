# Riverfed icons

Original icon set for Riverfed. **Single source of truth:**
[`build.py`](build.py) generates every `.svg` and every `png/<name>*.png` in
this folder (except the `riverfed-mark*` favicon files) is
generated from it.

## Why this exists

We previously used icons from the [Streamline](https://streamlinehq.com)
library that were borrowed from the Computacenter brand library (CC
licenses Streamline for *their* brand use). Continuing to ship them
inside Riverfed would have been IP-theft from the CC brand
licence. These originals replace them and remove the legal risk.

The `riverfed-mark*.svg` files are the Riverfed favicon. This is the only
pictorial brand use; pages and decks carry the text wordmark instead. These
files were never part of the issue and were left untouched.

## Style spec

| Property      | Value                                 |
|---------------|---------------------------------------|
| viewBox       | `0 0 64 64` (4px grid, 16 cells)      |
| Default color | `#4f8cff` (saber-blue)                |
| Fill          | `currentColor` (themeable)            |
| Stroke        | none; flat filled shapes only         |
| Depth         | `opacity` 0.5-0.85 (no shadows)       |
| Corner radius | `rx=2-4` on rectangles                |
| AI motif      | 4-point sparkle, reused everywhere    |

The icons inherit from `currentColor` so they theme automatically when
embedded inline. Used as `<img src="...">` they show in the default
saber-blue. To override:

```html
<!-- Inline (themeable) -->
<svg class="icon"><use href="folder-spark.svg#icon"/></svg>
<style>.icon { color: #7a59e2; }</style>   /* renders purple */
```

## PNG variants (for pptx embedding)

The pptx renderer can't recolour an SVG at embed time, so `build.py`
also emits one 256px **transparent PNG** variant in [`png/`](png/) for
each saber-colour accent:

| Suffix    | Colour            | Used when                    |
|-----------|-------------------|------------------------------|
| (none)    | `#4f8cff` blue    | Default; accent = saber-blue |
| `-purple` | `#7a59e2` neural  | Accent = neural purple       |
| `-green`  | `#46c98b` circuit | Accent = circuit green       |
| `-yellow` | `#ffd93d` voltage | Accent = voltage yellow      |

So `folder-spark.png`, `folder-spark-purple.png`, `folder-spark-green.png`,
`folder-spark-yellow.png` all exist. 22 icons × 4 colours = 88 PNGs,
plus 2 riverfed-mark PNGs = 90 files.

The `_add_icon(slide, name, x, y, size, accent_hex=...)` helper in
`studio_pptx.py` resolves the accent → suffix mapping and embeds the
matching variant. Cells with no accent get the default saber-blue.

**Transparency**: svglib+reportlab always renders to an opaque white
canvas. `build.py` post-processes via PIL: convert to RGBA, scale
alpha by `min(R,G,B) > 200` (pure white → alpha 0; near-white
anti-aliased fringe → partial alpha). Result: icons sit cleanly on
any background, not as white squares.

## The set

22 utility icons + 3 logo files (25 total).

### Network / connectivity
| | |
|-|-|
| `hub-integration.svg`  | Central node + 4 satellites for MCP/integrations |
| `network.svg`          | 5 connected nodes for distributed systems        |

### Files / storage
| | |
|-|-|
| `folder-spark.svg`  | Folder with AI sparkle |
| `file-spark.svg`    | Page with corner fold + sparkle |
| `database-ai.svg`   | 3-cylinder stack + sparkle |
| `layers.svg`        | 3 stacked rounded rects |
| `layers-stack.svg`  | Pyramid stack for abstraction layers |

### AI / sparks
| | |
|-|-|
| `ai-spark.svg`  | The brand sparkle motif, used solo and large |

### Comms
| | |
|-|-|
| `chat-check.svg`     | Speech bubble + checkmark |
| `mail-send.svg`      | Envelope |
| `announcement.svg`   | Bullhorn-shaped megaphone |
| `megaphone.svg`      | Speaker-cone megaphone with sound stripe |

### Devices
| | |
|-|-|
| `laptop.svg`  | Screen + base |

### People
| | |
|-|-|
| `users-team.svg`         | 3 overlapping person silhouettes |
| `critical-thinking.svg`  | Head silhouette + sparkle |

### Time
| | |
|-|-|
| `calendar-schedule.svg`  | Calendar grid + binding rings + date dots |

### System
| | |
|-|-|
| `cog.svg`  | 8-tooth gear with cut-out center |

### Business
| | |
|-|-|
| `coins-stack.svg`  | 3 stacked coins (ellipses) |
| `trophy.svg`       | Cup with handles + stem + base |

### Product / build
| | |
|-|-|
| `browser-build.svg`  | Browser chrome + chevron + dash |
| `startup.svg`        | Rocket + flame trail |

### Workflow
| | |
|-|-|
| `loop.svg`  | Circular arrow for a recurring cycle |

### Brand marks (untouched, Riverfed-original)
| | |
|-|-|
| `riverfed-mark.svg`        | Ink square + green dot for light surfaces and the favicon |
| `riverfed-mark-ivory.svg`  | Ivory square + green dot for dark deck covers      |

## Regenerating

After editing `build.py`:

```powershell
py -3.13 landing/icons/build.py
```

The script overwrites every `.svg` listed in the `ICONS` dict (the 22
generated ones). It does not touch the 3 logo files.

## Adding a new icon

1. Add an entry to `ICONS` in `build.py`; keep to ~3-6 shapes
2. Use the `sparkle(cx, cy, r)` helper for AI accents
3. Stay inside the style spec above
4. Run `build.py` to regenerate
