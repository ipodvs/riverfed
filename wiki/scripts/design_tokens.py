#!/usr/bin/env python3
"""Parse a design.md file (google-labs-code/design.md spec) into
structured tokens that studio renderers can use to override their
hardcoded palette + typography.

Design.md format:
  ---
  name: Heritage
  colors:
    primary: "#1A1C1E"
    secondary: "#6C7278"
  typography:
    h1:
      fontFamily: Public Sans
      fontSize: 3rem
  rounded: { sm: 4px, md: 8px }
  spacing: { sm: 8px, md: 16px }
  components:
    button-primary:
      backgroundColor: "{colors.tertiary}"
      textColor: "{colors.on-tertiary}"
  ---

  ## Overview ...
  ## Colors ...

This module:
- Parses the YAML front matter
- Resolves `{path.to.token}` references (e.g. `{colors.primary}`)
- Returns a `DesignTokens` dataclass with .colors, .typography,
  .rounded, .spacing, .components

Spec: https://github.com/google-labs-code/design.md

Usage:
    from design_tokens import load_design
    d = load_design(Path("designs/heritage.md"))
    print(d.colors["primary"])               # "#1A1C1E"
    print(d.typography["h1"]["fontSize"])    # "3rem"
    print(d.color("primary"))                # "1A1C1E"  (hex without #)
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DesignTokens:
    """Resolved design.md tokens."""
    name: str = ""
    description: str = ""
    colors: dict[str, str] = field(default_factory=dict)
    typography: dict[str, dict[str, Any]] = field(default_factory=dict)
    rounded: dict[str, str] = field(default_factory=dict)
    spacing: dict[str, str] = field(default_factory=dict)
    components: dict[str, dict[str, Any]] = field(default_factory=dict)
    source_path: Path | None = None
    # Provenance — set by load_designs():
    #   "shipped" = lives in designs/<id>.md (committed presets)
    #   "custom"  = lives in designs/custom/<id>.md (user-created/edited)
    source: str = "shipped"
    # True if a custom version overrides a same-id shipped preset
    overrides_shipped: bool = False

    # --- convenience accessors with sensible fallbacks ---

    def color(self, key: str, default_hex: str = "4f8cff") -> str:
        """Return colour as hex WITHOUT the leading '#'. Lower-case.
        Falls back to saber-blue if the token isn't defined."""
        v = self.colors.get(key, "")
        if not v:
            return default_hex.lstrip("#").lower()
        return str(v).lstrip("#").lower()

    def font_family(self, role: str, default: str = "Inter") -> str:
        """Pull `fontFamily` from a typography role (e.g. 'h1', 'body-md')."""
        spec = self.typography.get(role) or {}
        return spec.get("fontFamily", default)

    def font_size_pt(self, role: str, default_pt: float = 18) -> float:
        """Pull `fontSize` from a typography role, converted to points.

        CSS rem (assuming 16 px = 12 pt base) and px → pt approximations.
        The Studio renderer doesn't need pixel-perfect parity — it just
        needs proportional scaling between the roles."""
        spec = self.typography.get(role) or {}
        raw = spec.get("fontSize")
        if raw is None:
            return default_pt
        s = str(raw).strip().lower()
        try:
            if s.endswith("rem"):
                return float(s[:-3]) * 12.0
            if s.endswith("em"):
                return float(s[:-2]) * 12.0
            if s.endswith("px"):
                return float(s[:-2]) * 0.75
            if s.endswith("pt"):
                return float(s[:-2])
            return float(s)
        except ValueError:
            return default_pt


# --- tiny YAML front-matter parser ---
#
# We avoid taking a YAML dependency. The design.md front matter is a
# small, predictable shape: top-level keys, nested keys for typography/
# components, hex strings with quotes, plain numbers, > folded scalars.
#
# This parser supports exactly what the spec needs:
#   key: value                       (scalar)
#   key: "value"                     (quoted scalar)
#   key: >                           (folded scalar; lines until next top-level)
#   key:                             (nested mapping; next lines are 2+ spaces indented)
#     subkey: value
#     nested:
#       subsubkey: value
#
# It rejects gracefully on YAML it doesn't understand (returns what
# parsed cleanly, prints a stderr note).

def _strip_inline_comment(v: str) -> str:
    """Strip end-of-line `# comment` while respecting quoted strings."""
    out: list[str] = []
    quote: str | None = None
    for ch in v:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
            out.append(ch)
            continue
        if ch == "#":
            break  # rest of the line is a comment
        out.append(ch)
    return "".join(out).rstrip()


def _strip_value(v: str) -> str:
    v = _strip_inline_comment(v).strip()
    if not v:
        return v
    # Strip matched outer quotes
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        return v[1:-1]
    return v


