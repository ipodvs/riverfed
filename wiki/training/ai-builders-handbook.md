---
marp: true
theme: ai-builders
paginate: true
title: The AI Builders Handbook
description: A 35-slide training distilled from a 25-source video wiki on agents, design, marketing, and business.
tags: [wiki]
---

<!-- _class: cover -->
<!-- _paginate: false -->

<div class="cover-shapes"></div>
<div class="cover-wordmark">Riverfed<span class="dot">.</span></div>

<p class="eyebrow">A practical training</p>

# The AI Builders Handbook

## Agents · Design · Marketing · Business — distilled from builders shipping real products.

<div class="tag-row">
  <span>25 sources</span>
  <span>6 concepts</span>
  <span>11 topics</span>
  <span>27 entities</span>
  <span>Markdown-native</span>
</div>

---

<!-- _class: lead -->

<p class="eyebrow">In one sentence</p>

# Most decks talk about AI.<br>This one shows you how operators *use* it.

## Every claim traces back to a video transcript in `wiki/sources/`. Verify anything.

---

# The shape of this training

<div class="cards four">
  <div class="is-neural">
    <span class="num">Module 1</span>
    <h3>Foundations</h3>
    <p>Six mental models that change how you operate.</p>
  </div>
  <div class="is-circuit">
    <span class="num">Module 2</span>
    <h3>Architecture</h3>
    <p>Why every modern agent is the same shape.</p>
  </div>
  <div class="is-fibre">
    <span class="num">Module 3</span>
    <h3>Build &amp; Operate</h3>
    <p>From toy demos to production systems.</p>
  </div>
  <div class="is-voltage">
    <span class="num">Module 4</span>
    <h3>Marketing</h3>
    <p>The vibe-marketing stack, end to end.</p>
  </div>
</div>

<div class="cards" style="margin-top: 14px; grid-template-columns: repeat(3, 1fr);">
  <div class="is-circuit">
    <span class="num">Module 5</span>
    <h3>Design &amp; Coding</h3>
    <p>Taste as the moat.</p>
  </div>
  <div>
    <span class="num">Module 6</span>
    <h3>Business</h3>
    <p>$100B companies with &lt;5 employees.</p>
  </div>
  <div class="is-neural">
    <span class="num">Wrap-up</span>
    <h3>What good looks like</h3>
    <p>The minimum viable AI builder.</p>
  </div>
</div>

---

<!-- _class: section -->

<div class="section-num">01</div>
<p class="eyebrow">Module 1</p>

# Foundations

## Six mental models that change how you operate.

---

# The six concepts

<div class="six-up iconic">
  <div><div class="icon"><img src="assets/icons/laptop.svg" /></div><span class="num">01</span><h3>Terminal as the interface of work</h3><p>One session: research, design, copy, deploy.</p></div>
  <div><div class="icon"><img src="assets/icons/file-spark.svg" /></div><span class="num">02</span><h3>Markdown is the oxygen of LLMs</h3><p>The substrate for context, memory, output.</p></div>
  <div><div class="icon"><img src="assets/icons/database-ai.svg" /></div><span class="num">03</span><h3>Memory failures are write failures</h3><p>If the agent forgets, the bug is in the write.</p></div>
  <div><div class="icon"><img src="assets/icons/coins-stack.svg" /></div><span class="num">04</span><h3>Opportunity cost &gt; token cost</h3><p>Price on value delivered, not spend.</p></div>
  <div><div class="icon"><img src="assets/icons/megaphone.svg" /></div><span class="num">05</span><h3>Distribution beats engineering</h3><p>Ship-and-distribute > build-perfectly.</p></div>
  <div><div class="icon"><img src="assets/icons/network.svg" /></div><span class="num">06</span><h3>Agent-friendly websites</h3><p>20% of e-commerce traffic by 2030 = agents.</p></div>
</div>

<p class="cite">concepts/terminal-as-the-interface · markdown-as-llm-substrate · memory-failures-are-write-failures · opportunity-cost-vs-token-cost · distribution-over-engineering · agent-friendly-websites</p>

---

<!-- _class: dark -->

<p class="eyebrow">Concept 01</p>

