"""THE handbook source. Slides and teaching notes together, one list.

Rules for editing:
  - Only the ten slide types both renderers support: cover, lead, section,
    content, cards, six-up, flow, versus, kpi, quote.
  - ONE accent. `is-neural` / `is-fibre` / `is-voltage` are for a comparison
    side, a warning, a highlight. Never to make card 2 differ from card 1.
  - Every claim gets a `cite` naming the concept slug and its source count,
    so a reader can go verify it. That promise is the deck's spine.
  - `notes` is written for someone who uses AI in a browser and has never run
    an agent. Explain, do not cue.
  - No em dashes (house style). Use a colon, comma, or full stop.
"""

DECK = {
    "title": "The Riverfed Handbook",
    "description": ("A practical training on operating AI agents, distilled "
                    "from a 53-source video wiki."),
    "theme": "riverfed",
    "notes_intro": (
        "These notes assume the room already uses AI in a browser and has "
        "never run an agent. Every section states what the audience already "
        "believes, then what has to change. Live demos are marked DEMO with "
        "the exact commands to type."),
}

SLIDES = [
    {
        "type": "cover",
        "title": "The Riverfed Handbook",
        "subtitle": "How to stop chatting with AI and start operating it.",
        "eyebrow": "A practical training",
        "tags": ["53 sources", "21 concepts", "12 topics", "61 entities"],
        "notes": (
            "Say the counts out loud. They are the deck's credibility: every "
            "claim traces to a transcript, and nothing here is opinion "
            "dressed as fact.\n\n"
            "Do not open with a definition of agents. The room has heard it "
            "and it did not stick, because a definition cannot be checked "
            "against anything they have touched. We are going to make them "
            "believe one physical fact first, then define terms afterwards."),
    },
    {
        "type": "lead",
        "eyebrow": "In one sentence",
        "headline": "You have been renting the AI.<br>Today you install it.",
        "subtitle": "Same model. Different place. That difference is the whole training.",
        "notes": (
            "The distinction is not capability, it is location, and location "
            "is what unlocks everything else.\n\n"
            "The AI in a browser tab runs on someone else's computer. It can "
            "return words to you and nothing else. The same model running on "
            "your machine can read your files, write new ones, and run "
            "commands. Nobody argues with this once they see it, which is why "
            "the next four slides are a demo rather than an explanation."),
    },

    # ---------------- Module 1: where the AI actually runs ----------------
    {
        "type": "section",
        "number": "01",
        "title": "Where the AI actually runs",
        "subtitle": "The setup nobody explains, and the one demo that makes it click.",
        "notes": (
            "This module exists because of a pattern seen across many "
            "training sessions: people who use AI daily still picture it as a "
            "website. Until that picture changes, terminal, vault and skills "
            "all sound like developer trivia.\n\n"
            "Budget real time here. If the room leaves this module believing "
            "the AI is a program on their laptop with hands, the rest of the "
            "day lands. If they do not, nothing later recovers it."),
    },
    {
        "type": "versus",
        "eyebrow": "Where you are now",
        "title": "A tab, or a program on your machine",
        "old": {
            "title": "AI in a browser tab",
            "desc": "Runs in someone else's cloud. You paste things in, you copy things out.",
            "bullets": ["Cannot see your files",
                        "Cannot create anything you can open",
                        "Cannot run anything",
                        "You are the clipboard between it and your work"],
        },
        "new": {
            "title": "AI in your terminal",
            "desc": "The same model, running next to your work, with your permission.",
            "bullets": ["Reads the files you point it at",
                        "Writes new files onto your disk",
                        "Runs commands and sees what they return",
                        "You stop being the clipboard"],
        },
        "callout": ("<strong>The whole shift in one line:</strong> it stops "
                    "being something you talk to and starts being something "
                    "that does."),
        "notes": (
            "Ask the room how they currently move work between the AI and "
            "their computer. The honest answer is copy and paste. Let them "
            "say it.\n\n"
            "That is the cost being removed. Not intelligence: plumbing. The "
            "model is often literally the same one they already pay for."),
    },
    {
        "type": "flow",
        "eyebrow": "DEMO. Do this live, do not describe it",
        "title": "Two commands that change the room",
        "steps": [
            {"num": "01", "title": "Ask it to write",
             "desc": "Type: <code>create a txt file saying hello Maria</code>. "
                     "Use the name of someone actually sitting there."},
            {"num": "02", "title": "The file appears",
             "desc": "Show it in Finder or Explorer. A real file, on their "
                     "kind of machine, with a classmate's name in it."},
            {"num": "03", "title": "Ask it to open",
             "desc": "Type: <code>now open the file</code>. It opens. That was "
                     "not text: that was a command running on the computer."},
        ],
        "callout": ("<strong>Why a real name matters:</strong> it kills the "
                    "\"this is a canned demo\" doubt before anyone says it out "
                    "loud. Nobody prepared a file with Maria's name in it."),
        "notes": (
            "DEMO. Type it, do not paste it, so the room sees ordinary "
            "language going in rather than a magic incantation.\n\n"
            "Beat 1: 'create a txt file saying hello Maria'. Pick someone in "
            "the room and say why you are picking them. While it runs, say "
            "nothing. Let them watch.\n\n"
            "Beat 2: switch to Finder or Explorer and open the folder. Do not "
            "narrate this as a technical step. It is a file. It is on the "
            "computer in front of them.\n\n"
            "Beat 3: back to the terminal, 'now open the file'. When it "
            "opens, that is the moment. Pause.\n\n"
            "Expect one of two reactions: silence, or someone asking whether "
            "it can do that to any file. The second question is the whole "
            "afternoon and you should welcome it. Answer honestly: yes, "
            "within the folder you started it in, and that is exactly why "
            "permissions and directories matter later."),
    },
    {
        "type": "lead",
        "eyebrow": "The bridge",
        "headline": "A text file and a program<br>are the same thing to it.",
        "subtitle": ("Writing .txt or writing .py is one skill. Opening a file "
                     "or running a program is one skill. It has both."),
        "notes": (
            "This is the single most important sentence in the deck. Say it "
            "slowly and then say it again in their words.\n\n"
            "It just wrote text to a file. Code is text. So it can write "
            "code. It just ran a command to open that file. Running a program "
            "is a command. So it can run code.\n\n"
            "Write, then execute. Everything the rest of the day describes, "
            "building tools, automating work, agents that operate for hours, "
            "is that same loop repeated with better instructions.\n\n"
            "This is also where you defuse the fear. Someone is thinking "
            "'so it can do anything to my computer?'. Answer before they ask: "
            "it acts in the folder you point it at, it shows you what it is "
            "about to do, and you can make it ask permission every time."),
    },
    {
        "type": "cards",
        "eyebrow": "A question that stops mattering",
        "title": "So which editor should you use?",
        "cards": [
            {"num": "VS Code", "title": "Fine",
             "desc": "Popular, free, huge extension ecosystem."},
            {"num": "Cursor", "title": "Also fine",
             "desc": "An editor with AI built in. Convenient, not required."},
            {"num": "None", "title": "Also fine",
             "desc": "A terminal and any text editor is a complete setup."},
        ],
        "callout": ("<strong>The point:</strong> the agent runs beside your "
                    "editor, not inside it. Which editor you open is a "
                    "preference, not an architecture decision."),
        "notes": (
            "People arrive expecting to be told which tool to buy, and that "
            "expectation makes them passive. Removing the question hands the "
            "decision back to them.\n\n"
            "If someone has already paid for an AI editor, do not undercut "
            "them. It is genuinely convenient. The point is that their "
            "capability does not come from the editor, so they are not locked "
            "in and not behind."),
    },

    {
        "type": "versus",
        "eyebrow": "So do you abandon the browser?",
        "title": "No. You learn where the handoff is",
        "old": {
            "title": "Stay in the GUI",
            "desc": "Lowest friction. Where thinking happens.",
            "bullets": ["Research and reading around a problem",
                        "Ideation, drafting, arguing with yourself",
                        "Simple automations",
                        "Anyone who is not ready for a terminal yet"],
        },
        "new": {
            "title": "Escalate to the terminal",
            "desc": "Full filesystem and shell. Where shipping happens.",
            "bullets": ["Work that spans many files",
                        "Anything that has to run, not just read",
                        "Deployment and real output",
                        "Long jobs you want to leave running"],
        },
        "callout": ("<strong>The handoff point, not the tool choice, is the "
                    "decision.</strong> They can share context, so moving "
                    "between them is a continuation rather than a restart."),
        "cite": "concepts/gui-to-terminal-handoff (6 sources)",
        "notes": (
            "Say this plainly: the previous slides were not an argument that "
            "the browser is bad. Overselling the terminal is how you lose the "
            "half of the room that is not ready for it.\n\n"
            "This is the slide that gives people permission to start where "
            "they are. Nobody has to migrate their whole working life today. "
            "They need one job that is worth escalating.\n\n"
            "Ask the room for a candidate: something they gave up on because "
            "copy and paste made it not worth it. That is their first "
            "terminal job, and it is a better homework assignment than "
            "anything you could set."),
    },

    # ---------------- Module 2: the substrate ----------------
    {
        "type": "section",
        "number": "02",
        "title": "What it reads and writes",
        "subtitle": "Plain text is the substrate. That is not a limitation, it is the point.",
        "notes": (
            "The room has just watched the agent write and open a file. This "
            "module answers the obvious next question: what should be in "
            "those files?\n\n"
            "The answer is boring and that is why it works. Not a database, "
            "not a special format, not a product. Markdown."),
    },
    {
        "type": "content",
        "eyebrow": "The most evidenced idea in the whole wiki",
        "title": "Markdown is the oxygen",
        "body": ("Agents consume markdown: <code>agents.md</code>, "
                 "<code>memory.md</code>, skills, <code>design.md</code>. "
                 "Agents produce markdown: reports, wiki pages, new skills. "
                 "Knowledge persists as markdown."),
        "bullets": [
            "Human readable, so you can check its work",
            "Version controllable, so you can see what changed",
            "Parseable by every model, so nothing locks you in",
        ],
        "callout": ("<strong>The consequence:</strong> the quality of your "
                    "markdown is the ceiling on your agent's intelligence. "
                    "Better files, better output. Every session, every tool."),
        "cite": "concepts/markdown-as-llm-substrate (26 sources)",
        "notes": (
            "26 of 53 sources land on this independently. It is the single "
            "most corroborated claim in the corpus, which is why it gets a "
            "slide this early.\n\n"
            "For this audience the useful translation is: you already know "
            "how to write. You do not need to learn a database, an API, or a "
            "framework. A document is the interface.\n\n"
            "The ceiling line is the one to dwell on. People try to fix bad "
            "agent output by rewriting the prompt. Usually the prompt is fine "
            "and the file it read was thin."),
    },
    {
        "type": "content",
        "eyebrow": "Why a terminal, specifically",
        "title": "The terminal is where things converge",
        "body": ("Context, tools, and execution meet in one place. That is "
                 "the whole argument. It is not about looking technical."),
        "bullets": [
            "Your context files are right there on disk",
            "Tools compose: the output of one becomes the input of the next",
            "Execution is local, so results are real rather than described",
            "It is the lowest common denominator across every agent harness",
        ],
        "callout": ("<strong>The practical upshot:</strong> invest in "
                    "context-file conventions, not in learning a specific "
                    "GUI. The conventions move with you. The GUI does not."),
        "cite": "concepts/terminal-as-the-interface (19 sources)",
        "notes": (
            "Do not oversell this. The wiki's own position, covered two "
            "slides from now, is that the browser still wins for research and "
            "ideation. The terminal wins for shipping.\n\n"
            "The honest framing for a non-technical room: you are not "
            "becoming a developer. You are choosing the place where your "
            "files, your tools, and the thing doing the work are all in the "
            "same room."),
    },
    {
        "type": "versus",
        "eyebrow": "The complaint you will hear most",
        "title": "\"It keeps forgetting everything\"",
        "old": {
            "title": "What people assume",
            "desc": "The model has a bad memory. Nothing to be done about it.",
            "bullets": ["Blame the model", "Repeat yourself every session",
                        "Conclude agents are not ready"],
        },
        "new": {
            "title": "What is actually happening",
            "desc": "Memory was never written down. Retrieval is not the broken part.",
            "bullets": ["Check <code>memory.md</code> exists",
                        "Check something is writing to it",
                        "Check compaction is not discarding it first"],
        },
        "callout": ("<strong>Memory failures are write failures.</strong> "
                    "If your agent forgets a correction, the bug is in what "
                    "got written, not in what got recalled."),
        "cite": "concepts/memory-failures-are-write-failures (12 sources)",
        "notes": (
            "This slide converts the room's most common frustration into "
            "something they can actually fix, which is worth more than any "
            "capability claim.\n\n"
            "It also pays off the demo. They watched it write a file. Memory "
            "is the same move: it is only remembered if it got written "
            "somewhere on disk.\n\n"
            "Good moment to ask who has repeated the same instruction to a "
            "chatbot three days running. Most hands go up. That is the "
            "problem being solved."),
    },
    {
        "type": "content",
        "eyebrow": "Where to put your effort",
        "title": "Manage the vault, not the agent",
        "body": ("Invest in organising the knowledge, not in configuring the "
                 "tool. Daily logs, project notes, style guides. A structure "
                 "built for your own thinking that the agent happens to read."),
        "bullets": [
            "Harnesses change. Agents forget. Context windows reset.",
            "A folder of markdown outlives all three.",
            "No lock-in: any agent, any model, can read it.",
            "If you organise it well enough to understand yourself, the agent inherits that.",
        ],
        "callout": ("<strong>The test:</strong> if you switched agent tools "
                    "tomorrow, how much of your setup would survive? Vault "
                    "work survives. Configuration does not."),
        "cite": "concepts/vault-first-delegation (5 sources)",
        "notes": (
            "This is the answer to \"which tool should I commit to?\", which "
            "is the question people are actually anxious about.\n\n"
            "The answer is that the question matters less than they think, "
            "provided their effort goes into the durable layer. Tools are a "
            "two-year bet. A vault is a ten-year one.\n\n"
            "It is also the honest sales pitch for doing the boring work: "
            "nobody is excited about organising notes, but it is the only "
            "part of this that compounds."),
    },

    # ---------------- Module 3: getting good ----------------
    {
        "type": "section",
        "number": "03",
        "title": "Getting good at it",
        "subtitle": "The loop that separates a demo from a system you trust.",
        "notes": (
            "Everything so far has been setup and substrate. This module is "
            "the actual craft, and it is where most people stall.\n\n"
            "Three ideas, in dependency order: how you build a repeatable "
            "skill, how you decide to trust it with more, and how you know "
            "whether it is any good. The third makes the second safe."),
    },
    {
        "type": "flow",
        "eyebrow": "The wiki's third most evidenced idea",
        "title": "Do it, formalize it, iterate it",
        "steps": [
            {"num": "01", "title": "Do it manually",
             "desc": "Walk the real workflow with the agent. Correct it as you go. "
                     "Keep going until the output is actually right."},
            {"num": "02", "title": "Formalize the run",
             "desc": "Have the agent package that successful run into a reusable "
                     "skill file. It captures the corrections you made."},
            {"num": "03", "title": "Iterate on use",
             "desc": "Each new use exposes a gap. Fold it back in. Quality "
                     "compounds toward a version 5 or 10 that genuinely works."},
        ],
        "callout": ("<strong>Why not just write the skill up front?</strong> "
                    "A hand-written or downloaded skill is a context-free SOP. "
                    "It never met the edge cases. A skill born from a real run "
                    "inherits every correction you made during it."),
        "cite": "concepts/workflow-first-skills (18 sources)",
        "notes": (
            "18 sources, and the previous version of this handbook never said "
            "it once. It named skills five times as a thing that exists and "
            "never explained how you get one.\n\n"
            "The instinct in the room will be to sit down and write the "
            "perfect instruction file first. That instinct is wrong and it is "
            "worth naming explicitly, because it is how people waste their "
            "first week.\n\n"
            "The analogy that lands: you do not write the training manual "
            "before doing the job. You do the job, notice what you had to "
            "explain, and write that down."),
    },
    {
        "type": "content",
        "eyebrow": "The question everyone asks at this point",
        "title": "Autonomy is earned, not configured",
        "body": ("Not a switch you flip. A ladder the agent climbs one bounded "
                 "workflow at a time. Start at the bottom rung: fixed workflow, "
                 "it drafts, you approve."),
        "bullets": [
            "Bottom rung is shippable on day one, because it is just a workflow",
            "Promotion criterion: demonstrated quality at the current rung",
            "Grant more judgment only after it has earned it, the way you would with a new hire",
            "\"It drafts, you approve, until it stops needing you\" is a story people trust",
        ],
        "callout": ("<strong>Why this matters commercially:</strong> full "
                    "autonomy is the value, but full autonomy on day one is "
                    "how you get slop, broken trust, and cancelled pilots."),
        "cite": "concepts/earned-autonomy (11 sources)",
        "notes": (
            "This answers the fear from Module 1 properly. Earlier you said "
            "\"it asks permission.\" Here is the grown-up version: permission "
            "is a rung, and you move up it deliberately.\n\n"
            "Every source in the wiki that actually took agents to production "
            "converges on this, which is worth saying out loud. It is not a "
            "cautious opinion, it is what the practitioners did.\n\n"
            "For anyone considering selling this: the ladder is also the "
            "pitch. A customer will not buy full autonomy from a stranger. "
            "They will buy draft-and-approve."),
    },
    {
        "type": "content",
        "eyebrow": "The part almost everyone skips",
        "title": "If you cannot measure it, you cannot promote it",
        "body": ("Evals are a set of real examples with known right answers, "
                 "scored by a rubric or by another model. They turn \"is it "
                 "any good?\" from vibes into a number."),
        "bullets": [
            "Track that number across every prompt, model, or tool change",
            "It is the promotion criterion for the autonomy ladder",
            "It catches quality drift before a customer does",
            "The eval set is both your QA loop and your sales evidence",
        ],
        "callout": ("<strong>The dependency:</strong> autonomy is only "
                    "sellable when quality is visible. Evals are what convert "
                    "\"trust me\" into evidence."),
        "cite": "concepts/evals-as-quality-visibility (8 sources)",
        "notes": (
            "Put this immediately after autonomy, because it is what makes "
            "the ladder safe rather than optimistic.\n\n"
            "For a beginner audience, keep it concrete and small. An eval set "
            "can be twenty real examples in a markdown file with the answer "
            "you would have given. That is enough to notice regression. It "
            "does not require a framework.\n\n"
            "This is also the slide that separates people who will still be "
            "running agents in a year from people who will have given up. "
            "Without a number, every change feels like a coin flip."),
    },

    # ---------------- Module 4: architecture and tools ----------------
    {
        "type": "section",
        "number": "04",
        "title": "How it is put together",
        "subtitle": "Same four pieces underneath, whichever product you picked.",
        "notes": (
            "The room is now choosing tools, or worrying that they chose "
            "wrong. This module defuses that by showing the shared anatomy "
            "first and the branded wrappers second.\n\n"
            "Keep it structural. Nobody needs to implement any of this today. "
            "They need to be able to read a product page and recognise which "
            "of the four pieces it is talking about."),
    },
    {
        "type": "cards",
        "eyebrow": "The anatomy",
        "title": "Four pieces of every production agent",
        "cards": [
            {"num": "01", "title": "A model",
             "desc": "The reasoning. Swappable, and cheaper every quarter."},
            {"num": "02", "title": "Tools",
             "desc": "How it touches the world: files, shell, APIs, a browser."},
            {"num": "03", "title": "A loop",
             "desc": "Act, observe the result, decide again. Not one shot."},
            {"num": "04", "title": "Context",
             "desc": "What it knows going in: your files, your instructions, your memory."},
        ],
        "callout": ("<strong>Where your leverage is:</strong> you do not "
                    "control the model and you barely control the loop. You "
                    "control the tools you expose and the context you write. "
                    "That is the job."),
        "notes": (
            "Tie each piece back to the demo. It had a model, it had a tool "
            "(the filesystem), it ran a loop (write, then open), and it had "
            "context (the folder, and the name of someone in the room).\n\n"
            "The callout is the argument for everything in Module 2. If "
            "leverage lives in tools and context, then time spent on markdown "
            "is not admin, it is the actual work."),
    },
    {
        "type": "kpi",
        "eyebrow": "An architecture decision with a price tag",
        "title": "CLI first, API second, MCP last",
        "kpis": [
            {"value": "~200", "label": "tokens a CLI returns for a query:<br>scoped, pre-formatted, out of your way"},
            {"value": "~132K", "label": "tokens an MCP can dump for the same<br>query, as raw JSON"},
            {"value": "every", "label": "turn an MCP re-sends its tool schemas,<br>whether you use them or not"},
        ],
        "callout": ("<strong>Two costs, not one.</strong> Tokens are an "
                    "operating expense, and reliability drops as well: the "
                    "more an agent has to parse, the more it loses the thread."),
        "cite": "concepts/cli-over-mcp (6 sources)",
        "notes": (
            "This one usually surprises people, because MCP is the thing they "
            "have heard of. It is the newest and most marketed layer, so it "
            "gets treated as the most advanced. It is the last resort.\n\n"
            "The plain version: a CLI is a tool that already knows how to "
            "summarise itself. An MCP hands the agent everything and makes it "
            "sort through the pile.\n\n"
            "Do not turn this into an anti-MCP rant. The rule is a tier "
            "order. Use MCP when there is no CLI and no clean API, which does "
            "happen."),
    },
    {
        "type": "six-up",
        "eyebrow": "Same engine, different car",
        "title": "The harnesses people actually use",
        # Six cells on one slide: keep `num` to a short label and `desc` to a
        # single short line, or the 3x2 grid overflows the slide height.
        "items": [
            {"num": "37", "title": "Claude Code", "desc": "Terminal-native. The reference for this deck."},
            {"num": "19", "title": "Codex", "desc": "GUI plus CLI. Strong on long runs."},
            {"num": "18", "title": "OpenClaw", "desc": "Open harness, bring your own model."},
            {"num": "8", "title": "Cowork", "desc": "GUI-first. Where the handoff often starts."},
            {"num": "6", "title": "Hermes", "desc": "Always-on personal assistant framing."},
            {"num": "3", "title": "Cursor", "desc": "The editor with the agent built in."},
        ],
        "callout": ("<strong>Read the numbers, not the names.</strong> That "
                    "is how many independent sources in this wiki discuss "
                    "each one. The list will look different in six months, "
                    "which is exactly why the four pieces matter more."),
        "notes": (
            "Deliberately labelled with evidence counts rather than opinions, "
            "so the slide ages honestly and nobody mistakes it for a "
            "recommendation.\n\n"
            "The previous version of this handbook had a table like this and "
            "it rotted badly: two of its six entries were tools with a single "
            "source that nobody had mentioned since May. Say that out loud if "
            "the room is technical. It is a good lesson about tool churn.\n\n"
            "If asked what to pick: whichever their team already uses, or "
            "Claude Code because most material is written for it. The answer "
            "genuinely does not matter as much as they want it to."),
    },
    {
        "type": "content",
        "eyebrow": "How other people get to use it",
        "title": "A dashboard is the access layer, not the system",
        "body": ("Terminal-first agents create leverage for one power user "
                 "and exclude everyone else. A dashboard turns hidden agent "
                 "work into something a teammate can see and run."),
        "bullets": [
            "Status, queues, and metrics for runs nobody watched",
            "Buttons and approvals for people who should never touch a prompt",
            "Handoff points, so a stalled run gets noticed",
            "A packaging surface: it is how this becomes something you can sell",
        ],
        "callout": ("<strong>The failure mode has a name:</strong> dashboard "
                    "theater. A polished control panel with no reliable "
                    "workflow underneath it. Build the workflow first."),
        "cite": "concepts/dashboard-as-access-layer (7 sources)",
        "notes": (
            "This is the bridge from personal productivity to something with "
            "commercial value, and it is where the non-technical half of the "
            "room re-engages if you lost them in the CLI slide.\n\n"
            "The point to land: the dashboard is not a simplification for "
            "people who cannot handle the terminal. It is the interface that "
            "makes the system operable by a team at all.\n\n"
            "Dashboard theater is worth naming because it is the most common "
            "way agent demos impress in a meeting and collapse in use."),
    },
    {
        "type": "content",
        "eyebrow": "When one agent is not enough",
        "title": "Long jobs fail in three specific ways",
        "body": ("On a long task in a single context window, agents degrade "
                 "predictably. Naming the three failure modes makes them "
                 "diagnosable instead of mysterious."),
        "bullets": [
            "<strong>Stops early.</strong> Declares the job done when it is not.",
            "<strong>Favours its own work.</strong> Ask it to judge its output and it approves.",
            "<strong>Loses the objective.</strong> Context grows, compacts, and the original goal fades. Context rot.",
        ],
        "callout": ("<strong>The fix:</strong> have the agent write its own "
                    "team for the job. Sub-agents with clean contexts, one "
                    "job each, judged separately. It costs real tokens, which "
                    "is the trade you are making."),
        "cite": "concepts/dynamic-workflows (5 sources)",
        "notes": (
            "Advanced, and worth including anyway: these three failure modes "
            "are what people hit in week three, and without names they read "
            "as \"the agent is unreliable\" rather than three fixable "
            "problems.\n\n"
            "The self-favouring one is the least intuitive and the most "
            "important. An agent asked to grade its own work says it is good. "
            "That is why the judging has to happen in a context that did not "
            "do the work, and it is the same logic as the evals slide.\n\n"
            "Flag the cost honestly. This is the most token-expensive pattern "
            "in the corpus. It is for jobs where being wrong is expensive."),
    },

    # ---------------- Module 5: the economics ----------------
    {
        "type": "section",
        "number": "05",
        "title": "What it costs, and against what",
        "subtitle": "The objection you will hear in every budget meeting.",
        "notes": (
            "\"Isn't that expensive?\" is the question that kills most agent "
            "adoption, and it is almost always asked against the wrong "
            "denominator.\n\n"
            "Three slides: reframe the cost, resist building what already "
            "exists, and structure the work so it compounds instead of "
            "repeating."),
    },
    {
        "type": "kpi",
        "eyebrow": "The reframe",
        "title": "Price it against the hours, not the tokens",
        "kpis": [
            {"value": "$150", "label": "of tokens for a board memo that would<br>have taken hours of analyst time"},
            {"value": "$40K", "label": "a month in model spend, replacing<br>several full-time salaries"},
            {"value": "0&times;", "label": "marginal cost of the second, fifth,<br>or fiftieth variant"},
        ],
        "callout": ("<strong>Token cost is the wrong denominator.</strong> "
                    "The right one is the human time replaced, plus the "
                    "overhead and onboarding you never paid."),
        "cite": "concepts/opportunity-cost-vs-token-cost (16 sources)",
        "notes": (
            "This is the mental model that makes \"companies worth billions "
            "with under five people\" sound arithmetic rather than "
            "hype.\n\n"
            "Warn them the objection will not arrive as arithmetic. It "
            "arrives as a feeling that $150 for one document is outrageous, "
            "usually from someone who has never priced the analyst hours "
            "against it. The answer is to always quote both numbers.\n\n"
            "Do not oversell. There are plenty of tasks where the tokens do "
            "cost more than the value. The point is to do the comparison at "
            "all, not to assume it always wins."),
    },
    {
        "type": "content",
        "eyebrow": "The discipline nobody wants",
        "title": "Ask first, build second",
        "body": ("Building got cheap, so the temptation to build is higher "
                 "than it has ever been. The cost of building the wrong thing "
                 "did not fall at all."),
        "bullets": [
            "Check whether a tool, plugin, or platform already does it",
            "Custom builds carry maintenance and context rot that off-the-shelf does not",
            "Three days on a proposal generator is three days not spent on customers",
            "The cheaper building gets, the more valuable this discipline becomes",
        ],
        "callout": ("<strong>The trap:</strong> being able to build anything "
                    "in an afternoon feels like leverage. It is only leverage "
                    "if the thing needed to exist."),
        "cite": "concepts/off-the-shelf-before-vibe-code (4 sources)",
        "notes": (
            "Deliberately placed right after the slide that makes everything "
            "sound affordable, because that is exactly when people start "
            "building things they should have bought.\n\n"
            "It is also the counterweight to the whole deck. Five modules "
            "have been encouraging them to build. This is the one that says "
            "check first.\n\n"
            "Good question for the room: what did you build in the last year "
            "that you could have bought for a subscription? Most people have "
            "one, and naming it out loud makes the lesson stick better than "
            "any slide."),
    },
    {
        "type": "flow",
        "eyebrow": "Turning a task into a system",
        "title": "Loop engineering",
        "steps": [
            {"num": "01", "title": "One objective metric",
             "desc": "Black or white. A ranking, a score, revenue, a rubric result. "
                     "Without one the agent loops forever."},
            {"num": "02", "title": "A stop condition",
             "desc": "What good enough looks like. This is what makes long-running "
                     "autonomy safe to leave scheduled."},
            {"num": "03", "title": "Memory between runs",
             "desc": "Each run writes what it learned to a markdown file. The next "
                     "run starts from there instead of from zero."},
        ],
        "callout": ("<strong>The difference this makes:</strong> an agent "
                    "that does a task once versus a system that compounds. "
                    "Run monthly for years, and each expensive run becomes an "
                    "asset for the next one."),
        "cite": "concepts/objective-metric-loops (4 sources)",
        "notes": (
            "This is the most advanced idea in the deck and it is worth "
            "ending the module on, because it is the shape of everything that "
            "actually kept running.\n\n"
            "Notice it reuses every earlier piece: a metric is an eval, the "
            "markdown memory is the vault, the stop condition is a rung on "
            "the autonomy ladder. Say that. It tells the room the day had a "
            "structure.\n\n"
            "Because a scheduled loop fires rarely, it is also cheap in "
            "practice despite doing expensive work each time."),
    },

    # ---------------- Module 6: taste and templates ----------------
    {
        "type": "section",
        "number": "06",
        "title": "Taste is the part that does not commoditize",
        "subtitle": "Everyone has the same models. The inputs are what differ.",
        "notes": (
            "The room now knows how to operate an agent. This module is about "
            "why two people with identical tools produce work of wildly "
            "different quality.\n\n"
            "Keep it concrete. Taste sounds like an excuse for people who "
            "cannot measure things. The two slides here make it a set of "
            "artifacts you can actually maintain."),
    },
    {
        "type": "content",
        "eyebrow": "The most leveraged file you own",
        "title": "The templates renaissance",
        "body": ("Code and content are commoditized. A well-structured "
                 "template is not: it hands the agent structure, voice, and "
                 "domain conventions from the very first token."),
        "bullets": [
            "Without one, an agent starts from zero and produces generic output",
            "With one, it inherits your standards before it writes a word",
            "Starter files, boilerplates, storyboard formats, style guides",
            "What used to be dismissed as boilerplate is now the highest-leverage thing you maintain",
        ],
        "callout": ("<strong>The rule:</strong> the quality ceiling of "
                    "agent-produced work is proportional to the quality of "
                    "the template it started from. Fix the template, not the "
                    "output."),
        "cite": "concepts/templates-as-agent-context (8 sources)",
        "notes": (
            "This is Module 2's markdown argument applied to quality rather "
            "than memory, and it is the practical definition of taste: taste "
            "is what you wrote down in the template.\n\n"
            "For people who are not designers or writers, this is liberating. "
            "You do not need to have taste on demand, in the moment, every "
            "time. You need to capture it once, carefully, and reuse it.\n\n"
            "Connect it back to workflow-first skills: the template is what a "
            "formalized run leaves behind."),
    },
    {
        "type": "versus",
        "eyebrow": "A trick worth stealing",
        "title": "Show it, do not describe it",
        "old": {
            "title": "Text-only brief",
            "desc": "You describe what you want in words and hope it lands.",
            "bullets": ["Palette and spacing get lost",
                        "\"Clean and modern\" means nothing",
                        "You iterate by arguing about adjectives"],
        },
        "new": {
            "title": "Visual-first brief",
            "desc": "Screenshots and reference images become the spec.",
            "bullets": ["A multimodal model reads the images",
                        "It writes the structured brief",
                        "An agent executes it"],
        },
        "callout": ("<strong>Why it works:</strong> images carry design "
                    "intent, palette, layout, typography, spacing, that "
                    "text-only prompts consistently fail to convey."),
        "cite": "concepts/visual-first-prd (3 sources)",
        "notes": (
            "Small concept, three sources, and it earns a slide because it is "
            "immediately usable by the least technical person in the room "
            "this afternoon.\n\n"
            "The demo, if you have time: screenshot any site you like, hand "
            "it over, ask for a structured brief. People who have spent "
            "months failing to describe what they want in words find this "
            "genuinely emotional.\n\n"
            "It also generalises beyond design. A screenshot of a spreadsheet "
            "or a form is a better spec than a paragraph about it."),
    },

    # ---------------- Module 7: the business ----------------
    {
        "type": "section",
        "number": "07",
        "title": "What this does to the work",
        "subtitle": "Roles, distribution, and how the first sale actually happens.",
        "notes": (
            "Shift the register here. Everything so far has been how to "
            "operate. This module is what it changes about jobs and "
            "businesses, and it is the part people take home.\n\n"
            "Some of the room is employed and some wants to sell this. The "
            "three slides serve both, in that order."),
    },
    {
        "type": "versus",
        "eyebrow": "Two forces at once",
        "title": "Roles are collapsing in two directions",
        "old": {
            "title": "Horizontal collapse",
            "desc": "The coder, the PM, and the designer merge into one builder.",
            "bullets": ["Each can now do the other two's work",
                        "One person with judgment spans functions",
                        "Specialisation stops being the hiring signal"],
        },
        "new": {
            "title": "Vertical shift",
            "desc": "The individual contributor becomes a manager of agents.",
            "bullets": ["You direct a fleet rather than doing the work",
                        "The skill is delegation and review",
                        "Your throughput stops being bounded by your hands"],
        },
        "callout": ("<strong>What hiring becomes:</strong> not \"can this "
                    "person code, design, or manage a product?\" but \"can "
                    "this person direct agents and judge the result?\""),
        "cite": "concepts/role-collapse (10 sources)",
        "notes": (
            "The old handbook had the horizontal half of this and missed the "
            "vertical entirely, which is the half the room is actually living "
            "through.\n\n"
            "Read the mood carefully. For some people this slide is exciting "
            "and for others it is a threat to a specialism they spent a "
            "decade building. Both readings are legitimate.\n\n"
            "The honest reassurance: judgment is the part that survives, and "
            "judgment is what a decade of specialism actually bought them. "
            "What they lose is the monopoly on execution, not the "
            "expertise."),
    },
    {
        "type": "content",
        "eyebrow": "The uncomfortable one",
        "title": "Distribution beats engineering now",
        "body": ("Code is commoditized: hundreds of thousands of new "
                 "vibe-coded projects a day. The durable advantage moved from "
                 "building to getting it in front of people."),
        "bullets": [
            "The correct sequence inverts: audience first, product second",
            "Founders who spend half their time on traffic and selling outperform those optimising code",
            "An hour building without a distribution plan is procrastination with a nice IDE",
            "The wealthiest builders in this era will be marketers",
        ],
        "callout": ("<strong>Sharp version:</strong> a product nobody knows "
                    "about is a hobby, and agents just made building the "
                    "cheap part of the equation."),
        "cite": "concepts/distribution-over-engineering (8 sources)",
        "notes": (
            "This lands badly with technical audiences and it is worth saying "
            "anyway, because it is the most repeated business claim in the "
            "corpus.\n\n"
            "Do not soften it into \"marketing is also important.\" The claim "
            "is stronger: the scarce thing moved, and the people who keep "
            "optimising the abundant thing will lose to people who did not.\n\n"
            "Pair it with the next slide immediately, because \"go do "
            "distribution\" is useless advice without a concrete motion."),
    },
    {
        "type": "flow",
        "eyebrow": "How the first sale actually happens",
        "title": "Lead with a cheap diagnostic",
        "steps": [
            {"num": "01", "title": "Sell a small audit",
             "desc": "Cheap or free. Low risk, high clarity. The buyer is deciding "
                     "on a small thing, not a big one."},
            {"num": "02", "title": "Prove value inside it",
             "desc": "Find something measurable. You also learn the real, "
                     "undocumented workflow before you ever quote a build."},
            {"num": "03", "title": "Let the proof pull them up",
             "desc": "The client asks for the implementation. Then the retainer. "
                     "You never had to make the hard first sale."},
        ],
        "callout": ("<strong>Why it works:</strong> when intelligence and "
                    "code are commoditized, the scarce thing is a trusted "
                    "path into a specific business. An audit buys that."),
        "cite": "concepts/audit-as-tripwire (3 sources)",
        "notes": (
            "The practical answer to the previous slide. Distribution sounds "
            "abstract; this is a motion someone can run next week.\n\n"
            "The insight that makes it more than a sales trick: you cannot "
            "quote a build accurately for a business whose real workflow you "
            "have not seen, and every business's real workflow differs from "
            "its documented one. The audit is how you find out, and they pay "
            "you to do the discovery.\n\n"
            "The diagnostic is deliberately underpriced against the lifetime "
            "value. That is the trade, and it is worth making."),
    },

    # ---------------- Module 8: the limits ----------------
    {
        "type": "section",
        "number": "08",
        "title": "Where this stops working",
        "subtitle": "One source in this wiki reports a failure. It is the most useful one.",
        "notes": (
            "Every other source in the corpus is a success story, which is "
            "exactly why this module exists. A training with no limits is "
            "marketing, and the room can tell.\n\n"
            "This also protects them. People who believe agents have no "
            "ceiling discover the ceiling in production, on something that "
            "matters."),
    },
    {
        "type": "content",
        "eyebrow": "The lights-off experiment",
        "title": "Nobody read the code, and it fell apart",
        "body": ("An agent software factory run with nobody reading the "
                 "output. It worked, until an issue appeared that no amount "
                 "of prompting could fix, the site was down, and the fix "
                 "meant digging through a codebase abandoned months earlier."),
        "bullets": [
            "Not a skill problem, and not a scale problem",
            "No harness and no extra tokens fixes it",
            "Coding models are rewarded for one thing: did the test pass without breaking another",
            "Nothing in that reward penalises bad architecture, whose cost arrives months later",
        ],
        "callout": ("<strong>The uncomfortable part:</strong> they get better "
                    "at passing tests and no better at keeping a codebase "
                    "maintainable. If a model knew what good looked like, it "
                    "would already write it."),
        "cite": "sources/harness-engineering-is-not-enough (AI Engineer)",
        "notes": (
            "Deliver this straight. No hedging, no rescuing it with "
            "optimism at the end of every sentence.\n\n"
            "The reason it is credible is that it comes from someone who "
            "built the thing and reported it failing, which is rarer than any "
            "success story and worth more.\n\n"
            "The mechanism is the part to make sure they keep: models are "
            "trained against verifiable rewards, tests pass or fail, and "
            "maintainability is not verifiable that way. That is why this is "
            "not fixed by a better prompt."),
    },
    {
        "type": "content",
        "eyebrow": "So what do you do about it",
        "title": "Turn the lights back on",
        "body": ("The fix is not to use agents less. It is to keep a human in "
                 "the parts the reward function cannot see."),
        "bullets": [
            "Plan up front: product review, then system architecture",
            "Program design down to types and call graphs, the step everyone skips",
            "Then vertical slices, so each piece is reviewable",
            "Keep reading the output. You can still move fast while doing it.",
        ],
        "callout": ("<strong>The trade:</strong> thirty minutes of alignment "
                    "up front saves hours of review afterwards, and a good "
                    "result becomes a joy to read instead of slop to untangle."),
        "cite": "topics/software-factory (2 sources)",
        "notes": (
            "End the module constructively so the room does not leave "
            "deflated. The conclusion is not that agents fail, it is that "
            "unattended agents fail on the dimension nobody is measuring.\n\n"
            "This also loops back to autonomy. The ladder exists precisely "
            "because the top rung is not free, and this slide is what the top "
            "rung costs when you skip the climb.\n\n"
            "For a non-technical room, translate: you cannot stop reviewing "
            "the work just because it arrives faster."),
    },

    # ---------------- Close ----------------
    {
        "type": "lead",
        "eyebrow": "The whole training in one line",
        "headline": "Write the context. Judge the output.<br>Everything else is the tool's job.",
        "subtitle": ("The models improve without you. Your files and your "
                     "judgment are the parts that compound."),
        "notes": (
            "If they remember one slide, this is the one. Both halves matter: "
            "writing without judging produces confident slop, judging without "
            "writing means starting from zero every time.\n\n"
            "It also quietly re-states the two things that survive every tool "
            "change, which is the honest answer to \"what should I invest in "
            "learning?\""),
    },
    {
        "type": "cards",
        "eyebrow": "If you do nothing else",
        "title": "Minimum viable operator",
        "cards": [
            {"num": "01", "title": "Install it locally",
             "desc": "One agent, running in a terminal, in a folder you care about."},
            {"num": "02", "title": "Start one file",
             "desc": "A markdown file it reads every session. Add to it when you correct it."},
            {"num": "03", "title": "Formalize one workflow",
             "desc": "Do a real job manually, then have it package the run into a skill."},
            {"num": "04", "title": "Keep twenty examples",
             "desc": "Real cases with the answer you would have given. That is your eval set."},
        ],
        "callout": ("<strong>Note what is missing:</strong> no MCP servers, "
                    "no dashboard, no fleet. Those come after this works, not "
                    "before."),
        "notes": (
            "The previous handbook's version of this slide told people to "
            "wire up three MCP servers on day one, which contradicts the "
            "CLI-first architecture in Module 4 and is the wrong first move "
            "regardless.\n\n"
            "Four steps, deliberately small enough to finish this week. The "
            "failure mode for this audience is not lack of ambition, it is "
            "building an elaborate setup before doing any real work with "
            "it.\n\n"
            "Send them away with the first one only, if the room is new. "
            "Install it, and give it one real job."),
    },
    {
        "type": "lead",
        "eyebrow": "Last thing",
        "headline": "Go and give it something real to do.",
        "subtitle": ("Not a test. Something from your actual work, today, "
                     "that you would otherwise have done by hand."),
        "notes": (
            "Do not end on a summary. End on an instruction.\n\n"
            "The single biggest predictor of whether someone is still doing "
            "this in a month is whether their first job was real. Test tasks "
            "teach nothing because nothing is at stake and no correction "
            "matters.\n\n"
            "If you take questions afterwards, the most common one is \"what "
            "should I use it for?\" Turn it around: what did you do this week "
            "that you resented doing? Start there."),
    },
]
