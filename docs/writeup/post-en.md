# Agent skills get installed, not read. I measured what they change

*Draft · Kwan Hyeon · numbers as of 2026-10-27*

**At a glance**

- **Safety**: in a public index of 2,785 skills, 1.9% trip an injection-scan warning, 9.0% bundle scripts and 2.4% are big enough to eat an agent's turns. Most warnings I read were not attacks; they are where to look before you install ([numbers.md](numbers.md) §25).
- **Knowledge**: on 60 facts taken from 30 skills that promise knowledge a model may lack, the model without the skill answered 173 of 180 correctly. One skill cites a guideline I could not find ([numbers.md](numbers.md) §24).
- **Effect**: with eight popular skills installed, results were the same as with none, except on one design task, where a large design skill ran the agent into its turn limit. The per-task router matched no skill at 62% more cost ([numbers.md](numbers.md) §26).
- **Where skills help**: rules a team wrote down and the code does not show. Given the right skills, rule checks passed went from 0.246 to 0.929; installing all 24 of the team's skills reached 0.905 ([numbers.md](numbers.md) §27).

## 1. Skills are installed, not read

A skill is a folder with a `SKILL.md` that a coding agent loads when it thinks the skill applies. People install them the way they install packages: from a ranking, a list or a friend's repo, and almost nobody reads them first. The agent does read them, every word, and does what they say.

I wanted to know three things about that habit. Is what we install safe to hand an agent? Does it tell the agent anything it does not already know? And does installing it change the work? This post answers each with a measurement, then says where skills did help, and what I built from it: `skillfetch scan`, a check you run before you install.

The numbers come from a released index of 2,785 public skills and from real Claude Code sessions run after my first post on this ([2026-10-22](post-2026-10-22-en.md)). Every number links to the section of [numbers.md](numbers.md) that holds it, with the commands to reproduce it. A note on authorship: I designed the experiments and made the calls; Claude Code wrote most of the code and ran the sessions. Where this post says "I read", a human read.

## 2. Safety: what a scan finds before you install

I ran the same checks `skillfetch scan` runs on every skill of the released index ([numbers.md](numbers.md) §25). The index had already rejected 143 skills at build time (110 failed lint, 33 the injection scan), so the failure rates below are 0 by construction; what is left is warnings.

![Figure 1. The scan rules over the 2,785 skills of the public index. Injection-scan warning 1.9% (52 skills), of which remote instructions 0.4% (11); size warning 2.4% (67); bundles scripts 9.0% (252); states a year or version 32.0% (890); no license in the skill itself 89.3% (2,486); none after the repo-root rule 53.5% (1,491). Advice per skill, with the license not part of it: recommended 88.3%, caution 11.7%, not recommended 0.0%. The index admitted only skills that pass lint and the injection scan; its build rejected 143 more.](img/fig7-index-scan-en.png)

**Remote instructions.** 11 skills (0.4%) point the agent at text that lives somewhere else. That matters because what you vetted is not what the agent will read: the remote file can change after you install the skill. The hits are a mix:
- `semgrep-rule-creator` lists a raw GitHub URL of the Semgrep docs as a page to read while writing rules: documentation, but fetched at use time.
- `using-neon` has a reference file that tells you to download an install script and pipe it straight into `bash` (that one is the `pipe-to-shell` rule, 7 skills).
- `lightpanda-browser` was flagged for a Twitter badge in a README it bundles. That is a false positive.

None of the hits I read was an attack. That is the point of a warning: it tells you which line to read, not what to think of it.

**Scripts.** 252 skills (9.0%) bundle scripts. Nothing is wrong with that in itself, but it changes the question from "what does this text tell my agent to do" to "what does this code do when my agent runs it", which no reading of `SKILL.md` answers.

**Size.** 67 skills (2.4%) are over a limit: a `SKILL.md` over 8,000 tokens, more than 20 files, or more than 1 MB. Section 4 shows why that is a warning and not a style note.

