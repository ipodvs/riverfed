#!/usr/bin/env python3
"""One-shot update: renumber existing slide sections to match the
35-slide deck and inject speaker-notes for the 5 new slides.

After this runs, ai-builders-handbook-speaker-notes.md has a section
for every slide in ai-builders-handbook.md, in order. Then re-run
build_speaker_doc.py to refresh the .docx.

Usage:
    py -3.13 wiki/training/scripts/update_speaker_notes.py
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NOTES = ROOT / "wiki" / "training" / "ai-builders-handbook-speaker-notes.md"

NEW_SECTIONS = {
    9: """## Slide 9 — Dark content: *A universal superpower* (KPI block)

**On screen:** Dark slide. Three KPIs: **20×** (programmer productivity, Andreessen). **2–4×** (corporate overstaffing — "AI vampires"). **$100B** (solo-founder companies plausible with <5 staff). Callout about the builder role collapsing.

**Script:**

> *"Three more numbers. Twenty times. Two to four times. A hundred billion."*

> *"20× — Andreessen's claim about programmer productivity in an AI-augmented world. Not 1.5×, not 3× — 20×. That's a different industry."*

> *"2 to 4× — corporate overstaffing. Andreessen calls them 'AI vampires' — incumbents whose business model depends on slow rollout. Most of the people pushing back have a reason to want this transition to take a decade."*

> *"A hundred billion dollars — companies are now plausible with under five employees. That's a vertical I-told-you-so for solo founders."*

**Rhetorical hook:**

> *"If the builder role is collapsing the coder, the PM, and the designer into one operator — what's the leverage left? Not the role. The toolchain underneath it."*

