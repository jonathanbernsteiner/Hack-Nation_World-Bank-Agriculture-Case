# Design system

Every screen of the farmer dashboard follows this file. It copies the look of OrbitFlow Portal v1 one to one: same colors, type, spacing, buttons, tables and dialogs. When something here is unclear, copy what OrbitFlow does; don't invent a new style.

**Stack the recipes assume:** Next.js 14 (App Router), Tailwind CSS 3, `lucide-react` icons, Recharts for charts. Light mode only.

---

## 1. Setup (copy these two files)

`tailwind.config.ts`

```ts
import type { Config } from "tailwindcss";
import typography from "@tailwindcss/typography";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["DM Sans", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      colors: {
        surface: "#F9FAFB", // page background behind cards
        accent: "#3B82F6",  // active nav, tabs, focus, icons
        ai: "#8B5CF6",      // anything the AI did
        // Aliases for hex values OrbitFlow writes inline (same colors, easier to type)
        navy: "#0B1628",    // sidebar, toasts, logo, dialog backdrop
        ink: "#0F172A",     // headings, KPI values, tooltips
        muted: "#64748B",   // labels, table headers
        faint: "#94A3B8",   // hints, empty-state text, chart ticks
        line: "#E2E8F0",    // card, table and panel borders
        divider: "#F1F5F9", // row dividers inside lists, chart grid
      },
    },
  },
  plugins: [typography],
};

export default config;
```

`app/globals.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@import url("https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&family=JetBrains+Mono:wght@400;500;600&display=swap");

body {
  font-family: "DM Sans", system-ui, sans-serif;
  background-color: #ffffff;
  color: #111827;
}

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #9ca3af; }
```

`<body className="bg-white antialiased">` in the root layout.

---

## 2. Colors

| Token | Hex | Tailwind | Used for |
|---|---|---|---|
| Navy | `#0B1628` | `bg-navy` | Sidebar, mobile bottom nav, toasts, logo circle, dialog backdrop (`bg-navy/60`) |
| Ink | `#0F172A` | `text-ink` | Page titles, KPI numbers, names in lists, tooltip background |
| Body text | `#111827` | `text-gray-900` | Default text, table names |
| Secondary text | `#374151` / `#4B5563` | `text-gray-700` / `text-gray-600` | Secondary button text, table cells, labels |
| Muted | `#64748B` | `text-muted` | Table headers, KPI labels, field labels in filter rows |
| Faint | `#94A3B8` | `text-faint` | Hints, placeholders, empty states, chart ticks, inactive mobile nav |
| Line | `#E2E8F0` | `border-line` | Borders of cards, tables, filter panels, top bar |
| Input border | `#E5E7EB` | `border-gray-200` | Inputs, secondary buttons, dropdown triggers |
| Divider | `#F1F5F9` | `border-divider` / `border-gray-100` | Lines between table rows and list items, chart grid |
| Surface | `#F9FAFB` | `bg-surface` | Main content background (cards sit on it in white) |
| Row hover | `#F8FAFC` / `#F9FAFB` | `hover:bg-gray-50` | Table rows, list rows, secondary button hover |
| Accent | `#3B82F6` | `accent` / `blue-500` | Active nav pill, active tab underline, focus ring, KPI icons, links |
| Primary button | `#2563EB` → `#1D4ED8` | `bg-blue-600 hover:bg-blue-700` | Main action button |
| AI | `#8B5CF6` | `ai` | AI-generated content, AI channel badges |

**Status colors** (always tinted background + strong text, never solid fills except the danger button):

| Meaning | Pill (bordered) | Soft badge | Icon / number color |
|---|---|---|---|
| Success / active / AI handling | `bg-[#ECFDF5] text-[#10B981] border-[#A7F3D0]` | `bg-green-100 text-green-800` | `#10B981`, money in `#059669` |
| Warning / needs person | `bg-[#FFFBEB] text-[#F59E0B] border-[#FDE68A]` | `bg-amber-100 text-amber-800` | `#F59E0B` |
| Danger / overdue | `bg-red-50 text-red-700 border-red-200` | `bg-red-100 text-red-800` | `text-red-600` |
| Info / selected filter | `bg-blue-50 text-blue-700 border-blue-200` | `bg-blue-100 text-blue-800` | `#3B82F6` |
| Closed / neutral | `bg-[#F1F5F9] text-[#94A3B8] border-[#E2E8F0]` | `bg-gray-100 text-gray-800` | `#64748B` |
| Test / AI tag | `bg-purple-50 text-purple-700 border-purple-200` | — | `#8B5CF6` |

