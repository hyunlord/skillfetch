## s2-docs

| code | 정확성 1-5 | 완전성 1-5 | 명확성 1-5 | 간결성 1-5 | 문서 구성 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 0a0e5ebd | 4 | 5 | 5 | 4 | 4 | 4 | Accurate README/USAGE with a good data-flow diagram and caveats, but it commits a generated AGENTS.md for AI agents and makes claims that cannot be checked against the repo (`agentRules: false` option, an exact lockfile version). |
| 38595747 | 5 | 5 | 5 | 5 | 4 | 5 | Every command, route and behaviour matches the code (fallback: false 404, the 500 path, the API ignores the HTTP method); good extension guide; usage.md repeats the README's install/run steps. |
| 4069958b | 5 | 5 | 5 | 5 | 5 | 5 | Short, accurate, complete: requirements, scripts, a routes table with files, data location and how to edit it (dev vs rebuild), page addition, caveats; clean README/USAGE split with links both ways. |
| 4ad00562 | 5 | 5 | 5 | 4 | 4 | 5 | Accurate and thorough, with a status-code table and troubleshooting (TS 4.x warning, Node version); some overlap between the README tree and the usage routes table, and a generic deploy line. |
| a1946f1a | 5 | 5 | 5 | 4 | 5 | 5 | Accurate, with sharp code-level notes (item undefined with fallback, `output: export` breaks the API, build-output symbols) and a TOC; the usage doc is longer than this small app needs. |
| b1ba4222 | 4 | 5 | 5 | 5 | 5 | 4 | Clear and well split, but the type example adds an optional `email?` while saying type-check will flag the places it is missing (it will not), the 500 condition is stated vaguely, and "add a user" omits the rebuild. |

1. 4069958b
2. 38595747, a1946f1a
4. 4ad00562
5. b1ba4222
6. 0a0e5ebd