def _parse_inline_mapping(s: str) -> dict[str, Any]:
    """Parse `{ key: val, key: val }` inline mapping (used in compact form)."""
    s = s.strip()
    if not (s.startswith("{") and s.endswith("}")):
        return {}
    body = s[1:-1].strip()
    if not body:
        return {}
    out: dict[str, Any] = {}
    # Split on commas not inside quotes/braces. Simple state machine.
    parts: list[str] = []
    depth = 0
    quote: str | None = None
    buf: list[str] = []
    for ch in body:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
            buf.append(ch)
            continue
        if ch == "{":
            depth += 1
            buf.append(ch)
            continue
        if ch == "}":
            depth -= 1
            buf.append(ch)
            continue
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    if buf:
        parts.append("".join(buf))
    for p in parts:
        if ":" not in p:
            continue
        k, v = p.split(":", 1)
        out[k.strip()] = _strip_value(v)
    return out


def _parse_front_matter(text: str) -> dict[str, Any]:
    """Parse the YAML front matter between --- fences. Returns a dict
    suitable for DesignTokens consumption."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}
    body = m.group(1)
    lines = body.splitlines()

    root: dict[str, Any] = {}
    # Stack of (indent_level, dict_to_write_into)
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    folded_target: tuple[dict[str, Any], str] | None = None
    folded_indent: int = -1
    folded_buf: list[str] = []

    def flush_folded():
        nonlocal folded_target, folded_indent, folded_buf
        if folded_target is not None:
            parent, key = folded_target
            parent[key] = " ".join(s.strip() for s in folded_buf if s.strip())
        folded_target = None
        folded_indent = -1
        folded_buf = []

    for raw in lines:
        if not raw.strip():
            continue
        if raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()

        # Handle continuation of a folded scalar
        if folded_target is not None:
            if indent > folded_indent:
                folded_buf.append(line)
                continue
            flush_folded()

        # Pop stack until we find the right parent for this indent
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]

        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()

        if not value:
            # New nested mapping
            new_map: dict[str, Any] = {}
            parent[key] = new_map
            stack.append((indent, new_map))
        elif value == ">":
            # Folded scalar; collect indented lines below
            folded_target = (parent, key)
            folded_indent = indent
            folded_buf = []
        elif value.startswith("{") and value.endswith("}"):
            parent[key] = _parse_inline_mapping(value)
        else:
            parent[key] = _strip_value(value)

    flush_folded()
    return root


def _resolve_refs(value: Any, root: dict[str, Any]) -> Any:
    """Recursively resolve `{path.to.token}` references against root."""
    if isinstance(value, str):
        m = re.fullmatch(r"\{([\w.-]+)\}", value.strip())
        if m:
            parts = m.group(1).split(".")
            cur: Any = root
            for p in parts:
                if isinstance(cur, dict) and p in cur:
                    cur = cur[p]
                else:
                    return value  # unresolved
            return cur
        return value
    if isinstance(value, dict):
        return {k: _resolve_refs(v, root) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_refs(v, root) for v in value]
    return value


def load_design(path: Path) -> DesignTokens:
    """Load a design.md file and return resolved DesignTokens."""
    text = path.read_text(encoding="utf-8")
    fm = _parse_front_matter(text)
    fm = _resolve_refs(fm, fm)

    return DesignTokens(
        name=str(fm.get("name", path.stem)),
        description=str(fm.get("description", "")),
        colors=dict(fm.get("colors") or {}),
        typography=dict(fm.get("typography") or {}),
        rounded=dict(fm.get("rounded") or {}),
        spacing=dict(fm.get("spacing") or {}),
        components=dict(fm.get("components") or {}),
        source_path=path,
    )


def find_designs(root: Path) -> list[DesignTokens]:
    """Back-compat alias — returns shipped designs only. New code
    should use list_designs() which unions shipped + custom."""
    return [d for d in list_designs(root) if d.source == "shipped"
            and not d.overrides_shipped]


def list_designs(root: Path) -> list[DesignTokens]:
    """Return the merged catalogue of shipped + custom designs.

    - Shipped:  designs/<id>.md
    - Custom:   designs/custom/<id>.md (user-created or edited)
    - When a custom design has the same id as a shipped design, the
      custom one wins AND its `overrides_shipped` flag is set.
    """
    out: dict[str, DesignTokens] = {}
    shipped_dir = root / "designs"
    custom_dir = root / "designs" / "custom"

    for p in sorted(shipped_dir.glob("*.md")):
        if p.name.lower() == "readme.md":
            continue
        try:
            d = load_design(p)
            d.source = "shipped"
            out[p.stem] = d
        except Exception as exc:
            print(f"warning: failed to load {p}: {exc}")

    if custom_dir.exists():
        for p in sorted(custom_dir.glob("*.md")):
            try:
                d = load_design(p)
                d.source = "custom"
                d.overrides_shipped = p.stem in out
                out[p.stem] = d
            except Exception as exc:
                print(f"warning: failed to load {p}: {exc}")

    # Stable ordering: shipped (original order) first, then customs alpha
    shipped_order = [p.stem for p in sorted(shipped_dir.glob("*.md"))
                     if p.name.lower() != "readme.md"]
    custom_only = [k for k in sorted(out.keys()) if k not in shipped_order]
    ordered = [out[k] for k in shipped_order if k in out] + \
              [out[k] for k in custom_only]
    return ordered


# === Serialization ============================================================

def _yaml_quote(s: str) -> str:
    """Quote a string for YAML. Always double-quotes; escapes embedded
    quotes and backslashes. Simple — design.md values are short."""
    if s is None:
        return '""'
    s = str(s)
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _yaml_value(v: Any) -> str:
    """Format a single scalar for YAML output."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).strip()
    if not s:
        return '""'
    # Dimension-like values (e.g. "8px", "1.5rem", "-0.02em") emit unquoted
    if re.fullmatch(r"-?\d+(?:\.\d+)?(?:px|rem|em|pt|%)", s):
        return s
    # Hex colors → quoted with the # preserved
    if re.fullmatch(r"#[0-9A-Fa-f]{3,8}", s):
        return _yaml_quote(s)
    # Token references {colors.primary} — quoted (safer)
    if s.startswith("{") and s.endswith("}"):
        return _yaml_quote(s)
    # Anything else with special YAML characters → quote
    if any(c in s for c in ':#[]{},&*!|>%@`"\''):
        return _yaml_quote(s)
    if s.lower() in {"yes", "no", "true", "false", "null", "~", "on", "off"}:
        return _yaml_quote(s)
    return s  # bare string is fine