Channel badges use a 10% tint of the text color: `background: rgba(59,130,246,0.1); color: #3B82F6` (SMS), `rgba(139,92,246,0.1)` / `#8B5CF6` (AI/email), `rgba(16,185,129,0.1)` / `#10B981` (call), `rgba(245,158,11,0.1)` / `#F59E0B` (promise), `rgba(100,116,139,0.1)` / `#64748B` (system).

---

## 3. Typography

Font: **DM Sans** for everything. **JetBrains Mono** (`font-mono`) only for IDs, phone numbers in dense tables and right-aligned figures.

| Role | Style |
|---|---|
| Page heading (inside page) | `text-2xl font-bold text-gray-900` (24/700) |
| Top bar title | 18px, 600, `#0F172A` |
| Section heading | 16px, 600, `#0F172A`, `mb-4` (16px) above its card |
| Modal title | `text-lg font-semibold text-gray-900` |
| Confirm dialog title | `text-base font-semibold text-gray-900` |
| KPI value | 28px, 700, `#0F172A` |
| KPI label | 14px, 500, `#64748B`, 4px above |
| KPI sub-label | 12px, `#94A3B8`, 2px above |
| Body, table, buttons, inputs | `text-sm` (14px) |
| Field label | `text-sm font-medium text-gray-700 mb-1` |
| Hint / error under field | `text-xs text-gray-400` / `text-xs text-red-600`, `mt-1` |
| Badge | `text-xs font-medium` (soft) or `text-[11px] font-semibold` (bordered pill) |
| Tiny tag (TEST) | `text-[10px] font-semibold` |
| Mobile nav label | `text-[10px] font-medium` |
| Footer meta ("Showing 20 of 340") | `text-sm text-gray-500` |

---

## 4. Spacing and radius

Base unit is 4px (Tailwind default scale). The numbers that repeat everywhere:

| Where | Value |
|---|---|
| Page padding | `p-4 sm:p-6` (16 → 24px) |
| Page width (list pages) | `max-w-7xl mx-auto` |
| Gap between page blocks (header, tabs, filters, table) | `mb-6` / `gap-6` (24px) |
| Gap inside a grid of cards | `gap-4` (16px) |
| Card padding | `p-6` (24px) |
| Filter panel padding | `p-4`, rows `space-y-3`, controls `gap-3` |
| Table cell | `px-4 py-3` |
| List row (activity feed) | `16px 24px` |
| Modal header and body | `p-6`, header has `border-b border-gray-200` |
| Confirm dialog | `px-5`, `pt-5` top, `pb-5` bottom |
| Button | `px-3 py-2` (default) · `px-4 py-2` (form) · `px-3 py-1.5` (in bars) · `px-2.5 py-1 text-xs` (row actions) |
| Icon-to-label gap in buttons | `gap-1.5` (small) or `gap-2` |

| Radius | Value | Used for |
|---|---|---|
| `rounded-md` | 6px | Row action buttons, dropdown items, tooltips |
| `rounded-lg` | 8px | Buttons, inputs, selects, dropdown menus, nav pills |
| `rounded-xl` | 12px | Cards, KPI tiles, chart cards, modals, toasts |
| `rounded-[14px]` | 14px | Tables, filter panels, bulk-action bar, empty/loading blocks on list pages |
| `rounded-2xl` | 16px | Confirm dialog |
| `rounded-full` | — | Badges, chips, logo, KPI icon circle |
| 24px | — | Top bar search pill |

Shadows are rare: none on resting cards; `hover:shadow-md` on clickable cards; `shadow-lg` on dropdown menus; `shadow-xl` on modals; `shadow-2xl` on confirm dialogs and toasts.

---

## 5. App shell

