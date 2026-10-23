# I vetted 1,800 public agent skills

*2026-10-22 · Kwan Hyeon*

SKILL.md files are the new npm: you install thirty of them into your coding agent and never read one. I pulled 1,831 public skills, linted them, scanned them for prompt-injection patterns, extracted 29,880 individual instructions from them, and checked which instructions contradict each other. Then I ran 1,708 agent sessions to see what any of it changes. Four things stood out. Only one in five states a license. The rules found almost no outright contradictions: both of their two hard flags were false, and how many they miss is unmeasured. When two skills do disagree, the agent usually picks the same one on a given task, and none of the three ways I tried to name the winner was a reliable control: the named skill was followed in 43–56% of runs, and the best method turned the agent's own choice around in only 8 of the 23 pairs where it had one. And skills mattered in 1 of the 5 task types I measured: on design, the expert's skill removed the template look; on tests, APIs, docs and data scripts the agent passed every check with or without one. For 93% of the 284 benchmark tasks that have a relevant skill, the router's search puts at least one in its top 50. In real repos the router fired on 68% of non-trivial tasks (39/57); rewriting one line of its description took that to 96% (55/57), while firing on 1 of 30 trivial ones.

## What I did

Two sources: Anthropic's own [skills repo](https://github.com/anthropics/skills) (19 skills) and the [Universal AI Skills Library](https://github.com/onfire7777/universal-ai-skills-library), an aggregate of 1,812 skills collected from 11 upstream repos. Every skill went through the same pipeline:

1. **Lint**: frontmatter parses, has a name and description, no broken relative links.
2. **Injection scan**: a regex blocklist for instruction overrides, credential reads, privilege escalation, hidden text. A blocklist, not a proof of safety.
3. **Constraint extraction**: an LLM reads each SKILL.md and turns every actionable instruction into a typed record: subject, directive (require / forbid / prefer / avoid), object, scope, and the exact source line it came from. A constraint with no quotable line is dropped.
4. **Pairwise comparison**: two constraints on the same subject with opposite polarity and overlapping scope are a candidate conflict. Anything the rules cannot settle from the text is marked `needs_review`, never `conflict`.
5. **LLM judge** over the open pairs, using a different vendor's model than the extractor, reading the original lines rather than the extracted records.
6. **Obedience test**: for pairs the judge called a real conflict, load both skills into an agent, give it a task that touches the disputed rule, and record which skill it obeys.

Apart from the Claude Code subscription, the only money spent was **$15.75** on external APIs: $6.23 for extraction (gpt-6-luna, the cheapest of the four models tried on the fixtures), $9.36 for the judge (claude-sonnet-5.5), $0.16 for task generation. The 1,708 agent sessions and the benchmarks' batch calls ran on that subscription; at API prices they would have cost about $650 ([numbers.md](numbers.md) §7), which is roughly what reproducing them from scratch costs. That figure leaves out the interactive sessions that wrote the code and classified outputs, and human time. The obedience runs and all classification happened inside Claude Code sessions. A note on authorship: I designed the pipeline and made the calls; Claude Code wrote most of the code and ran the experiments. Where this post says "I read", a human read. Code and numbers: [hyunlord/skillfetch](https://github.com/hyunlord/skillfetch).

## 1. Only one in five skills states a license

377 of 1,831 skills (20.6%) carry a license, either in their own folder or in the upstream repo they were copied from. The rest state nothing. Under copyright law, nothing stated means all rights reserved: you can read it on GitHub, but you cannot legally bundle it into an index and ship it.

| License status | Skills | Share |
| --- | --- | --- |
| Explicit (367 permissive, 10 proprietary) | 377 | 20.6% |
| Upstream repo found, no LICENSE file in it | 824 | 45.0% |
| Upstream repo unknown | 630 | 34.4% |

822 of the 824 "upstream found, no license" skills come from a single aggregator, `ComposioHQ/awesome-claude-skills`, which has no repo-level LICENSE. The library that re-collects them is MIT, but an MIT badge on an aggregator does not license the files it copied from somewhere else. This is not specific to either project; it is how the whole ecosystem currently works, and I doubt most maintainers have thought about it. Even Anthropic's own repo is mixed: 4 of its 19 skills (docx, pdf, pptx, xlsx) are all-rights-reserved and one has no license file.

