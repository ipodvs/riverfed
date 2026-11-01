---
marp: true
theme: riverfed
paginate: true
title: The Riverfed Handbook
description: A practical training on operating AI agents, distilled from a 53-source video wiki.
tags: [wiki]
---
<!-- _class: cover -->
<!-- _paginate: false -->

<div class="cover-shapes"></div>
<div class="cover-wordmark">Riverfed<span class="dot">.</span></div>

<p class="eyebrow">A practical training</p>

# The Riverfed Handbook

## How to stop chatting with AI and start operating it.

<div class="tag-row">
  <span>53 sources</span>
  <span>21 concepts</span>
  <span>12 topics</span>
  <span>61 entities</span>
</div>

---

<!-- _class: lead -->

<p class="eyebrow">In one sentence</p>

# You have been renting the AI.<br>Today you install it.

## Same model. Different place. That difference is the whole training.

---

<!-- _class: section -->

<span class="section-num">01</span>

# Where the AI actually runs

## The setup nobody explains, and the one demo that makes it click.

---

<p class="eyebrow">Where you are now</p>

# A tab, or a program on your machine

<div class="versus">
<div class="panel old">
<h3>AI in a browser tab</h3>
<p>Runs in someone else's cloud. You paste things in, you copy things out.</p>
<ul>
  <li>Cannot see your files</li>
  <li>Cannot create anything you can open</li>
  <li>Cannot run anything</li>
  <li>You are the clipboard between it and your work</li>
</ul>
</div>
<div class="arrow">&rarr;</div>
<div class="panel new">
<h3>AI in your terminal</h3>
<p>The same model, running next to your work, with your permission.</p>
<ul>
  <li>Reads the files you point it at</li>
  <li>Writes new files onto your disk</li>
  <li>Runs commands and sees what they return</li>
  <li>You stop being the clipboard</li>
</ul>
</div>
</div>

<div class="callout">
<p><strong>The whole shift in one line:</strong> it stops being something you talk to and starts being something that does.</p>
</div>

---

<p class="eyebrow">DEMO. Do this live, do not describe it</p>

# Two commands that change the room

<div class="steps">
  <div><span class="num">01</span><h3>Ask it to write</h3><p>Type: <code>create a txt file saying hello Maria</code>. Use the name of someone actually sitting there.</p></div>
  <div><span class="num">02</span><h3>The file appears</h3><p>Show it in Finder or Explorer. A real file, on their kind of machine, with a classmate's name in it.</p></div>
  <div><span class="num">03</span><h3>Ask it to open</h3><p>Type: <code>now open the file</code>. It opens. That was not text: that was a command running on the computer.</p></div>
</div>

<div class="callout">
<p><strong>Why a real name matters:</strong> it kills the "this is a canned demo" doubt before anyone says it out loud. Nobody prepared a file with Maria's name in it.</p>
</div>

---

<!-- _class: lead -->

<p class="eyebrow">The bridge</p>

# A text file and a program<br>are the same thing to it.

## Writing .txt or writing .py is one skill. Opening a file or running a program is one skill. It has both.

---

<p class="eyebrow">A question that stops mattering</p>

# So which editor should you use?

<div class="cards">
  <div><span class="num">VS Code</span><h3>Fine</h3><p>Popular, free, huge extension ecosystem.</p></div>
  <div><span class="num">Cursor</span><h3>Also fine</h3><p>An editor with AI built in. Convenient, not required.</p></div>
  <div><span class="num">None</span><h3>Also fine</h3><p>A terminal and any text editor is a complete setup.</p></div>
</div>

<div class="callout">
<p><strong>The point:</strong> the agent runs beside your editor, not inside it. Which editor you open is a preference, not an architecture decision.</p>
</div>

---

<p class="eyebrow">So do you abandon the browser?</p>

# No. You learn where the handoff is

<div class="versus">
<div class="panel old">
<h3>Stay in the GUI</h3>
<p>Lowest friction. Where thinking happens.</p>
<ul>
  <li>Research and reading around a problem</li>
  <li>Ideation, drafting, arguing with yourself</li>
  <li>Simple automations</li>
  <li>Anyone who is not ready for a terminal yet</li>
