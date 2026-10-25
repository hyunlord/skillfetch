## s1-fa-01-r1#1
Repo: fastapi full-stack template
User's task:
> GET /api/v1/items/ always sorts newest first. Add an `order_by` query parameter that accepts `created_at` (default) or `title`, and an `order` parameter that accepts `asc` or `desc` (default `desc`). Any other value should be rejected with a 422.
Query sent to search_skills:
> Add validated order_by and order query parameters to the FastAPI GET /api/v1/items/ endpoint with SQLModel sorting and 422 on invalid values, with tests

## s1-fa-02-r1#1
Repo: fastapi full-stack template
User's task:
> 아이템에 완료 여부를 나타내는 `is_done` 불리언 필드를 추가해줘. 기본값은 false이고, 아이템 생성·수정·조회 API에서 다룰 수 있어야 해. 기존 데이터가 있는 DB에도 적용되도록 alembic 마이그레이션도 만들어줘.
Query sent to search_skills:
> Add an is_done boolean field (default false) to the SQLModel Item model in a FastAPI backend, expose it in create/update/read API schemas, and write an Alembic migration that applies to existing databases

## s1-fa-02-r2#1
Repo: fastapi full-stack template
User's task:
> 아이템에 완료 여부를 나타내는 `is_done` 불리언 필드를 추가해줘. 기본값은 false이고, 아이템 생성·수정·조회 API에서 다룰 수 있어야 해. 기존 데이터가 있는 DB에도 적용되도록 alembic 마이그레이션도 만들어줘.
Query sent to search_skills:
> Add an is_done boolean field (default false) to the Item SQLModel model in a FastAPI backend, expose it in item create/update/read APIs, and write an Alembic migration for existing databases

## s1-fa-03-r1#1
Repo: fastapi full-stack template
User's task:
> 프론트엔드 대시보드(/)가 인사말만 있고 비어 있어. 내 아이템 개수와 가장 최근 아이템 3개의 제목을 보여주는 카드를 대시보드에 추가해줘. 기존 UI 컴포넌트 스타일에 맞춰줘.
Query sent to search_skills:
> Add a dashboard card to the React frontend home page showing the current user's item count and the titles of the three most recent items, matching existing UI component styles

## s1-fa-03-r2#1
Repo: fastapi full-stack template
User's task:
> 프론트엔드 대시보드(/)가 인사말만 있고 비어 있어. 내 아이템 개수와 가장 최근 아이템 3개의 제목을 보여주는 카드를 대시보드에 추가해줘. 기존 UI 컴포넌트 스타일에 맞춰줘.
Query sent to search_skills:
> Add a dashboard card to the React TypeScript frontend home route showing the user's item count and three most recent item titles, matching existing UI component styles

## s1-fa-05-r1#1
Repo: fastapi full-stack template
User's task:
> users.py의 사용자 목록과 items.py의 아이템 목록 엔드포인트가 skip/limit 파라미터를 각자 선언하고 있어. 공통 페이지네이션 의존성 하나로 묶어서 두 엔드포인트가 같이 쓰게 해줘. 기존 동작(기본값 skip=0, limit=100)은 그대로 유지해.
Query sent to search_skills:
> Refactor FastAPI user list and item list endpoints in users.py and items.py to share a common pagination dependency for skip/limit query parameters

## s1-fa-06-r1#1
Repo: fastapi full-stack template
User's task:
> There are no tests showing that a normal user's GET /api/v1/items/ only returns their own items. Add tests that cover the item list and its `count` for a normal user who owns some items while other users own others.
Query sent to search_skills:
> Add pytest tests for the FastAPI GET /api/v1/items/ endpoint verifying a normal user only sees their own items and the correct count when other users own items