# Terminal as the interface of work

<div class="two-column">
<div>

## The terminal isn't just for engineers anymore

- Research, design, copy, ad creative, A/B tests, deploys — **one session**
- Context, tools, execution converge in one place
- Five independent sources land on this frame
- It's why Claude Code, Codex, OpenClaw all *feel* the same

</div>
<div>

> "The terminal is the interface of work."

<p style="opacity: 0.7; font-size: 18px;">— Greg Isenberg, citing the pattern across his entire roster of guests.</p>

</div>
</div>

<p class="cite">concepts/terminal-as-the-interface · 9 sources (now incl. claude-cowork-fundamentals · claude-code-just-got-a-dashboard · build-sell-claude-code-operating-systems)</p>

---

<p class="eyebrow">Concept 02 + 03</p>

# Two markdown rules that compound

<div class="versus">
<div class="panel old">
<h3>Markdown is just text</h3>
<p>What most people see: format for blog posts, README files, notes.</p>
<ul>
  <li>Static, decorative</li>
  <li>One-way: human writes, human reads</li>
</ul>
</div>
<div class="arrow">→</div>
<div class="panel new">
<h3>Markdown is the agent's oxygen</h3>
<p>What operators see: the substrate for context, memory, skills, outputs.</p>
<ul>
  <li>Live, queryable, append-only</li>
  <li>Round-trip: agent reads → acts → writes → reads again</li>
</ul>
</div>
</div>

<div class="callout">
<p><strong>Corollary:</strong> if your agent forgets a correction, the bug isn't in retrieval — it's in <em>what you wrote</em>. Fix the write step.</p>
</div>

<p class="cite">concepts/markdown-as-llm-substrate (12 sources) · memory-failures-are-write-failures (6 sources) · how-i-use-obsidian-claude-code-to-run-my-life</p>

---

<p class="eyebrow">Concepts 04, 05, 06</p>

# The economic shift

<div class="kpi">
<div><strong>$150</strong><p>Token spend for a board memo<br>that beats 4 hours of analyst time.</p></div>
<div><strong>0×</strong><p>Marginal cost of one more<br>landing-page variant.</p></div>
<div><strong>20%</strong><p>Of e-commerce traffic by 2030 =<br>agents shopping for humans.</p></div>
</div>

<div class="callout">
<p><strong>The reframe:</strong> stop pricing on tokens, start pricing on <em>value delivered</em>. Stop building the perfect product, start <em>distributing</em> the rough one. Stop designing for human visitors, start designing for the agent reading your site.</p>
</div>

<p class="cite">concepts/opportunity-cost-vs-token-cost · distribution-over-engineering · agent-friendly-websites</p>

---

<!-- _class: dark -->

<p class="eyebrow">Concepts in the macro</p>

# A universal superpower

<div class="kpi">
<div><strong>20×</strong><p>Programmer productivity Andreessen attributes to AI-augmented builders.</p></div>
<div><strong>2–4×</strong><p>Corporate overstaffing — the "AI vampires" slowing the shift down.</p></div>
<div><strong>$100B</strong><p>Companies are now plausible with under five employees.</p></div>
</div>

<div class="callout">
<p><strong>The builder role is collapsing</strong> coder, PM, and designer into one operator. The leverage isn't the role — it's the toolchain underneath it.</p>
</div>

<p class="cite">sources/the-golden-age-thesis-marc-andreessen-on-mts · sources/ai-agents-run-my-business · sources/how-to-start-an-ai-agent-business-today</p>

---

<!-- _class: section -->

<div class="section-num">02</div>
<p class="eyebrow">Module 2</p>

# Architecture

## Every modern AI agent is the same shape — and that's the leverage.

---

# What is an agent?

<div class="versus">
<div class="panel old">
<h3>Chat</h3>
<p style="font-size: 22px;"><strong>Question → answer.</strong></p>
<p>One turn. Stateless. You drive every step.</p>
</div>
<div class="arrow">→</div>
<div class="panel new">
<h3>Agent</h3>
<p style="font-size: 22px;"><strong>Goal → loop until done.</strong></p>
<p>Observe → think → act, repeated. Persists between sessions.</p>
</div>
</div>