This is a count of what is stated, not a legal opinion. But a registry that redistributes bodies has, for about 80% of this inventory, no license we could find that grants that permission; for 630 entries we could not even check an upstream. The practical consequence for my own tool was that the index can only hold metadata and content hashes; skill bodies have to be fetched from the original repo at use time.

## 2. 107 skills fail basic hygiene; 216 ship executable scripts

82 skills failed lint and 25 tripped the injection scan, so 1,724 made it into the index. Most lint failures are broken links: a SKILL.md pointing at `references/auth.md` that does not exist in the folder, or at a file outside the skill entirely. The scan hits are more interesting:

| Scan rule | Hits | What it catches |
| --- | --- | --- |
| `privilege.dangerous-flag` | 23 | `--dangerously-skip-permissions`, `--no-sandbox` |
| `exfil.secret-env` | 7 | echo or send of `$API_KEY`, `$TOKEN`, `$SECRET` |
| `hidden.html-comment-instruction` | 7 | instructions to the agent inside `<!-- -->` |
| `exfil.ssh-keys` | 5 | read or copy of `~/.ssh` |
| `privilege.disable-sandbox` | 3 | "disable / bypass the sandbox" |
| `exfil.cloud-credentials` | 3 | `~/.aws`, `~/.kube`, `~/.config/gcloud` |
| `hidden.invisible-chars` | 3 | zero-width characters in the body |
| `override.ignore-previous` | 1 | "ignore previous instructions" |
| `exfil.dotenv` | 1 | cat or upload of `.env` |

The hits I checked by hand were not attacks. One was Anthropic's own API guide, rejected for quoting the phrase "ignore what the user said" while telling you not to write prompts like that. Another was an end-to-end testing skill passing `--no-sandbox` to headless Chrome. That is exactly the problem: a regex cannot tell a tutorial from an exploit. Whether an agent that has just loaded the file can, I did not test. A scan like this earns its place as a gate for "show me what to look at", not as a verdict. I have not read all 25, so I cannot say none is malicious; I can say the pattern-matching alone does not establish it.

Separately, 216 skills bundle shell or Python scripts the agent is expected to run. Nothing is wrong with that in itself, but it moves the trust question from "what does this text tell my agent to do" to "what does this code do when my agent runs it", which no SKILL.md linter answers.

## 3. Skills almost never contradict each other outright. They carve each other up.

This is the finding I did not expect. I built the pipeline to catch pairs like "squash every feature into one commit" versus "never squash". From 29,880 extracted constraints across 1,722 skills, the rules flagged **2 hard conflicts**. I read both. Both are wrong.

```
CONFLICT  darwin ⟷ thinking-ooda
  darwin:37          "**Principles:** Observe before acting · …"
  thinking-ooda:108  "Immediately return to OBSERVE"
```

That is the OODA loop, not a contradiction. The other one pairs caveman-review:51, "Drop terse mode for: security findings (CVE-class bugs need full explanation + reference) …", with saga:394, "Skip verbose explanations, focus on deliverables", which applies in saga's autorun mode: different situations. So neither of the rules' two hard flags is a real contradiction. That does not show there are none: recall is unmeasured, the default mode downgrades blanket rules on purpose, and the judge below calls 90 pairs conflicts.

What the rules did find was 2,011 pairs they could not settle: 137 soft tensions and 1,874 marked `needs_review`. I had a second model read the original lines for every one of them.

| Judge verdict | Pairs | Share |
| --- | --- | --- |
| Independent (same topic, compatible) | 1,666 | 82.8% |
| Situational (true in different contexts) | 191 | 9.5% |
| Conflict | 90 | 4.5% |
| Carve-out (one narrows the other) | 57 | 2.8% |
| Error or unclear | 7 | 0.3% |

Four in five pairs that looked suspicious to the rules are fine. Of the 90 the judge called conflicts, most are of the form "always ask before acting" against "once the team is chosen, proceed without asking": one rule carving an exception out of another. The judge over-calls these: on a hand-labelled set it marked 6 of 7 known carve-outs as conflicts, so some of the 90 are not real conflicts. The pairs it called independent were not audited, so 90 is not a ceiling on conflicts in the corpus either.

The pattern across all of it: skill authors do not disagree about what to do. They disagree about **when** and **how much**: in paraphrase, keep responses short versus be thorough on security findings, or log every significant step versus never log from inside test code. These are not bugs in the skills. They are exactly the kind of thing an agent should reconcile, and the question is whether it does.