</ul>
</div>
<div class="arrow">&rarr;</div>
<div class="panel new">
<h3>Escalate to the terminal</h3>
<p>Full filesystem and shell. Where shipping happens.</p>
<ul>
  <li>Work that spans many files</li>
  <li>Anything that has to run, not just read</li>
  <li>Deployment and real output</li>
  <li>Long jobs you want to leave running</li>
</ul>
</div>
</div>

<div class="callout">
<p><strong>The handoff point, not the tool choice, is the decision.</strong> They can share context, so moving between them is a continuation rather than a restart.</p>
</div>

<p class="cite">concepts/gui-to-terminal-handoff (6 sources)</p>

---

<!-- _class: section -->

<span class="section-num">02</span>

# What it reads and writes

## Plain text is the substrate. That is not a limitation, it is the point.

---

<p class="eyebrow">The most evidenced idea in the whole wiki</p>

# Markdown is the oxygen

Agents consume markdown: <code>agents.md</code>, <code>memory.md</code>, skills, <code>design.md</code>. Agents produce markdown: reports, wiki pages, new skills. Knowledge persists as markdown.

<ul>
  <li>Human readable, so you can check its work</li>
  <li>Version controllable, so you can see what changed</li>
  <li>Parseable by every model, so nothing locks you in</li>
</ul>

<div class="callout">
<p><strong>The consequence:</strong> the quality of your markdown is the ceiling on your agent's intelligence. Better files, better output. Every session, every tool.</p>
</div>

<p class="cite">concepts/markdown-as-llm-substrate (26 sources)</p>

---

<p class="eyebrow">Why a terminal, specifically</p>

# The terminal is where things converge

Context, tools, and execution meet in one place. That is the whole argument. It is not about looking technical.

<ul>
  <li>Your context files are right there on disk</li>
  <li>Tools compose: the output of one becomes the input of the next</li>
  <li>Execution is local, so results are real rather than described</li>
  <li>It is the lowest common denominator across every agent harness</li>
</ul>

<div class="callout">
<p><strong>The practical upshot:</strong> invest in context-file conventions, not in learning a specific GUI. The conventions move with you. The GUI does not.</p>
</div>

<p class="cite">concepts/terminal-as-the-interface (19 sources)</p>

---

<p class="eyebrow">The complaint you will hear most</p>

# "It keeps forgetting everything"

<div class="versus">
<div class="panel old">
<h3>What people assume</h3>
<p>The model has a bad memory. Nothing to be done about it.</p>
<ul>
  <li>Blame the model</li>
  <li>Repeat yourself every session</li>
  <li>Conclude agents are not ready</li>
</ul>
</div>
<div class="arrow">&rarr;</div>
<div class="panel new">
<h3>What is actually happening</h3>
<p>Memory was never written down. Retrieval is not the broken part.</p>
<ul>
  <li>Check <code>memory.md</code> exists</li>
  <li>Check something is writing to it</li>
  <li>Check compaction is not discarding it first</li>
</ul>
</div>
</div>

<div class="callout">
<p><strong>Memory failures are write failures.</strong> If your agent forgets a correction, the bug is in what got written, not in what got recalled.</p>
</div>

<p class="cite">concepts/memory-failures-are-write-failures (12 sources)</p>

---

<p class="eyebrow">Where to put your effort</p>

# Manage the vault, not the agent

Invest in organising the knowledge, not in configuring the tool. Daily logs, project notes, style guides. A structure built for your own thinking that the agent happens to read.

<ul>
  <li>Harnesses change. Agents forget. Context windows reset.</li>
  <li>A folder of markdown outlives all three.</li>
  <li>No lock-in: any agent, any model, can read it.</li>
  <li>If you organise it well enough to understand yourself, the agent inherits that.</li>
</ul>

<div class="callout">
<p><strong>The test:</strong> if you switched agent tools tomorrow, how much of your setup would survive? Vault work survives. Configuration does not.</p>
</div>

<p class="cite">concepts/vault-first-delegation (5 sources)</p>

---

<!-- _class: section -->

<span class="section-num">03</span>

# Getting good at it

## The loop that separates a demo from a system you trust.

---

<p class="eyebrow">The wiki's third most evidenced idea</p>

