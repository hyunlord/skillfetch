# Stage 2 — B skills (fixed before any session ran)

Procedure: `search_skills(search_sentence, profile_repo(<repo>))` with skillfetch `e2a1b65` (k=50 compact), index
built 2026-10-22T06:15:43Z. Full lists: `search/top50.txt`, `search/<task>.json`. Bodies of the candidates read in
full, fetched and hash-verified through `load_skills` (`search/bodies/`). One skill per domain, chosen as the one whose
body most directly covers the task. All four domains had one in the top 50, so no domain was replaced by a reserve.

| domain | task | B skill (exact id) | rank in top 50 | tokens (load) | why this one | runners-up not chosen |
|---|---|---|---|---|---|---|
| test writing | s2-tests | `uasl/python-testing-patterns@e62d0f1ca316` | 1 | 6,213 | pytest-specific: AAA, fixtures, `parametrize`, testing exceptions, coverage and isolation — exactly what a suite for a pure-Python parser/expander needs | `uasl/unit-testing@6c5fbb821103` (#2): most of the body is C#/Java/Go/TS; `uasl/property-based-testing@a168f6739085` (#23): fits the parse/serialise round trip but covers one technique, not a suite |
| backend API | s2-api | `uasl/fastapi-templates@effcd0de0b4c` | 2 | 3,682 | "Starting new FastAPI projects from scratch": project layout, Pydantic schemas, repository/service layers, `HTTPException` errors, pytest with an SQLite test database | `uasl/fastapi-endpoint@2a93d50c4970` (#1): its Phase 2 is an AskUserQuestion interview and Phase 3 an ExitPlanMode approval, which a headless `claude -p` session with these tools cannot do, and it assumes async SQLAlchemy in an existing project; `uasl/api-design@bba608f8c974` (#9): REST contract and status-code rules only, no FastAPI implementation or tests |
| documentation | s2-docs | `uasl/quill@336ba74b0e79` | 3 | 3,133 | the one documentation skill in the list: README creation/audit (installation, usage, configuration sections), API docs, accuracy checklist. About a third of the body is AUTORUN/Nexus hand-off protocol (noted in stage 1) | `uasl/onboarding-ux@525055bbdf31` (#29): in-app onboarding UX for end users, not repository docs; `uasl/architecture-decision-records@715e99d0306d` (#30): ADRs only |
| data script | s2-data | `uasl/data-analyst-engine@79799e01e2dd` | 2 | 1,898 | its Phase 2 "Data Cleaning" checklist is the task: missing values, duplicates, numbers stored as strings, unparsed dates, outliers, inconsistent categories, impossible values (negative / future), document every decision; plus pandas patterns and a summary/storytelling phase | `anthropics-skills/xlsx@5350d36b768c` (#1): spreadsheet files with formulas and openpyxl, not CSV cleaning; `uasl/python-error-handling@8dc34883a143` (#24): validation and partial failures in general, nothing on data cleaning |

B is given exactly as in stage 1 / 1b: the `load_skills` output for the pinned id (precedence header + body) is passed
with `--append-system-prompt-file` (`expert-content/<task>.md`). Not installed into `~/.claude/skills` (see report
header). All four ids are in the index, so C2 can find them.
