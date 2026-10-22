# I vetted 1,800 public agent skills

*2026-10-22 · Kwan Hyeon*

SKILL.md files are the new npm: you install thirty of them into your coding agent and never read one. I pulled 1,831 public skills, linted them, scanned them for prompt-injection patterns, extracted 29,880 individual instructions from them, and checked which instructions contradict each other. Then I ran 1,160 agent sessions to see what any of it changes. Four things stood out. Only one in five states a license. Outright contradictions between skills are almost nonexistent. When two skills do disagree, the agent quietly picks one, the same one every time, and none of the three ways I tried to name the winner was a reliable control: the named skill was followed in 43–56% of runs, and the best method turned the agent's own choice around in only 8 of the 23 pairs where it had one. And skills mattered in 1 of the 5 task types I measured: on design, the expert's skill removed the template look; on tests, APIs, docs and data scripts the agent passed every check with or without one.

## What I did

Two sources: Anthropic's own [skills repo](https://github.com/anthropics/skills) (19 skills) and the [Universal AI Skills Library](https://github.com/onfire7777/universal-ai-skills-library), an aggregate of 1,812 skills collected from 11 upstream repos. Every skill went through the same pipeline:

1. **Lint**: frontmatter parses, has a name and description, no broken relative links.
2. **Injection scan**: a regex blocklist for instruction overrides, credential reads, privilege escalation, hidden text. A blocklist, not a proof of safety.
3. **Constraint extraction**: an LLM reads each SKILL.md and turns every actionable instruction into a typed record: subject, directive (require / forbid / prefer / avoid), object, scope, and the exact source line it came from. A constraint with no quotable line is dropped.
4. **Pairwise comparison**: two constraints on the same subject with opposite polarity and overlapping scope are a candidate conflict. Anything the rules cannot settle from the text is marked `needs_review`, never `conflict`.
5. **LLM judge** over the open pairs, using a different vendor's model than the extractor, reading the original lines rather than the extracted records.
6. **Obedience test**: for pairs the judge called a real conflict, load both skills into an agent, give it a task that touches the disputed rule, and record which skill it obeys.

