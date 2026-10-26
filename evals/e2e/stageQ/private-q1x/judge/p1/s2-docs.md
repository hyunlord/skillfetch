## s2-docs

| code | 정확성 1-5 | 완전성 1-5 | 명확성 1-5 | 간결성 1-5 | 문서 구성 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 0aa8abb3 | 5 | 5 | 5 | 5 | 5 | 5 | Every script, route, 404 behaviour, API response and data path matches the source. Also notes correctly that the legacy `as` Link, the @types/react 17 vs react 18 mismatch, and the API data are bundled at build time. Tight README; usage.md covers changes without repeating it; the two link to each other. |
| 6ab49aa3 | 5 | 5 | 5 | 4 | 5 | 5 | Accurate and complete, with a routes table showing files, rendering mode and the data flow; usage.md adds a troubleshooting table. Some overlap: usage repeats install, dev and type-check from the README. |
| 812aa6f9 | 5 | 5 | 5 | 5 | 5 | 5 | Accurate (fallback:false 404, dev hot-reload vs rebuild, API 500 shape, no method check). Lean README; usage.md has a data-flow table, extension steps and caveats; the split is clean and cross-linked. |
| b2689158 | 4 | 5 | 5 | 3 | 4 | 4 | Complete and mostly accurate. It adds build-output trees and specific build warnings (React 18 deprecation, TS < 5.1) that cannot be checked from the repo. USAGE.md is 170 lines for a 4-page example and repeats README install/run/type-check. |
| b9ee971e | 5 | 5 | 5 | 4 | 4 | 4 | Accurate and complete. The README has a full file tree, and usage.md repeats install/run and the page list, so the two overlap and run long; the SSG example uses an undefined `loadSomething()` placeholder. |
| e14e2b29 | 5 | 5 | 5 | 5 | 5 | 5 | Accurate: the scripts table shows the underlying commands, the routes table shows files, the README has a working curl example, and the quick start uses `npm ci`. Focused usage.md with no duplication; the only extra is a one-line upstream-license note. |

1. 0aa8abb3, 812aa6f9, e14e2b29
4. 6ab49aa3
5. b9ee971e
6. b2689158
