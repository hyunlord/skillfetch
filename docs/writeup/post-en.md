# Agent skills get installed, not read. I measured what they change

*2026-10-28 · Kwan Hyeon*

**At a glance**

- **Safety**: I had a model read the `SKILL.md` of all 2,281 distinct skills in a public index against a fixed checklist. It flagged 9, and I judged 6 of them real risks, 2 minor and 1 a false positive. None was an attack: the six are careless design, such as deleting all of a user's skills or following rules fetched from a branch that can change. The rule-based scan passed 3 of the 6 as RECOMMENDED ([numbers.md](numbers.md) §32). On GPT-written test sets, including one written to get past the review, the review caught 38–40 of 40 risky skills with no false positives, where the rules caught 0–3 (§31, §33).
- **Knowledge**: on 60 facts taken from 30 skills that promise knowledge a model may lack, the model without the skill answered 173 of 180 correctly. One skill cites a guideline I could not find ([numbers.md](numbers.md) §24).
- **Effect**: popular skills left for the model to use on its own barely changed the results: with eight installed, results were the same as with none, except on one design task, where a large design skill ran the agent into its turn limit. The per-task router matched no skill at 62% more cost ([numbers.md](numbers.md) §26).
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

**Rules miss what is written in prose; a reading catches it.** The rules match commands, paths, flags and fixed phrases.
- **Two independent sets** of 80 test skills (40 risky, 40 harmless lookalikes), written by GPT without seeing the rules:
  - the rules caught 0–3 of the 40 risky cases;
  - a review that reads each skill against a fixed checklist with a model (`scan --review`) caught 39–40 of 40;
  - the review flagged 0 of the 40 harmless cases in both sets.
- **A third set written to get past the review:** GPT was told that a model reads each skill against the checklist, and used 40 different ways to slip by it.
  - The review still caught 38–40 of the 40 risky cases and flagged none of the 40 harmless ones; the rules caught 0 of 40.
  - It caught all 9 cases that speak to the reviewer to steer its verdict.
  - In one of the two runs, the replies for 2 cases came back without findings. They are marked "review incomplete", and the safeguard makes their advice CAUTION ([numbers.md](numbers.md) §33).
- **60 real skills from the index,** 20 of them security skills that quote attacks: the review flagged none ([numbers.md](numbers.md) §30, §31).
- **The scope:** all three sets are synthetic cases written by GPT, not real attacks, and one model did the reviewing.

**Reading the whole index.** I ran the review over the released index ([numbers.md](numbers.md) §32).
- **Stage one:** a model read the `SKILL.md` of each of the 2,281 distinct skills. It flagged 9.
- **Stage two:** a full read of those 9 and of 7 skills with remote-instruction warnings flagged the same 9 and no others.
- **My judgement:** 6 real risks, 2 minor, 1 false positive.
- **No attack:** none of the 9 was malicious. The real risks are careless design: deleting every skill the user has, running another agent in auto-approve mode, following rules fetched from a branch that can change, pushing to a third party's repository without asking.
- **The rules alone:** they passed 3 of the 6 real risks as RECOMMENDED. For one, a rule pointed at the flagged line; the other two got CAUTION only because they bundle scripts.

