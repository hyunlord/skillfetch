---
name: nw-endpoint-registry
description: "Northwind platform HTTP endpoint registration in routes.toml"
---
# Endpoint Registry

Every new HTTP endpoint must be registered in `api/routes.toml`:

```toml
[[routes]]
method = "POST"
path = "/refunds"
owner = "orders"
rate_limit = 100
```

Required fields: `method`, `path`, `owner` (team name), `rate_limit` (requests/min).

## Good Example

Adding `POST /refunds` then add to `api/routes.toml`:
```toml
[[routes]]
method = "POST"
path = "/refunds"
owner = "orders"
rate_limit = 100
```

## Bad Example

Adding a new endpoint without registering it in `api/routes.toml`.

## Why
The route registry feeds the API gateway for rate limiting, ownership tracking, and automated documentation.