External API cost for the whole analysis was **$15.75** (separately, the 1,160 agent sessions ran on a Claude Code plan: about $315 at API prices, [numbers.md](numbers.md) §7): $6.23 for extraction (gpt-6-luna, the cheapest of the four models tried on the fixtures), $9.36 for the judge (claude-sonnet-5.5), $0.16 for task generation. The obedience runs and all classification happened inside Claude Code sessions. A note on authorship: I designed the pipeline and made the calls; Claude Code wrote most of the code and ran the experiments. Where this post says "I read", a human read. Code and numbers: [hyunlord/skillfetch](https://github.com/hyunlord/skillfetch).

## 1. Only one in five skills states a license

377 of 1,831 skills (20.6%) carry a license, either in their own folder or in the upstream repo they were copied from. The rest state nothing. Under copyright law, nothing stated means all rights reserved: you can read it on GitHub, but you cannot legally bundle it into an index and ship it.

| License status | Skills | Share |
| --- | --- | --- |
| Explicit (367 permissive, 10 proprietary) | 377 | 20.6% |
| Upstream repo found, no LICENSE file in it | 824 | 45.0% |
| Upstream repo unknown | 630 | 34.4% |

822 of the 824 "upstream found, no license" skills come from a single aggregator, `ComposioHQ/awesome-claude-skills`, which has no repo-level LICENSE. The library that re-collects them is MIT, but an MIT badge on an aggregator does not license the files it copied from somewhere else. This is not specific to either project; it is how the whole ecosystem currently works, and I doubt most maintainers have thought about it. Even Anthropic's own repo is mixed: 4 of its 19 skills (docx, pdf, pptx, xlsx) are all-rights-reserved and one has no license file.

This is a count of what is stated, not a legal opinion. But it means any "skill registry" that redistributes bodies is, for about 80% of its inventory, doing so without permission. The practical consequence for my own tool was that the index can only hold metadata and content hashes; skill bodies have to be fetched from the original repo at use time.

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

The hits I checked by hand were not attacks. One was Anthropic's own API guide, rejected for quoting the phrase "ignore what the user said" while telling you not to write prompts like that. Another was an end-to-end testing skill passing `--no-sandbox` to headless Chrome. That is exactly the problem: a regex cannot tell a tutorial from an exploit, and neither can an agent that has just loaded the file into its context. A scan like this earns its place as a gate for "show me what to look at", not as a verdict. I have not read all 25, so I cannot say none is malicious; I can say the pattern-matching alone does not establish it.

Separately, 216 skills bundle shell or Python scripts the agent is expected to run. Nothing is wrong with that in itself, but it moves the trust question from "what does this text tell my agent to do" to "what does this code do when my agent runs it", which no SKILL.md linter answers.

## 3. Skills almost never contradict each other outright. They carve each other up.

This is the finding I did not expect. I built the pipeline to catch pairs like "squash every feature into one commit" versus "never squash". From 29,880 extracted constraints across 1,722 skills, the rules flagged **2 hard conflicts**. I read both. Both are wrong.

```
CONFLICT  darwin ⟷ thinking-ooda
  darwin:37          "**Principles:** Observe before acting · …"
  thinking-ooda:108  "Immediately return to OBSERVE"
```

That is the OODA loop, not a contradiction. The other one pairs caveman-review:51, "Drop terse mode for: security findings (CVE-class bugs need full explanation + reference) …", with saga:394, "Skip verbose explanations, focus on deliverables", which applies in saga's autorun mode: different situations. So the honest count of textual contradictions in 1,700 public skills is zero.

What the rules did find was 2,011 pairs they could not settle: 137 soft tensions and 1,874 marked `needs_review`. I had a second model read the original lines for every one of them.

| Judge verdict | Pairs | Share |
| --- | --- | --- |
| Independent (same topic, compatible) | 1,666 | 82.8% |
| Situational (true in different contexts) | 191 | 9.5% |
| Conflict | 90 | 4.5% |
| Carve-out (one narrows the other) | 57 | 2.8% |
| Error or unclear | 7 | 0.3% |

Four in five pairs that looked suspicious to the rules are fine. Of the 90 the judge called conflicts, most are of the form "always ask before acting" against "once the team is chosen, proceed without asking": one rule carving an exception out of another. The judge over-calls these; on a hand-labelled set it marked 6 of 7 known carve-outs as conflicts, so 90 is a ceiling.

The pattern across all of it: skill authors do not disagree about what to do. They disagree about **when** and **how much**: in paraphrase, keep responses short versus be thorough on security findings, or log every significant step versus never log from inside test code. These are not bugs in the skills. They are exactly the kind of thing an agent should reconcile, and the question is whether it does.

## 4. When two skills disagree, the agent does not flip a coin. It picks one, every time.

I took 26 pairs the judge had called both a conflict and "ambiguous to follow together", wrote one task per pair that forces the disputed rule to matter, and ran each task five times in a fresh agent session with both skill bodies loaded and no precedence hint. Order alternated: A first on odd runs, B first on even. I then classified each output as following A, following B, both, or neither.

| Outcome across 5 runs | Pairs |
| --- | --- |
| Same skill followed in all 5 runs | 17 |
| Same non-skill outcome in all 5 (both, or neither) | 2 |
| Mixed: A on some runs, B on others | 4 |
| Other mixes | 3 |

Only 4 of 26 pairs were non-deterministic. In 17, the agent followed the same one skill five times out of five. Which skill was loaded first made no difference: when exactly one was obeyed, it was the first-loaded one 51 times and the second 53.

So the failure mode is not randomness. It is a stable, invisible precedence. You install `tdd` and `warden`; one of them wins on every task where they disagree, and nothing in your session tells you which or why. If you later wonder why the agent stopped writing tests first, the answer is a line in a skill you installed three weeks ago.

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

On 20 small maintenance tasks on two repos (a FastAPI template and a Next.js starter; add a 404 page, link pagination, a README table), each run twice per condition (stage 1; B only on the 15 tasks with an expert skill), the three conditions were indistinguishable: 110 of 110 passed the hidden checks, screenshots tied, documents tied. Skills do not change what the agent writes when the task is small. C cost 6.5 more turns than A on the 15 tasks with an expert skill (6 over all 20) and 59% more input tokens, for nothing.

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

Widening the search to 50 compact summaries and letting the agent choose from those solved search for tasks that name their domain:

| Task type | Expert's skill | In the router's top 50 | Mean rank there | Loaded |
|---|---|---|---|---|
| Landing page (1b) | `frontend-design` | 4/4 | 29.2 | 4/4 |
| Test writing | `python-testing-patterns` | 5/5 | 1.0 | 5/5 |
| Backend API | `fastapi-templates` | 5/5 | 2.0 | 4/5 |
| Documentation | `quill` | 5/5 | 1.8 | 5/5 |
| Data script | `data-analyst-engine` | 5/5 | 2.0 | 5/5 |
| All | | 24/24 | | 23/24 |

Finding the skill is not the same as needing it. Design is the only domain where the expert's skill changed the result. On tests, the API, docs and the data script, all three conditions hit every objective metric (100% branch coverage, 27 of 27 contract calls, every check passed), and the score differences between conditions (0.6 or less) are within the noise of five runs and two judging passes that agreed exactly on 8 to 14 of 15 outputs. The router costs 1.7 to 2.1 times the input tokens of no skill and 6 to 8 more turns. That is the scope of this result: tasks the base model finishes in a median 9 to 15 turns without help, one model, five runs per condition.

The router still misses skills about *how* to work. The expert's `writing-plans` skill describes a way of working, the planning task describes a feature, and keyword search does not bridge that. A 22M-parameter embedding model did not bridge it either (top-50 recall 0.74 fused with BM25 vs BM25's 0.71, [numbers.md](numbers.md) §12), so it is not in the product.