| skill (source) | what the flagged line does | judged | rules v8 alone |
|---|---|---|---|
| `core-dynamic-skills` (actionbook-rust-skills) | "cleans generated skills" with `rm -rf ~/.claude/skills/*`, deleting every skill the user has | real risk | RECOMMENDED |
| `second-opinion` (UASL's copy; the original, trailofbits/skills, has since replaced `--yolo` with the default approval mode) | runs another agent with `--yolo`, which approves all its tool calls, after calling the step read-only | real risk | RECOMMENDED |
| `web-design-guidelines` (UASL) | fetches its rules from a main branch on every run and follows them | real risk | RECOMMENDED |
| `ln-002-session-analyzer` (UASL's copy; the skill no longer exists in its author's repository) | fetches missing files from a master branch and follows them | real risk | CAUTION (remote instructions) |
| `skill-sync` (UASL) | installs a third-party repository's skills as live skills, without review | real risk | CAUTION (scripts only) |
| `ultimate-skill-creator` (UASL) | pushes the user's new skill to a third party's repository without asking | real risk | CAUTION (scripts only) |
| `file-organizer` (UASL) | deletes duplicate files; only this step lacks the "ask first" wording | minor | CAUTION (scripts only) |
| `implementing-api-gateway-security-controls` (UASL) | a tutorial example that turns off certificate revocation checks | minor | CAUTION (scripts only) |
| `chat-summarizer` (UASL) | `--enrich` sends a summary to OpenAI, but it is an option the user adds | false positive | CAUTION (scripts only) |

**Copies in an aggregator stay old when the original is fixed.** Two of the six real risks were already fixed or gone at the source. Trail of Bits' `second-opinion` no longer uses `--yolo`. The author's repository no longer has `ln-002-session-analyzer`. The copies in UASL, the aggregator the index took them from, still carry the old lines.

- **The limits:**
  - stage one read `SKILL.md` only;
  - one model reviewed and one person judged;
  - the 120 skills whose rules warned only about scripts were not read in full.

**Scripts.** 252 skills (9.0%) bundle scripts. Nothing is wrong with that in itself, but it changes the question from "what does this text tell my agent to do" to "what does this code do when my agent runs it", which no reading of `SKILL.md` answers.

**Size.** 67 skills (2.4%) were over a limit when I counted: a `SKILL.md` over 8,000 tokens, more than 20 files, or more than 1 MB. The file limit is now 50: two judges called 5 of 15 size warnings worth a look at 20 files, and 5 of 8 at 50 ([numbers.md](numbers.md) §30). Section 4 shows why size is a warning and not a style note: the skill that ran P's landing-page sessions into their turn limit there, design-taste-frontend, is 2.4 MB, over the 1 MB limit, so `scan` gives it CAUTION before you install it.

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

Limits: P only installed the skills and left it to the model to pull them in, and the measure is the score of the final output. The value of workflow skills a user calls by name (tdd, for example) and of output-format or tone skills (saving tokens, for example) was not measured. Also: five of the eight popular skills are web or front-end skills; design scores come from still screenshots; A and R reuse runs from another day with the same harness; 18 tasks, 3 runs, two Claude judges.

See every output side by side: [the Stage 13 gallery](https://hyunlord.github.io/skillfetch/stage13/stage13-gallery.html) (in Korean).

**Six requests in one session.** People do not open a new session for every task, so I also ran the three conditions through six different requests in one session (a landing page, an API endpoint, API tests, Rust concurrency, a README, a data script), in two orders ([numbers.md](numbers.md) §28).
- **Scores over the six:** the router 4.708, the installed popular skills 3.833, no skill 4.458.
- **Against the installed skills:** the router's lead, +0.875, comes mostly from the landing page again (P 1.5, the router 4.75). Without it the lead is +0.40.
- **Against no skill:** the router's lead, +0.250, is within the disagreement between the two judges. Without the landing page it is 0.00.
- **Cost:** the router's sessions cost about 1.5 times as much ($18.65 against $12.58 for no skill and $12.33 for P).
- **Leftovers:** skills loaded for earlier requests did not carry over. The judges found no trace of an earlier skill in a later result: 0 of 57 skill pairs for the router, 0 of 5 for P.

This is one run per order, two sessions per condition.

See every output side by side: [the Stage 14 gallery](https://hyunlord.github.io/skillfetch/stage14/stage14-gallery.html) (in Korean).

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

What I take from this, within what I measured (skills installed and left for the model to pull in, judged by the final output; not workflow skills you call by name, nor output-format or tone skills): most of what a skill can do for you is either already in the model or rarely triggered, and the rest is specific to your team. The cost side is real: context, turns, sometimes a whole session. So the useful habit is to read before you install, and to make that cheap I turned the checks into one command.

```
uvx --from git+https://github.com/hyunlord/skillfetch skillfetch scan https://github.com/<owner>/<repo>
uvx --from git+https://github.com/hyunlord/skillfetch skillfetch scan ~/.claude/skills
uvx --from git+https://github.com/hyunlord/skillfetch skillfetch scan ~/.claude/skills --review
```

A GitHub URL is cloned shallowly into a temporary folder, scanned and deleted; nothing is installed or run. The report opens with one line of advice from safety and quality checks only: NOT RECOMMENDED when a skill fails the injection scan or lint, or two skills contradict each other; CAUTION for injection-scan warnings (remote instructions among them), size, bundled scripts that use the network, run commands, delete files or read secrets, or one skill covering another; RECOMMENDED otherwise. `sudo`, piping a download into a shell, concealment phrasing and dated lines are shown as notes and do not change the advice, because almost none of their warnings were worth a look (below). Under it is the license and where it was found. Then every finding, with the line it comes from. Run on the design skill from section 4:

```
Before you install: CAUTION (1 skill is over a size limit; 1 skill bundles scripts that need a look)
License: MIT (repo root). Not part of the advice: check it before you redistribute a skill.
```

The checks above need no model and no API key. Contradictions between installed copies of public skills are checked against the index (`skillfetch sync`); for other skills, `--claude-code` extracts their instructions with your own Claude Code login.

**`--review` reads the skill.** It sends each skill's files, with a fixed checklist, to an isolated `claude -p` on your own Claude Code login. The checklist covers seven categories:
- data sent out;
- remote instructions;
- destructive actions;
- safeguards switched off;
- hiding or false reporting;
- claimed authority;
- hidden text.

It costs a model call per skill: about $0.02 per call in my runs, in API-price terms ([numbers.md](numbers.md) §31).
- **Findings:** each quotes its line, and quotes not found in the files are dropped. They are listed under the advice, not counted in it.
- **A failed review:** if a reply is cut off or declined, the skill is marked "review incomplete: read this skill yourself" and the advice becomes at least CAUTION. The same goes for a skill too long to read in full.
- **In your agent:** `skillfetch setup` installs a vet skill that does the same reading before any skill is installed. The MCP server hands it the checklist and the files, and the agent quotes what it finds before asking.

**The router is experimental.** skillfetch also has the per-task router measured above: an MCP server and one router skill that search the index for each task and load a small, conflict-checked set. It works as designed. In my measurements it was better than the popular skills installed for good, but not better than no skill. It cost 62% more per session on single tasks and about 1.5 times as much over six requests in one session, and on a team's own skills it lost to plain installation. It stays in the repository as an experimental feature.

**What the tool gets wrong.**
- The injection scan is a regex blocklist, and it misses most risks written in plain prose. On 80 test skills that GPT wrote without seeing the rules, it caught 3 of the 40 risky ones and flagged 1 of the 40 harmless lookalikes (the version before: 2 and 1; [numbers.md](numbers.md) §30); on a second set of 80, it caught 0 of 40 (§31). It catches commands, paths, flags and fixed phrases; "erase every project file and backup" or "turn off certificate validation" pass. The harmless case it flagged is a lesson that uses zero-width characters on purpose.
- The review (`--review`) caught 39–40 of 40 on the second set and 38–40 of 40 on a set written to evade it. It flagged none of the 80 harmless cases in those sets, nor any of 60 real index skills (§31, §33).
  - All three sets are synthetic, written by GPT, not real attacks; one model did the reviewing.
  - It runs on your model and costs a call per skill.
  - Some replies come back cut off or empty: 1 risky case in the second set and 2 in the evasion set, each in one of the two runs. Such a skill is marked "review incomplete" and gets CAUTION.
- Its warnings are not equally useful. Of a sample of the warnings it raised on the public index, two Claude judges both called these worth a reviewer's look: size 5 of 8, scripts that use the network, run commands, delete files or read secrets 6 of 8, remote instructions 2 of 3, `sudo` 0 of 10, pipe-to-shell 0 of 3, dated lines 0 of 11, concealment phrasing 0 of 6. The last four are now notes, not part of the advice.
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