```
┌──────┬──────────────────────────────────────────────┐
│ navy │ Top bar (white, 56px, border-b #E2E8F0)        │
│ 56px │ Title (left) · search pill (center) · Sign out │
│      ├──────────────────────────────────────────────┤
│ logo │                                              │
│ icon │   main: bg-surface, p-4 sm:p-6               │
│ icon │   white cards with #E2E8F0 borders           │
│ icon │                                              │
└──────┴──────────────────────────────────────────────┘
Mobile (<768px): sidebar hidden, navy bottom nav 56px, main gets pb-16.
```

```tsx
<Sidebar />
<TopBar />
<main className="min-h-screen bg-surface pt-14 pb-16 md:pb-0 md:ml-14">{children}</main>
```

Login and public pages render without the shell (white page, centered).

**Sidebar** (`fixed top-0 left-0 h-screen w-14 bg-navy z-40 hidden md:flex flex-col`)
- Logo: 32px white circle, product initial in navy, 14px bold; 12px above, 16px below.
- Each nav item is a 56×56 cell with a 40×40 `rounded-lg` link in the middle; lucide icon 22px, always white.
- Active and hover both fill the pill with `#3B82F6`; `transition: background-color 150ms ease`.
- Labels only as tooltips: appear after 200ms hover, 8px right of the cell, `bg-ink text-white`, 13px/500, `padding 6px 12px`, `rounded-md` (6px), `box-shadow 0 2px 8px rgba(0,0,0,0.3)`.

**Mobile bottom nav** (`fixed bottom-0 inset-x-0 h-14 bg-navy md:hidden flex justify-around`): icon 20px + 10px label; active `#3B82F6`, inactive `#94A3B8`.

**Top bar** (`fixed top-0 left-0 md:left-14 right-0 h-14 z-50 bg-white border-b border-line px-4 md:px-6 flex items-center justify-between`)
- Left: page title, 18px/600, ink.
- Center: search pill, absolutely centered, `w-48 sm:w-72 md:w-96`, 40px tall, 24px radius, `border-[#CBD5E1]`, hover `#94A3B8`, focused `#3B82F6` + `box-shadow 0 0 0 2px rgba(59,130,246,0.1)`. Search icon 18px faint (accent when focused), placeholder 15px faint. ⌘K opens it, Esc closes it, 300ms debounce.
- Right: `Sign out` text button, `text-sm text-gray-600 hover:text-gray-900`, `LogOut` icon 16px.

**Nav for this project** (same component, our pages): Dashboard `LayoutDashboard`, Map `Map`, Farmers `Users`, Calls `Phone`, Prices `TrendingUp`, Settings `Settings`.

---

## 6. Buttons

| Kind | Classes |
|---|---|
| **Primary** | `inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors` |
| **Secondary** (white, bordered) | `inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-white border border-line text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-60` |
| **Ghost** (cancel) | `rounded-lg px-4 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-100` |
| **Danger** (confirm only) | `rounded-lg px-4 py-2 text-sm font-semibold text-white shadow-sm bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500` |
| **Row action** (inside tables) | `px-2.5 py-1 text-xs font-medium rounded-md bg-white text-gray-700 border border-gray-200 hover:bg-gray-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed` |
| **Toggle filter** off / on | off `px-3 py-2 text-sm rounded-lg border inline-flex items-center gap-1.5 bg-white text-gray-600 border-gray-200 hover:bg-gray-50` · on (alert) `bg-red-50 text-red-700 border-red-200` · on (neutral) `bg-gray-800 text-white border-gray-800` |
| **Text link button** | `text-xs font-medium text-gray-500 hover:text-gray-700` (e.g. "Clear all") |
| **Icon close** | `p-1 rounded-lg text-gray-400 hover:bg-gray-50 hover:text-gray-600 transition-colors`, `X` 20px |
| **Full-width form submit** | `w-full text-sm font-medium text-white rounded-lg px-3 py-2.5 bg-accent disabled:opacity-50` |

Rules: icons in buttons are 14px (`size={14}`). While busy, swap the icon for `<Loader2 size={14} className="animate-spin" />` and change the label ("Signing in..."). One primary button per view; everything else secondary or ghost. Red buttons only inside a confirm dialog; destructive actions in tables stay neutral row-action buttons.

---

## 7. Forms