> "Chat is question-to-answer. Agent is goal-to-result."

<p class="cite">sources/building-ai-agents · sources/agentic-ai-systems-clearly-explained</p>

---

# The spectrum: chatbot → system

<div class="cards four">
  <div class="is-circuit">
    <span class="num">L1</span>
    <h3>Chatbot</h3>
    <p>Question → answer. Stateless. You drive every step.</p>
  </div>
  <div class="is-voltage">
    <span class="num">L2</span>
    <h3>Workflow</h3>
    <p>Multi-step but fixed. The LLM fills slots in a script <em>you</em> wrote.</p>
  </div>
  <div class="is-fibre">
    <span class="num">L3</span>
    <h3>Agentic workflow</h3>
    <p>Same script, but the LLM picks which steps to skip, repeat, or revisit.</p>
  </div>
  <div class="is-neural">
    <span class="num">L4</span>
    <h3>Agentic system</h3>
    <p>The LLM defines the goal-state, the loop, and which tools to call.</p>
  </div>
</div>

<div class="callout">
<p><strong>Pick the level you actually need.</strong> Most "agent" projects only need L2 or L3 — labelling them L4 is the over-engineering trap.</p>
</div>

<p class="cite">sources/agentic-ai-systems-clearly-explained · sources/claude-cowork-fundamentals-in-22-minutes</p>

---

# Four pieces of every production agent

<div class="cards four">
  <div class="is-neural">
    <div class="icon"><img src="assets/icons/ai-spark.svg" /></div>
    <span class="num">01</span>
    <h3>Model</h3>
    <p>The brain. Opus 4.7, GPT 5.5, etc.</p>
  </div>
  <div class="is-circuit">
    <div class="icon"><img src="assets/icons/folder-spark.svg" /></div>
    <span class="num">02</span>
    <h3>Context</h3>
    <p><code>agents.md</code> + <code>memory.md</code><br>Role + learned rules.</p>
  </div>
  <div class="is-fibre">
    <div class="icon"><img src="assets/icons/hub-integration.svg" /></div>
    <span class="num">03</span>
    <h3>Tools</h3>
    <p>MCP servers — Gmail, Linear, Stripe, your data.</p>
  </div>
  <div class="is-voltage">
    <div class="icon"><img src="assets/icons/layers.svg" /></div>
    <span class="num">04</span>
    <h3>Skills</h3>
    <p>Markdown SOPs. Reusable procedures.</p>
  </div>
</div>

<div class="callout">
<p><strong>Master these four files</strong> and you can switch harnesses without rebuilding the workflow.</p>
</div>

<p class="cite">sources/building-ai-agents · sources/claude-code-agentic-os-unstoppable (four-layer Agentic OS) · entities/agents-md · memory-md · skills · mcp</p>

---

# Same engine, different car

| Harness | Maker | Best for |
|---|---|---|
| **Claude Code** | Anthropic | Terminal-first, agentic coding |
| **Codex** | OpenAI | GUI super-app, docs + sheets + browser |
| **OpenClaw** | Open-source | Customizable, runs on your vault |
| **HyperAgent** | Airtable | Fleet observability, command-center |
| **Manus** | — | Computer-use specialist |
| **GenSpark** | — | Emerging super-app |

> "Once you know how to drive, you can jump in any car."

<p class="cite">topics/ai-coding-tools · entities/claude-code · codex · openclaw · hyperagent · manus</p>

---

<!-- _class: section -->

<div class="section-num">03</div>
<p class="eyebrow">Module 3</p>

# Build &amp; Operate

## From toy demos to production systems.

---

<p class="eyebrow">Nate Herk · AIOS course</p>

# The Four C's of an AIOS