## 4. When two skills disagree, the agent rarely flips a coin. On a given task it mostly picks the same one.

I took 26 pairs the judge had called both a conflict and "ambiguous to follow together", wrote one task per pair that forces the disputed rule to matter, and ran each task five times in a fresh agent session with both skill bodies loaded and no precedence hint. Order alternated: A first on odd runs, B first on even. I then classified each output as following A, following B, both, or neither.

| Outcome across 5 runs | Pairs |
| --- | --- |
| Same skill followed in all 5 runs | 17 |
| Same non-skill outcome in all 5 (both, or neither) | 2 |
| Mixed: A on some runs, B on others | 4 |
| Other mixes | 3 |

In 17 of 26 pairs the agent followed the same one skill five times out of five; 7 had varying outcomes, 4 of them switching between A and B. Load order showed no effect in aggregate: when exactly one was obeyed, it was the first-loaded one 51 times and the second 53.

So on the tested tasks the failure mode was mostly not randomness but a stable, invisible preference. On the `tdd` ⟷ `warden` task the agent followed `tdd` in all five runs, and nothing in the session said why. With one task per pair, I cannot say whether such a preference holds on other tasks.

Two caveats that matter. First, the harness wording moved results: in a discarded batch, a note saying "finish in this one reply" pushed every "stop and ask the user" rule to lose. Pairs about pausing versus proceeding are the most fragile. Second, all 130 outputs were classified by one classifier, a Claude Code session; there was no second rater. I would want one before putting a decimal on any of this.

**No method I tried gave skills a reliable order.** The obvious fix is to tell the agent which skill wins. I tried three ways on the same 26 pairs: five runs with A named the winner and five with B, 260 runs per method, same harness and classification.

| How the winner was named | Runs that followed the named winner |
| --- | --- |
| Header before the skills: "Skills are listed in precedence order. If two instructions disagree, follow the earlier one." (what `load_skills` emitted) | 43% (112/260) |
| A block naming the winner and quoting both conflicting lines | 56% (145/260) |
| The loser's conflicting lines replaced with `<!-- overridden by <winner>: "<line>" -->` | 46% (120/260) |

None of the three is a reliable control: 43–56% of runs followed the named skill. The best, the block that names the winner, turned the agent's own choice around in 8 of the 23 pairs where it had one (the other 3 had no majority winner). That is 910 runs counting the 130 above. Per-pair tables are in [numbers.md](numbers.md) §8–§10.

## 5. Does loading skills per task help? In one of five task types.

To find out, I ran real Claude Code sessions in three conditions: **A** no skills; **B** the one skill an expert would have installed, pre-loaded; **C** skillfetch's router (the MCP server described under "Try it") picking from the index. Everything was scored blind by model judges (Claude), with the condition hidden behind random codes: in stage 1 by the session that ran the test, in the 1b rejudge and stage 2 by fresh subagents that saw only the rubric and the outputs.

On 20 small maintenance tasks on two repos (a FastAPI template and a Next.js starter; add a 404 page, link pagination, a README table), each run twice per condition (stage 1; B only on the 15 tasks with an expert skill), the three conditions were indistinguishable: 110 of 110 passed the hidden checks, screenshots tied, documents tied. On these small tasks the skills made no difference that the checks or the judges could see. C cost 6.5 more turns than A on the 15 tasks with an expert skill (6 over all 20) and 59% more input tokens, for nothing.

On 5 larger tasks on the same two repos, each run twice per condition (stage 1b), the picture split. To see whether that generalises, I then ran one large task in each of four more domains, each in its own repo (stage 2): tests for an untested 280-line module, a FastAPI bookmarks API, a README for an undocumented Next.js app, and a script that cleans a 375-row orders CSV with ten planted problems. Five runs per condition, checks frozen before the runs, every output judged blind twice by fresh model judges. Stage 2 used only the router after the search fix described below.