## s1-fa-06-r2#1
Repo: fastapi full-stack template
User's task:
> There are no tests showing that a normal user's GET /api/v1/items/ only returns their own items. Add tests that cover the item list and its `count` for a normal user who owns some items while other users own others.
Query sent to search_skills:
> Add pytest tests for the FastAPI SQLModel backend verifying GET /api/v1/items/ returns only the normal user's own items and correct count in backend/tests/api/routes/test_items.py

## s1-fa-07-r1#1
Repo: fastapi full-stack template
User's task:
> 인증 의존성 get_current_user(backend/app/api/deps.py)에 대한 테스트가 없어. 잘못된 서명의 토큰, 만료된 토큰, 삭제된 사용자의 토큰, 비활성 사용자의 토큰 각각에 대해 API가 어떤 응답을 주는지 테스트를 작성해줘.
Query sent to search_skills:
> Add pytest tests for the FastAPI get_current_user dependency in backend/app/api/deps.py covering invalid-signature, expired, deleted-user and inactive-user JWT tokens

## s1-fa-07-r2#1
Repo: fastapi full-stack template
User's task:
> 인증 의존성 get_current_user(backend/app/api/deps.py)에 대한 테스트가 없어. 잘못된 서명의 토큰, 만료된 토큰, 삭제된 사용자의 토큰, 비활성 사용자의 토큰 각각에 대해 API가 어떤 응답을 주는지 테스트를 작성해줘.
Query sent to search_skills:
> Write pytest tests for the FastAPI authentication dependency get_current_user in backend/app/api/deps.py covering invalid JWT signature, expired token, deleted user, and inactive user

## s1-fa-08-r1#1
Repo: fastapi full-stack template
User's task:
> Sending PUT /api/v1/items/{id} with {"title": null} makes the server return a 500. It should be rejected as a validation error and the item must stay unchanged.
Query sent to search_skills:
> Fix a FastAPI PUT /api/v1/items/{id} update endpoint that returns 500 when a non-nullable field like title is sent as null, so it is rejected with a 422 validation error and the item is not modified

## s1-fa-08-r2#1
Repo: fastapi full-stack template
User's task:
> Sending PUT /api/v1/items/{id} with {"title": null} makes the server return a 500. It should be rejected as a validation error and the item must stay unchanged.
Query sent to search_skills:
> Fix a FastAPI SQLModel PUT /api/v1/items/{id} endpoint in backend/app so that sending null for a required field like title returns a 422 validation error instead of a 500, with a regression test

## s1-fa-10-r1#1
Repo: fastapi full-stack template
User's task:
> Add a table of the backend's configuration environment variables to backend/README.md, based on Settings in app/core/config.py: name, default value (mark it as required if there is none) and a short description.
Query sent to search_skills:
> Document the FastAPI backend's pydantic-settings environment variables from backend/app/core/config.py as a table in backend/README.md

## s1-nx-02-r1#1
Repo: Next.js with-typescript (Pages Router)
User's task:
> Add an API endpoint GET /api/users/[id] that returns one user as JSON. Return 404 with a JSON error message if no user has that id, and 400 if the id is not a number.
Query sent to search_skills:
> Add a Next.js TypeScript API route GET /api/users/[id] that returns a user as JSON with 404 and 400 error handling

## s1-nx-02-r2#1
Repo: Next.js with-typescript (Pages Router)
User's task:
> Add an API endpoint GET /api/users/[id] that returns one user as JSON. Return 404 with a JSON error message if no user has that id, and 400 if the id is not a number.
Query sent to search_skills:
> Add a Next.js TypeScript API route GET /api/users/[id] that returns a user as JSON with 404 and 400 error handling

## s1-nx-04-r1#1
Repo: Next.js with-typescript (Pages Router)
User's task:
> About 페이지에 우리 팀 소개 섹션을 넣어줘. utils/sample-data.ts의 유저들을 카드 그리드로 보여주고, 카드마다 이름, ID, 상세 페이지 링크를 넣어줘. 화면이 좁으면 한 줄에 한 장씩 보이게 해줘.
Query sent to search_skills:
> Add a responsive team section to the Next.js TypeScript About page that renders users from utils/sample-data.ts as a card grid with name, ID and a link to each user's detail page, collapsing to one card per row on narrow screens