<div class="cards four">
  <div class="is-voltage">
    <div class="icon"><img src="assets/icons/folder-spark.svg" /></div>
    <span class="num">C1</span>
    <h3>Context</h3>
    <p>What the agent knows about you. <code>agents.md</code>, <code>memory.md</code>, plus the wiki it queries.</p>
  </div>
  <div class="is-neural">
    <div class="icon"><img src="assets/icons/hub-integration.svg" /></div>
    <span class="num">C2</span>
    <h3>Connections</h3>
    <p>API endpoints + CLI tools — Gmail, ClickUp, Stripe. Often beats MCP servers on tokens.</p>
  </div>
  <div class="is-circuit">
    <div class="icon"><img src="assets/icons/layers.svg" /></div>
    <span class="num">C3</span>
    <h3>Capabilities</h3>
    <p>Skills — markdown SOPs in <code>.claude/skills/</code>. Reusable, composable, agent-readable.</p>
  </div>
  <div class="is-fibre">
    <div class="icon"><img src="assets/icons/calendar-schedule.svg" /></div>
    <span class="num">C4</span>
    <h3>Cadence</h3>
    <p>Scheduled routines — cloud (laptop off), local (desktop on), <code>/loop</code> (in-session crons).</p>
  </div>
</div>

<div class="callout">
<p><strong>Each layer depends on the one below.</strong> No Cadence without Capabilities; no Capabilities without Connections; nothing works without Context.</p>
</div>

<p class="cite">sources/build-sell-claude-code-operating-systems · entities/agents-md · memory-md · skills</p>

---

# Onboard your agent like an employee

<div class="steps">
  <div><div class="icon"><img src="assets/icons/critical-thinking.svg" /></div><span class="num">01</span><h3>Define</h3><p>Write <code>agents.md</code> — the job description.</p></div>
  <div><div class="icon"><img src="assets/icons/hub-integration.svg" /></div><span class="num">02</span><h3>Wire</h3><p>Hook up 3 MCPs: search, your data, the action target.</p></div>
  <div><div class="icon"><img src="assets/icons/users-team.svg" /></div><span class="num">03</span><h3>Train</h3><p>Run on real tasks. Correct in <code>memory.md</code>.</p></div>
  <div><div class="icon"><img src="assets/icons/calendar-schedule.svg" /></div><span class="num">04</span><h3>Schedule</h3><p>Turn the recurring procedure into a skill, cron it.</p></div>
</div>

<div class="callout">
<p><strong>Cadence:</strong> meaningful improvements at 30 / 60 / 90 days. Same as hiring a junior.</p>
</div>

<p class="cite">sources/building-ai-agents · ai-agents-run-my-business</p>

---

<!-- _class: dark -->

<p class="eyebrow">The arbitrage</p>

# Persistence is the moat

<div class="two-column">
<div>

## 99% of people one-shot a prompt and quit.

The 1% who use it daily for 90 days are unrecognisable from the 99%.

The capability is the same. The discipline isn't.

</div>
<div>

<div class="kpi stack">
<div><strong>30%</strong><p>Casual-user output quality</p></div>
<div><strong>90%</strong><p>Daily-user output quality after 90 days</p></div>
<div><strong>3×</strong><p>The gap. From nothing but showing up.</p></div>
</div>

</div>
</div>

<p class="cite">sources/making-with-ai-agents · howie-liu</p>

---

# Context engineering beats prompt engineering

<div class="versus">
<div class="panel old">
<h3>Prompt engineering</h3>
<p>Clever wording. "You are an expert in…" "Think step by step…"</p>
<ul>
  <li>Manual every time</li>
  <li>Doesn't compound</li>
  <li>Brittle to model changes</li>
</ul>
</div>
<div class="arrow">→</div>
<div class="panel new">
<h3>Context engineering</h3>
<p>Rich <code>agents.md</code> + accumulating <code>memory.md</code> + examples folder.</p>
<ul>
  <li>Load once, leverage forever</li>
  <li>Compounds weekly</li>
  <li>Survives model upgrades</li>
</ul>
</div>
</div>

> "A two-word prompt produces excellent output if `agents.md` is rich."

<p class="cite">sources/building-ai-agents</p>

---

<!-- _class: dark -->

<p class="eyebrow">New tooling · ships in Claude Code</p>

# The fleet dashboard

<div class="two-column">
<div>

## `claude agents`

Three swim lanes for parallel sessions, native in the terminal.

- **Needs input** — where to focus next
- **Working** — already running
- **Completed** — ready to ship

