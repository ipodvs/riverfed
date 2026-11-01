# The Riverfed Handbook — teaching notes

These notes assume the room already uses AI in a browser and has never run an agent. Every section states what the audience already believes, then what has to change. Live demos are marked DEMO with the exact commands to type.

## Slide 1 · The Riverfed Handbook

Say the counts out loud. They are the deck's credibility: every claim traces to a transcript, and nothing here is opinion dressed as fact.

Do not open with a definition of agents. The room has heard it and it did not stick, because a definition cannot be checked against anything they have touched. We are going to make them believe one physical fact first, then define terms afterwards.

## Slide 2 · You have been renting the AI. Today you install it.

The distinction is not capability, it is location, and location is what unlocks everything else.

The AI in a browser tab runs on someone else's computer. It can return words to you and nothing else. The same model running on your machine can read your files, write new ones, and run commands. Nobody argues with this once they see it, which is why the next four slides are a demo rather than an explanation.

## Slide 3 · Where the AI actually runs

This module exists because of a pattern seen across many training sessions: people who use AI daily still picture it as a website. Until that picture changes, terminal, vault and skills all sound like developer trivia.

Budget real time here. If the room leaves this module believing the AI is a program on their laptop with hands, the rest of the day lands. If they do not, nothing later recovers it.

## Slide 4 · A tab, or a program on your machine

Ask the room how they currently move work between the AI and their computer. The honest answer is copy and paste. Let them say it.

That is the cost being removed. Not intelligence: plumbing. The model is often literally the same one they already pay for.

## Slide 5 · Two commands that change the room

DEMO. Type it, do not paste it, so the room sees ordinary language going in rather than a magic incantation.

Beat 1: 'create a txt file saying hello Maria'. Pick someone in the room and say why you are picking them. While it runs, say nothing. Let them watch.

Beat 2: switch to Finder or Explorer and open the folder. Do not narrate this as a technical step. It is a file. It is on the computer in front of them.

Beat 3: back to the terminal, 'now open the file'. When it opens, that is the moment. Pause.

Expect one of two reactions: silence, or someone asking whether it can do that to any file. The second question is the whole afternoon and you should welcome it. Answer honestly: yes, within the folder you started it in, and that is exactly why permissions and directories matter later.

## Slide 6 · A text file and a program are the same thing to it.

This is the single most important sentence in the deck. Say it slowly and then say it again in their words.

It just wrote text to a file. Code is text. So it can write code. It just ran a command to open that file. Running a program is a command. So it can run code.

Write, then execute. Everything the rest of the day describes, building tools, automating work, agents that operate for hours, is that same loop repeated with better instructions.

This is also where you defuse the fear. Someone is thinking 'so it can do anything to my computer?'. Answer before they ask: it acts in the folder you point it at, it shows you what it is about to do, and you can make it ask permission every time.

## Slide 7 · So which editor should you use?

People arrive expecting to be told which tool to buy, and that expectation makes them passive. Removing the question hands the decision back to them.

If someone has already paid for an AI editor, do not undercut them. It is genuinely convenient. The point is that their capability does not come from the editor, so they are not locked in and not behind.

## Slide 8 · No. You learn where the handoff is

Say this plainly: the previous slides were not an argument that the browser is bad. Overselling the terminal is how you lose the half of the room that is not ready for it.

This is the slide that gives people permission to start where they are. Nobody has to migrate their whole working life today. They need one job that is worth escalating.

Ask the room for a candidate: something they gave up on because copy and paste made it not worth it. That is their first terminal job, and it is a better homework assignment than anything you could set.

## Slide 9 · What it reads and writes

The room has just watched the agent write and open a file. This module answers the obvious next question: what should be in those files?

The answer is boring and that is why it works. Not a database, not a special format, not a product. Markdown.

## Slide 10 · Markdown is the oxygen

26 of 53 sources land on this independently. It is the single most corroborated claim in the corpus, which is why it gets a slide this early.

For this audience the useful translation is: you already know how to write. You do not need to learn a database, an API, or a framework. A document is the interface.

The ceiling line is the one to dwell on. People try to fix bad agent output by rewriting the prompt. Usually the prompt is fine and the file it read was thin.

## Slide 11 · The terminal is where things converge

Do not oversell this. The wiki's own position, covered two slides from now, is that the browser still wins for research and ideation. The terminal wins for shipping.

The honest framing for a non-technical room: you are not becoming a developer. You are choosing the place where your files, your tools, and the thing doing the work are all in the same room.

## Slide 12 · "It keeps forgetting everything"

This slide converts the room's most common frustration into something they can actually fix, which is worth more than any capability claim.

It also pays off the demo. They watched it write a file. Memory is the same move: it is only remembered if it got written somewhere on disk.

Good moment to ask who has repeated the same instruction to a chatbot three days running. Most hands go up. That is the problem being solved.

## Slide 13 · Manage the vault, not the agent

This is the answer to "which tool should I commit to?", which is the question people are actually anxious about.

The answer is that the question matters less than they think, provided their effort goes into the durable layer. Tools are a two-year bet. A vault is a ten-year one.

