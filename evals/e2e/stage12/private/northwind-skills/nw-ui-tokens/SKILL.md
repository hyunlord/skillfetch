---
name: nw-ui-tokens
description: "Northwind platform CSS design tokens for colors and spacing"
---
# UI Design Tokens

All colors and spacing in new or modified styles must use `var(--nw-*)` CSS custom properties:

```css
color: var(--nw-color-primary);
padding: var(--nw-spacing-md);
```

- No raw hex color values (e.g. `#0066cc`).
- No raw pixel spacing values (e.g. `16px` for layout spacing). Use `--nw-spacing-*` tokens.
- Token definitions are in `styles/tokens.css`.

## Good Example

```tsx
<div style={{ color: 'var(--nw-color-text)', padding: 'var(--nw-spacing-md)' }}>
```

## Bad Example

```tsx
<div style={{ color: '#212529', padding: '16px' }}>
```

## Why
Design tokens enable theme-wide changes from a single source and ensure visual consistency across the application.