| | A: no skill | B: expert's skill | C: router, first version | C: router, after the search fix |
|---|---|---|---|---|
| Landing page, usable (1–5) | 3.50 | 4.75 | 4.50 | 4.75 |
| Landing page, "AI-template" tells | 2.00 | 0.50 | 2.00 | 0.50 |
| Test writing: score (1–5) · branch coverage | 4.90 · 100% | 5.00 · 100% | – | 5.00 · 100% |
| Test writing: median turns / input tokens | 10 / 0.78M | 9 / 0.83M | – | 16 / 1.49M |
| Backend API: score · contract calls passed | 4.20 · 27/27 | 4.20 · 27/27 | – | 4.80 · 27/27 |
| Backend API: median turns / input tokens | 15 / 0.90M | 14 / 0.87M | – | 23 / 1.87M |
| Documentation: score · checks passed | 4.10 · 5/5 | 4.70 · 5/5 | – | 4.40 · 5/5 |
| Documentation: median turns / input tokens | 10 / 0.69M | 9 / 0.73M | – | 17 / 1.33M |
| Data script: score · output checks passed | 4.50 · 5/5 | 4.50 · 5/5 | – | 4.50 · 5/5 |
| Data script: median turns / input tokens | 12 / 0.91M | 12 / 0.85M | – | 18 / 1.52M |
| Plan quality (rank, 0 = best) | 0.36 | 0.00 | 0.79 | 0.71 |
| Stage 1b, all 5 tasks: median turns | 19.5 | 24 | 34 | 26.5 |

*Two notes on stage 2.* (a) Documentation: two C2 runs described the router's install files (`.mcp.json` and `.claude/`, present only in the C2 repo) in their README, and the first judging pass cited that when marking them down. That is a trace of the harness, not a weakness of the router; allowing for it, documentation is also close to no difference between conditions. (b) The harness gave the sessions no AskUserQuestion or plan-mode tools, so this experiment cannot observe whether an interactive skill the router picks (one with interview or approval steps) stalls a real session. Backend API run 1 is such a case: it loaded `fastapi-endpoint`, which says "Enter plan mode" and "Use AskUserQuestion to clarify requirements", and went ahead with "Requirements are clear enough to implement directly."

The expert's skill matters: with Anthropic's `frontend-design` loaded, the landing pages lost their template look. The router's first version never found that skill (it ranked 13th to 41st, never in the 10 results the search returned) and loaded design-adjacent skills instead. On the landing pages they did not reduce the template tells (2.00, the same as no skill); on the planning task they made the plan worse than no skill (rank 0.79 vs 0.36). There, loading the wrong skill was worse than loading none.

Widening the search to 50 compact summaries and letting the agent choose from those put the expert's skill in the router's top 50 in every one of these domain-named tasks:

| Task type | Expert's skill | In the router's top 50 | Mean rank there | Loaded |
|---|---|---|---|---|
| Landing page (1b) | `frontend-design` | 4/4 | 29.2 | 4/4 |
| Test writing | `python-testing-patterns` | 5/5 | 1.0 | 5/5 |
| Backend API | `fastapi-templates` | 5/5 | 2.0 | 4/5 |
| Documentation | `quill` | 5/5 | 1.8 | 5/5 |
| Data script | `data-analyst-engine` | 5/5 | 2.0 | 5/5 |
| All | | 24/24 | | 23/24 |

Finding the skill is not the same as needing it. Design is the only domain where I saw the expert's skill change the result. On tests, the API, docs and the data script, all three conditions hit every objective metric (100% branch coverage, 27 of 27 contract calls, every check passed), and the score differences between conditions (0.6 or less) are small next to the variation between two judging passes, which agreed exactly on 8 to 14 of 15 outputs. With one task per domain and five runs per condition, this neither shows a benefit nor establishes that there is none. The router costs 1.7 to 2.1 times the input tokens of no skill and 6 to 8 more turns. That is the scope of this result: tasks the base model finishes in a median 9 to 15 turns without help, one model, five runs per condition.

The router still misses skills about *how* to work. The expert's `writing-plans` skill describes a way of working, the planning task describes a feature, and keyword search does not bridge that. A 22M-parameter embedding model did not bridge it either (top-50 recall 0.74 fused with BM25 vs BM25's 0.71, [numbers.md](numbers.md) §12), so it is not in the product.

## 6. How often does it find the right skill? A 380-task benchmark.

Five task types is a small sample, so I built a larger, offline one: 380 synthetic developer requests. 300 fill 300 of the 360 combinations of 12 task types × 6 stacks × 5 phrasings, one task each, 40 are trivial requests that should load nothing, and 20 pairs differ only in how the user asked to work. For every task a model graded the candidate skills 0–3, and the relevant set is grade 2 or more. That model (Opus 5.5) is the one that runs the router, so the labels measure consistency, not ground truth: two grading passes agreed exactly on 94% of 500 pairs. A second model (GPT Astra) relabelled 120 tasks: it marks generic process skills relevant far more often (κ 0.48 on relevance), but the ranking of methods is unchanged on the labels both agree on. The tasks, labels, queries and the scorer are in the repo (`evals/retrieval/`, `skillfetch eval retrieval`).