(Beat. Don't rush. This is the macro framing the rest of the deck lives inside.)

**Bridge:** *"End of Module 1 — the why. Now: what does that toolchain actually look like?"*

---
""",

    12: """## Slide 12 — Content: *The spectrum: chatbot → system* (4-card grid)

**On screen:** Four cards in different Jedi colors. L1 Chatbot (green), L2 Workflow (yellow), L3 Agentic workflow (orange), L4 Agentic system (purple). Callout: "Pick the level you actually need."

**Script:**

> *"Simon Scrapes has a framework I keep coming back to. Four levels."*

> *"L1, the chatbot. Question to answer. You drive every step. ChatGPT in the browser."*

> *"L2, the workflow. Multi-step but fixed. The LLM fills slots in a script that **you** wrote. n8n with an OpenAI node."*

> *"L3, the agentic workflow. Same script — but the LLM picks which steps to skip, repeat, or revisit. The control flow is dynamic."*

> *"L4, the agentic system. The LLM defines the goal-state, the loop, and which tools to call. This is what Claude Code does."*

**Rhetorical hook:**

> *"Pick the level you actually need. Most projects pitched as 'agents' only need L2 or L3. Calling them L4 is the over-engineering trap — and that's what gives 'agents' a bad reputation when they fail."*

**Bridge:** *"Once you've picked the level, the architecture inside is the same shape. Four pieces. Let's open it up."*

---
""",

    16: """## Slide 16 — Content: *The Four C's of an AIOS* (4-card grid)

**On screen:** Four cards in Jedi colors. C1 Context (yellow), C2 Connections (purple), C3 Capabilities (green), C4 Cadence (orange). Callout: "Each layer depends on the one below."

**Script:**

> *"Nate Herk runs a course on building an AIOS — an AI Operating System inside Claude Code. The most useful frame he uses is the Four C's."*

> *"C1 — Context. What the agent knows about you. Your `agents.md`, your `memory.md`, the wiki it queries. This is the layer most builders skip — and it's the one that everything else depends on."*

> *"C2 — Connections. APIs and CLIs. Gmail, ClickUp, Stripe. Nate makes a point worth stealing — direct API calls with a markdown reference guide often beat MCP servers on tokens, because MCPs expose every endpoint and chew context budget."*

> *"C3 — Capabilities. Skills as markdown SOPs in `.claude/skills/`. The recipes your agent can pick up and run. Reusable, composable, agent-readable."*

> *"C4 — Cadence. Scheduled routines. Cloud routines run with your laptop closed. Local tasks need the desktop app open. Slash-loop creates short crons inside a session."*

**Rhetorical hook:**

> *"Punchline: each layer depends on the one below. No Cadence without Capabilities. No Capabilities without Connections. Nothing works without Context. So when your agent breaks, start at the bottom of the stack."*

**Bridge:** *"Let's start there — Context. Onboarding the agent. That's next."*

---
""",

    20: """## Slide 20 — Dark content: *The fleet dashboard*

**On screen:** Dark slide. `claude agents` command in mono. Three swim lanes: Needs input · Working · Completed. Chase AI quote on the right.

**Script:**

> *"Quick tactical note — Anthropic just shipped a native dashboard inside Claude Code. The command is `claude agents`."*

> *"Three swim lanes. **Needs input** — sessions waiting on you. **Working** — already running. **Completed** — ready to ship."*

> *"Spacebar peeks into any session without entering it. Slash-bg backgrounds any standalone Claude Code session and pulls it into the dashboard. Sessions persist across dashboard restarts — close the laptop, come back, resume."*

**Rhetorical hook:**

> *"Chase AI has the cleanest justification — 'if you don't visually see it, you tend to forget about it.' If you're running three or more concurrent agents — and once you've built Capabilities you will be — the dashboard is fleet awareness. Without it, you forget about half your fleet."*

**Bridge:** *"End of Module 3. We leave the build side now and move into how you market what you've built."*

---
""",

    32: """## Slide 32 — Content: *Autoresearch as a niche business* (two-column)

**On screen:** Two-column. Left: pattern explanation + Karpathy quote — "The bottleneck is judgment, not compute." Right: three numbered cards — Pick a tight niche · Define "better" · Charge monthly.

**Script:**

> *"One concrete starter idea before we close. Karpathy open-sourced something called Autoresearch a few months ago."*

> *"The pattern is simple. Define a metric you want to maximize — clicks, revenue, conversion, any single scalar. The loop generates variants. Keeps the ones that improve the metric. Throws the rest away. You press accept on the winners."*

> *"Now — the principle generalizes way past hyperparameter search. Greg Isenberg walked through ten business ideas built on this loop. Optimizing Amazon listings. Email subject lines. SaaS pricing pages. Clinical-trial design. Anywhere there's a measurable goal and cheap iteration."*

> *"Pick the niche. Define 'better' as a scalar. Rent the GPU — Colab, Lambda, RunPod, doesn't matter. Build the loop. Charge monthly."*

**Rhetorical hook:**

> *"The bottleneck isn't compute. Compute is rented. The bottleneck is picking the right niche and the right metric. That's a judgment problem. And judgment — for now — is uncopiable."*

**Bridge:** *"And that's the field. Foundations, architecture, operations, marketing, design, business. One lead slide to land it."*

---
""",
}

# Map: existing slide number → new slide number (for renumbering only the
# headers; bodies stay the same).
RENUMBER = {
    9: 10,   # Module 02 section
    10: 11,  # What is an agent?
    11: 13,  # Four pieces
    12: 14,  # Same engine
    13: 15,  # Module 03 section
    14: 17,  # Onboard
    15: 18,  # Persistence
    16: 19,  # Context engineering
    17: 21,  # Module 04 section
    18: 22,  # Pipeline
    19: 23,  # Promoter Blueprint
    20: 24,  # Three growth levers
    21: 25,  # Module 05 section
    22: 26,  # design.md
    23: 27,  # New levels
    24: 28,  # Module 06 section
    25: 29,  # Tiny model
    26: 30,  # CEO Promoter
    27: 31,  # Five-step playbook
    28: 33,  # Lead "whole training"
    29: 34,  # MVP builder
    30: 35,  # Now go build
}


def main() -> int:
    text = NOTES.read_text(encoding="utf-8")

    # 1) Renumber headers (do high → low to avoid clobbering 10 with 1+0 etc.)
    for old in sorted(RENUMBER.keys(), reverse=True):
        new = RENUMBER[old]
        # Tag with a sentinel marker first so subsequent passes don't re-match.
        text = re.sub(
            rf"^## Slide {old} — ",
            f"## Slide §{new}§ — ",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    # Replace sentinel markers with the real new numbers
    text = re.sub(r"## Slide §(\d+)§ — ", lambda m: f"## Slide {m.group(1)} — ", text)

    # 2) Insert new sections immediately before the section whose number is
    # one higher (so slide 9 inserts before slide 10, slide 12 before 13,
    # slide 16 before 17, slide 20 before 21, slide 32 before 33).
    insertion_anchor = {9: 10, 12: 13, 16: 17, 20: 21, 32: 33}
    for new_num in sorted(NEW_SECTIONS.keys(), reverse=True):
        anchor = insertion_anchor[new_num]
        anchor_pattern = rf"(^## Slide {anchor} — )"
        section_body = NEW_SECTIONS[new_num]
        text, n = re.subn(
            anchor_pattern,
            f"{section_body}{chr(10)}\\1",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if n == 0:
            print(f"warn: could not find anchor for new slide {new_num} (anchor was {anchor})")

    # 3) Update the top-of-file slide count header if it says 30
    text = re.sub(r"30-slide", "35-slide", text)
    text = re.sub(r"30 slides", "35 slides", text)

    NOTES.write_text(text, encoding="utf-8")
    print(f"wrote {NOTES}")
    print(f"  renumbered {len(RENUMBER)} existing headers")
    print(f"  inserted {len(NEW_SECTIONS)} new sections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
