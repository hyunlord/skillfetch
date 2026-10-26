## s2-docs

| code | 정확성 1-5 | 완전성 1-5 | 명확성 1-5 | 간결성 1-5 | 문서 구성 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| e9b94045 | 4 | 5 | 5 | 5 | 5 | 5 | Accurate routes/scripts/data flow, notes the legacy `href`+`as` in ListItem and bundled API data; one slightly wrong claim that `strict: false` may let omitted fields pass type-check; clean README/usage split with no repetition |
| f8bf56f7 | 4 | 5 | 5 | 5 | 5 | 5 | Accurate and complete with a data-flow table, API error/method behaviour and caveats; lists `/api/users` as reading data "at request time" without noting production still needs a rebuild; good split |
| db1db1cf | 5 | 5 | 5 | 4 | 4 | 5 | Very precise (build route summary, errors prop path, method-agnostic API, 500 shape, build warnings, @types mismatch); USAGE repeats install/build from README and the warnings section is a bit long |
| 23f1942a | 5 | 5 | 5 | 5 | 4 | 5 | Accurate scripts/routes table, data change workflow, add page/API examples, deploy notes and troubleshooting table; usage re-lists install/dev/build commands already in README |
| 4206862d | 5 | 5 | 5 | 5 | 5 | 5 | Accurate throughout (SSG vs API, fallback:false 404, API data baked into build, next-env.d.ts, lockfile/npm ci), compact README and usage that starts after quick start with no duplication |
| b04adef5 | 5 | 5 | 5 | 4 | 4 | 5 | Accurate and complete with full file tree and troubleshooting; longest set, usage repeats install/run/build from README and includes a generic `loadSomething()` SSG snippet |

1. 4206862d
2. e9b94045, f8bf56f7, 23f1942a
5. db1db1cf, b04adef5