<p style="margin-top: 18px; opacity: 0.78; font-size: 17px;">
Spacebar to peek without entering. <code>/bg</code> backgrounds any standalone session. Sessions survive dashboard exit and relaunch.
</p>

</div>
<div>

> "If you don't visually see it, you tend to forget about it."

<p style="opacity: 0.7; font-size: 18px;">— Chase AI, on why visual fleet awareness matters when you're juggling 3–6 concurrent agents.</p>

</div>
</div>

<p class="cite">sources/claude-code-just-got-a-dashboard · entities/claude-code</p>

---

<!-- _class: section -->

<div class="section-num">04</div>
<p class="eyebrow">Module 4</p>

# Marketing

## The vibe-marketing stack — end-to-end inside one terminal.

---

# The pipeline

<div class="steps">
  <div><div class="icon"><img src="assets/icons/cog.svg" /></div><span class="num">01</span><h3>Research</h3><p>Perplexity + Firecrawl + Playwright. Find the competitive gap.</p></div>
  <div><div class="icon"><img src="assets/icons/folder-spark.svg" /></div><span class="num">02</span><h3>Context</h3><p>Idea Browser MCP pipes ICP, positioning, offer into the agent.</p></div>
  <div><div class="icon"><img src="assets/icons/browser-build.svg" /></div><span class="num">03</span><h3>Build</h3><p>Positioning → copy → design → lead magnet → Remotion video.</p></div>
  <div><div class="icon"><img src="assets/icons/chat-check.svg" /></div><span class="num">04</span><h3>Experiment</h3><p>HumbleLytics swaps headlines on live traffic. No redeploys.</p></div>
</div>

<div class="callout">
<p><strong>The full stack in one Claude Code session.</strong> Researcher, copywriter, designer, video editor, paid-media buyer, CRO analyst — collapsed into a single agent loop.</p>
</div>

<p class="cite">sources/ai-marketing-masterclass · my-claude-code-workflow · topics/ai-marketing</p>

---

<p class="eyebrow">Jonathan Courtney · AJ&amp;Smart</p>

# The Promoter Blueprint

<div class="two-column narrow">
<div>

## Four-phase revenue loop

Marketing strategy upstream of tactics.

Most people optimise step 3 (sell). Winners design the loop.

</div>
<div>

<div class="steps" style="grid-template-columns: 1fr 1fr;">
<div class="is-neural"><span class="num">01</span><h3>Traffic</h3><p>Organic + paid</p></div>
<div class="is-circuit"><span class="num">02</span><h3>Holding pattern</h3><p>Newsletter, podcast, social</p></div>
<div class="is-fibre"><span class="num">03</span><h3>Selling event</h3><p>Webinar, campaign, retargeting</p></div>
<div class="is-voltage"><span class="num">04</span><h3>Conversion</h3><p>(Non-converters loop back)</p></div>
</div>

</div>
</div>

<p class="cite">sources/claude-code-built-my-450k-marketing-campaign</p>

---

# Three growth levers most builders ignore

<div class="cards">
  <div class="is-neural">
    <div class="icon"><img src="assets/icons/mail-send.svg" /></div>
    <span class="num">AEO</span>
    <h3>Answer Engine Optimization</h3>
    <p>Be cited by Perplexity / ChatGPT / Claude. Monitor with Otterly, Profound. SEO is dying; AEO replaces it.</p>
  </div>
  <div class="is-circuit">
    <div class="icon"><img src="assets/icons/hub-integration.svg" /></div>
    <span class="num">MCP</span>
    <h3>MCP as distribution channel</h3>
    <p>Publish to Smithery, MCPT, OpenTools. Every AI assistant = a 24/7, zero-CAC sales rep.</p>
  </div>
  <div class="is-fibre">
    <div class="icon"><img src="assets/icons/announcement.svg" /></div>
    <span class="num">Buy</span>
    <h3>Newsletter acquisition</h3>
    <p>$5–20K acquisitions in niches. Pre-built distribution + warm audience + recurring revenue.</p>
  </div>
</div>

<p class="cite">sources/stop-vibe-coding-start-getting-customers</p>

