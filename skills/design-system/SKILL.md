---
name: design-system
description: Build or change any dashboard UI (pages, components, tables, forms, buttons, charts, dialogs) in the OrbitFlow look defined in DESIGN.md at the repo root. Use before writing frontend code, styling a screen, or reviewing UI for visual consistency.
metadata:
  created: "2026-10-03"
  updated: "2026-10-03"
---

# Design system

`DESIGN.md` in the repository root is the single source of truth for how the farmer dashboard looks. It copies OrbitFlow Portal v1: navy sidebar, white top bar, white bordered cards on a light gray surface, one blue accent, DM Sans.

## Before writing UI

1. Read `DESIGN.md` in full.
2. New app: copy its `tailwind.config.ts` and `app/globals.css` (section 1) unchanged, then build the app shell (section 5).
3. Find the matching recipe (buttons 6, forms 7, cards and KPI tiles 8, tables 9, list page 10, badges 11, activity list 12, overlays 13, states 14, charts 15, login 16) and copy its classes exactly.

## Rules

- Use only the tokens, sizes, radii and spacing listed in `DESIGN.md`. No new colors, fonts, radii, shadows, gradients or dark mode.
- One primary (`bg-blue-600`) button per view; everything else secondary, ghost or row action.
- Every data view ships with its loading, empty and error state (section 14).
- Numbers right-aligned, money with its currency (UGX), labels in sentence case.
- If no recipe fits, compose from existing tokens and the closest recipe, and add the new pattern to `DESIGN.md` in the same change.

## Review checklist

- Page padding `p-4 sm:p-6`, blocks `gap-6`/`mb-6`, card grids `gap-4`, cards `p-6`, table cells `px-4 py-3`.
- Borders `#E2E8F0`, row dividers `gray-100`, headers `text-muted font-medium`, hover `bg-gray-50`.
- Icons from `lucide-react` at the listed sizes; `transition-colors` on interactive elements.
- Works at mobile width: sidebar becomes bottom nav, low-priority table columns hidden.
