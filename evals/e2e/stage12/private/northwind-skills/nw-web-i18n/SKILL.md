---
name: nw-web-i18n
description: "Northwind platform web internationalization via t() helper"
---
# Web Internationalization

All user-visible strings in web pages must use the `t()` helper instead of hardcoded text:

```tsx
import { t } from '@/lib/i18n'

<h1>{t('orders.heading')}</h1>
```

- Key format: `<page>.<key>` (e.g. `orders.heading`, `settings.save_button`).
- Every key must exist in BOTH `locales/en.json` and `locales/ko.json`.
- No hardcoded user-visible strings in JSX.

## Good Example

```tsx
import { t } from '../lib/i18n'

<h1>{t('orders.heading')}</h1>
<p>{t('orders.empty_state')}</p>
```

locales/en.json: `{ "orders": { "heading": "Orders", "empty_state": "No orders yet." } }`
locales/ko.json: `{ "orders": { "heading": "주문", "empty_state": "주문이 없습니다." } }`

## Bad Example

```tsx
<h1>Orders</h1>
<p>No orders yet.</p>
```

Hardcoded English strings that cannot be localized.

## Why
All Northwind web products must support English and Korean for our dual-market user base.