## s1-nx-04-r2#1
Repo: Next.js with-typescript (Pages Router)
User's task:
> About 페이지에 우리 팀 소개 섹션을 넣어줘. utils/sample-data.ts의 유저들을 카드 그리드로 보여주고, 카드마다 이름, ID, 상세 페이지 링크를 넣어줘. 화면이 좁으면 한 줄에 한 장씩 보이게 해줘.
Query sent to search_skills:
> Add a responsive team intro section to the Next.js TypeScript About page rendering users from utils/sample-data.ts as a card grid with name, ID, and a link to each user's detail page, one card per row on narrow screens

## s1-nx-06-r1#1
Repo: Next.js with-typescript (Pages Router)
User's task:
> Pages and the API route import sampleUserData directly. Put all user data access behind a small module lib/users.ts with getAllUsers() and getUserById(id), and use it everywhere. Rendered pages and API output must stay exactly the same.
Query sent to search_skills:
> Refactor a Next.js TypeScript app so pages and API routes access user data through a new lib/users.ts data-access module with getAllUsers and getUserById instead of importing sample data directly, keeping output identical

## s1-nx-06-r2#1
Repo: Next.js with-typescript (Pages Router)
User's task:
> Pages and the API route import sampleUserData directly. Put all user data access behind a small module lib/users.ts with getAllUsers() and getUserById(id), and use it everywhere. Rendered pages and API output must stay exactly the same.
Query sent to search_skills:
> Refactor a Next.js TypeScript app so pages and the API route access user data through a new lib/users.ts module with getAllUsers() and getUserById(id) instead of importing sampleUserData directly, preserving output

## s1-nx-07-r1#1
Repo: Next.js with-typescript (Pages Router)
User's task:
> 이 프로젝트엔 테스트 러너가 없어. Vitest와 React Testing Library를 설정하고 `npm test`로 돌아가게 한 다음, ListDetail 컴포넌트(이름과 ID 표시)와 Layout 컴포넌트(내비게이션 링크 4개와 제목) 테스트를 작성해줘.
Query sent to search_skills:
> Set up Vitest with React Testing Library in a Next.js TypeScript project so npm test runs, and write component tests for ListDetail and Layout components

## s1-nx-07-r2#1
Repo: Next.js with-typescript (Pages Router)
User's task:
> 이 프로젝트엔 테스트 러너가 없어. Vitest와 React Testing Library를 설정하고 `npm test`로 돌아가게 한 다음, ListDetail 컴포넌트(이름과 ID 표시)와 Layout 컴포넌트(내비게이션 링크 4개와 제목) 테스트를 작성해줘.
Query sent to search_skills:
> Set up Vitest with React Testing Library in a Next.js TypeScript project so npm test runs, and write component tests for ListDetail and Layout

## s1-nx-08-r1#1
Repo: Next.js with-typescript (Pages Router)
User's task:
> Add tests for getStaticPaths and getStaticProps in pages/users/[id].tsx: the generated paths, the props for an existing id, and what happens for an unknown id.
Query sent to search_skills:
> Add Jest unit tests for the Next.js Pages Router getStaticPaths and getStaticProps functions in TypeScript file pages/users/[id].tsx

## s1-nx-08-r2#1
Repo: Next.js with-typescript (Pages Router)
User's task:
> Add tests for getStaticPaths and getStaticProps in pages/users/[id].tsx: the generated paths, the props for an existing id, and what happens for an unknown id.
Query sent to search_skills:
> Add unit tests for the Next.js Pages Router data-fetching functions getStaticPaths and getStaticProps in pages/users/[id].tsx (TypeScript), covering generated paths, props for an existing id, and an unknown id

