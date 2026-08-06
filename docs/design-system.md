# Nexus Design System — Paper / Ink

> **Source of truth:** `frontend/css/style.css`. Theme tokens live under `[data-theme="light"]` (PAPER) and `[data-theme="dark"]` (INK). This document is the reference for the design language — keep it in sync when tokens change.

## 1. Philosophy

Nexus reads like **premium electronic paper** in a high-end desktop productivity tool:

- The chrome is **monochrome**. `--accent` is *ink* — a near-black in PAPER, a soft white in INK — never a brand hue.
- **Color is rare and semantic** — used only to signal status (success / warning / danger / info / reasoning).
- **Expense comes from spacing, typography, alignment, hierarchy and interaction quality** — not gradients, glow, glass, heavy shadows, or excessive animation.
- **Never pure `#FFF` / `#000`** as a surface fill. PAPER uses warm off-whites; INK uses deep charcoals.

## 2. Themes

Themes are applied as a `data-theme` attribute on `<html>`:

| Theme | Attribute | Feel |
|---|---|---|
| PAPER (light) | `data-theme="light"` | warm paper whites, thin borders, graphite ink |
| INK (dark) | `data-theme="dark"` | deep charcoal, graphite, soft white |

`system` resolves to one of the two at runtime (Settings → Theme). The switch is animated with a 200 ms background/color transition on `html`.

## 3. Color Tokens

### 3.1 Chrome (monochrome)

| Token | PAPER (light) | INK (dark) | Purpose |
|---|---|---|---|
| `--accent` | `#3A342B` | `#E6E4DE` | ink — primary action fills, focus, active states |
| `--accent-rgb` | `58,52,43` | `230,228,222` | `rgba(var(--accent-rgb), X)` translucent ink |
| `--accent-soft` | `#6B6355` | `#C9C6BD` | muted ink (hover text, secondary accent) |
| `--on-accent` | `#FBFAF7` | `#201D17` | text on accent fill |

### 3.2 Surfaces

| Token | PAPER (light) | INK (dark) | Purpose |
|---|---|---|---|
| `--bg-base` | `#F4F2ED` | `#121315` | page ground |
| `--bg-surface` | `#FBFAF7` | `#191A1D` | app chrome (sidebar, topbar) |
| `--bg-elevated` | `#FEFDF9` | `#202125` | raised cards, inputs |
| `--bg-elevated-2` | `#EDEAE3` | `#28292E` | wells, inset fields, active rows |
| `--bg-hover` | `#F1EFEA` | `#26272B` | hover fill |
| `--bg-active` | `#E7E3D9` | `#2E2F34` | pressed fill |

**Semantic surface aliases** keep layering consistent across components:

| Alias | Maps to | Used for |
|---|---|---|
| `--surface-page` | `--bg-base` | page ground |
| `--surface-panel` | `--bg-surface` | sidebar, topbar, suggestion cards |
| `--surface-raised` | `--bg-elevated` | modals, popovers, dialogs, dropdowns |
| `--surface-sunken` | `--bg-elevated-2` | active rows, wells, inset fields |

### 3.3 Text

| Token | PAPER (light) | INK (dark) | Purpose |
|---|---|---|---|
| `--text-primary` | `#201D17` | `#EAE9E4` | body / headings |
| `--text-secondary` | `#5A554A` | `#A3A29B` | subtext, metadata |
| `--text-tertiary` | `#857E70` | `#6E6D66` | hints, placeholders |
| `--text-disabled` | `#B4AD9E` | `#4A4A46` | disabled controls |

### 3.4 Borders & shadows

| Token | PAPER (light) | INK (dark) |
|---|---|---|
| `--border` | `#DCD7CC` | `#2C2D32` |
| `--border-strong` | `#C7C0B1` | `#3A3B41` |
| `--border-soft` | `#E6E2D8` | `#24252A` |

Shadows are depth cues only: `--shadow-1` (hairline), `--shadow-2` (cards/popovers), `--shadow-3` (modals/dialogs).

### 3.5 Semantic color (rare, status only)

