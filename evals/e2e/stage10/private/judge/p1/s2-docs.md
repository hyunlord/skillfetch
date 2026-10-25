## s2-docs

| code | 정확성 1-5 | 완전성 1-5 | 명확성 1-5 | 간결성 1-5 | 문서 구성 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 013fedca | 5 | 5 | 5 | 5 | 5 | 5 | Every claim matches the code (routes, fallback:false 404, API 200/500, any-method behaviour, dev vs prod rebuild). README has scripts, routes and a full tree; usage.md covers data, pages, TS, deploy and troubleshooting. Linked both ways, no real duplication |
| 2cf58ee2 | 5 | 5 | 5 | 5 | 5 | 5 | Shortest complete set (README 199 words). All facts correct, says there are no test or lint scripts, usage covers routes, API, data change with rebuild note, extension and caveats. Clean split and cross-links |
| 2e9faee9 | 5 | 5 | 5 | 4 | 5 | 5 | Accurate. Data-flow table with run timing, add-user and add-API examples, @types/react 17 mismatch noted. Tree omits users/ and is slightly long, but the split is sound |
| 3ce741e7 | 5 | 5 | 5 | 4 | 4 | 4 | Accurate and complete, with port, Number(id) and alias notes. The "알아 둘 점" caveats (latest, TS warning) are repeated in usage troubleshooting, and the build-output block is paraphrased |
| 408b8a2d | 4 | 5 | 5 | 3 | 3 | 4 | Thorough and mostly correct, but the diff commits the auto-generated AGENTS.md (AI-agent instructions unrelated to the docs). USAGE is long, with Vercel CLI, ISR and React 19 upgrade padding |
| 458558b2 | 5 | 5 | 5 | 4 | 5 | 5 | Correct throughout: npm ci, data flow, rebuild and 404 behaviour, build route table, troubleshooting table. A bit long but focused on this repo |
| 53de2821 | 4 | 5 | 5 | 5 | 5 | 5 | Compact and accurate overall. The one slip is the hedged hint that strict mode would force changes to `catch (err: any)`, which does not hold. Good README/usage split |
| 551a3e4b | 5 | 5 | 5 | 4 | 5 | 5 | Accurate. Useful fresh-clone note that type-check needs next-env.d.ts generated first, id-uniqueness note, TS option table. A little long |
| 840e9af3 | 5 | 5 | 5 | 4 | 5 | 5 | Accurate and complete, with a verification section (type-check + build, no tests or lint). Clear split and links |
| 983f92ea | 5 | 5 | 5 | 3 | 4 | 4 | Correct and detailed (per-page details, component props table). USAGE is 231 lines and restates the README's scripts and data, so it is heavier than a 4-user example needs |
| 9c90a78f | 4 | 5 | 5 | 5 | 5 | 5 | Concise and clear. The README's "설치 시점의 최신 Next.js가 들어옵니다" ignores the lockfile, a minor imprecision. Otherwise all claims check out |
| b3c83bdc | 5 | 5 | 4 | 5 | 5 | 5 | Accurate and lean. The add-user section says /users/105 is generated automatically without repeating the rebuild caveat given earlier |
| bb75c987 | 5 | 5 | 5 | 4 | 5 | 5 | Accurate, including the correct ../../../ relative-path equivalent. Good troubleshooting (EBADENGINE, missing next-env.d.ts). Clean split |
| c7a0f3fd | 4 | 5 | 5 | 3 | 4 | 4 | Accurate on scripts and routes, but the "../../utils (동일)" alias example is ambiguous. README is long (417 words, full tree plus caveats), and usage repeats the install/run steps |
| cd8c86d4 | 5 | 5 | 5 | 4 | 4 | 4 | Correct and thorough: run modes, build-output legend, component table, known warnings. The usage "실행 모드" section largely duplicates the README scripts |
| d648d9f6 | 5 | 5 | 4 | 4 | 3 | 4 | Content is accurate, but it is split into three docs (architecture, development, deployment) that do not link back to the README. How to change the data is scattered across files |
| deb6a9d4 | 4 | 5 | 4 | 3 | 4 | 4 | Long, generic Next.js tutorial content (fallback:true, NextPage, a getServerSideProps sample). Recommends @types/react@latest while runtime is React 18 |
| ee0ee1f7 | 3 | 5 | 4 | 3 | 4 | 4 | Detailed and mostly right, but gives an apparently made-up `agentRules: false` next.config option. A 253-line USAGE with generic padding |

1. 2cf58ee2, 013fedca
3. 2e9faee9, 458558b2, 53de2821, 551a3e4b, 840e9af3, 9c90a78f, b3c83bdc, bb75c987
11. 3ce741e7, cd8c86d4
13. 983f92ea
14. c7a0f3fd, d648d9f6
16. 408b8a2d, deb6a9d4
18. ee0ee1f7