- **Input**: `w-full text-sm border rounded-lg px-3 py-2 border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors disabled:opacity-50 disabled:bg-gray-50`
- **Error state**: `border-red-300 bg-red-50`, message `text-xs text-red-600 mt-1`.
- **Label**: `block text-sm font-medium text-gray-700 mb-1`; required star `text-red-500 ml-0.5`.
- **Search input with icon**: wrapper `relative`, icon `Search size={16}` at `absolute left-3 top-1/2 -translate-y-1/2 text-gray-400`, input `pl-9 pr-3 py-2`.
- **Select / dropdown trigger**: input classes + `appearance-none flex items-center justify-between gap-2 min-w-[150px]`, `ChevronDown size={14} text-gray-400`; selected count in `text-accent font-semibold`.
- **Dropdown menu**: `absolute z-20 mt-1 w-56 max-h-72 overflow-auto bg-white border border-line rounded-lg shadow-lg p-1`; items `flex items-center gap-2 px-2 py-1.5 text-sm rounded-md hover:bg-gray-50`.
- **Range filter**: label `text-xs font-medium text-muted`, two inputs `w-24`/`w-28`, en dash `text-gray-400` between.
- Vertical form spacing: `flex flex-col gap-4`.

---

## 8. Cards and KPI tiles

**Card**: `bg-white border border-gray-200 rounded-xl p-6`; clickable adds `cursor-pointer hover:shadow-md transition-shadow`.

**KPI row**: `grid grid-cols-2 lg:grid-cols-4 gap-4`. Each tile:

```tsx
<div className="bg-white border border-line rounded-xl p-6">
  <div className="w-10 h-10 rounded-full flex items-center justify-center mb-4"
       style={{ background: "rgba(59,130,246,0.1)" }}>
    <Users size={20} color="#3B82F6" />
  </div>
  <div style={{ fontSize: 28, fontWeight: 700, color: "#0F172A" }}>1,284</div>
  <div style={{ fontSize: 14, fontWeight: 500, color: "#64748B", marginTop: 4 }}>Registered farmers</div>
  <div style={{ fontSize: 12, color: "#94A3B8", marginTop: 2 }}>across 12 districts</div>
</div>
```

All KPI icons use the same blue circle; don't color-code tiles.

---

## 9. Tables

```tsx
<div className="bg-white border border-line rounded-[14px] overflow-hidden">
  <div className="overflow-x-auto">
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-line bg-gray-50">
          <th className="w-10 px-4 py-3"><input type="checkbox" /></th>
          <th className="text-left font-medium text-muted px-4 py-3 whitespace-nowrap">Name</th>
          <th className="text-left font-medium text-muted px-4 py-3 whitespace-nowrap hidden sm:table-cell">District</th>
          <th className="text-right font-medium text-muted px-4 py-3 whitespace-nowrap">Last sale (UGX)</th>
          <th className="text-right font-medium text-muted px-4 py-3 whitespace-nowrap">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors">
          <td className="px-4 py-3"><input type="checkbox" /></td>
          <td className="px-4 py-3 font-medium text-gray-900">Grace</td>
          <td className="px-4 py-3 text-gray-600 hidden sm:table-cell">Mbale</td>
          <td className="px-4 py-3 text-right font-mono text-gray-700 whitespace-nowrap">7,200</td>
          <td className="px-4 py-3">…row actions…</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
```

- Headers: sentence case, `font-medium text-muted`, left for text, right for numbers.
- First text column `font-medium text-gray-900`; other cells `text-gray-600`; numbers right-aligned (`font-mono` in dense tables).
- Alert values: `text-red-600 font-medium` (e.g. overdue, problem reported).
- Missing value: an em dash `—` in `text-gray-300`.
- Selected row: `bg-blue-50/50`. Row click opens the detail page; checkboxes and action cells use `stopPropagation`.
- Hide low-priority columns: `hidden sm:table-cell`, `hidden lg:table-cell`. Truncate long text with `max-w-[180px] truncate`.
- Footer under the table: `flex items-center justify-between mt-4` with `Showing X of Y` left and a secondary `Load more` button right.
- **Bulk-action bar** (when rows are selected, above the table): `flex items-center gap-3 flex-wrap mb-4 p-3 rounded-[14px] bg-blue-50 border border-blue-200`; count `text-sm font-medium text-blue-800`; small secondary buttons; `Clear selection` pushed right with `ml-auto text-sm font-medium text-blue-700 hover:text-blue-900`.
- **Notice banner**: `mb-3 px-3 py-2 rounded-lg bg-amber-50 border border-amber-200 text-sm text-amber-800 text-center`, links inside `font-medium underline`.

