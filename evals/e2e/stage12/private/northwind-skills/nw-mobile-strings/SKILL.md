---
name: nw-mobile-strings
description: "Mobile app team string localization via strings.xml"
---
# Mobile App Strings

The Mobile app team manages translations in Android-style `strings.xml`:

```xml
<resources>
  <string name="orders_heading">Orders</string>
</resources>
```

Keys use `snake_case` without dots.

## Good Example

```xml
<string name="order_cancel_confirm">Cancel this order?</string>
```

## Bad Example

```ts
t('orders.cancel_confirm')
```

## Why
The mobile apps use native Android/iOS localization pipelines that consume XML resource files.
