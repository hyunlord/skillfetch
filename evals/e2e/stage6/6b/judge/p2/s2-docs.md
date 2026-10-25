## s2-docs

| code | 정확성 1-5 | 완전성 1-5 | 명확성 1-5 | 간결성 1-5 | 문서 구성 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 17c679d6 | 5 | 5 | 5 | 5 | 5 | 5 | Every script, route, data path and behaviour matches the code (fallback 404, dev vs prod rebuild, 500 body); README is tight and usage covers data, types, pages, API and caveats with no overlap |
| 6824c96a | 5 | 5 | 5 | 5 | 5 | 5 | Accurate data-flow diagram, API status table, components table and real caveats (TS 4.9 warning, @types 17, latest); README/usage split cleanly with no repetition |
| 7830d5b2 | 5 | 5 | 5 | 5 | 5 | 5 | Accurate and compact; correctly notes there is no /api/users/[id], that the API also needs a rebuild in prod, and the default title; good README/usage split |
| 23c0868a | 5 | 5 | 5 | 4 | 4 | 5 | Accurate and thorough (method-agnostic handler, 404 cases, troubleshooting table), but usage repeats README's run/build/type-check section and the TS warning appears in both |
| 55be082f | 5 | 5 | 5 | 3 | 4 | 4 | Correct, but padded with generic Next.js material (ISR, getServerSideProps, build legend, alias troubleshooting, doc links), and install/run repeated in usage |
| 99edb422 | 5 | 4 | 5 | 5 | 5 | 5 | Concise and correct with a clean split; leaves out the build-time TS warning and the type-package caveats a newcomer will run into |
| d368fe1f | 5 | 4 | 5 | 5 | 5 | 5 | Accurate (correct fallback/notFound advice, count API example), concise; structure tree omits pages/users and page contents are barely described |
| d7171327 | 5 | 5 | 5 | 3 | 4 | 4 | Accurate but long for this app: TOC, invented Post type and posts/[slug] examples, ISR/SSR, Vercel; build commands and TS warning repeated across README and usage |
| d850b746 | 5 | 5 | 5 | 4 | 5 | 5 | Accurate and complete with useful code-specific notes (legacy Link as prop, why the API link is a plain <a>); a bit long (full sample data and props table) |

1. 17c679d6, 6824c96a, 7830d5b2
4. 99edb422, d368fe1f, d850b746
7. 23c0868a
8. 55be082f, d7171327