---

## 10. List page layout (header → tabs → filters → table)

```tsx
<div className="p-4 sm:p-6 max-w-7xl mx-auto">
  {/* Header */}
  <div className="flex items-center justify-between mb-6 gap-3 flex-wrap">
    <h1 className="text-2xl font-bold text-gray-900">Farmers</h1>
    {/* secondary "Download" button */}
  </div>

  {/* Tabs */}
  <div className="flex gap-1 border-b border-line mb-6">
    <button className="px-4 py-2 text-sm font-medium border-b-2 transition-colors border-accent text-accent">Active</button>
    <button className="px-4 py-2 text-sm font-medium border-b-2 transition-colors border-transparent text-gray-500 hover:text-gray-700">Closed</button>
  </div>

  {/* Filter panel */}
  <div className="bg-white border border-line rounded-[14px] p-4 mb-6 space-y-3">
    <div className="flex flex-col sm:flex-row sm:flex-wrap gap-3">…search, dropdowns, toggles…</div>
    {/* Active filter chips */}
    <div className="flex items-start justify-between gap-3 pt-1 border-t border-gray-100">
      <div className="flex flex-wrap gap-1.5 pt-2">
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-blue-50 text-blue-700 border border-blue-200">
          District: Mbale <button className="hover:text-blue-900"><X size={12} /></button>
        </span>
      </div>
      <button className="text-xs font-medium text-gray-500 hover:text-gray-700 whitespace-nowrap shrink-0 pt-2">Clear all</button>
    </div>
  </div>

  {/* Table (section 9) */}
</div>
```

Dashboard pages use `p-4 sm:p-6 flex flex-col gap-6` without the max width.

---

## 11. Badges, pills, chips, dots

- **Soft badge**: `inline-flex items-center text-xs font-medium rounded-full px-2 py-0.5` + a soft color from section 2.
- **Status pill** (bordered, can be a dropdown trigger): `inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold border` + a pill color from section 2; as a button add `hover:brightness-95` and `ChevronDown size={11} className="opacity-60"`.
- **Progress chip**: `inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border` + pill color.
- **Tiny tag**: `inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-semibold border bg-purple-50 text-purple-700 border-purple-200`.
- **Filter chip**: see section 10.
- **Status dot**: `inline-flex items-center gap-1.5 text-xs text-gray-500` with `h-2 w-2 rounded-full` in `bg-green-500` (live), `bg-blue-500` (connected), `bg-gray-300` (off), `bg-amber-500` (check).
- **Channel badge** (activity feed): inline style, 11px/600, `padding 2px 8px`, `border-radius 9999`, 10% tint background (section 2).

---

## 12. Lists (activity feed)

Section heading (16/600) above a card: `bg-white border border-line rounded-xl max-h-[400px] overflow-y-auto`. Each row: `flex items-center`, `padding 16px 24px`, `border-bottom 1px solid #F1F5F9` (none on last), hover background `#F8FAFC`, `transition: background 0.15s`, `cursor-pointer`, keyboard Enter opens it.

Row layout: channel badge + 14px direction/type icon (left, `gap-2 mr-4`) · name 14/600 ink + message 14 muted truncated (middle, `flex-1 min-w-0`) · relative time faint 12px (right).

Type icon colors: call `#10B981`, payment `#059669`, promise `#F59E0B`, note `#64748B`, outbound `#3B82F6`, inbound `#10B981`.

---

## 13. Overlays

**Modal**
```tsx
<div className="fixed inset-0 z-50 flex items-center justify-center">
  <div className="absolute inset-0 bg-black/50" onClick={onClose} />
  <div className="relative bg-white rounded-xl shadow-xl max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
    <div className="flex items-center justify-between p-6 border-b border-gray-200">
      <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      {/* icon close button */}
    </div>
    <div className="p-6">{children}</div>
  </div>
</div>
```

