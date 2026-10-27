---
name: nw-marketing-analytics
description: "Marketing site analytics via Google Analytics gtag"
---
# Marketing Site Analytics

The Marketing site tracks events using Google Analytics `gtag()`:

```ts
gtag('event', 'page_view', { page_title: 'Products' })
```

- Event names follow Google Analytics conventions.
- No custom `track()` wrapper is used.

## Good Example

```ts
gtag('event', 'purchase', { value: 29.99, currency: 'USD' })
```

## Bad Example

```ts
track('purchase_completed', { amount: 29.99 })
```

## Why
The marketing site needs direct Google Analytics integration for campaign attribution and conversion tracking.
