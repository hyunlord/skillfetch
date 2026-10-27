# s14-mono

Four independent areas, each built and tested in its own directory.

| area | what | run | test |
|---|---|---|---|
| `web/` | Next.js (pages router) example app | `cd web && npm ci && npm run dev` | `npm run type-check` |
| `api/` | FastAPI service | `cd api && uv sync && uv run uvicorn app.main:app` | `uv run pytest` |
| `media/` | axum CMS with image resize | `cd media && cargo run` | `cargo test` |
| `data/` | data scripts over `data/data/orders.csv` | `cd data && uv sync` | – |