# Do it, formalize it, iterate it

<div class="steps">
  <div><span class="num">01</span><h3>Do it manually</h3><p>Walk the real workflow with the agent. Correct it as you go. Keep going until the output is actually right.</p></div>
  <div><span class="num">02</span><h3>Formalize the run</h3><p>Have the agent package that successful run into a reusable skill file. It captures the corrections you made.</p></div>
  <div><span class="num">03</span><h3>Iterate on use</h3><p>Each new use exposes a gap. Fold it back in. Quality compounds toward a version 5 or 10 that genuinely works.</p></div>
</div>

<div class="callout">
<p><strong>Why not just write the skill up front?</strong> A hand-written or downloaded skill is a context-free SOP. It never met the edge cases. A skill born from a real run inherits every correction you made during it.</p>
</div>

<p class="cite">concepts/workflow-first-skills (18 sources)</p>

---

<p class="eyebrow">The question everyone asks at this point</p>

# Autonomy is earned, not configured

Not a switch you flip. A ladder the agent climbs one bounded workflow at a time. Start at the bottom rung: fixed workflow, it drafts, you approve.

<ul>
  <li>Bottom rung is shippable on day one, because it is just a workflow</li>
  <li>Promotion criterion: demonstrated quality at the current rung</li>
  <li>Grant more judgment only after it has earned it, the way you would with a new hire</li>
  <li>"It drafts, you approve, until it stops needing you" is a story people trust</li>
</ul>

<div class="callout">
<p><strong>Why this matters commercially:</strong> full autonomy is the value, but full autonomy on day one is how you get slop, broken trust, and cancelled pilots.</p>
</div>

<p class="cite">concepts/earned-autonomy (11 sources)</p>

---

<p class="eyebrow">The part almost everyone skips</p>

# If you cannot measure it, you cannot promote it

Evals are a set of real examples with known right answers, scored by a rubric or by another model. They turn "is it any good?" from vibes into a number.

<ul>
  <li>Track that number across every prompt, model, or tool change</li>
  <li>It is the promotion criterion for the autonomy ladder</li>
  <li>It catches quality drift before a customer does</li>
  <li>The eval set is both your QA loop and your sales evidence</li>
</ul>

<div class="callout">
<p><strong>The dependency:</strong> autonomy is only sellable when quality is visible. Evals are what convert "trust me" into evidence.</p>
</div>

<p class="cite">concepts/evals-as-quality-visibility (8 sources)</p>

---

<!-- _class: section -->

<span class="section-num">04</span>

# How it is put together

## Same four pieces underneath, whichever product you picked.

---

<p class="eyebrow">The anatomy</p>

# Four pieces of every production agent

<div class="cards four">
  <div><span class="num">01</span><h3>A model</h3><p>The reasoning. Swappable, and cheaper every quarter.</p></div>
  <div><span class="num">02</span><h3>Tools</h3><p>How it touches the world: files, shell, APIs, a browser.</p></div>
  <div><span class="num">03</span><h3>A loop</h3><p>Act, observe the result, decide again. Not one shot.</p></div>
  <div><span class="num">04</span><h3>Context</h3><p>What it knows going in: your files, your instructions, your memory.</p></div>
</div>

<div class="callout">
<p><strong>Where your leverage is:</strong> you do not control the model and you barely control the loop. You control the tools you expose and the context you write. That is the job.</p>
</div>

---

<p class="eyebrow">An architecture decision with a price tag</p>

# CLI first, API second, MCP last

<div class="kpi">
<div><strong>~200</strong><p>tokens a CLI returns for a query:<br>scoped, pre-formatted, out of your way</p></div>
<div><strong>~132K</strong><p>tokens an MCP can dump for the same<br>query, as raw JSON</p></div>
<div><strong>every</strong><p>turn an MCP re-sends its tool schemas,<br>whether you use them or not</p></div>
</div>

<div class="callout">
<p><strong>Two costs, not one.</strong> Tokens are an operating expense, and reliability drops as well: the more an agent has to parse, the more it loses the thread.</p>
</div>

<p class="cite">concepts/cli-over-mcp (6 sources)</p>

---

<p class="eyebrow">Same engine, different car</p>

