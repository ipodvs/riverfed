# Ingest prompt for Claude Code

Paste this whole block into Claude Code from the project root
(`C:\Users\ipodvs\Youtuber`). It tells the agent exactly how to ingest
new transcripts using this wiki's conventions.

This is kept **in sync** with the embedded prompt inside
`wiki/scripts/ingest.py` — when one changes the other should too.

---

You are maintaining a wiki at `wiki/`. The conventions are in
`wiki/SCHEMA.md` — read it first if you haven't this session.

**Task:** ingest every transcript in `output/` that does not yet have a
matching page in `wiki/sources/`. Run
`py -3.13 wiki/scripts/pending.py` to get the list.

For **each** uningested transcript:

1. **Read the source.** The file lives in `output/<slug>.md`. The first
   ~25 lines are metadata + description, the rest is the raw transcript.

   **If the source has a `## Visual content` section near the bottom**
   (added by `convert.py --frames`), the on-screen text from each frame
   is inline as blockquotes — read those, they capture slides, code,
   dashboards, terminal output and UI labels the audio doesn't.

   **If a `output/<slug>-frames/` directory is mounted**, the frames
   themselves are available — `Read` only the frames tagged with the
   🔍 marker in the Visual content section (those are vision-relevant:
   slides, code, dashboards). Skip the · ones (talking-head footage —
   the audio transcript already covers them). Weave specific visual
   details into the wiki page, e.g. *"the swim lanes are labelled
   Needs input / Working / Completed"* — and cite the timestamp like
   `(frame t=01:24)`.

2. **Read existing topic, entity, and concept pages** in
   `wiki/topics/`, `wiki/entities/`, and `wiki/concepts/` to calibrate
   voice and find what to update.

3. **Write `wiki/sources/<slug>.md`** following the source-page template
   in `SCHEMA.md`. Required: frontmatter (slug, source_file, url, title,
   channel, duration, published, topics, entities, ingested), TL;DR,
   Top takeaways (3), Key concepts (3-7 bullets, ≤12 words each),
   Entities mentioned, Quotes (1-3 verbatim), See also.

4. **Update topic pages** (`wiki/topics/<topic>.md`):
   - If the source touches a topic that already has a page: add it to
     the `sources:` frontmatter list, add a cite or paragraph in the
     relevant section, bump `last_updated`.
   - If the source is the **second** source for a topic that currently
     lives single-source-only in `index.md`: **promote it** — create the
     topic page from the template in `SCHEMA.md`, list both sources,
     update `index.md` to move it from "Single-source items" to "Topics."
   - If the source is the **first** of a new topic: do not create a
     topic page yet. Add the item to "Single-source items" in
     `index.md`.

5. **Update / create entity pages** (`wiki/entities/<slug>.md`):
   - For every named tool, product, person, format the transcript
     names: add a one-line "Mentions" bullet to its entity page (or
     create the entity page if absent).
   - Only create new entity pages for things mentioned in ≥2 sources
     (or things that obviously deserve a page on their own — major
     tools, books, people).

6. **Handle concepts (cross-cutting themes/patterns)** —
   `wiki/concepts/<slug>.md`:
   - A *concept* is an idea/stance/pattern that recurs across multiple
     topics (e.g. "terminal as the interface of work", "memory failures
     are write failures", "CEO = promoter, not builder"). It is NOT a
     domain like `ai-marketing` — those are topics.
   - If this source explicitly names an idea that already has a concept
     page: rewrite the concept page adding this source to `sources:`
     and a new bullet under "Evidence across sources" describing the
     framing.
   - If a candidate flagged in `wiki/log.md` from prior ingests is
     named by this source AND now has ≥3 sources of evidence:
     PROMOTE — create `wiki/concepts/<slug>.md` using the concept-page
     template in `SCHEMA.md` (TL;DR / Why it matters / Evidence across
     sources / How to apply / Open questions / Sources).
   - If it's a novel idea named only here: do NOT create a page;
     record it under "Patterns crystallizing" in this ingest's
     `log.md` entry so future ingests can promote it.

7. **Update `wiki/index.md`** — add the new source under "Sources" with
   a one-line summary; register new entities in their existing sections;
   list any new concepts under a "Concepts" section; move any promoted
   topics out of "Single-source items"; bump `last_updated`.

8. **Append to `wiki/log.md`** — one entry per ingest with: date,
   source slug, topics assigned, pages created or modified, plus a
   "Patterns crystallizing" section listing any cross-cutting themes
   worth watching.

9. **Stop and report.** When you finish all pending sources, summarize:
   sources ingested, topics promoted, entities created, concepts
   created, and anything that surprised you that the user should know
   about.

Style rules:

- Dense, concrete, no fluff. Each bullet should *teach* something.
- Cite source slugs in parentheses, e.g. `(karpathys-autoresearch)`.
- **Use Obsidian wikilinks** for every internal reference: `[[slug]]` or
  `[[slug|display text]]`. **Never** use relative `[text](path.md)` for
  pages inside `wiki/`. External `https://…` links stay as standard
  markdown.
- Frontmatter is required. Filenames are kebab-case. No dates in
  filenames — frontmatter holds them.
- **Tags + aliases.** Set `tags:` on every new page (mirror `topics:` +
  `entities:` + `wiki/<folder>`; for entities also add `kind/<kind>`).
  On entity pages, add `aliases:` listing the canonical display names
  (e.g. `aliases: [Claude Code, claude code]`).
- Never edit anything in `output/`. Sources are immutable.

After ingestion, run `py -3.13 wiki/scripts/obsidian_pass.py` once to
auto-populate any tags/aliases you missed and convert any straggler
markdown links to wikilinks. It is idempotent.

For a periodic backlog promotion pass that scans `log.md` for flagged
candidates and creates concept/entity pages for everything with ≥2
sources of evidence, use `py -3.13 wiki/scripts/promote_backlog.py`
(or paste the prompt embedded in that script).

Begin.