---

<!-- _class: section -->

<div class="section-num">05</div>
<p class="eyebrow">Module 5</p>

# Design &amp; Coding

## Taste is the new moat. Code is the cheap part.

---

# design.md — the portable blueprint

<div class="two-column">
<div>

## The "soul" of a design in one markdown file

- Typography, color, spacing, motion, WebGL
- **Travels across mediums**: web, mobile, slides, motion
- **Travels across tools**: Figma, Framer, Aura, Codex, Claude Code
- New spec adds Tokens, Components, CLI linter for WCAG validation

</div>
<div>

> "Design is no longer about pixels. It's about judgement per minute."

<p style="font-size: 18px; opacity: 0.7;">— Meng To, who ships marketing sites for 4 SaaS products solo using a single design.md.</p>

</div>
</div>

<p class="cite">sources/googles-design-md · meet-designmd-a-new-open-standard-for-ai-generated-ui · entities/design-md</p>

---

# The new levels of AI coding

<div class="cards four">
  <div>
    <span class="num">Level 0</span>
    <h3>Autocomplete</h3>
    <p>Suggests next token. Old Copilot.</p>
  </div>
  <div class="is-neural">
    <span class="num">Level 1</span>
    <h3>Chat</h3>
    <p>Q&amp;A about code. ChatGPT, Claude.ai.</p>
  </div>
  <div class="is-circuit">
    <span class="num">Level 2</span>
    <h3>In-IDE agent</h3>
    <p>Reads + edits files in context. Cursor.</p>
  </div>
  <div class="is-fibre">
    <span class="num">Level 3</span>
    <h3>Autonomous harness</h3>
    <p>Owns end-to-end tasks. Claude Code, Codex, OpenClaw.</p>
  </div>
</div>

<div class="callout">
<p><strong>Most builders should operate at Level 3.</strong> The autonomy threshold was crossed in late 2025 — pre-threshold mental models are now actively wrong.</p>
</div>

<p class="cite">sources/agentic-ai-systems-clearly-explained · making-with-ai-agents</p>

---

<!-- _class: section -->

<div class="section-num">06</div>
<p class="eyebrow">Module 6</p>

# Business

## $100B companies with under five employees.

---

# The Tiny model — agents in production

<div class="kpi">
<div><strong>132</strong><p>Portfolio companies<br>at Andrew Wilkinson's Tiny</p></div>
<div><strong>$40K</strong><p>Monthly Claude bill — replacing<br>multiple ops headcount</p></div>
<div><strong>2 wks</strong><p>For a CFO with zero coding<br>to ship a $50K platform replacement</p></div>
</div>

> "Support as a job is months away from disappearing."

<p class="cite">sources/ai-agents-run-my-business</p>

---

# CEO = Promoter, not Builder

<div class="versus">
<div class="panel old">
<h3>Old model</h3>
<p>The CEO builds the company. Hires, manages, ships features, runs ops.</p>
<ul>
  <li>Scale by hiring humans</li>
  <li>10-person team = 10-person output</li>
  <li>Software is the moat</li>
</ul>
</div>
<div class="arrow">→</div>
<div class="panel new">
<h3>New model</h3>
<p>The CEO promotes the company. Picks channels; agents handle execution.</p>
<ul>
  <li>Scale by hiring agents</li>
  <li>1-person team = 10-person output</li>
  <li>Distribution + compute are the moats</li>
</ul>
</div>
</div>

<p class="cite">concepts/distribution-over-engineering · sources/claude-code-built-my-450k-marketing-campaign · ai-agents-run-my-business</p>

---

<!-- _class: dark -->

<p class="eyebrow">Where to start your AI agent business today</p>

# The five-step playbook

<div class="cards">
<div class="is-circuit">
<div class="icon"><img src="assets/icons/critical-thinking.svg" /></div>
<span class="num">01</span><h3>Pick a vertical</h3><p>Where AI replaces a $1K–$10K/month line item.</p>
</div>
<div class="is-neural">
<div class="icon"><img src="assets/icons/cog.svg" /></div>
<span class="num">02</span><h3>Build the agent</h3><p>As an internal workflow first. Get it bullet-proof.</p>
</div>
<div class="is-fibre">
<div class="icon"><img src="assets/icons/coins-stack.svg" /></div>
<span class="num">03</span><h3>Sell as managed service</h3><p>Not SaaS. $5–20K/month. Opportunity-cost pricing.</p>
</div>
</div>