| Token | PAPER (light) | INK (dark) | Use |
|---|---|---|---|
| `--success` | `#2E9E5B` | `#54C07E` | connected, copied |
| `--warning` | `#A97A13` | `#E2A13E` | pinned, slow |
| `--danger` | `#C24343` | `#EF6B6B` | stop, delete, errors |
| `--danger-strong` | `#A63636` | `#F28A8A` | danger hover |
| `--on-danger` | `#FFF9F8` | `#3A1515` | text on danger fill |
| `--info` | `#2F6FB3` | `#6EA8E6` | informational |
| `--reasoning` | `#7752CE` | `#A78BFA` | reasoning-effort indicator |

Each has a matching `-soft` translucent variant for tinted backgrounds.

## 4. Typography

| Role | Family | Weights |
|---|---|---|
| Display | **Sora** | 400–800 |
| Body | **Inter** | 400–700 |
| Mono | **JetBrains Mono** | 400–700 |

**Scale:** base body 14.5 px. The Settings font-size maps to `--font-scale` (`sm .92` / `md 1` / `lg 1.1`) and is applied via `calc(…px * var(--font-scale))` on message content, composer textarea, suggestion cards and welcome copy.

**Hierarchy:** primary (body, `--text-primary`), secondary (metadata, `--text-secondary`), muted (hints/placeholders, `--text-tertiary`), disabled (`--text-disabled`). Headings use Sora with tightened `letter-spacing`; h1/h2 carry `font-weight:700`.

## 5. Shape & motion

| Token | Value |
|---|---|
| `--radius-sm / md / lg / xl` | `8 / 14 / 20 / 26` px |
| `--dur-fast` | 120 ms |
| `--dur-med` | 200 ms |
| `--ease` | `cubic-bezier(.4,0,.2,1)` |

Micro-interactions stay within **120–200 ms** and use the shared easing curve.

## 6. Interaction states

Every control defines all five states:

| State | Guidance |
|---|---|
| default | token fill + 1 px border |
| hover | `--bg-hover` (or accent-strong fill on primary actions), border → `--border-strong` |
| focus-visible | `outline:3px solid var(--focus-ring)` (or an accent box-shadow ring on round buttons); never removed for keyboard users |
| active/pressed | `transform:scale(.92–.97)` + `--bg-active` |
| disabled | `--bg-elevated-2` fill, `--text-disabled`, `cursor:not-allowed`, no shadow |

Primary actions (send, stop, auth) additionally carry `:focus-visible` box-shadow rings and, under `forced-colors`, a `CanvasText` outline.

## 7. Iconography

- **Font Awesome 6** glyphs throughout.
- Icons inherit text or accent color — **monochrome**, no emoji in chrome.
- Icon buttons are 32–36 px with `--radius-sm`, transparent fill, `--bg-hover` on hover.

## 8. Accessibility

- Focus is always visible (`:focus-visible`); round buttons use box-shadow rings plus a `forced-colors` outline fallback.
- Live regions: chat messages `aria-live="polite"`, toasts `role="status"`.
- `prefers-reduced-motion: reduce` collapses all animation to ~0 ms; the Settings "animations" toggle sets `data-animations="off"` for a full kill-switch.
- Contrast is checked against WCAG AA; semantic tokens were chosen to hold 4.5:1 on their fills.

## 9. Component notes

| Component | Signature |
|---|---|
| **Composer** | translucent `--composer-bg`, 1 px border → `--border-strong` on hover, ink border + 3 px ring on focus-within; send button is a 34 px ink circle (Stop swaps to a danger circle with `--danger-strong` hover); `kbd` shortcut hints in mono |
| **Sidebar** | `--surface-panel`, collapsible to a 60 px icon rail; active chat row uses `--surface-sunken` + 3 px ink indicator |
| **Topbar** | `--surface-panel`, uniform 32 px icon buttons, model selector + provider status pill |
| **Suggestion cards** | `--surface-panel` grid, hover lifts 1 px with `--shadow-1` |
| **User messages** | compact monochrome bubble (`--user-bubble`), no color chrome |
| **Markdown** | clean heading ladder, bordered code blocks with copy buttons, `overflow-wrap` + scrollable pre/table regions |

## 10. Changing tokens

1. Edit values under the matching `[data-theme="…"]` block in `frontend/css/style.css`.
2. Add shared aliases (e.g. surface hierarchy) in `:root`.
3. Bump the `css/style.css?v=` cache-bust in `frontend/index.html`.
4. Update this document and the token table in `ARCHITECTURE.md` §4.5.