**Licenses.** 89.3% of skills state no license of their own. If the license file of the repository they live in counts, which is the rule `scan` uses unless the repository is an aggregator of other people's skills, 53.5% have none. The license is shown next to the advice, not in it: it decides what you may redistribute, not whether a skill is safe to run.

**Contradictions, briefly.** My first post looked for skills that give opposite instructions. From 29,880 instructions extracted from 1,722 skills, the rules flagged 2 hard conflicts, and both were false ([numbers.md](numbers.md) §3). Where two skills did disagree, telling the agent which one wins was not a reliable control: the named skill was followed in 43–56% of runs, depending on how it was named (112/260, 145/260 and 120/260; [numbers.md](numbers.md) §8–§10). `scan` still checks pairs, quoting both lines, but outright contradiction is rare.

## 3. Knowledge: does the skill tell the model anything new?

Many skills sell knowledge: a library's new API, a service's limits, a regulation's details. If the model already knows it, the skill costs context and adds nothing; if the skill is wrong, it does harm. So I asked the model first ([numbers.md](numbers.md) §24).

I picked 30 skills from the index whose descriptions promise knowledge a model may lack, took 2 short factual questions from each skill's own files (60 questions), checked each accepted answer against official documentation, and asked each question 3 times to the same model the experiment sessions ran (claude-opus-5-5, [numbers.md](numbers.md) §24), in an isolated session with no tools and no skills. 180 calls cost $0.88.

![Figure 2. Top: 180 answers to factual questions without the skill (60 questions × 3 runs): correct 173, wrong 7. Middle: the three questions with a wrong answer, runs answered correctly out of 3: Claude Opus 5.5 input price 0/3; iOS version that added AdAttributionKit conversion tags 2/3; EDPB document on processing personal data through AI systems 0/3. The other 57 questions: 3 of 3 correct. Bottom: the 60 accepted answers checked against official sources: confirmed 47, partial 12, not confirmed 1.](img/fig6-knowledge-en.png)

**173 of 180 answers were correct**, and 28 of the 30 skills were answered 6/6. The model did not know one thing a skill knew: the Claude Opus 5.5 input price, which it put at $5 in all three runs where the `claude-api` skill gives $4. It also gave iOS 18.0 instead of 18.4 for an AdAttributionKit change in one run of three.

The third question is the uncomfortable one. The `ai-dpia` skill cites "EDPB Guidelines 04/2025 on processing personal data through AI systems". I could not find that document in the EDPB's list of guidelines, which shows 01/2025, 02/2025 and 3/2025. The model named the EDPB's Opinion 28/2024 instead. I am not saying the skill is wrong; I am saying I could not confirm it, and an agent that loads it will cite it with confidence.

That is why `scan` marks dated claims: 32.0% of indexed skills have a prose line that states a year or a version ([numbers.md](numbers.md) §25). The check is a pattern match, not a judgement. It tells you which lines may have changed since the model was trained, or since the author wrote them.

The limits are real: these are short factual questions, one model, three runs each. They do not show whether the model applies a fact while coding, and no question was asked with the skill loaded.

## 4. Effect: what installing popular skills changed

The direct test ([numbers.md](numbers.md) §26): 18 tasks, four of them design tasks, 3 runs each, in three conditions, judged blind by two Claude judges.
- **A:** no skills.
- **P:** eight popular skills installed in `.claude/skills`. The rule, fixed before the run: from the top 200 of the skills.sh all-time ranking and the official Anthropic skills, leave out non-coding domains (video and image, document tools, marketing and the like) and a few other kinds that cannot run in these sessions, keep at most 3 per publisher, then take the first 8 by rank. The eight: improve-codebase-architecture, tdd, frontend-design, domain-modeling, vercel-react-best-practices, web-design-guidelines, design-taste-frontend, vercel-composition-patterns.
- **R:** skillfetch's per-task router, which searches the index for each task and loads up to three skills.

![Figure 3. Stage 13. Mean score on the 17 tasks without d1-landing: no skill 4.618 (checks 53/54), 8 popular skills installed 4.725 (51/54), router 4.627 (52/54). d1-landing, a product landing page: 3.00, 1.33, 4.67. Mean cost per session, API-price equivalent: $0.370, $0.642, $0.599. All three P sessions on d1-landing ended at the 40-turn limit.](img/fig5-stage13-en.png)

