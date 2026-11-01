#!/usr/bin/env python3
"""Studio: generate an Excalidraw diagram from a wiki + a short user prompt.

Reads the wiki content, applies the Excalidraw conventions in
wiki/training/design.md (palette + element defaults), and asks Claude
Code (headless mode) to synthesize a diagram. Outputs the .excalidraw
JSON to diagrams/studio/<slug>.excalidraw.

Usage (from repo root):
    py -3.13 wiki/scripts/studio_diagram.py \\
        --wiki wiki \\
        --prompt "the three-layer wiki architecture"
"""
from __future__ import annotations
import argparse
import re
import sys
import unicodedata
from pathlib import Path

# The provider layer, imported at module level because the
# --provider help text is built from it during argparse setup.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent_runner  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
DESIGN_MD_REL = "wiki/training/design.md"
EXEMPLAR_REL = "diagrams/wiki-atlas.excalidraw"

# Default house diagram palette — these are the hexes the canonical
# wiki-atlas.excalidraw actually uses. A --design overrides the node colours.
_DEFAULT_PALETTE = {
    "background": "#0a0d12",   # deep space canvas
    "container": "#181b22",    # node fill
    "container_alt": "#0f1729",
    "body": "#e6e8ee",         # primary label text
    "soft": "#cae3ff",         # soft label / connector text
    "connector": "#4dbeff",    # thin line connectors / glow
    "muted": "#9aa3b5",
    # category node strokes (rotate across these)
    "nodes": ["#4f8cff", "#46c98b", "#ffd93d", "#7a59e2", "#ff6b35"],
}


def _diagram_palette(design_path: str | None) -> dict:
    """Resolve the diagram palette from a design.md, falling back to the
    house/atlas palette. Only the node/accent colours are design-driven;
    the dark canvas + light text stay (the atlas is a dark map)."""
    pal = {**_DEFAULT_PALETTE, "nodes": list(_DEFAULT_PALETTE["nodes"])}
    if not design_path:
        return pal
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from design_tokens import load_design
        d = load_design(Path(design_path))
        c = d.colors or {}
    except Exception as exc:
        print(f"[studio_diagram] design load failed: {exc} — default palette",
              file=sys.stderr)
        return pal

    def hx(k):
        v = c.get(k)
        if not v:
            return None
        s = str(v).strip()
        return s if s.startswith("#") else "#" + s

    nodes = [hx(k) for k in ("primary", "secondary", "success", "highlight", "warning")]
    nodes = [n for n in nodes if n]
    if nodes:
        pal["nodes"] = nodes
    foundation = hx("foundation")
    if foundation:
        pal["background"] = foundation
        pal["container_alt"] = foundation
    if hx("primary"):
        pal["connector"] = hx("primary")
    return pal


def slugify(s: str, max_len: int = 60) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    s = re.sub(r"[-\s]+", "-", s)
    return s[:max_len].rstrip("-") or "untitled-diagram"


def build_prompt(wiki: str, user_prompt: str, out_path: str, palette: dict) -> str:
    nodes = ", ".join(palette["nodes"])
    return f"""You are the Riverfed studio agent. Generate an Excalidraw
diagram as a `.excalidraw` JSON file.

User request: {user_prompt}

**Match the canonical exemplar exactly.** First READ
`{EXEMPLAR_REL}` and replicate its visual style — it is the gold
standard for what our diagrams look like. Mirror its element conventions:

- `roughness`: **0** (clean, crisp) on essentially everything. Do NOT use
  roughness 1 across the board — that produces the sketchy/messy look we
  are avoiding. At most one or two accents may use roughness 1.
- `strokeWidth`: **1** by default, **2** for emphasis, 3 only very
  sparingly. Thin, elegant lines — not heavy.
- Connect nodes with thin **`line`** elements (NOT `arrow`). The atlas
  uses clean connector lines, not sketchy arrowheads. Avoid `arrow`
  elements unless direction is essential, and then keep them thin.
- Rectangles get rounded corners (`roundness.type: 3`), `fillStyle: solid`.
- `fontFamily`: 4 (Excalifont) for headings/body, 3 (Cascadia) for small
  eyebrow tags. Body text `{palette['body']}`, soft labels `{palette['soft']}`.
- Lay nodes out on a clean grid / radial map with generous spacing — the
  atlas is map-like and readable, not a cramped flowchart.

Palette (use these hexes):
- Canvas `appState.viewBackgroundColor`: `{palette['background']}`
- Node fills: `{palette['container']}` (and `{palette['container_alt']}`)
- Node strokes — rotate across these for category coding: {nodes}
- Connector lines / glow: `{palette['connector']}`
- Body text `{palette['body']}`, soft labels `{palette['soft']}`, muted `{palette['muted']}`
- Sith Red rule: never use `#ff4d4d` for decorative elements — error only.

Also read `{DESIGN_MD_REL}` → "Excalidraw conventions" for the full rules,
but the exemplar above wins on any conflict. Draw content from the wiki at
`{wiki}/` if the topic needs facts. Canvas ~1000-1400 wide.

Write the final Excalidraw JSON to `{out_path}`. It must be a valid
Excalidraw v2 document with `type: "excalidraw"`, an `elements` array, and
`appState.viewBackgroundColor: "{palette['background']}"`. Do not output
anything else to stdout. When done, print a single line:
  WROTE {out_path}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out-dir", default="diagrams/studio")
    ap.add_argument("--design", default=None,
                    help="Optional design.md path. Its palette drives the "
                         "diagram's node/accent colours (canvas stays a dark "
                         "map). Falls back to the house/atlas palette.")
    ap.add_argument("--provider", default="auto",
                    help=agent_runner.provider_arg_help(
                        "run this generation on"))
    args = ap.parse_args()
    palette = _diagram_palette(args.design)
    if args.design:
        print(f"[studio_diagram] palette from {args.design}: "
              f"nodes={palette['nodes']}", file=sys.stderr)

    slug = slugify(args.prompt)
    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.excalidraw"
    rel_out = out_path.relative_to(ROOT).as_posix()

    from _wikis import resolve_vault_dir
    wiki_dir = resolve_vault_dir(args.wiki)
    prompt = build_prompt(args.wiki, args.prompt, rel_out, palette)

    # Agent invocation goes through the provider layer (A6 step 1).
    provider, pstatus = agent_runner.resolve_provider(args.provider)
    if provider is None:
        print(f"Error: {agent_runner.unavailable_message(pstatus)}",
              file=sys.stderr)
        return 2

    print(f"[studio_diagram] generating: {rel_out}", file=sys.stderr)
    try:
        res = agent_runner.run(prompt, cwd=ROOT, timeout=600,
                               add_dirs=[ROOT, wiki_dir], provider=provider)
    except FileNotFoundError:
        print(f"Error: the {provider} CLI could not be executed.",
              file=sys.stderr)
        return 2
    if res.timed_out:
        print("Error: generation timed out after 10 minutes.", file=sys.stderr)
        return 3

    if res.returncode != 0:
        sys.stderr.write(res.stderr or "")
        return res.returncode

    if not out_path.exists():
        print(f"Error: agent did not write {rel_out}", file=sys.stderr)
        sys.stderr.write(res.output or "")
        return 4

    print(rel_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
