#!/usr/bin/env python3
"""Studio generator: spaced-repetition flashcards from a knowledge base.

Same split as the native PPTX generator: Claude Code (headless) reads the
vault and emits a JSON card spec; Python renders it deterministically —
here to a real Anki package (.apkg via genanki) that imports straight
into Anki desktop/mobile. "Teach forever": the wiki you built becomes the
deck you review.

Usage:
    py -3.13 wiki/scripts/studio_anki.py --wiki wiki \\
        --prompt "the agent-architecture concepts" [--cards 30] [--design <path>]

Outputs (next to each other in wiki/training/studio/anki/):
    <slug>.cards.json    the reviewable/editable card spec
    <slug>.apkg          the importable Anki package

Prints `RENDERED:json:<rel>` + the .apkg path as the final stdout line
(server.py's studio dispatch contract). `--design` is accepted for API
consistency; card styling is Anki-native, so it is not applied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

# The provider layer, imported at module level because the
# --provider help text is built from it during argparse setup.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent_runner  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]


def slugify(s: str, max_len: int = 60) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    s = re.sub(r"[-\s]+", "-", s)
    return s[:max_len].rstrip("-") or "deck"


PROMPT_TEMPLATE = """You are the Riverfed flashcard author. Read a knowledge base and
emit a JSON spec of spaced-repetition cards.

User request: {user_prompt}

Source knowledge base: `{wiki}/` — read `SCHEMA.md` + `index.md` first,
then the pages relevant to the request (all of them if the request says
everything). Write cards that earn their reviews:

- ATOMIC — one fact/idea per card; if the answer needs "and", split it.
- The front is a precise question someone could fail ("What threshold
  promotes a concept page in the karpathy-wiki model?"), never a topic
  label or a yes/no question.
- The back is the answer in 1-3 sentences, keeping the WHY when the
  source explains it, and ends with the source page slug in parentheses.
- Prefer the durable knowledge (patterns, rules, definitions, numbers,
  trade-offs) over news/anecdotes.
- Ground every card in the base's pages — do not invent facts. Target
  ~{cards} cards; fewer is fine if the base is thin on the topic.
- Tag each card with the page slugs it draws from (kebab-case).

Write EXACTLY this JSON shape to `{out_rel}` (UTF-8, no trailing
comments):

{{
  "deck": "<Short deck name>",
  "description": "<one line — what this deck teaches>",
  "cards": [
    {{"front": "<question>", "back": "<answer (source-slug)>",
      "tags": ["source-slug", "topic-slug"]}}
  ]
}}

You are running NON-INTERACTIVE (headless); edits are pre-approved.
When done, print exactly one line:
  WROTE {out_rel}
"""


def render_apkg(spec: dict, out_apkg: Path) -> int:
    """Deterministic JSON → .apkg. Returns the card count."""
    import genanki

    deck_name = str(spec.get("deck") or "Riverfed deck").strip()
    description = str(spec.get("description") or "")
    cards = spec.get("cards") or []
    if not isinstance(cards, list) or not cards:
        raise ValueError("spec has no cards")

    def stable_id(text: str) -> int:
        # genanki wants stable 31-bit ids — derive from the name so a
        # re-generated deck UPDATES in Anki instead of duplicating.
        return int(hashlib.sha1(text.encode("utf-8")).hexdigest()[:8], 16) & 0x7FFFFFFF

    model = genanki.Model(
        # Never change these stable_id seeds: a new seed changes every
        # deck/model id and forks users' existing Anki decks instead of
        # updating them in place.
        stable_id("riverfed-basic-model"),
        "Riverfed Basic",
        fields=[{"name": "Front"}, {"name": "Back"}],
        templates=[{
            "name": "Card 1",
            "qfmt": "{{Front}}",
            "afmt": "{{FrontSide}}<hr id='answer'>{{Back}}",
        }],
        css=".card { font-family: Inter, Segoe UI, Arial, sans-serif; font-size: 19px; "
            "text-align: left; color: #1a1c1e; background: #fafaff; padding: 6px; }\n"
            "hr#answer { border: none; border-top: 2px solid #4f8cff; }",
    )
    deck = genanki.Deck(stable_id(f"riverfed-deck-{deck_name}"), deck_name,
                        description=description)

    count = 0
    for card in cards:
        if not isinstance(card, dict):
            continue
        front = str(card.get("front") or "").strip()
        back = str(card.get("back") or "").strip()
        if not front or not back:
            continue
        tags = [re.sub(r"[^\w-]", "-", str(t)) for t in (card.get("tags") or [])
                if str(t).strip()]
        deck.add_note(genanki.Note(model=model, fields=[front, back],
                                   tags=tags,
                                   guid=genanki.guid_for(deck_name, front)))
        count += 1
    if count == 0:
        raise ValueError("no usable cards in the spec")

    genanki.Package(deck).write_to_file(str(out_apkg))
    return count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki", required=True,
                    help="Path to the knowledge base (e.g. 'wiki')")
    ap.add_argument("--prompt", required=True,
                    help="What the deck should teach")
    ap.add_argument("--cards", type=int, default=30,
                    help="Target card count (default 30)")
    ap.add_argument("--out-dir", default="wiki/training/studio/anki")
    ap.add_argument("--design", default=None,
                    help="Accepted for Studio API consistency; not applied.")
    ap.add_argument("--provider", default="auto",
                    help=agent_runner.provider_arg_help(
                        "run this generation on"))
    args = ap.parse_args()

    from _wikis import display_path, resolve_vault_dir
    wiki_dir = resolve_vault_dir(args.wiki)
    wiki_rel = display_path(wiki_dir)
    if not (wiki_dir / "index.md").exists():
        print(f"Error: no knowledge base at {wiki_rel}/", file=sys.stderr)
        return 2

    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(args.prompt)
    out_json = out_dir / f"{slug}.cards.json"
    out_apkg = out_dir / f"{slug}.apkg"
    json_rel = out_json.relative_to(ROOT).as_posix()

    cards_n = max(5, min(200, args.cards))
    prompt = PROMPT_TEMPLATE.format(user_prompt=args.prompt, wiki=wiki_rel,
                                    cards=cards_n, out_rel=json_rel)

    # Agent invocation goes through the provider layer (A6 step 1).
    provider, pstatus = agent_runner.resolve_provider(args.provider)
    if provider is None:
        print(f"Error: {agent_runner.unavailable_message(pstatus)}",
              file=sys.stderr)
        return 2

    print(f"[studio_anki] authoring cards from {wiki_rel} -> {json_rel}",
          file=sys.stderr)
    res = agent_runner.run(prompt, cwd=ROOT, timeout=600,
                           add_dirs=[ROOT, wiki_dir], provider=provider)
    if res.timed_out:
        print("Error: card authoring timed out after 10 minutes.", file=sys.stderr)
        return 3
    if res.returncode != 0:
        sys.stderr.write(res.stderr or "")
        return res.returncode
    if not out_json.exists():
        sys.stderr.write((res.output or "")[-1000:] + "\n")
        print(f"Error: the agent did not write {json_rel}", file=sys.stderr)
        return 4

    try:
        spec = json.loads(out_json.read_text(encoding="utf-8"))
        count = render_apkg(spec, out_apkg)
    except Exception as exc:
        print(f"Error: card spec -> apkg failed: {exc}", file=sys.stderr)
        return 5

    print(f"[studio_anki] {count} card(s) -> {out_apkg.name}", file=sys.stderr)
    print(f"RENDERED:json:{json_rel}")
    print(out_apkg.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