## s1-nx-10-r1#1
Repo: Next.js with-typescript (Pages Router)
User's task:
> Add JSDoc comments to every component in components/ and every exported type in interfaces/ describing what it renders or represents and what each prop/field means. Do not change any code.
Query sent to search_skills:
> Add JSDoc comments to the React TypeScript components in components/ and the exported types in interfaces/index.ts of a Next.js app, without changing any code

## s1b-fa-landing-r1#1
Repo: fastapi full-stack template
User's task:
> 로그인 전 소개용 랜딩 페이지를 신규 라우트에 처음부터 만들어줘 — 히어로, 기능 3개, CTA 포함
Query sent to search_skills:
> Build a new pre-login marketing landing page route from scratch with a hero section, three feature cards, and a call-to-action, served by a FastAPI app

## s1b-fa-landing-r2#1
Repo: fastapi full-stack template
User's task:
> 로그인 전 소개용 랜딩 페이지를 신규 라우트에 처음부터 만들어줘 — 히어로, 기능 3개, CTA 포함
Query sent to search_skills:
> Build a new pre-login marketing landing page route from scratch with a hero section, three feature cards and a call-to-action in this repo's frontend

## s1b-fa-service-r1#1
Repo: fastapi full-stack template
User's task:
> items 라우터의 비즈니스 로직을 서비스 레이어로 분리해줘
Query sent to search_skills:
> Refactor the FastAPI items router by extracting its business logic into a separate service layer module

## s1b-fa-service-r2#1
Repo: fastapi full-stack template
User's task:
> items 라우터의 비즈니스 로직을 서비스 레이어로 분리해줘
Query sent to search_skills:
> Refactor the FastAPI items router by extracting its business logic into a separate service layer module in Python

## s1b-fa-tags-plan-r1#1
Repo: fastapi full-stack template
User's task:
> 아이템에 태그 기능 추가해줘 (모델·마이그레이션·API·프론트). 계획을 먼저 PLAN.md로 쓰고 그 다음 구현해
Query sent to search_skills:
> Add a tags feature to items in a FastAPI + SQLModel full-stack app: write a PLAN.md, then add a Tag model with many-to-many link to Item, an Alembic migration, REST API endpoints, and React frontend UI

## s1b-fa-tags-plan-r2#1
Repo: fastapi full-stack template
User's task:
> 아이템에 태그 기능 추가해줘 (모델·마이그레이션·API·프론트). 계획을 먼저 PLAN.md로 쓰고 그 다음 구현해
Query sent to search_skills:
> Add a tags feature to items in a FastAPI + SQLModel backend with Alembic migration, REST API endpoints, and a React TypeScript frontend, writing a PLAN.md implementation plan first

## s1b-fa-utils-tests-r1#1
Repo: fastapi full-stack template
User's task:
> backend/app/utils.py에 테스트 추가해줘
Query sent to search_skills:
> Add pytest unit tests for the Python FastAPI backend utility module backend/app/utils.py

## s1b-fa-utils-tests-r2#1
Repo: fastapi full-stack template
User's task:
> backend/app/utils.py에 테스트 추가해줘
Query sent to search_skills:
> Add pytest unit tests for the FastAPI backend helper module backend/app/utils.py in backend/tests/

## s1b-nx-landing-r1#1
Repo: Next.js with-typescript (Pages Router)
User's task:
> 이 앱의 제품 랜딩 페이지를 신규 라우트 /landing에 처음부터 만들어줘 — 히어로, 기능 3개, 가격, CTA 포함
Query sent to search_skills:
> Build a new product landing page at the /landing route in a Next.js TypeScript app with hero, three feature sections, pricing, and call-to-action

## s1b-nx-landing-r2#1
Repo: Next.js with-typescript (Pages Router)
User's task:
> 이 앱의 제품 랜딩 페이지를 신규 라우트 /landing에 처음부터 만들어줘 — 히어로, 기능 3개, 가격, CTA 포함
Query sent to search_skills:
> Build a new product landing page at the /landing route in a Next.js TypeScript pages-router app with hero, three feature cards, pricing section and call-to-action