# The harnesses people actually use

<div class="six-up">
  <div><span class="num">37</span><h3>Claude Code</h3><p>Terminal-native. The reference for this deck.</p></div>
  <div><span class="num">19</span><h3>Codex</h3><p>GUI plus CLI. Strong on long runs.</p></div>
  <div><span class="num">18</span><h3>OpenClaw</h3><p>Open harness, bring your own model.</p></div>
  <div><span class="num">8</span><h3>Cowork</h3><p>GUI-first. Where the handoff often starts.</p></div>
  <div><span class="num">6</span><h3>Hermes</h3><p>Always-on personal assistant framing.</p></div>
  <div><span class="num">3</span><h3>Cursor</h3><p>The editor with the agent built in.</p></div>
</div>

<div class="callout">
<p><strong>Read the numbers, not the names.</strong> That is how many independent sources in this wiki discuss each one. The list will look different in six months, which is exactly why the four pieces matter more.</p>
</div>

---

<p class="eyebrow">How other people get to use it</p>

# A dashboard is the access layer, not the system

Terminal-first agents create leverage for one power user and exclude everyone else. A dashboard turns hidden agent work into something a teammate can see and run.

<ul>
  <li>Status, queues, and metrics for runs nobody watched</li>
  <li>Buttons and approvals for people who should never touch a prompt</li>
  <li>Handoff points, so a stalled run gets noticed</li>
  <li>A packaging surface: it is how this becomes something you can sell</li>
</ul>

<div class="callout">
<p><strong>The failure mode has a name:</strong> dashboard theater. A polished control panel with no reliable workflow underneath it. Build the workflow first.</p>
</div>

<p class="cite">concepts/dashboard-as-access-layer (7 sources)</p>

---

<p class="eyebrow">When one agent is not enough</p>

# Long jobs fail in three specific ways

On a long task in a single context window, agents degrade predictably. Naming the three failure modes makes them diagnosable instead of mysterious.

<ul>
  <li><strong>Stops early.</strong> Declares the job done when it is not.</li>
  <li><strong>Favours its own work.</strong> Ask it to judge its output and it approves.</li>
  <li><strong>Loses the objective.</strong> Context grows, compacts, and the original goal fades. Context rot.</li>
</ul>

<div class="callout">
<p><strong>The fix:</strong> have the agent write its own team for the job. Sub-agents with clean contexts, one job each, judged separately. It costs real tokens, which is the trade you are making.</p>
</div>

<p class="cite">concepts/dynamic-workflows (5 sources)</p>

---

<!-- _class: section -->

<span class="section-num">05</span>

# What it costs, and against what

## The objection you will hear in every budget meeting.

---

<p class="eyebrow">The reframe</p>

# Price it against the hours, not the tokens

<div class="kpi">
<div><strong>$150</strong><p>of tokens for a board memo that would<br>have taken hours of analyst time</p></div>
<div><strong>$40K</strong><p>a month in model spend, replacing<br>several full-time salaries</p></div>
<div><strong>0&amp;times;</strong><p>marginal cost of the second, fifth,<br>or fiftieth variant</p></div>
</div>

<div class="callout">
<p><strong>Token cost is the wrong denominator.</strong> The right one is the human time replaced, plus the overhead and onboarding you never paid.</p>
</div>

<p class="cite">concepts/opportunity-cost-vs-token-cost (16 sources)</p>

---

<p class="eyebrow">The discipline nobody wants</p>

# Ask first, build second

Building got cheap, so the temptation to build is higher than it has ever been. The cost of building the wrong thing did not fall at all.

<ul>
  <li>Check whether a tool, plugin, or platform already does it</li>
  <li>Custom builds carry maintenance and context rot that off-the-shelf does not</li>
  <li>Three days on a proposal generator is three days not spent on customers</li>
  <li>The cheaper building gets, the more valuable this discipline becomes</li>
</ul>

<div class="callout">
<p><strong>The trap:</strong> being able to build anything in an afternoon feels like leverage. It is only leverage if the thing needed to exist.</p>
</div>

<p class="cite">concepts/off-the-shelf-before-vibe-code (4 sources)</p>

---

<p class="eyebrow">Turning a task into a system</p>

# Loop engineering

