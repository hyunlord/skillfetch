# Next.js + TypeScript example

A small Next.js (Pages Router) app in TypeScript: a home page, an about page, a list of users at `/users`, a
detail page per user at `/users/[id]`, and a JSON API at `/api/users`. The users come from `utils/sample-data.ts`.

## Run

```bash
npm ci
npm run dev        # http://localhost:3000
npm run build && npm start
npm run type-check
```
