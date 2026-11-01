#!/usr/bin/env python3
"""Translate the canonical Marp handbook into a native, editable .pptx.

The Marp deck at wiki/training/ai-builders-handbook.md is the source
of truth for content. This script builds a 36-slide python-pptx
document so anyone can open it in PowerPoint and hand-edit cleanly
(real text boxes, real shapes, embedded brand icons, brand-mark
diamond on every content slide — no flattened HTML).

The HANDBOOK dict below is the source of truth for the pptx version.
When you update the Marp deck, also edit HANDBOOK (or vice versa).
They're two presentations of the same content; we haven't wired up a
Marp parser to keep them in lock-step.

Slide-type usage in this handbook (see studio_pptx.py docstring for
the full vocabulary of 13 types):
  - 1 cover, 3 lead, 6 section (one per module)
  - 4 content, 3 kpi, 1 donut-kpi, 4 versus
  - 5 cards (parallel siblings), 4 flow (sequential steps),
    4 six-up (tight catalogues), 1 hub (Four C's = parts of AIOS),
    1 timeline (30/60/90 onboarding cadence)

Atomic-swap output (handles PowerPoint file lock):
  - Build always writes to wiki/training/out/ai-builders-handbook-
    native.tmp.pptx first.
  - Then tries Path.replace() to move tmp -> canonical .pptx.
  - If PowerPoint has the canonical file open, the swap raises
    PermissionError; we keep the .tmp.pptx and print a friendly
    warning. Close PowerPoint and re-run to land the swap.
  - .tmp.pptx is in .gitignore.

Output:
  wiki/training/out/ai-builders-handbook-native.pptx          (binary)
  wiki/training/out/ai-builders-handbook-native.pptx.json     (sidecar —
                                                               studio_guide
                                                               can speaker-
                                                               note from it)

Usage (from repo root):
    .venv\\Scripts\\python.exe wiki/training/scripts/build_handbook_pptx.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

# Reach into wiki/scripts/studio_pptx.py for the renderer
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "wiki" / "scripts"))
from studio_pptx import build_pptx  # noqa: E402

OUT_PPTX = ROOT / "wiki" / "training" / "out" / "ai-builders-handbook-native.pptx"
OUT_JSON = OUT_PPTX.with_suffix(".pptx.json")


HANDBOOK: dict = {
    "title": "The AI Builders Handbook",
    "subtitle": "Agents · Design · Marketing · Business — distilled from builders shipping real products.",
    "audience": "Builders, founders, operators who already know what an agent is",
    "slides": [
        # ============ FOUNDATIONS ============
        {
            "type": "cover",
            "title": "The AI Builders Handbook",
            "subtitle": "Agents · Design · Marketing · Business — distilled from builders shipping real products.",
            "tags": ["25 sources", "6 concepts", "11 topics", "27 entities", "Markdown-native"],
        },
        {
            "type": "lead",
            "eyebrow": "In one sentence",
            "headline": "Most decks talk about AI. This one shows you how operators use it.",
            "cite": "Every claim traces back to a video transcript in wiki/sources/",
        },
        {
            "type": "six-up",
            "title": "The shape of this training",
            "items": [
                {"num": "Module 1", "title": "Foundations", "desc": "Six mental models that change how you operate.", "icon": "critical-thinking"},
                {"num": "Module 2", "title": "Architecture", "desc": "Why every modern agent is the same shape.", "icon": "layers-stack"},
                {"num": "Module 3", "title": "Build & Operate", "desc": "From toy demos to production systems.", "icon": "cog"},
                {"num": "Module 4", "title": "Marketing", "desc": "The vibe-marketing stack, end to end.", "icon": "megaphone"},
                {"num": "Module 5", "title": "Design & Coding", "desc": "Taste as the moat.", "icon": "laptop"},
                {"num": "Module 6", "title": "Business", "desc": "$100B companies with <5 employees.", "icon": "coins-stack"},
            ],
        },
        {
            "type": "section",
            "number": "01",
            "module": "Module 1",
            "title": "Foundations",
            "subtitle": "Six mental models that change how you operate.",
        },
        {
            "type": "six-up",
            "title": "The six concepts",
            "items": [
                {"num": "01", "title": "Terminal as interface", "desc": "One session: research, design, copy, deploy.", "icon": "laptop"},
                {"num": "02", "title": "Markdown is oxygen", "desc": "The substrate for context, memory, output.", "icon": "file-spark"},
                {"num": "03", "title": "Memory = write failures", "desc": "If the agent forgets, the bug is in the write.", "icon": "database-ai"},
                {"num": "04", "title": "Opportunity > tokens", "desc": "Price on value delivered, not spend.", "icon": "coins-stack"},
                {"num": "05", "title": "Distribution > engineering", "desc": "Ship-and-distribute > build-perfectly.", "icon": "megaphone"},
                {"num": "06", "title": "Agent-friendly websites", "desc": "20% of e-commerce traffic by 2030 = agents.", "icon": "network"},
            ],
            "cite": "concepts/ (six pages)",
        },
        {
            "type": "content",
            "eyebrow": "Concept 01",
            "title": "Terminal as the interface of work",
            "bullets": [
                "Research, design, copy, ad creative, A/B tests, deploys — one session",
                "Context, tools, execution converge in one place",
                "Nine independent sources land on this frame",
                "It's why Claude Code, Codex, OpenClaw all feel the same",
            ],
            "callout": '"The terminal is the interface of work." — Greg Isenberg',
            "cite": "concepts/terminal-as-the-interface · 9 sources",
        },
        {
            "type": "versus",
            "eyebrow": "Concept 02 + 03",
            "title": "Two markdown rules that compound",
            "old": {
                "title": "Markdown is just text",
                "desc": "What most people see: format for blog posts, README files, notes.",
                "bullets": ["Static, decorative", "One-way: human writes, human reads"],
            },
            "new": {
                "title": "Markdown is the agent's oxygen",
                "desc": "What operators see: the substrate for context, memory, skills, outputs.",
                "bullets": ["Live, queryable, append-only", "Round-trip: agent reads → acts → writes → reads"],
            },
            "callout": "Corollary: if your agent forgets a correction, the bug isn't in retrieval — it's in what you wrote.",
            "cite": "concepts/markdown-as-llm-substrate · memory-failures-are-write-failures",
        },
        {
            "type": "kpi",
            "eyebrow": "Concepts 04, 05, 06",
            "title": "The economic shift",
            "kpis": [
                {"value": "$150", "label": "Token spend for a board memo that beats 4 hours of analyst time."},
                {"value": "0×", "label": "Marginal cost of one more landing-page variant."},
                {"value": "20%", "label": "Of e-commerce traffic by 2030 = agents shopping for humans."},
            ],
            "callout": "Stop pricing on tokens, start pricing on value delivered.",
            "cite": "concepts/opportunity-cost-vs-token-cost · distribution-over-engineering · agent-friendly-websites",
        },
        {
            "type": "kpi",
            "eyebrow": "Concepts in the macro",
            "title": "A universal superpower",
            "kpis": [
                {"value": "20×", "label": "Programmer productivity Andreessen attributes to AI-augmented builders."},
                {"value": "2–4×", "label": "Corporate overstaffing — the 'AI vampires' slowing the shift down."},
                {"value": "$100B", "label": "Companies now plausible with under five employees."},
            ],
            "callout": "The builder role is collapsing coder, PM, and designer into one operator. The leverage isn't the role — it's the toolchain underneath it.",
            "cite": "sources/the-golden-age-thesis-marc-andreessen-on-mts",
        },

        # ============ ARCHITECTURE ============
        {
            "type": "section",
            "number": "02",
            "module": "Module 2",
            "title": "Architecture",
            "subtitle": "Every modern AI agent is the same shape — and that's the leverage.",
        },
        {
            "type": "versus",
            "title": "What is an agent?",
            "old": {
                "title": "Chat",
                "desc": "Question → answer.",
                "bullets": ["One turn", "Stateless", "You drive every step"],
            },
            "new": {
                "title": "Agent",
                "desc": "Goal → loop until done.",
                "bullets": ["Observe → think → act, repeated", "Persists between sessions"],
            },
            "callout": '"Chat is question-to-answer. Agent is goal-to-result."',
            "cite": "sources/building-ai-agents · agentic-ai-systems-clearly-explained",
        },
        {
            "type": "flow",
            "title": "The spectrum: chatbot → system",
            "steps": [
                {"num": "L1", "title": "Chatbot", "desc": "Question → answer. Stateless. You drive every step.", "icon": "chat-check"},
                {"num": "L2", "title": "Workflow", "desc": "Multi-step but fixed. The LLM fills slots in a script you wrote.", "icon": "loop"},
                {"num": "L3", "title": "Agentic workflow", "desc": "Same script, but the LLM picks which steps to skip, repeat, revisit.", "icon": "cog"},
                {"num": "L4", "title": "Agentic system", "desc": "The LLM defines the goal-state, the loop, and which tools to call.", "icon": "hub-integration"},
            ],
            "callout": "Pick the level you actually need. Most 'agent' projects only need L2 or L3 — labelling them L4 is the over-engineering trap.",
            "cite": "sources/agentic-ai-systems-clearly-explained · claude-cowork-fundamentals",
        },
        {
            "type": "cards",
            "title": "Four pieces of every production agent",
            "cards": [
                {"num": "01", "title": "Model", "desc": "The brain. Opus 4.7, GPT 5.5, etc.", "icon": "critical-thinking"},
                {"num": "02", "title": "Context", "desc": "agents.md + memory.md. Role + learned rules.", "icon": "file-spark"},
                {"num": "03", "title": "Tools", "desc": "MCP servers — Gmail, Linear, Stripe, your data.", "icon": "hub-integration"},
                {"num": "04", "title": "Skills", "desc": "Markdown SOPs. Reusable procedures.", "icon": "layers-stack"},
            ],
            "callout": "Master these four files and you can switch harnesses without rebuilding the workflow.",
            "cite": "sources/building-ai-agents · claude-code-agentic-os-unstoppable",
        },
        {
            "type": "content",
            "title": "Same engine, different car",
            "bullets": [
                "Claude Code — terminal-first, Anthropic, deepest tool ecosystem",
                "Codex — GUI-first super-app from OpenAI (GPT 5.5)",
                "OpenClaw — open-source persistent personal agent",
                "Cursor / Cowork / HyperAgent / Manus — same loop, different ergonomics",
            ],
            "callout": "Invest in the loop (skills, context files, harnesses) — your investment ports across every tool you'll touch next year.",
            "cite": "topics/ai-coding-tools · entities/claude-code · codex · openclaw · manus",
        },

        # ============ BUILD & OPERATE ============
        {
            "type": "section",
            "number": "03",
            "module": "Module 3",
            "title": "Build & Operate",
            "subtitle": "From toy demos to production systems.",
        },
        {
            "type": "hub",
            "eyebrow": "Nate Herk · AIOS course",
            "title": "The Four C's of an AIOS",
            "hub": "AIOS",
            "spokes": [
                {"title": "C1 · Context",      "desc": "What the agent knows about you. agents.md, memory.md, plus the wiki it queries."},
                {"title": "C2 · Connections",  "desc": "API endpoints + CLI tools. Often beats MCP servers on tokens."},
                {"title": "C3 · Capabilities", "desc": "Skills — markdown SOPs in .claude/skills/. Reusable, composable, agent-readable."},
                {"title": "C4 · Cadence",      "desc": "Scheduled routines — cloud (laptop off), local (desktop on), /loop (in-session crons)."},
            ],
            "callout": "Each layer depends on the one below. No Cadence without Capabilities; no Capabilities without Connections; nothing works without Context.",
            "cite": "sources/build-sell-claude-code-operating-systems",
        },
        {
            "type": "flow",
            "title": "Onboard your agent like an employee",
            "steps": [
                {"num": "01", "title": "Define", "desc": "Write agents.md — the job description.", "icon": "critical-thinking"},
                {"num": "02", "title": "Wire", "desc": "Hook up 3 MCPs: search, your data, the action target.", "icon": "hub-integration"},
                {"num": "03", "title": "Train", "desc": "Run on real tasks. Correct in memory.md.", "icon": "cog"},
                {"num": "04", "title": "Schedule", "desc": "Turn the recurring procedure into a skill, cron it.", "icon": "calendar-schedule"},
            ],
            "callout": "Cadence: meaningful improvements at 30 / 60 / 90 days. Same as hiring a junior.",
            "cite": "sources/building-ai-agents · ai-agents-run-my-business",
        },
        {
            "type": "timeline",
            "eyebrow": "Onboarding cadence",
            "title": "Same shape as hiring a junior",
            "milestones": [
                {"label": "DAY 0",  "title": "Define",            "desc": "Write agents.md. Wire 3 MCPs. Run the first test task."},
                {"label": "DAY 30", "title": "First wins",        "desc": "Routine tasks land cleanly. Corrections flow into memory.md."},
                {"label": "DAY 60", "title": "Routine ops",       "desc": "Most workflows on autopilot. You sample-check, don't direct."},
                {"label": "DAY 90", "title": "Trusted autopilot", "desc": "Different agent altogether. Your role shifts to judgment."},
            ],
            "callout": "The capability is the same. The discipline isn't.",
            "cite": "sources/building-ai-agents · making-with-ai-agents",
        },
        {
            "type": "donut-kpi",
            "eyebrow": "The arbitrage",
            "title": "Persistence is the moat",
            "kpis": [
                {"value": "30%", "label": "Casual-user output quality"},
                {"value": "90%", "label": "Daily-user output after 90 days"},
            ],
            "callout": "3× the output quality — from nothing but showing up. 99% one-shot a prompt and quit. The 1% who use it daily for 90 days are unrecognisable.",
            "cite": "sources/making-with-ai-agents · howie-liu",
        },
        {
            "type": "versus",
            "title": "Context engineering beats prompt engineering",
            "old": {
                "title": "Prompt engineering",
                "desc": "Clever wording. 'You are an expert in…' 'Think step by step…'",
                "bullets": ["Manual every time", "Doesn't compound", "Brittle to model changes"],
            },
            "new": {
                "title": "Context engineering",
                "desc": "Rich agents.md + accumulating memory.md + examples folder.",
                "bullets": ["Load once, leverage forever", "Compounds weekly", "Survives model upgrades"],
            },
            "callout": '"A two-word prompt produces excellent output if agents.md is rich."',
            "cite": "sources/building-ai-agents",
        },
        {
            "type": "content",
            "eyebrow": "New tooling · ships in Claude Code",
            "title": "The fleet dashboard",
            "bullets": [
                "`claude agents` opens a native multi-session dashboard in the terminal",
                "Three swim lanes: Needs input · Working · Completed",
                "Spacebar peeks into any session without entering it",
                "`/bg` backgrounds any standalone Claude Code session into the dashboard",
                "Sessions persist across dashboard restarts — close, come back, resume",
            ],
            "callout": '"If you don\'t visually see it, you tend to forget about it." — Chase AI, on why fleet awareness matters when you\'re juggling 3–6 concurrent agents.',
            "cite": "sources/claude-code-just-got-a-dashboard",
        },

        # ============ MARKETING ============
        {
            "type": "section",
            "number": "04",
            "module": "Module 4",
            "title": "Marketing",
            "subtitle": "The vibe-marketing stack — end-to-end inside one terminal.",
        },
        {
            "type": "flow",
            "title": "The pipeline",
            "steps": [
                {"num": "01", "title": "Research", "desc": "Perplexity + Firecrawl + Playwright. Find the competitive gap.", "icon": "critical-thinking"},
                {"num": "02", "title": "Context", "desc": "Idea Browser MCP pipes ICP, positioning, offer into the agent.", "icon": "file-spark"},
                {"num": "03", "title": "Build", "desc": "Positioning → copy → design → lead magnet → Remotion video.", "icon": "cog"},
                {"num": "04", "title": "Ship", "desc": "Vercel + HumbleLytics. A/B test variants by morning.", "icon": "startup"},
            ],
            "cite": "sources/ai-marketing-masterclass · my-claude-code-workflow",
        },
        {
            "type": "cards",
            "eyebrow": "Jonathan Courtney · AJ&Smart",
            "title": "The Promoter Blueprint",
            "cards": [
                {"num": "01", "title": "Traffic", "desc": "Organic + paid. Where your audience first hears your name.", "icon": "network"},
                {"num": "02", "title": "Holding pattern", "desc": "Newsletter, podcast, social. Keep them warm.", "icon": "loop"},
                {"num": "03", "title": "Selling event", "desc": "Webinar, campaign, retargeting. The conversion moment.", "icon": "megaphone"},
                {"num": "04", "title": "Conversion", "desc": "Non-converters loop back into the holding pattern.", "icon": "trophy"},
            ],
            "callout": "Marketing strategy upstream of tactics. Most people optimise step 3 (sell). Winners design the loop.",
            "cite": "sources/claude-code-built-my-450k-marketing-campaign",
        },
        {
            "type": "cards",
            "title": "Three growth levers most builders ignore",
            "cards": [
                {"num": "AEO", "title": "Answer Engine Optimization", "desc": "Be cited by Perplexity / ChatGPT / Claude. Monitor with Otterly, Profound. SEO is dying; AEO replaces it.", "icon": "ai-spark"},
                {"num": "MCP", "title": "MCP as distribution channel", "desc": "Publish to Smithery, MCPT, OpenTools. Every AI assistant = a 24/7, zero-CAC sales rep.", "icon": "hub-integration"},
                {"num": "Buy", "title": "Newsletter acquisition", "desc": "$5–20K acquisitions in niches. Pre-built distribution + warm audience + recurring revenue.", "icon": "mail-send"},
            ],
            "cite": "sources/stop-vibe-coding-start-getting-customers",
        },

        # ============ DESIGN & CODING ============
        {
            "type": "section",
            "number": "05",
            "module": "Module 5",
            "title": "Design & Coding",
            "subtitle": "Taste is the new moat. Code is the cheap part.",
        },
        {
            "type": "content",
            "title": "design.md — the portable blueprint",
            "bullets": [
                "Tokens (colour, type, spacing) live as roles, not raw values",
                "Reasoning + values are co-located with the design specs",
                "CLI linter lets agents self-validate generated UI",
                "One markdown file portable across web, mobile, slides, docs",
            ],
            "callout": "The 'soul' of a design in one markdown file. Taste survives every harness migration.",
            "cite": "sources/googles-design-md · meet-designmd-a-new-open-standard-for-ai-generated-ui",
        },
        {
            "type": "cards",
            "title": "The new levels of AI coding",
            "cards": [
                {"num": "L1", "title": "Code completion", "desc": "Copilot-style autocomplete. You drive.", "icon": "chat-check"},
                {"num": "L2", "title": "Prompt-to-snippet", "desc": "'Write me a function that…' You glue.", "icon": "file-spark"},
                {"num": "L3", "title": "Vibe coding", "desc": "Whole files / features from intent. You review + merge.", "icon": "ai-spark"},
                {"num": "L4", "title": "Agentic coding", "desc": "Multi-step, tool-using, looped builds. You set goals + accept.", "icon": "hub-integration"},
            ],
            "cite": "sources/agentic-ai-systems-clearly-explained · making-with-ai-agents",
        },

        # ============ BUSINESS ============
        {
            "type": "section",
            "number": "06",
            "module": "Module 6",
            "title": "Business",
            "subtitle": "$100B companies with under five employees.",
        },
        {
            "type": "kpi",
            "title": "The Tiny model — agents in production",
            "kpis": [
                {"value": "132", "label": "Portfolio companies at Andrew Wilkinson's Tiny."},
                {"value": "$40K", "label": "Monthly Claude bill — replacing multiple ops headcount."},
                {"value": "2 wks", "label": "For a CFO with zero coding to ship a $50K platform replacement."},
            ],
            "callout": '"Support as a job is months away from disappearing."',
            "cite": "sources/ai-agents-run-my-business",
        },
        {
            "type": "versus",
            "title": "CEO = Promoter, not Builder",
            "old": {
                "title": "Old model",
                "desc": "The CEO builds the company. Hires, manages, ships features, runs ops.",
                "bullets": ["Scale by hiring humans", "10-person team = 10-person output", "Software is the moat"],
            },
            "new": {
                "title": "New model",
                "desc": "The CEO promotes the company. Picks channels; agents handle execution.",
                "bullets": ["Scale by hiring agents", "1-person team = 10-person output", "Distribution + compute are the moats"],
            },
            "cite": "concepts/distribution-over-engineering · sources/claude-code-built-my-450k-marketing-campaign",
        },
        {
            "type": "six-up",
            "eyebrow": "Where to start your AI agent business today",
            "title": "The five-step playbook",
            "items": [
                {"num": "01", "title": "Pick a vertical", "desc": "Where AI replaces a $1K–$10K/month line item.", "icon": "critical-thinking"},
                {"num": "02", "title": "Build the agent", "desc": "As an internal workflow first. Get it bullet-proof.", "icon": "cog"},
                {"num": "03", "title": "Sell as managed service", "desc": "Not SaaS. $5–20K/month. Opportunity-cost pricing.", "icon": "mail-send"},
                {"num": "04", "title": "Scale with agents, not humans", "desc": "Each new client = clone the agent + customise the context.", "icon": "users-team"},
                {"num": "05", "title": "Park gains in infrastructure", "desc": "Software moats erode. Compute moats compound.", "icon": "layers-stack"},
            ],
            "cite": "sources/how-to-start-an-ai-agent-business-today · ai-agents-run-my-business · the-golden-age-thesis",
        },
        {
            "type": "flow",
            "eyebrow": "A concrete starter idea · Karpathy's open-source loop",
            "title": "Autoresearch as a niche business",
            "steps": [
                {"num": "01", "title": "Pick a tight niche", "desc": "Amazon listings · email sequences · SaaS pricing · clinical-trial design.", "icon": "critical-thinking"},
                {"num": "02", "title": 'Define "better"', "desc": "A single scalar — clicks, revenue, conversion, model score.", "icon": "trophy"},
                {"num": "03", "title": "Charge monthly", "desc": '"Press accept, get winners." Recurring revenue; compute as the moat.', "icon": "coins-stack"},
            ],
            "callout": "The bottleneck isn't compute. Compute is rented. The bottleneck is picking the right niche and the right metric. That's a judgment problem — and judgment is uncopiable.",
            "cite": "sources/karpathys-autoresearch · entities/karpathy",
        },

        # ============ WRAP ============
        {
            "type": "lead",
            "headline": "Pick one harness. Build one agent. Use it daily for 90 days.",
            "eyebrow": "The whole training in one line",
            "cite": "Curate the markdown vault that lives behind it. Then ship — distribution-first.",
        },
        {
            "type": "six-up",
            "title": "Minimum viable AI builder",
            "items": [
                {"num": "01", "title": "One harness", "desc": "Claude Code, Codex, or OpenClaw. Pick. Don't shop.", "icon": "laptop"},
                {"num": "02", "title": "One agents.md", "desc": "Your standing role. 200 words.", "icon": "file-spark"},
                {"num": "03", "title": "Three MCPs", "desc": "Search, your data, your action target.", "icon": "hub-integration"},
                {"num": "04", "title": "Five skills", "desc": "Your recurring workflows.", "icon": "cog"},
                {"num": "05", "title": "One vault", "desc": "Markdown. Everything you learn.", "icon": "folder-spark"},
                {"num": "06", "title": "One shipped thing", "desc": "Distribution-first. Not engineering-first.", "icon": "startup"},
            ],
        },
        {
            "type": "lead",
            "headline": "Now go build.",
            "eyebrow": "The wiki is the textbook · this deck is the course",
            "cite": "25 sources · 6 concepts · 11 topics · 27 entities — all in wiki/",
        },
    ],
}


def main() -> int:
    OUT_PPTX.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(HANDBOOK, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    # Write to a temp filename and swap into place, so we can rebuild
    # even when PowerPoint has the canonical file open (which holds an
    # exclusive lock on Windows).
    tmp_pptx = OUT_PPTX.with_suffix(".tmp.pptx")
    build_pptx(HANDBOOK, tmp_pptx)
    rel_pptx = OUT_PPTX.relative_to(ROOT).as_posix()
    rel_json = OUT_JSON.relative_to(ROOT).as_posix()
    try:
        tmp_pptx.replace(OUT_PPTX)
        final_path = OUT_PPTX
    except PermissionError:
        # PowerPoint still has it open; leave the new build at the
        # temp filename so it's at least available to inspect.
        final_path = tmp_pptx
        print(f"warning: {rel_pptx} is locked (close PowerPoint to swap). "
              f"New build available at {tmp_pptx.relative_to(ROOT).as_posix()}",
              file=sys.stderr)
    print(f"wrote {final_path.relative_to(ROOT).as_posix()}  "
          f"({final_path.stat().st_size:,} bytes, "
          f"{len(HANDBOOK['slides'])} slides)")
    print(f"wrote {rel_json}  (sidecar — studio_guide.py can speaker-note from this)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