def _emit_mapping(out: list[str], data: dict[str, Any], indent: int) -> None:
    """Recursively emit a mapping as YAML lines. Stable key order."""
    pad = " " * indent
    for k, v in data.items():
        if isinstance(v, dict):
            out.append(f"{pad}{k}:")
            _emit_mapping(out, v, indent + 2)
        elif isinstance(v, list):
            out.append(f"{pad}{k}:")
            for item in v:
                if isinstance(item, dict):
                    out.append(f"{pad}  -")
                    _emit_mapping(out, item, indent + 4)
                else:
                    out.append(f"{pad}  - {_yaml_value(item)}")
        else:
            out.append(f"{pad}{k}: {_yaml_value(v)}")


def serialize_design(d: DesignTokens, body: str | None = None) -> str:
    """Render a DesignTokens object back to design.md format.

    `body` is the markdown body after the YAML front matter. If None,
    a minimal Overview / Colors / Typography skeleton is emitted from
    the description + token data."""
    fm: dict[str, Any] = {"version": "alpha", "name": d.name or ""}
    if d.description:
        fm["description"] = d.description
    if d.colors:
        fm["colors"] = dict(d.colors)
    if d.typography:
        fm["typography"] = {k: dict(v) for k, v in d.typography.items()}
    if d.rounded:
        fm["rounded"] = dict(d.rounded)
    if d.spacing:
        fm["spacing"] = dict(d.spacing)
    if d.components:
        fm["components"] = {k: dict(v) for k, v in d.components.items()}

    yaml_lines: list[str] = ["---"]
    _emit_mapping(yaml_lines, fm, 0)
    yaml_lines.append("---")
    yaml = "\n".join(yaml_lines)

    if body is None:
        prose: list[str] = ["", "## Overview", "",
                            d.description.strip() if d.description else
                            f"A custom design preset for {d.name or 'this deck'}."]
        if d.colors:
            prose += ["", "## Colors", ""]
            for k, v in d.colors.items():
                prose.append(f"- **{k}** — `{v}`")
        if d.typography:
            prose += ["", "## Typography", ""]
            for role, spec in d.typography.items():
                family = spec.get("fontFamily") if isinstance(spec, dict) else None
                if family:
                    prose.append(f"- **{role}** — {family}")
        body = "\n".join(prose) + "\n"

    return yaml + "\n" + body


def save_design(path: Path, d: DesignTokens, body: str | None = None) -> None:
    """Write a design to disk in design.md format. Creates parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_design(d, body=body), encoding="utf-8")


if __name__ == "__main__":
    # Quick smoke test
    import sys
    ROOT = Path(__file__).resolve().parent.parent.parent
    for d in find_designs(ROOT):
        print(f"=== {d.name} ({d.source_path.name if d.source_path else '?'}) ===")
        print(f"  primary={d.color('primary')}  secondary={d.color('secondary')}")
        print(f"  h1 font={d.font_family('h1')}, size={d.font_size_pt('h1'):.1f}pt")
        print(f"  components: {list(d.components.keys())[:4]}")