## What the tool gets wrong

The pipeline is tuned for precision over recall, and that cost is visible in the numbers.

- **Recall is unmeasured.** Nobody has hand-labelled 1,700 public skills for conflicts, so I can say the tool rarely lies; I cannot say how much it misses. The default mode deliberately downgrades blanket rules without a named object ("never use emoji") to `needs_review`, because on real skills those were the source of every false conflict. On my hand-written test set that hides 8 of 19 real conflicts.
- **The judge leans one way.** It called 6 of 7 known carve-outs "conflict". Its 90 is an upper bound.
- **Six extraction prompts, one test set.** I revised the extraction schema six times against the 41 hand-written fixture skills of the time until conflict precision was 1.0 and informative-pair accuracy 0.912 on them (the fixture directory now holds 52: 44 hand-written plus 8 cap fixtures that keep real public lines). On a held-out set of 26 public skills, extraction v4 then flagged 24 conflicts, all false; the final version flags 0 there and 2 in the full build. The lesson generalises: a perfect score on the set you tuned against means nothing until a held-out set agrees.
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

The part I actually set out to build is the other half. Given that 80% of skills cannot be redistributed, that most of them are fine together, and that the ones that are not resolve by silent precedence, the thing I want is an agent that **does not install skills at all**: for each task it searches a vetted index, picks a small set, checks that set for the tensions above, fetches the bodies from their original repos with hash verification, and drops them when the task is done. An early version of that MCP server is in the repo: `search_skills`, `resolve_set`, `load_skills`, working end to end in Claude Code. The index holds metadata, constraints and hashes, never bodies. Section 5 is what happened when I ran it.

If you maintain a skill: add a LICENSE file. If you maintain a registry: show it. If you have a pair of skills you suspect disagree, run the scanner on them and open an issue with the output; I want to know what it misses more than what it finds.

## Sources and data

- Code, design docs and the number-by-number appendix with reproduction commands: [hyunlord/skillfetch](https://github.com/hyunlord/skillfetch), `docs/writeup/numbers.md`
- Corpus: [anthropics/skills](https://github.com/anthropics/skills) at `dbd4588f`; [onfire7777/universal-ai-skills-library](https://github.com/onfire7777/universal-ai-skills-library) at `2a76bf42`
- Skill format: [Agent Skills specification](https://github.com/anthropics/skills/tree/main/spec)
- Related work on skill retrieval at scale: [SkillRouter](https://arxiv.org/abs/2603.22455) (full-text retrieve-and-rerank); [Compositional Skill Routing](https://papers.cool/arxiv/2606.18051) (decompose-retrieve-compose). Neither addresses whether retrieved skills agree with each other, which is the gap this looks at.

All counts are as of 2026-10-22. The corpus moves daily; rerun `scripts/write_numbers.py` after a rebuild.