| | A, no skill | P, popular skills | R, router |
|---|---:|---:|---:|
| mean score, 18 tasks | 4.528 | 4.537 | 4.630 |
| mean score, without d1-landing (17) | 4.618 | 4.725 | 4.627 |
| checks passed | 53/54 | 51/54 | 52/54 |
| mean cost per session (API-price equivalent) | $0.370 | $0.642 | $0.599 |

Without the landing page, the three conditions are close: P 4.725, R 4.627, A 4.618. The router matched no skill (4.627 against 4.618) at 62% more cost per session. The popular skills were mostly not used: 11 of the 54 P sessions used one of the eight, 9 of them on design tasks, and five of the eight were never used at all. None of the Rust, Swift, Go, Java or TypeScript sessions touched them.

**The landing page.** One task split the conditions: d1-landing, a product landing page. R scored 4.67, A 3.00, P 1.33. All three P sessions ended at the 40-turn limit with an empty final answer, at $3.09–$3.28 each. In one of them, 26 tool calls read files of the design-taste-frontend skill, which has 39 files and 2.4 MB. The pages it did leave hid their sections behind a scroll animation, so the still screenshots the judges scored showed them blank; the functional checks passed.

![Figure 4. d1-landing, run 1, full-page desktop screenshots. Left: P, with eight popular skills installed: a large hero, then long blank bands where the sections wait for a scroll animation, then the footer. Right: R, the router (it loaded copywriting and frontend-design): a complete page with a team list, features, pricing and a call to action.](img/stage13-d1-landing-p-r.png)

The other three design tasks did not repeat it: d2-redesign A 3.50, P 4.50, R 3.67; d3-dashboard 4.00, 3.67, 3.00; d4-email 4.33, 4.67, 4.00. My first post found the same shape over five task types: the expert's skill changed the result on design and nowhere else ([numbers.md](numbers.md) §11).

Limits: five of the eight popular skills are web or front-end skills; design scores come from still screenshots; A and R reuse runs from another day with the same harness; 18 tasks, 3 runs, two Claude judges.

## 5. Where skills do help: rules the code does not show

If the model already knows public facts and popular skills rarely change the work, what is a skill for? The case I could think of is knowledge nobody published: a team's own rules. So I wrote a fictional company, Northwind, with two repositories and 24 skills holding rules you cannot infer from the code (how money and public IDs are represented, when to add a changelog entry, how to log), 8 of them distractors that look similar ([numbers.md](numbers.md) §27). Ten tasks, three runs each; the main measure is the share of hidden rule checks passed on the eight rule tasks (126 checks per condition).

| condition | rule checks passed | median turns | mean cost per session |
|---|---:|---:|---:|
| A: no skills | 31/126 (0.246) | 8 | $0.283 |
| R: the router over the index plus the 24 | 71/126 (0.563) | 16 | $0.463 |
| O: the skills each task needs, given up front | 117/126 (0.929) | 9 | $0.284 |
| R′: router with the team's 4 common skills pinned | 107/126 (0.849) | 17.5 | $0.526 |
| N: all 24 installed in `.claude/skills` | 114/126 (0.905) | 13 | $0.345 |
| F: all 24 bodies in the first message | 106/126 (0.841) | 9 | $0.401 |

Here skills matter: 0.246 without them, 0.929 with the right ones. The router got halfway (0.563), and the way it missed is instructive. Of its 55 failed checks, 32 were rules whose skill was not in its top 50 at all, and all of them were rules the request does not point at: a changelog entry, design tokens, structured logging, an endpoint registry. A task that says "add a refund endpoint" does not say "and update the changelog", so a search for the task does not find the changelog rule.

Pinning the team's four common skills (R′, an organisation mode I built for this; not merged) took the router to 0.849. But simply installing all 24 skills (N) did better, 0.905, with fewer turns (13 against 17.5) and at two-thirds of the cost ($0.345 against $0.526). At 24 skills, the agent's own skill list was enough: it loaded 72 of the 78 skills the tasks needed. I did not test larger sets. Distractor rules were followed 0 times in all six conditions.

