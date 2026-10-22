# I vetted 1,800 public agent skills

*2026-10-22 · Kwan Hyeon*

SKILL.md files are the new npm: you install thirty of them into your coding agent and never read one. I pulled 1,831 public skills, linted them, scanned them for prompt-injection patterns, extracted 29,880 individual instructions from them, and checked which instructions contradict each other. Then I ran 1,100 agent sessions to see what any of it changes. Four things stood out. Only one in five states a license. Outright contradictions between skills are almost nonexistent. When two skills do disagree, the agent quietly picks one, the same one every time, and no header, block or edit I tried could change which. And loading the *right* skill visibly improves a large task, while loading a *plausible* one makes it worse than loading nothing.

## What I did

Two sources: Anthropic's own [skills repo](https://github.com/anthropics/skills) (19 skills) and the [Universal AI Skills Library](https://github.com/onfire7777/universal-ai-skills-library), an aggregate of 1,812 skills collected from 11 upstream repos. Every skill went through the same pipeline:

1. **Lint**: frontmatter parses, has a name and description, no broken relative links.
2. **Injection scan**: a regex blocklist for instruction overrides, credential reads, privilege escalation, hidden text. A blocklist, not a proof of safety.
3. **Constraint extraction**: an LLM reads each SKILL.md and turns every actionable instruction into a typed record: subject, directive (require / forbid / prefer / avoid), object, scope, and the exact source line it came from. A constraint with no quotable line is dropped.
4. **Pairwise comparison**: two constraints on the same subject with opposite polarity and overlapping scope are a candidate conflict. Anything the rules cannot settle from the text is marked `needs_review`, never `conflict`.
5. **LLM judge** over the open pairs, using a different vendor's model than the extractor, reading the original lines rather than the extracted records.
6. **Obedience test**: for pairs the judge called a real conflict, load both skills into an agent, give it a task that touches the disputed rule, and record which skill it obeys.

