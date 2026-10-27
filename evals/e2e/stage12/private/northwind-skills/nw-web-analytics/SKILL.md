---
name: nw-web-analytics
description: "Northwind platform web analytics event tracking via track()"
---
# Web Analytics

User-facing actions must fire analytics events using the `track()` helper:

```tsx
import { track } from '@/lib/analytics'

track('<page>_<action>', { key: value })
```

- Event name format: `<page>_<action>` (e.g. `orders_view`, `orders_cancel`).
- Every event name must be declared in `analytics/events.ts` as a constant.

## Good Example

```tsx
import { track } from '../lib/analytics'
// in useEffect or handler:
track('orders_view', { source: 'nav' })
```

analytics/events.ts:
```ts
export const EVENTS = {
  ORDERS_VIEW: 'orders_view',
} as const
```

## Bad Example

```tsx
console.log('page viewed')
// or
window.analytics.track('ordersView')
```

## Why
Centralized event tracking with declared event names ensures consistent product analytics and prevents undocumented telemetry.