## s1-fa-09-r1#1
Repo: fastapi full-stack template
User's task:
> 대소문자만 다른 이메일로 회원가입하면 계정이 하나 더 생겨요 (foo@example.com이 있는데 FOO@example.com으로 가입 가능). 그리고 ADMIN@EXAMPLE.COM으로는 로그인이 안 돼요. 이메일은 대소문자 구분 없이 같은 계정으로 취급되게 고쳐줘.
Query sent to search_skills:
> Fix a FastAPI/SQLModel backend bug so user emails are treated case-insensitively for signup uniqueness and login, normalizing email in the user CRUD and auth routes, with pytest tests

## s1-fa-09-r2#1
Repo: fastapi full-stack template
User's task:
> 대소문자만 다른 이메일로 회원가입하면 계정이 하나 더 생겨요 (foo@example.com이 있는데 FOO@example.com으로 가입 가능). 그리고 ADMIN@EXAMPLE.COM으로는 로그인이 안 돼요. 이메일은 대소문자 구분 없이 같은 계정으로 취급되게 고쳐줘.
Query sent to search_skills:
> Fix a FastAPI SQLModel backend bug so user email signup and login are case-insensitive, preventing duplicate accounts that differ only in letter case

## s1-nx-01-r1#1
Repo: Next.js with-typescript (Pages Router)
User's task:
> On the user detail page, add links labelled "Previous" and "Next" to the neighbouring users (in the order of the users list) and a "Back to list" link to /users. The first user has no Previous link and the last user has no Next link.
Query sent to search_skills:
> Add Previous/Next and Back to list navigation links to the Next.js TypeScript user detail page (pages/users/[id].tsx) based on the order of the users list

## s1-nx-01-r2#1
Repo: Next.js with-typescript (Pages Router)
User's task:
> On the user detail page, add links labelled "Previous" and "Next" to the neighbouring users (in the order of the users list) and a "Back to list" link to /users. The first user has no Previous link and the last user has no Next link.
Query sent to search_skills:
> Add Previous/Next navigation links and a Back to list link to the Next.js TypeScript user detail page (pages/users/[id].tsx) based on the order of the users list

## s1-nx-03-r1#1
Repo: Next.js with-typescript (Pages Router)
User's task:
> 없는 주소로 들어가면 Next.js 기본 404 화면이 나와. 사이트 Layout(상단 내비게이션, 푸터 포함)을 쓰는 404 페이지를 만들고 "페이지를 찾을 수 없습니다" 문구와 홈으로 가는 링크를 넣어줘.
Query sent to search_skills:
> Add a custom 404 Not Found page to a Next.js TypeScript app that uses the shared site Layout component (navigation and footer), with a "page not found" message and a link back to home

## s1-nx-05-r1#1
Repo: Next.js with-typescript (Pages Router)
User's task:
> Layout 컴포넌트의 상단 내비게이션 링크를 하드코딩 대신 배열 하나로 정의해서 렌더링하게 바꾸고, 현재 페이지에 해당하는 링크에는 aria-current="page"를 붙여줘. 보이는 모양은 지금과 같게 유지해.
Query sent to search_skills:
> Refactor the Next.js TypeScript Layout component's top navigation links into a single array rendered with map, adding aria-current="page" to the link for the current route while keeping the visual output unchanged

## s1-nx-05-r2#1
Repo: Next.js with-typescript (Pages Router)
User's task:
> Layout 컴포넌트의 상단 내비게이션 링크를 하드코딩 대신 배열 하나로 정의해서 렌더링하게 바꾸고, 현재 페이지에 해당하는 링크에는 aria-current="page"를 붙여줘. 보이는 모양은 지금과 같게 유지해.
Query sent to search_skills:
> Refactor the Next.js React TypeScript Layout component's top navigation links into a single data array rendered with map, adding aria-current="page" to the active link while keeping the visual appearance unchanged