**Confirm dialog** (replaces `window.confirm`; Enter confirms, Esc cancels, confirm button gets focus)
- Backdrop `bg-navy/60 backdrop-blur-[2px]`, `z-[100]`.
- Panel `w-full max-w-sm rounded-2xl bg-white shadow-2xl ring-1 ring-black/5`.
- Brand bar: 24px navy logo circle + product name `text-xs font-semibold tracking-wide text-gray-400` + close `X` 18px `text-gray-300`.
- Body: 36px round icon (`bg-blue-50 text-accent` + `Info`, or `bg-red-50 text-red-600` + `AlertTriangle`), title `text-base font-semibold`, message `text-sm leading-relaxed text-gray-500`.
- Actions `flex justify-end gap-2 px-5 pb-5 pt-4`: ghost Cancel + `bg-accent hover:bg-blue-600` (or danger) confirm.

**Toast** (bottom center, `fixed inset-x-0 bottom-6 z-[110]`): `flex w-full max-w-sm items-start gap-3 rounded-xl bg-navy px-4 py-3 text-white shadow-2xl ring-1 ring-white/10`, text `text-sm leading-snug`, dismiss `X` 16px `text-white/40 hover:text-white`. Use for errors after actions ("Network error").

---

## 14. States

| State | Pattern |
|---|---|
| Page loading | Route `loading.tsx` with `Skeleton` blocks (`animate-pulse bg-gray-200 rounded`) shaped like the real layout |
| Table loading | `bg-white border border-line rounded-[14px] p-12 text-center` + spinner `animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto` |
| KPI loading | Same tile with skeletons: 40px circle, `w-20 h-7`, `w-28 h-4`, `w-32 h-3` |
| Empty | Inside the card: `flex flex-col items-center justify-center py-16 text-gray-400`, icon 48px `mb-4`, title `text-lg font-medium text-gray-500`, hint `text-sm text-gray-400 mt-1` ("Try adjusting your filters") |
| Empty chart / feed | Centered `#94A3B8` 14px sentence that says when data will appear |
| Error (route) | Centered `min-h-[50vh]`: `AlertCircle` 48px `text-red-300`, title `text-lg font-semibold text-gray-700`, message `text-sm text-gray-500`, secondary `Retry` button with `RefreshCw` 14px |
| Error (inline) | Card with centered faint text: "Failed to load … Please try refreshing." |

---

## 15. Charts (Recharts)

- Inside a card: `bg-white border border-line rounded-xl p-6`, fixed height 280px, section heading above.
- Area chart, line/area in `#3B82F6`, fill flat `rgba(59,130,246,0.06)`.
- `CartesianGrid stroke="#F1F5F9" vertical={false}`.
- Axes: `axisLine={false} tickLine={false}`, ticks `fontSize 12, fill #94A3B8`; Y axis `width={45}`, percentages as `0/25/50/75/100%`.
- Custom tooltip: white, `border 1px solid #E2E8F0`, radius 8px.
- Margins `{ top: 15, right: 20, left: 20, bottom: 0 }`. Pad sparse series to 14 days so data anchors left.

---

## 16. Login page

White page, centered column `max-w-[380px]`: 48px navy circle with the initial (`mb-4`), `text-xl font-semibold text-gray-900` "Sign in to …", `text-sm text-gray-500 mt-1` subline, `mb-8`; then a Card with the form (`flex flex-col gap-4`), full-width accent submit; footnote `text-xs text-center text-gray-400 mt-6`.

---

## 17. Icons and motion

- Icons: `lucide-react` only. Sizes: nav 22 (mobile 20), search 18, input icon 16, button icon 14, chip remove 12, KPI 20, empty/error 48.
- Transitions: `transition-colors` (150ms) on every interactive element; `transition-shadow` on clickable cards. Tooltip delay 200ms. Search debounce 300ms. No other animation besides `animate-spin` and `animate-pulse`.

---

## 18. Do and don't

- Do put content in white cards with a 1px `#E2E8F0` border on the `bg-surface` page. Don't use shadows to separate resting cards.
- Do keep color for meaning (status, alerts, AI). Chrome stays navy, white and gray; the only bright color is the blue accent.
- Do right-align numbers and show money with its currency (UGX). Don't center table text.
- Do write labels in sentence case ("Last sale", "Clear all").
- Don't add dark mode, gradients, new fonts or new radii. If a component isn't here, build it from these tokens and match the closest OrbitFlow component.