It is also the honest sales pitch for doing the boring work: nobody is excited about organising notes, but it is the only part of this that compounds.

## Slide 14 · Getting good at it

Everything so far has been setup and substrate. This module is the actual craft, and it is where most people stall.

Three ideas, in dependency order: how you build a repeatable skill, how you decide to trust it with more, and how you know whether it is any good. The third makes the second safe.

## Slide 15 · Do it, formalize it, iterate it

18 sources, and the previous version of this handbook never said it once. It named skills five times as a thing that exists and never explained how you get one.

The instinct in the room will be to sit down and write the perfect instruction file first. That instinct is wrong and it is worth naming explicitly, because it is how people waste their first week.

The analogy that lands: you do not write the training manual before doing the job. You do the job, notice what you had to explain, and write that down.

## Slide 16 · Autonomy is earned, not configured

This answers the fear from Module 1 properly. Earlier you said "it asks permission." Here is the grown-up version: permission is a rung, and you move up it deliberately.

Every source in the wiki that actually took agents to production converges on this, which is worth saying out loud. It is not a cautious opinion, it is what the practitioners did.

For anyone considering selling this: the ladder is also the pitch. A customer will not buy full autonomy from a stranger. They will buy draft-and-approve.

## Slide 17 · If you cannot measure it, you cannot promote it

Put this immediately after autonomy, because it is what makes the ladder safe rather than optimistic.

For a beginner audience, keep it concrete and small. An eval set can be twenty real examples in a markdown file with the answer you would have given. That is enough to notice regression. It does not require a framework.

This is also the slide that separates people who will still be running agents in a year from people who will have given up. Without a number, every change feels like a coin flip.

## Slide 18 · How it is put together

The room is now choosing tools, or worrying that they chose wrong. This module defuses that by showing the shared anatomy first and the branded wrappers second.

Keep it structural. Nobody needs to implement any of this today. They need to be able to read a product page and recognise which of the four pieces it is talking about.

## Slide 19 · Four pieces of every production agent

Tie each piece back to the demo. It had a model, it had a tool (the filesystem), it ran a loop (write, then open), and it had context (the folder, and the name of someone in the room).

The callout is the argument for everything in Module 2. If leverage lives in tools and context, then time spent on markdown is not admin, it is the actual work.

## Slide 20 · CLI first, API second, MCP last

This one usually surprises people, because MCP is the thing they have heard of. It is the newest and most marketed layer, so it gets treated as the most advanced. It is the last resort.

The plain version: a CLI is a tool that already knows how to summarise itself. An MCP hands the agent everything and makes it sort through the pile.

Do not turn this into an anti-MCP rant. The rule is a tier order. Use MCP when there is no CLI and no clean API, which does happen.

## Slide 21 · The harnesses people actually use

Deliberately labelled with evidence counts rather than opinions, so the slide ages honestly and nobody mistakes it for a recommendation.

The previous version of this handbook had a table like this and it rotted badly: two of its six entries were tools with a single source that nobody had mentioned since May. Say that out loud if the room is technical. It is a good lesson about tool churn.

If asked what to pick: whichever their team already uses, or Claude Code because most material is written for it. The answer genuinely does not matter as much as they want it to.

## Slide 22 · A dashboard is the access layer, not the system

This is the bridge from personal productivity to something with commercial value, and it is where the non-technical half of the room re-engages if you lost them in the CLI slide.

The point to land: the dashboard is not a simplification for people who cannot handle the terminal. It is the interface that makes the system operable by a team at all.

Dashboard theater is worth naming because it is the most common way agent demos impress in a meeting and collapse in use.

## Slide 23 · Long jobs fail in three specific ways

Advanced, and worth including anyway: these three failure modes are what people hit in week three, and without names they read as "the agent is unreliable" rather than three fixable problems.

The self-favouring one is the least intuitive and the most important. An agent asked to grade its own work says it is good. That is why the judging has to happen in a context that did not do the work, and it is the same logic as the evals slide.

Flag the cost honestly. This is the most token-expensive pattern in the corpus. It is for jobs where being wrong is expensive.

## Slide 24 · What it costs, and against what

"Isn't that expensive?" is the question that kills most agent adoption, and it is almost always asked against the wrong denominator.

Three slides: reframe the cost, resist building what already exists, and structure the work so it compounds instead of repeating.

## Slide 25 · Price it against the hours, not the tokens

This is the mental model that makes "companies worth billions with under five people" sound arithmetic rather than hype.

Warn them the objection will not arrive as arithmetic. It arrives as a feeling that $150 for one document is outrageous, usually from someone who has never priced the analyst hours against it. The answer is to always quote both numbers.

Do not oversell. There are plenty of tasks where the tokens do cost more than the value. The point is to do the comparison at all, not to assume it always wins.

## Slide 26 · Ask first, build second

Deliberately placed right after the slide that makes everything sound affordable, because that is exactly when people start building things they should have bought.

It is also the counterweight to the whole deck. Five modules have been encouraging them to build. This is the one that says check first.

