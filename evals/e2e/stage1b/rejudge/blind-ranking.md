# blind ranking — 1b A/B/C/C2 재판정 (판정자: 정답·조건 비공개 하위 에이전트 3개, 루브릭 rubric.md)

## s1b-nx-landing

| code | (a) AI느낌 수 | (b) 쓸만함 1-5 | 근거 |
|---|---|---|---|
| 39bba881 | 2 | 5 | #4 all feature/pricing cards same radius+soft shadow, #8 pill buttons throughout; Korean copy, real Alice-Dave + /users, /users/[id], /api/users mapped to features, monthly/annual pricing, clean mobile stack |
| 3e7828f3 | 0 | 4 | none of the 10; yellow badge-card hero with real 4 users, row-style features naming real routes, bordered pricing; plans have no per-plan CTA buttons |
| 71c78cb4 | 1 | 4 | #4 uniform rounded+shadow cards; API-response hero with real data, features tied to getStaticProps/paths, good pricing+CTA; large empty gap under hero, very dev-centric copy |
| 71fcd341 | 1 | 4 | #7 cream+serif+terracotta; "filed records" concept fits app, real IDs 101-104, full pricing+CTA; ghosted overlapping text in hero card stack, decorative A-Z strip, very long mobile |
| 735036d4 | 0 | 5 | none; giant real names + live JSON in hero, 3 features with concrete routes/types, clear pricing table with CTAs, strong CTA band, mobile tidy (odd: Dave lacks check) |
| 9d2a4569 | 0 | 4 | none; tabbed directory/API hero with real users, row features linking real routes, works on mobile; pricing plans have no buttons, plainer overall |
| a675c2d9 | 1 | 4 | #7 cream+serif+terracotta; index-card hero with real users, numbered features, full pricing+dark CTA; decorative outline "R", generic "done properly"/"no surprises" copy |
| abd0a2d8 | 0 | 5 | none; letter-board hero listing real users from /api/users, clear row features with real links, pricing with per-plan CTAs, demo-team CTA, clean mobile (Org $2 < Team $3 slightly odd) |

1. 735036d4, abd0a2d8
3. 39bba881
4. 3e7828f3, 9d2a4569
6. 71c78cb4, 71fcd341, a675c2d9

## s1b-fa-landing

| code | (a) AI느낌 수 | (b) 쓸만함 1-5 | 근거 |
|---|---|---|---|
| 35af4c58 | 3 | 3 | #3 all centred, #4 identical cards, #6 3-col icon cards; hero pitches the template to developers ("Ship your next app faster") with a teal glow, features are accurate but generic; mobile fine |
| 3f3bb8d9 | 2 | 5 | #6 3-col icon grid (joined, numbered), #10 decorative ring in CTA; left-aligned hero with real /items API sample, copy matches app (items, admin, recovery); mobile code block clips horizontally but OK |
| 6ed168c4 | 1 | 5 | #6 3-col icon features (no cards, dividers); left hero + realistic Items table mock, concrete app-specific copy, split CTA with login link; clean mobile stack |
| 9c86bcda | 1 | 5 | #6 3-col icon features (rule-topped, no cards); hero has a try-it item preview table, copy matches items/admin/settings; mobile truncates table cells but works |
| a53cd4ff | 1 | 5 | #6 3-col icon features; POST request + resulting item table shows exactly what the app does, accurate copy incl. forgot-password link in CTA; primary CTA is Log in rather than sign-up, mobile fine |
| c1f9daa4 | 1 | 5 | #6 3-col icon features (accent rules); dashboard-shaped mock with sidebar/Items/Admin, accurate copy, strong full-width teal CTA band, Sign up in nav; mobile good |
| d91526f5 | 3 | 4 | #3 everything centred, #4 identical icon cards, #6 3-col icon grid; copy is accurate (Argon2, pagination, admin) but no product visual, template-like layout; mobile fine |
| e59c75ef | 3 | 3 | #3 centred, #4 identical cards, #6 3-col icon grid; content sells the boilerplate to developers (async, Docker, OpenAPI) rather than the items app to its users; mobile fine |

1. 6ed168c4, 9c86bcda, a53cd4ff, c1f9daa4
5. 3f3bb8d9
6. d91526f5
7. 35af4c58, e59c75ef

## plans/s1b-fa-tags-plan

| code | 단계 구체성 1-5 | 파일 명시 1-5 | 리스크 1-5 | 검증 방법 1-5 | 순서 1-5 | 플랜 준수 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 0cc603f8 | 4 | 4 | 2 | 4 | 4 | 5 | Clear design and per-layer steps with paths (migration `<rev>`), no risk section, verification lists migration round-trip/pytest/lint/tsc; the diff matches the plan (only change: TagsInput.tsx became a tags.ts helper), tag filter Select and /tags route both present |
| 13017b68 | 5 | 5 | 4 | 5 | 5 | 5 | Task-by-task plan with code, an exact file map, a command and expected output per step, TDD order and parallelization notes, and the concurrency race is named; the diff follows it file for file (global tags, badge-link filter, e2e). The weak point is the global-tag scope |
| 2aaf174d | 4 | 4 | 2 | 4 | 4 | 3 | Good design table and steps, no risks beyond design rationale; impl never touched routes/_layout/items.tsx, so the TagFilter component is unused, the planned `?tag=` search param/validateSearch is missing, and the Playwright spec was never written |
| 62d1b5d1 | 4 | 4 | 2 | 4 | 4 | 5 | Numbered backend→frontend steps with paths, notes the superuser-dropdown caveat but has no risk section; impl matches fully: orphan cleanup, /tags, chip TagInput, URL filter Select and 4 e2e tests |
| 7c401036 | 4 | 4 | 2 | 4 | 4 | 2 | Solid plan (incl. DELETE /tags) but no risk section; impl is backend-only: no client regen, no Add/Edit/columns/items.tsx changes, no e2e, so half the planned scope is missing |
| b20215c8 | 5 | 5 | 4 | 5 | 5 | 5 | Very concrete (code, file map, local DB setup, baseline 58 tests, confirmed SQLModel model_validate gotcha, race noted, per-step commands), but checkboxes are pre-ticked; impl matches the plan exactly (frontend filter UI deliberately out of scope) |
| dd79f213 | 4 | 4 | 3 | 4 | 4 | 5 | Clear goals/YAGNI scope, explicit 리스크 section (unique-constraint race), alembic check in verification; impl follows it (TagName type, selectin, chip TagInput, e2e). The frontend filter was excluded by design |
| e5e778c5 | 4 | 4 | 2 | 4 | 4 | 5 | Design table and steps with paths, alembic check, no risk section, no e2e planned; impl matches (case-preserving names, /tags list+delete, comma input, URL-backed filter Select) |

1. 13017b68, b20215c8
3. dd79f213
4. 62d1b5d1
5. 0cc603f8, e5e778c5
7. 2aaf174d
8. 7c401036