Search first: the share of relevant skills in the top 10 and the top 50.

| What search_skills was given | top 10 | top 50 | process skills, top 50 |
|---|---|---|---|
| The request as typed | 0.387 | 0.683 | 0.632 |
| The router's one-sentence restatement | 0.483 | 0.775 | 0.727 |
| Three sentences (what it builds, how to work, the stack), each searched, merged | 0.535 | 0.835 | 0.783 |
| The one sentence, BM25 fused with MiniLM embeddings | 0.473 | 0.801 | 0.734 |

Splitting the restatement into three sentences recovers most of what one sentence missed, process skills included. The router first shipped a version that wrote the how-to-work sentence only when the user named one; it now always writes all three and adds the request as typed as a fourth query. Stage 4 below ran the earlier version in real sessions, not against the one-query version, and task outcomes were not scored. The embedding model added 0.026 at top 50 on the same sentence, under the 0.10 bar for adopting it, so it stays out.

Selection is where it breaks. Given the real top 50, the picker loaded at least one relevant skill in 82% of the tasks that had one (precision 0.81, recall 0.42). But in 30 of the 95 tasks where nothing in the index fits, it loaded something anyway, and it loaded a skill for 30% of the 40 trivial requests. Counted per task, the failures are: selection 55 (25 passed over a relevant skill that was in the list, 30 loaded one when none fit), restatement 20, search 7.

Some tasks have nothing to find. 62 of the 340 non-trivial tasks have no relevant skill in the index, most of them in ml (11 of 29), deploy (9 of 29), feature and performance (8 each) and data and ui_design (7 each).

Last, real sessions in the two real repositories (stage 4): 29 of these tasks, rewritten for the repos, three runs each in two environments, a clean one (skillfetch only) and my own (14 MCP servers, 134 skills, hooks on every tool call). On non-trivial tasks the router fired in 23 of 57 sessions in the clean environment and 22 of 57 in mine; per task the difference averaged +0.018 on these 19 tasks (0.000 over all 29, trivial ones included). On trivial tasks, which it is told to skip, it fired in 0 of 30 and 1 of 30. When it loaded something, the set held a relevant skill in 8 of 14 and 10 of 17 sessions, and it loaded a skill for a task with nothing relevant in 4 of 24 sessions in each environment. An earlier run on stub repositories (stage 3) reached search in 12 of 40 sessions; with no real code to work on, that number is a limit of the stubs, not a firing rate.

Three questions instead of one raised top-50 recall to 0.835 on the 278 tasks with a labelled relevant skill (0.764 on the catalogue-picked subset). The shipped router: top-50 recall 0.81 (0.75 on labels the search could not bias), up from 0.74 before this fix, on labels extended to the skills its queries find (284 tasks); it puts at least one relevant skill in its top 50 for 93% of them (89% before; 81% on the labels the search could not bias, 209 tasks). That does not make the index complete: 62 non-trivial tasks have no labelled relevant skill. In real repositories the router fired on 40% of non-trivial tasks, and removing my configuration did not raise that rate in this sample.

One more run, on what makes the router fire (stage 5): the 19 non-trivial tasks again, in the clean environment, three runs each, with 9 of them rewritten to point at code that is in the repo. Each variant changes one thing against the shipped router.

| Variant | Fired | Loaded a skill | Mean session cost |
|---|---|---|---|
| V0: the router as shipped then | 39/57 | 35/57 | $0.396 |
| V1: its description says to run before the first tool call (before git status, Read, Grep, Glob or ls) | 55/57 | 50/57 | $0.455 |
| V2: V0 plus one line in the project's CLAUDE.md | 57/57 | 55/57 | $0.533 |
| V3: V0 plus sharper MCP server instructions | 36/57 | 31/57 | $0.384 |

V1 and V2 each raised firing on 9 of the 19 tasks and lowered it on none (sign test p 0.004). MCP server instructions did not help: V3 fired in 36 sessions, 19 of them by calling the tools directly instead of through the router. V1 is now the router's description; on the 10 trivial tasks it fired in 1 of 30 runs (V0: 0 of 30). V2 is an option for a repository you control, measured with the old description only. When the router loaded a set on a task that has a relevant skill, the set held one in 26 of 32 sessions with V0 and 35 of 45 with V1; whether the work itself got better is not measured.