Good question for the room: what did you build in the last year that you could have bought for a subscription? Most people have one, and naming it out loud makes the lesson stick better than any slide.

## Slide 27 · Loop engineering

This is the most advanced idea in the deck and it is worth ending the module on, because it is the shape of everything that actually kept running.

Notice it reuses every earlier piece: a metric is an eval, the markdown memory is the vault, the stop condition is a rung on the autonomy ladder. Say that. It tells the room the day had a structure.

Because a scheduled loop fires rarely, it is also cheap in practice despite doing expensive work each time.

## Slide 28 · Taste is the part that does not commoditize

The room now knows how to operate an agent. This module is about why two people with identical tools produce work of wildly different quality.

Keep it concrete. Taste sounds like an excuse for people who cannot measure things. The two slides here make it a set of artifacts you can actually maintain.

## Slide 29 · The templates renaissance

This is Module 2's markdown argument applied to quality rather than memory, and it is the practical definition of taste: taste is what you wrote down in the template.

For people who are not designers or writers, this is liberating. You do not need to have taste on demand, in the moment, every time. You need to capture it once, carefully, and reuse it.

Connect it back to workflow-first skills: the template is what a formalized run leaves behind.

## Slide 30 · Show it, do not describe it

Small concept, three sources, and it earns a slide because it is immediately usable by the least technical person in the room this afternoon.

The demo, if you have time: screenshot any site you like, hand it over, ask for a structured brief. People who have spent months failing to describe what they want in words find this genuinely emotional.

It also generalises beyond design. A screenshot of a spreadsheet or a form is a better spec than a paragraph about it.

## Slide 31 · What this does to the work

Shift the register here. Everything so far has been how to operate. This module is what it changes about jobs and businesses, and it is the part people take home.

Some of the room is employed and some wants to sell this. The three slides serve both, in that order.

## Slide 32 · Roles are collapsing in two directions

The old handbook had the horizontal half of this and missed the vertical entirely, which is the half the room is actually living through.

Read the mood carefully. For some people this slide is exciting and for others it is a threat to a specialism they spent a decade building. Both readings are legitimate.

The honest reassurance: judgment is the part that survives, and judgment is what a decade of specialism actually bought them. What they lose is the monopoly on execution, not the expertise.

## Slide 33 · Distribution beats engineering now

This lands badly with technical audiences and it is worth saying anyway, because it is the most repeated business claim in the corpus.

Do not soften it into "marketing is also important." The claim is stronger: the scarce thing moved, and the people who keep optimising the abundant thing will lose to people who did not.

Pair it with the next slide immediately, because "go do distribution" is useless advice without a concrete motion.

## Slide 34 · Lead with a cheap diagnostic

The practical answer to the previous slide. Distribution sounds abstract; this is a motion someone can run next week.

The insight that makes it more than a sales trick: you cannot quote a build accurately for a business whose real workflow you have not seen, and every business's real workflow differs from its documented one. The audit is how you find out, and they pay you to do the discovery.

The diagnostic is deliberately underpriced against the lifetime value. That is the trade, and it is worth making.

## Slide 35 · Where this stops working

Every other source in the corpus is a success story, which is exactly why this module exists. A training with no limits is marketing, and the room can tell.

This also protects them. People who believe agents have no ceiling discover the ceiling in production, on something that matters.

## Slide 36 · Nobody read the code, and it fell apart

Deliver this straight. No hedging, no rescuing it with optimism at the end of every sentence.

The reason it is credible is that it comes from someone who built the thing and reported it failing, which is rarer than any success story and worth more.

The mechanism is the part to make sure they keep: models are trained against verifiable rewards, tests pass or fail, and maintainability is not verifiable that way. That is why this is not fixed by a better prompt.

## Slide 37 · Turn the lights back on

End the module constructively so the room does not leave deflated. The conclusion is not that agents fail, it is that unattended agents fail on the dimension nobody is measuring.

This also loops back to autonomy. The ladder exists precisely because the top rung is not free, and this slide is what the top rung costs when you skip the climb.

For a non-technical room, translate: you cannot stop reviewing the work just because it arrives faster.

## Slide 38 · Write the context. Judge the output. Everything else is the tool's job.

If they remember one slide, this is the one. Both halves matter: writing without judging produces confident slop, judging without writing means starting from zero every time.

It also quietly re-states the two things that survive every tool change, which is the honest answer to "what should I invest in learning?"

## Slide 39 · Minimum viable operator

The previous handbook's version of this slide told people to wire up three MCP servers on day one, which contradicts the CLI-first architecture in Module 4 and is the wrong first move regardless.

Four steps, deliberately small enough to finish this week. The failure mode for this audience is not lack of ambition, it is building an elaborate setup before doing any real work with it.

Send them away with the first one only, if the room is new. Install it, and give it one real job.

## Slide 40 · Go and give it something real to do.

Do not end on a summary. End on an instruction.

The single biggest predictor of whether someone is still doing this in a month is whether their first job was real. Test tasks teach nothing because nothing is at stake and no correction matters.

If you take questions afterwards, the most common one is "what should I use it for?" Turn it around: what did you do this week that you resented doing? Start there.