Two side notes. Putting all 24 bodies in the first message (F) passed almost as many rule checks but failed more functional ones (61/75): following the platform rule "new behaviour goes behind a flag", it shipped endpoints that were switched off. And blind judges who did not know the team's rules liked the no-skill code best (4.646 against 4.021 for O): following house rules looks like scope creep from outside. Given a summary of the rules, new judges put all six within 0.4 of each other.

Limits: the company and its rules are mine, 10 tasks, 3 runs, two Claude judges.

## 6. Scan before you install

What I take from this: most of what a skill can do for you is either already in the model or rarely triggered, and the rest is specific to your team. The cost side is real: context, turns, sometimes a whole session. So the useful habit is to read before you install, and to make that cheap I turned the checks into one command.

```
uvx --from git+https://github.com/hyunlord/skillfetch skillfetch scan https://github.com/<owner>/<repo>
uvx --from git+https://github.com/hyunlord/skillfetch skillfetch scan ~/.claude/skills
```

A GitHub URL is cloned shallowly into a temporary folder, scanned and deleted; nothing is installed or run. The report opens with one line of advice from safety and quality checks only: NOT RECOMMENDED when a skill fails the injection scan or lint, or two skills contradict each other; CAUTION for injection-scan warnings (remote instructions among them), size, bundled scripts, or one skill covering another; RECOMMENDED otherwise. Under it is the license and where it was found. Then every finding, with the line it comes from. Run on the design skill from section 4:

```
Before you install: CAUTION (1 skill is over a size limit; 1 skill bundles scripts)
License: MIT (repo root). Not part of the advice: check it before you redistribute a skill.
```

No model and no API key. Contradictions between installed copies of public skills are checked against the index (`skillfetch sync`); for other skills, `--claude-code` extracts their instructions with your own Claude Code login.

**The router is experimental.** skillfetch also has the per-task router measured above: an MCP server and one router skill that search the index for each task and load a small, conflict-checked set. It works as designed, and in my measurements it did not improve results on public skills, cost 62% more per session, and lost to plain installation on a team's own skills. It stays in the repository as an experimental feature.

**What the tool gets wrong.**
- The injection scan is a regex blocklist. It cannot tell a tutorial from an exploit, and some remote-instruction hits are badges and doc links.
- The dated-claim check is a pattern match. It does not know whether a claim is out of date.
- The size limits come from one failure I watched, not from a study of limits.
- The license line is a count of what is stated, not a legal opinion.
- Contradiction recall is unmeasured; on public skills both hard flags were false.

## 7. Reproduce it

- **Code, design notes and every number with its source and command:** [hyunlord/skillfetch](https://github.com/hyunlord/skillfetch), [`docs/writeup/numbers.md`](numbers.md).
- **The index scan:** `evals/index-scan/` (one derived row per skill, no skill text); `uv run python scripts/index_scan.py report`.
- **The knowledge probe:** `evals/knowledge-gap/` (questions, official checks, answers).
- **The sessions:** `evals/e2e/stage13/` and `evals/e2e/stage12/` (designs fixed before the runs with their hashes, reports, derived session rows, judge keys and scores). Stage 12's fictional skills, repositories and tasks are published in full; third-party skill bodies and transcripts are not. Judge-package diffs are in a release asset: `scripts/fetch_e2e_assets.sh`, then `scripts/verify_e2e_frozen.py`.
- **Cost**, API-price equivalent on a Claude Code plan, not money spent: Stage 13 $43.79, Stage 12 $34.97, Stage 12b $40.94, the knowledge probe $0.88 ([numbers.md](numbers.md) §7, §24, §26, §27). The first post's 1,708 sessions are counted in §7.
- **The first post**, with the license survey, the contradiction pipeline and the obedience tests: [2026-10-22](post-2026-10-22-en.md).

All counts are as of 2026-10-27. The corpus moves daily; rerun the scripts after a rebuild.