External API cost for the whole analysis was **$15.75**: $6.23 for extraction (gpt-6-luna, the cheapest model that kept conflict precision at 1.0 on a hand-labelled set), $9.36 for the judge (claude-sonnet-5.5), $0.16 for task generation. The obedience runs and all classification happened inside Claude Code sessions. A note on authorship: I designed the pipeline and made the calls; Claude Code wrote most of the code and ran the experiments. Where this post says "I read", a human read. Code and numbers: [hyunlord/skillfetch](https://github.com/hyunlord/skillfetch).

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
  darwin:        "Observe before acting."
  thinking-ooda: "Observe again after acting."
```

That is the OODA loop, not a contradiction. The other one pairs "be detailed for security findings" with "skip verbose explanations in autorun mode": different situations. So the honest count of textual contradictions in 1,700 public skills is zero.

What the rules did find was 2,011 pairs they could not settle: 137 soft tensions and 1,874 marked `needs_review`. I had a second model read the original lines for every one of them.

| Judge verdict | Pairs | Share |
| --- | --- | --- |
| Independent (same topic, compatible) | 1,666 | 82.8% |
| Situational (true in different contexts) | 191 | 9.5% |
| Conflict | 90 | 4.5% |
| Carve-out (one narrows the other) | 57 | 2.8% |
| Error or unclear | 7 | 0.3% |

Four in five pairs that looked suspicious to the rules are fine. Of the 90 the judge called conflicts, most are of the form "always ask before acting" against "once the team is chosen, proceed without asking": one rule carving an exception out of another. The judge over-calls these; on a hand-labelled set it marked 6 of 7 known carve-outs as conflicts, so 90 is a ceiling.

The pattern across all of it: skill authors do not disagree about what to do. They disagree about **when** and **how much**. "Keep responses short" versus "be thorough on security findings". "Log every significant step" versus "never log from inside test code". These are not bugs in the skills. They are exactly the kind of thing an agent should reconcile, and the question is whether it does.

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

Two caveats that matter. First, the harness wording moved results: in a discarded batch, a note saying "finish in this one reply" pushed every "stop and ask the user" rule to lose. Pairs about pausing versus proceeding are the most fragile. Second, one person classified all 130 outputs. I would want a second rater before putting a decimal on any of this.

**You cannot give skills an order.** The obvious fix is to tell the agent which skill wins. I tried three ways on the same 26 pairs: five runs with A named the winner and five with B, 260 runs per method, same harness and classification.

| How the winner was named | Runs that followed the named winner |
| --- | --- |
| Header before the skills: "Skills are listed in precedence order. If two instructions disagree, follow the earlier one." (what `load_skills` emits) | 43% (112/260) |
| A block naming the winner and quoting both conflicting lines | 56% (145/260) |
| The loser's conflicting lines replaced with `<!-- overridden by <winner>: "<line>" -->` | 46% (120/260) |

That is 910 runs counting the 130 above. Per-pair tables are in [numbers.md](numbers.md) §8–§10.

## What the tool gets wrong

The pipeline is tuned for precision over recall, and that cost is visible in the numbers.

- **Recall is unmeasured.** Nobody has hand-labelled 1,700 public skills for conflicts, so I can say the tool rarely lies; I cannot say how much it misses. The default mode deliberately downgrades blanket rules without a named object ("never use emoji") to `needs_review`, because on real skills those were the source of every false conflict. On my hand-written test set that hides 8 of 19 real conflicts.
- **The judge leans one way.** It called 6 of 7 known carve-outs "conflict". Its 90 is an upper bound.
- **Six extraction prompts, one test set.** I revised the extraction schema six times against 41 hand-written skills until it scored 1.0 on them. On the first 219 real skills it then produced 24 conflicts, all false. Two independent samples later it produces 0 to 2. The lesson generalises: a perfect score on the set you tuned against means nothing until a held-out set agrees.
- **Two false conflicts are in the shipped output** and documented in the README as such, rather than patched around.
- **Anti-pattern tables fool the extractor.** A row in a "❌ Don't" table is read as an instruction. Open issue.
- **Extraction is semantic, so it needs a model.** about $0.003 per skill with gpt-6-luna ($4.82 for the final run over 1,764 skills); cheaper models produced false conflicts, a 15x pricier one scored lower. Prompt structure mattered more than model size.

## Try it, and what comes next

The scanner runs on any local skills directory and prints every finding with the two source lines that caused it. Skills that are copies of public ones are analysed from the published index, no model or API key needed:

```
uvx --from git+https://github.com/hyunlord/skillfetch skillfetch sync
uvx --from git+https://github.com/hyunlord/skillfetch skillfetch scan ~/.claude/skills
uvx --from git+https://github.com/hyunlord/skillfetch skillfetch scan ~/.claude/skills --fail-on conflict   # for CI
```

The part I actually set out to build is the other half. Given that 80% of skills cannot be redistributed, that most of them are fine together, and that the ones that are not resolve by silent precedence, the thing I want is an agent that **does not install skills at all**: for each task it searches a vetted index, picks a small set, checks that set for the tensions above, fetches the bodies from their original repos with hash verification, and drops them when the task is done. An early version of that MCP server is in the repo: `search_skills`, `resolve_set`, `load_skills`, working end to end in Claude Code. The index holds metadata, constraints and hashes, never bodies.

### 5. Does loading skills per task actually help? Only when it finds the right one.

I ran it. Three conditions in real Claude Code sessions on two repos (a FastAPI template and a Next.js starter), each task twice: **A** no skills; **B** the one skill an expert would have installed, pre-loaded; **C** skillfetch's router picking from the index. Everything was scored blind, by raters who did not know the condition.

On 20 small maintenance tasks (add a 404 page, link pagination, a README table) the three conditions were indistinguishable: 110 of 110 passed the hidden checks, screenshots tied, documents tied. Skills do not change what the agent writes when the task is small. C cost 5 more turns and 59% more input tokens for nothing.

On 5 larger tasks the picture split:

| | A: no skill | B: expert's skill | C: router, first version | C: router, after the search fix |
|---|---|---|---|---|
| Landing page, usable (1–5) | 3.50 | 4.75 | 4.50 | 4.75 |
| Landing page, "AI-template" tells | 2.00 | 0.50 | 2.00 | 0.50 |
| Plan quality (rank, 0 = best) | 0.36 | 0.00 | 0.79 | 0.71 |
| Median turns | 19.5 | 24 | 34 | 26.5 |

The expert's skill matters: with Anthropic's `frontend-design` loaded, the landing pages lost their template look. The router's first version never found that skill (it ranked 34th in a 10-result search) and loaded design-adjacent skills instead, which made the pages *more* template-like than no skill at all. Loading the wrong skill is worse than loading none.

Widening the search to 50 compact summaries and letting the agent choose from those fixed the design tasks: the router then loaded `frontend-design` in 4 of 4 runs and matched the expert condition, at 7 extra turns instead of 14. It did not fix the planning task: the expert's `writing-plans` skill describes a way of working, the task describes a feature, and no amount of keyword search bridges that. A 22M-parameter embedding model did not bridge it either (top-50 recall 0.74 vs BM25's 0.71), so it is not in the product. The honest state of the router: it finds the right skill for tasks that name their domain, misses skills about *how* to work, and costs about seven turns per task.

If you maintain a skill: add a LICENSE file. If you maintain a registry: show it. If you have a pair of skills you suspect disagree, run the scanner on them and open an issue with the output; I want to know what it misses more than what it finds.

## Sources and data

- Code, design docs and the number-by-number appendix with reproduction commands: [hyunlord/skillfetch](https://github.com/hyunlord/skillfetch), `docs/writeup/numbers.md`
- Corpus: [anthropics/skills](https://github.com/anthropics/skills) at `dbd4588f`; [onfire7777/universal-ai-skills-library](https://github.com/onfire7777/universal-ai-skills-library) at `2a76bf42`
- Skill format: [Agent Skills specification](https://github.com/anthropics/skills/tree/main/spec)
- Related work on skill retrieval at scale: [SkillRouter](https://arxiv.org/abs/2603.22455) (full-text retrieve-and-rerank); [Compositional Skill Routing](https://papers.cool/arxiv/2606.18051) (decompose-retrieve-compose). Neither addresses whether retrieved skills agree with each other, which is the gap this looks at.

All counts are as of 2026-10-22. The corpus moves daily; rerun `scripts/write_numbers.py` after a rebuild.
