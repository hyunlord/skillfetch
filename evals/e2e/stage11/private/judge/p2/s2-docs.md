## s2-docs

| code | 정확성 1-5 | 완전성 1-5 | 명확성 1-5 | 간결성 1-5 | 문서 구성 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 28f94dea | 4 | 5 | 5 | 4 | 4 | 4 | Accurate routes, scripts, data flow and API behaviour, with good caveats; but it commits the `next dev`-generated AGENTS.md (agent instructions, not user docs) as part of the deliverable and makes claims the repo cannot confirm (exact locked version 16.4.2, an `agentRules` config option) |
| 485ae30b | 5 | 5 | 5 | 4 | 4 | 5 | Correct and complete (scripts, routes, SSG/404 behaviour, data change and rebuild, adding pages/APIs, alias, version caveats); the usage doc repeats the README's install/run steps |
| 76f93b4f | 5 | 5 | 5 | 5 | 5 | 5 | Compact, fully accurate README plus a usage guide with no overlap: screens, API example, where the sample data lives and when changes need a rebuild, adding fields and pages, caveats |
| 856a37f0 | 5 | 5 | 5 | 4 | 5 | 5 | Accurate data-flow diagram, API example and 500 case, add user/page/API route examples, alias and TS notes; a generic deployment section adds a little length |
| b2a88576 | 5 | 5 | 5 | 4 | 4 | 5 | Accurate and complete with a useful troubleshooting section (TS 4.x warning, Node version); the routes appear in both the README tree and the usage table |
| fb413e49 | 5 | 5 | 5 | 4 | 5 | 5 | Most thorough guide (TOC, data flow, fallback/notFound note matching the code, typing conventions, build output symbols, troubleshooting), all consistent with the source; longer than a small example app needs |

1. 76f93b4f
2. 856a37f0, fb413e49
4. 485ae30b, b2a88576
6. 28f94dea
