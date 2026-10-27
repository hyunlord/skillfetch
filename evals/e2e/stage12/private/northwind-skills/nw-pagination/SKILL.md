---
name: nw-pagination
description: "Northwind platform cursor-based pagination for list endpoints"
---
# Pagination

All list endpoints must use cursor-based pagination:

- Query parameters: `?cursor=<opaque>&limit=<1..100>` (default limit is up to the endpoint, max 100).
- Response envelope:

```json
{
  "data": [...],
  "next_cursor": "<opaque string or null>"
}
```

Do not use offset-based pagination (`?page=&per_page=`).

## Good Example

```
GET /orders?cursor=abc123&limit=20

{
  "data": [{...}, {...}],
  "next_cursor": "def456"
}
```

## Bad Example

```
GET /orders?page=2&per_page=20

{
  "orders": [{...}, {...}],
  "total": 100,
  "page": 2
}
```

## Why
Cursor pagination provides stable results under concurrent writes and avoids the performance cost of OFFSET on large tables.