<div class="steps">
  <div><span class="num">01</span><h3>One objective metric</h3><p>Black or white. A ranking, a score, revenue, a rubric result. Without one the agent loops forever.</p></div>
  <div><span class="num">02</span><h3>A stop condition</h3><p>What good enough looks like. This is what makes long-running autonomy safe to leave scheduled.</p></div>
  <div><span class="num">03</span><h3>Memory between runs</h3><p>Each run writes what it learned to a markdown file. The next run starts from there instead of from zero.</p></div>
</div>

<div class="callout">
<p><strong>The difference this makes:</strong> an agent that does a task once versus a system that compounds. Run monthly for years, and each expensive run becomes an asset for the next one.</p>
</div>

<p class="cite">concepts/objective-metric-loops (4 sources)</p>

---

<!-- _class: section -->

<span class="section-num">06</span>

# Taste is the part that does not commoditize

## Everyone has the same models. The inputs are what differ.

---

<p class="eyebrow">The most leveraged file you own</p>

# The templates renaissance

Code and content are commoditized. A well-structured template is not: it hands the agent structure, voice, and domain conventions from the very first token.

<ul>
  <li>Without one, an agent starts from zero and produces generic output</li>
  <li>With one, it inherits your standards before it writes a word</li>
  <li>Starter files, boilerplates, storyboard formats, style guides</li>
  <li>What used to be dismissed as boilerplate is now the highest-leverage thing you maintain</li>
</ul>

<div class="callout">
<p><strong>The rule:</strong> the quality ceiling of agent-produced work is proportional to the quality of the template it started from. Fix the template, not the output.</p>
</div>

<p class="cite">concepts/templates-as-agent-context (8 sources)</p>

---

<p class="eyebrow">A trick worth stealing</p>

# Show it, do not describe it

<div class="versus">
<div class="panel old">
<h3>Text-only brief</h3>
<p>You describe what you want in words and hope it lands.</p>
<ul>
  <li>Palette and spacing get lost</li>
  <li>"Clean and modern" means nothing</li>
  <li>You iterate by arguing about adjectives</li>
</ul>
</div>
<div class="arrow">&rarr;</div>
<div class="panel new">
<h3>Visual-first brief</h3>
<p>Screenshots and reference images become the spec.</p>
<ul>
  <li>A multimodal model reads the images</li>
  <li>It writes the structured brief</li>
  <li>An agent executes it</li>
</ul>
</div>
</div>

<div class="callout">
<p><strong>Why it works:</strong> images carry design intent, palette, layout, typography, spacing, that text-only prompts consistently fail to convey.</p>
</div>

<p class="cite">concepts/visual-first-prd (3 sources)</p>

---

<!-- _class: section -->

<span class="section-num">07</span>

# What this does to the work

## Roles, distribution, and how the first sale actually happens.

---

<p class="eyebrow">Two forces at once</p>

# Roles are collapsing in two directions

<div class="versus">
<div class="panel old">
<h3>Horizontal collapse</h3>
<p>The coder, the PM, and the designer merge into one builder.</p>
<ul>
  <li>Each can now do the other two's work</li>
  <li>One person with judgment spans functions</li>
  <li>Specialisation stops being the hiring signal</li>
</ul>
</div>
<div class="arrow">&rarr;</div>
<div class="panel new">
<h3>Vertical shift</h3>
<p>The individual contributor becomes a manager of agents.</p>
<ul>
  <li>You direct a fleet rather than doing the work</li>
  <li>The skill is delegation and review</li>
  <li>Your throughput stops being bounded by your hands</li>
</ul>
</div>
</div>

<div class="callout">
<p><strong>What hiring becomes:</strong> not "can this person code, design, or manage a product?" but "can this person direct agents and judge the result?"</p>
</div>

<p class="cite">concepts/role-collapse (10 sources)</p>

---

<p class="eyebrow">The uncomfortable one</p>

# Distribution beats engineering now

Code is commoditized: hundreds of thousands of new vibe-coded projects a day. The durable advantage moved from building to getting it in front of people.

