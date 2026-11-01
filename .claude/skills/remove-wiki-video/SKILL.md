---
name: remove-wiki-video
description: >
  Cleanly remove a video (or any source) that was ingested into the Riverfed wiki by mistake — purge the source page, the local transcript +
  frames, and every cross-reference, leaving no dangling links. Use whenever
  the user says a video "was a mistake", is "off-topic", "unrelated", "shouldn't
  be in the wiki", or "remove all references to X". Emphasises finding ALL
  references first (so nothing dangles) and that git makes tracked deletions
  recoverable.
---

# Remove a mistakenly-ingested video

Goal: leave the wiki coherent — no orphan links, no half-removed cross-refs.
Tracked deletions are recoverable from git history, so this is safe to do
decisively; the local transcript/frames are gitignored (regenerable).

## Step 1 — Find EVERY reference first

Grep by all identities of the video — the slug, the YouTube id, the title
words, and any topics it introduced. Don't delete the page until you know
everywhere it's linked.

```bash
# the files named for it
ls wiki/sources/<slug>.md output/<output-slug>.md
ls -d output/<output-slug>-frames 2>/dev/null

# every cross-reference across the wiki
grep -rniE "<slug>|<video-id>|<distinctive title words>" wiki/ --include="*.md" -l
```

Open the source page's frontmatter to see the `topics:` it claimed — those may
be **orphan topics** that exist only for this video (check
`wiki/topics/<topic>.md`, `wiki/index.md`, `wiki/SCHEMA.md`'s allowed-topics
list, and `wiki/log.md`).

## Step 2 — Remove the files

```bash
git rm wiki/sources/<slug>.md                 # tracked → recoverable from history
rm -f output/<output-slug>.md                 # local transcript (gitignored)
rm -rf output/<output-slug>-frames            # frames (gitignored)
```

## Step 3 — Scrub the cross-references

Edit out every link found in step 1:
- `wiki/index.md` — the recent-sources entry **and** any topic→source mapping.
- `wiki/log.md` — the inventory row, any "flag"/note about it, and its orphan
  topics in the deferred-topics list.
- `wiki/SCHEMA.md` — drop orphan topics from the allowed-topics list.
- Any `wiki/topics/`, `wiki/entities/`, `wiki/concepts/` page that listed it
  as a source (remove it from the `sources:` array + the prose).

## Step 4 — Verify nothing dangles, then commit

```bash
grep -rniE "<slug>|<video-id>|<title words>|<orphan topics>" wiki/ output/ docs/ diagrams/ --include="*.md"
# → expect NO matches
```

Commit as `content(wiki): remove <video> — ingested by mistake`, with a body
explaining what was removed and why. If the `git add` aborts on an
already-staged deletion ("pathspec did not match"), stage the edited files
separately — the deletion is already staged.

## Notes

- If you need to bring a wrongly-deleted page back: `git restore wiki/sources/<slug>.md`.
- A re-upload merged via `alt_url:` is **not** a mistake to remove — that's the
  ingest correctly de-duplicating. Only remove genuinely off-topic content.
