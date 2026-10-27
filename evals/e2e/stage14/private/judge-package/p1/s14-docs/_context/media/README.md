# cms-api

Backend for the CMS: articles API and media processing (uploads are resized to fit before they are stored).

```
cargo run              # listens on $CMS_BIND (default 0.0.0.0:8080)
cargo test
```

| route | |
|---|---|
| `GET /healthz` | liveness |
| `GET/POST /api/articles`, `GET /api/articles/{id}` | articles |
| `POST /api/media/resize?w=&h=` | body = image; returns it scaled to fit w×h as PNG |

Config (env): `CMS_BIND`, `CMS_MAX_UPLOAD_BYTES`, `CMS_MAX_DIMENSION`.