<div class="cards two" style="margin-top: 14px;">
<div class="is-voltage">
<div class="icon"><img src="assets/icons/users-team.svg" /></div>
<span class="num">04</span><h3>Scale with agents, not humans</h3><p>Each new client = clone the agent + customise the context.</p>
</div>
<div class="is-circuit">
<div class="icon"><img src="assets/icons/trophy.svg" /></div>
<span class="num">05</span><h3>Park gains in infrastructure</h3><p>Software moats erode. Compute moats compound.</p>
</div>
</div>

<p class="cite">sources/how-to-start-an-ai-agent-business-today · ai-agents-run-my-business · the-golden-age-thesis-marc-andreessen-on-mts</p>

---

<p class="eyebrow">A concrete starter idea · Karpathy's open-source loop</p>

# Autoresearch as a niche business

<div class="two-column narrow">
<div>

## The pattern

Define a metric. Let the loop iterate. Keep only the winners.

The infrastructure is rented (Colab / Lambda / RunPod). The moat is picking the right niche and defining "better" as a single scalar.

> "The bottleneck is judgment, not compute."

</div>
<div>

<div class="cards" style="grid-template-columns: 1fr;">
  <div class="is-circuit">
    <span class="num">01</span>
    <h3>Pick a tight niche</h3>
    <p>Amazon listings · email sequences · SaaS pricing · clinical-trial design.</p>
  </div>
  <div class="is-voltage">
    <span class="num">02</span>
    <h3>Define "better"</h3>
    <p>A single scalar — clicks, revenue, conversion, model score.</p>
  </div>
  <div class="is-neural">
    <span class="num">03</span>
    <h3>Charge monthly</h3>
    <p>UX = "press accept, get winners." Recurring revenue with compute as the moat.</p>
  </div>
</div>

</div>
</div>

<p class="cite">sources/karpathys-autoresearch · entities/karpathy</p>

---

<!-- _class: lead -->

# The whole training in one line:

<blockquote>
Pick one harness. Build one agent. Use it daily for 90 days.<br>
Curate the markdown vault that lives behind it.<br>
Then ship — <em>distribution-first</em>.
</blockquote>

---

# Minimum viable AI builder

<div class="six-up iconic">
<div><div class="icon"><img src="assets/icons/laptop.svg" /></div><span class="num">01</span><h3>One harness</h3><p>Claude Code, Codex, or OpenClaw. Pick. Don't shop.</p></div>
<div><div class="icon"><img src="assets/icons/file-spark.svg" /></div><span class="num">02</span><h3>One <code>agents.md</code></h3><p>Your standing role. 200 words.</p></div>
<div><div class="icon"><img src="assets/icons/hub-integration.svg" /></div><span class="num">03</span><h3>Three MCPs</h3><p>Search, your data, your action target.</p></div>
<div><div class="icon"><img src="assets/icons/layers.svg" /></div><span class="num">04</span><h3>Five skills</h3><p>Your recurring workflows.</p></div>
<div><div class="icon"><img src="assets/icons/database-ai.svg" /></div><span class="num">05</span><h3>One vault</h3><p>Markdown. Everything you learn.</p></div>
<div><div class="icon"><img src="assets/icons/startup.svg" /></div><span class="num">06</span><h3>One shipped thing</h3><p>Distribution-first. Not engineering-first.</p></div>
</div>

---

<!-- _class: lead -->

<p class="eyebrow">The wiki is the textbook · this deck is the course</p>

# Now go build.

<p style="font-size: 22px; color: var(--grey-3); margin-top: 26px;">25 sources · 6 concepts · 11 topics · 27 entities — all in <code>wiki/</code>.</p>

<p class="cite">Compiled 2026-05-12 from transcripts ingested between 2026-05-09 and 2026-05-12.</p>