<ul>
  <li>The correct sequence inverts: audience first, product second</li>
  <li>Founders who spend half their time on traffic and selling outperform those optimising code</li>
  <li>An hour building without a distribution plan is procrastination with a nice IDE</li>
  <li>The wealthiest builders in this era will be marketers</li>
</ul>

<div class="callout">
<p><strong>Sharp version:</strong> a product nobody knows about is a hobby, and agents just made building the cheap part of the equation.</p>
</div>

<p class="cite">concepts/distribution-over-engineering (8 sources)</p>

---

<p class="eyebrow">How the first sale actually happens</p>

# Lead with a cheap diagnostic

<div class="steps">
  <div><span class="num">01</span><h3>Sell a small audit</h3><p>Cheap or free. Low risk, high clarity. The buyer is deciding on a small thing, not a big one.</p></div>
  <div><span class="num">02</span><h3>Prove value inside it</h3><p>Find something measurable. You also learn the real, undocumented workflow before you ever quote a build.</p></div>
  <div><span class="num">03</span><h3>Let the proof pull them up</h3><p>The client asks for the implementation. Then the retainer. You never had to make the hard first sale.</p></div>
</div>

<div class="callout">
<p><strong>Why it works:</strong> when intelligence and code are commoditized, the scarce thing is a trusted path into a specific business. An audit buys that.</p>
</div>

<p class="cite">concepts/audit-as-tripwire (3 sources)</p>

---

<!-- _class: section -->

<span class="section-num">08</span>

# Where this stops working

## One source in this wiki reports a failure. It is the most useful one.

---

<p class="eyebrow">The lights-off experiment</p>

# Nobody read the code, and it fell apart

An agent software factory run with nobody reading the output. It worked, until an issue appeared that no amount of prompting could fix, the site was down, and the fix meant digging through a codebase abandoned months earlier.

<ul>
  <li>Not a skill problem, and not a scale problem</li>
  <li>No harness and no extra tokens fixes it</li>
  <li>Coding models are rewarded for one thing: did the test pass without breaking another</li>
  <li>Nothing in that reward penalises bad architecture, whose cost arrives months later</li>
</ul>

<div class="callout">
<p><strong>The uncomfortable part:</strong> they get better at passing tests and no better at keeping a codebase maintainable. If a model knew what good looked like, it would already write it.</p>
</div>

<p class="cite">sources/harness-engineering-is-not-enough (AI Engineer)</p>

---

<p class="eyebrow">So what do you do about it</p>

# Turn the lights back on

The fix is not to use agents less. It is to keep a human in the parts the reward function cannot see.

<ul>
  <li>Plan up front: product review, then system architecture</li>
  <li>Program design down to types and call graphs, the step everyone skips</li>
  <li>Then vertical slices, so each piece is reviewable</li>
  <li>Keep reading the output. You can still move fast while doing it.</li>
</ul>

<div class="callout">
<p><strong>The trade:</strong> thirty minutes of alignment up front saves hours of review afterwards, and a good result becomes a joy to read instead of slop to untangle.</p>
</div>

<p class="cite">topics/software-factory (2 sources)</p>

---

<!-- _class: lead -->

<p class="eyebrow">The whole training in one line</p>

# Write the context. Judge the output.<br>Everything else is the tool's job.

## The models improve without you. Your files and your judgment are the parts that compound.

---

<p class="eyebrow">If you do nothing else</p>

# Minimum viable operator

<div class="cards four">
  <div><span class="num">01</span><h3>Install it locally</h3><p>One agent, running in a terminal, in a folder you care about.</p></div>
  <div><span class="num">02</span><h3>Start one file</h3><p>A markdown file it reads every session. Add to it when you correct it.</p></div>
  <div><span class="num">03</span><h3>Formalize one workflow</h3><p>Do a real job manually, then have it package the run into a skill.</p></div>
  <div><span class="num">04</span><h3>Keep twenty examples</h3><p>Real cases with the answer you would have given. That is your eval set.</p></div>
</div>

<div class="callout">
<p><strong>Note what is missing:</strong> no MCP servers, no dashboard, no fleet. Those come after this works, not before.</p>
</div>

---

<!-- _class: lead -->

<p class="eyebrow">Last thing</p>

# Go and give it something real to do.

## Not a test. Something from your actual work, today, that you would otherwise have done by hand.