## What the tool gets wrong

The pipeline is tuned for precision over recall, and that cost is visible in the numbers.

- **Recall is unmeasured.** Nobody has hand-labelled 1,700 public skills for conflicts, so I know conflict precision only on the fixtures (1.0). On public skills both hard flags were false, too few to estimate precision, and I cannot say how much it misses. The default mode deliberately downgrades blanket rules without a named object ("never use emoji") to `needs_review`, because on real skills those were the source of every false conflict. On my hand-written test set that hides 8 of 19 real conflicts.
- **The judge leans one way.** It called 6 of 7 known carve-outs "conflict", so some of its 90 are not conflicts. The pairs it called independent were not audited, so 90 is not an upper bound.
- **Six extraction prompts, one test set.** I revised the extraction schema six times against the 41 hand-written fixture skills of the time until conflict precision was 1.0 and informative-pair accuracy 0.912 on them (the fixture directory now holds 52: 44 hand-written plus 8 cap fixtures that keep real public lines). On a held-out set of 26 public skills, extraction v4 then flagged 24 conflicts, all false; the final version flags 0 there and 2 in the full build. The later versions were made after seeing those 24, so that holdout is no longer independent, and 0 flags says nothing about recall. The lesson generalises: a perfect score on the set you tuned against means nothing until a held-out set agrees.
- **Two false conflicts are in the shipped output** and documented in the README as such, rather than patched around.
- **Anti-pattern tables fool the extractor.** A row in a "❌ Don't" table is read as an instruction. Open issue.
- **Extraction is semantic, so it needs a model.** about $0.003 per skill with gpt-6-luna ($4.82 for the final run: 1,764 requests, 1,723 public skills and the 41 fixtures).
- **Interactive skills are untested.** The end-to-end harness gave the sessions no AskUserQuestion or plan-mode tools, so whether a router-picked skill with interview or approval steps stalls a real session is not observed (§5, note b).

## Try it, and what comes next

The scanner runs on any local skills directory and prints every finding with the two source lines that caused it. Skills that are copies of public ones are analysed from the published index, no model or API key needed:

```
uvx --from git+https://github.com/hyunlord/skillfetch skillfetch sync
uvx --from git+https://github.com/hyunlord/skillfetch skillfetch scan ~/.claude/skills
uvx --from git+https://github.com/hyunlord/skillfetch skillfetch scan ~/.claude/skills --fail-on conflict   # for CI
```

The part I actually set out to build is the other half. Given that for 80% of skills I found no license that allows redistribution, that most of them are fine together, and that the ones that are not resolve by silent precedence, the thing I want is an agent that **does not install skills at all**: for each task it searches a vetted index, picks a small set, checks that set for the tensions above, fetches the bodies from their original repos with hash verification, and drops them when the task is done. An early version of that MCP server is in the repo: `search_skills`, `resolve_set`, `load_skills`, working end to end in Claude Code. It loads skills into the current context and does not unload them at the next task; per-task isolation is not built, and the conflict check is best effort, not a guarantee. The index holds metadata, constraints and hashes, never bodies. Section 5 is what happened when I ran it.

If you maintain a skill: add a LICENSE file. If you maintain a registry: show it. If you have a pair of skills you suspect disagree, run the scanner on them and open an issue with the output; I want to know what it misses more than what it finds.

## Sources and data

- Code, design docs and the number-by-number appendix with reproduction commands: [hyunlord/skillfetch](https://github.com/hyunlord/skillfetch), `docs/writeup/numbers.md`
- Corpus: [anthropics/skills](https://github.com/anthropics/skills) at `dbd4588f`; [onfire7777/universal-ai-skills-library](https://github.com/onfire7777/universal-ai-skills-library) at `2a76bf42`
- Skill format: [Agent Skills specification](https://github.com/anthropics/skills/tree/main/spec)
- Related work on skill retrieval at scale: [SkillRouter](https://arxiv.org/abs/2603.22455) (full-text retrieve-and-rerank); [Compositional Skill Routing](https://papers.cool/arxiv/2606.18051) (decompose-retrieve-compose). Neither addresses whether retrieved skills agree with each other, which is the gap this looks at.

All counts are as of 2026-10-22. The corpus moves daily; rerun `scripts/write_numbers.py` after a rebuild.
