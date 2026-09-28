---
name: High-Density Observability
colors:
  surface: '#111124'
  surface-dim: '#111124'
  surface-bright: '#38374c'
  surface-container-lowest: '#0c0c1f'
  surface-container-low: '#1a1a2d'
  surface-container: '#1e1e31'
  surface-container-high: '#28283c'
  surface-container-highest: '#333347'
  on-surface: '#e2e0fb'
  on-surface-variant: '#bfc7d5'
  inverse-surface: '#e2e0fb'
  inverse-on-surface: '#2f2e43'
  outline: '#8a919e'
  outline-variant: '#404753'
  surface-tint: '#a2c9ff'
  primary: '#a2c9ff'
  on-primary: '#00315b'
  primary-container: '#1496ff'
  on-primary-container: '#002d53'
  inverse-primary: '#0060a8'
  secondary: '#c7bfff'
  on-secondary: '#2b009e'
  secondary-container: '#442ac0'
  on-secondary-container: '#b8afff'
  tertiary: '#ffb784'
  on-tertiary: '#4f2500'
  tertiary-container: '#e47500'
  on-tertiary-container: '#492100'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d3e4ff'
  primary-fixed-dim: '#a2c9ff'
  on-primary-fixed: '#001c38'
  on-primary-fixed-variant: '#004881'
  secondary-fixed: '#e5deff'
  secondary-fixed-dim: '#c7bfff'
  on-secondary-fixed: '#180065'
  on-secondary-fixed-variant: '#4226bd'
  tertiary-fixed: '#ffdcc6'
  tertiary-fixed-dim: '#ffb784'
  on-tertiary-fixed: '#301400'
  on-tertiary-fixed-variant: '#713700'
  background: '#111124'
  on-background: '#e2e0fb'
  surface-variant: '#333347'
  shell-bg: '#141419'
  surface-elevated: '#212135'
  surface-hover: '#2A2A42'
  border-subtle: '#323248'
  border-contrast: '#42425E'
  text-primary: '#F0F0F5'
  text-muted: '#A0A1C0'
  text-disabled: '#686985'
  status-error: '#DA7288'
  status-warning: '#E9B86E'
  status-pass: '#47AE8F'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 26px
    letterSpacing: -0.015em
  headline-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 22px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 18px
    letterSpacing: -0.005em
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-md:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.01em
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 14px
  code-num:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 0.5rem
  margin: 0.75rem
  space-xs: 0.25rem
  space-sm: 0.375rem
  space-md: 0.5rem
  space-lg: 0.75rem
  space-xl: 1rem
---

## Brand & Style

This design system targets software engineers, ML infrastructure operators, and autonomous agent architects debugging complex agentic execution pipelines. It rejects the ambient glowing gradients, glassmorphic blurs, and sparkle motifs common in consumer AI applications. Instead, it embodies a technical, surgical aesthetic rooted in observability rigor: high data density, structured hierarchy, deterministic alignment, and instant legibility across deeply nested execution graphs.

The style blends the functional efficiency of modern issue tracking with the robust analytical frameworks of telemetry dashboards. Layouts prioritize maximized screen real estate, precise single-pixel delineations, and immediate scanning of anomalies, runtime durations, token expenditures, and call hierarchies.

## Colors

The palette operates in a native dark environment calibrated for low eye strain across extended debugging sessions. 

- **Primary Canvas & Shell:** `#141419` grounds the global sidebar and navigational frame, while `#19192C` serves as the primary canvas.
- **Surfaces & Layers:** `#212135` forms card surfaces, data tables, split-inspectors, and trace detail drawers. Hover and active states elevate with `#2A2A42`.
- **Structural Lines:** Separation relies entirely on 1px crisp borders (`#323248` for general dividers; `#42425E` for active panes, splitters, and keyboard-focused regions).
- **Brand & Interaction:** `#1496FF` indicates primary interactive targets, current execution spans, and active filtering tags. `#7D6AFA` distinguishes secondary categorizations such as auxiliary tool invocations and memory retrieval cycles.
- **Diagnostic Semantics:** Monitored states use specialized, low-glare indicators: `#DA7288` for agent failure, exceptions, and schema violations; `#E9B86E` for latency degradation and fallback retries; `#47AE8F` for verified completions and compliant evaluations.

## Typography

Typography balances rapid scanning with dense metric consumption. **Inter** powers primary structural framing, labels, navigation, and state summaries. **JetBrains Mono** governs all runtime payloads, token metrics, trace hashes, span names, JSON/YAML inspection, and tabular metric grids.

All numerical data—such as latencies, token counts, error rates, and byte measurements—must apply `font-variant-numeric: tabular-nums` and align flush right in tables. Dense body levels (11px–13px) minimize scrolling and allow complex execution trees to be analyzed side-by-side with code and telemetry.

## Layout & Spacing

The layout is built around a flexible, multi-pane workbench optimized for widescreen displays, supporting collapsible navigation rails, resizable tree panels, and contextual detail drawers.

- **Grid & Units:** Anchored strictly to an 8px base rhythm with 4px sub-increments for compact UI states (`space-xs` = 4px, `space-sm` = 6px, `space-md` = 8px, `space-lg` = 12px, `space-xl` = 16px).
- **Density:** Screen composition avoids loose padding. Table rows use `py-1.5 px-2.5` (`space-sm` / `space-md`), creating compact listings that fit dozens of trace cycles above the fold.
- **Responsiveness:** On monitors under 1280px, multi-column waterfall charts collapse into sequential tabs. Split inspect drawers expand to full-width modals on mobile viewports (<768px), maintaining developer-level inspection fidelity through sticky metric headers and horizontally scrollable code containers.

## Elevation & Depth

Visual hierarchy is communicated entirely through tonal layering and structural micro-borders, without drop shadows or ambient blurs.

- **Stacking Tiers:**
  - **Base / Shell:** `#141419` for outer frames and toolbars.
  - **Work Surface:** `#19192C` for timeline tracks, waterfall tracks, and active canvas areas.
  - **Elevated Surfaces:** `#212135` for analytical cards, node details, and trace tables.
  - **Interactive Popovers & Flyouts:** `#2A2A42` bounded by high-contrast `#42425E` borders.
- **Separation:** Every structural container uses an explicit 1px boundary (`#323248`). Selected traces, tree nodes, or active rows gain immediate focus through a 1px solid `#1496FF` outline or border replacement.

## Shapes

The design uses a restrained, compact corner geometry (`0.25rem` / 4px base radius) across interactive elements. 

- **Inputs, Buttons, and Cards:** Formed with a 4px corner radius to preserve architectural alignment and clean lines against high-density grids.
- **Status & Span Pills:** Micro-badges, span duration tags, and HTTP code pills use a slightly softer 6px radius (`rounded-lg`), ensuring clear separation from standard structural containers without turning into fully rounded pills.

## Components

### Buttons
- **Primary:** Solid `#1496FF` background with `#F0F0F5` bold text. Subtle hover state at `#38A7FF`. Pressed state scales down to `0.99`.
- **Secondary / Ghost:** Transparent background with a 1px `#323248` border. Hover background shifts to `#212135` with `#42425E` border.
- **Sizes:** Compact heights of 24px (micro) and 28px (default), padding `px-2` to `px-3`, paired with 12px Inter medium typography.

### Data Tables & Trace Lists
- Headers use 11px uppercase Inter (`#A0A1C0`) with subtle sort arrows and `#323248` bottom borders.
- Row heights are locked to 30px with inline hover highlights (`#2A2A42`). Selected rows display a 2px left border accent in `#1496FF`.
- Numerical metrics (duration, memory, tokens) utilize tabular-nums JetBrains Mono and right-align with column edges.

### Status Chips & Pills
- Micro badges display execution states (e.g., `200 OK`, `LLM_TIMEOUT`, `RETRY_EXCEEDED`).
- Backgrounds use 10% opacity tints of the semantic colors (`#DA7288`, `#E9B86E`, `#47AE8F`), bounded by a matching 1px solid stroke at 30% opacity, paired with high-contrast text.

### Waterfall Trace View
- Horizontal gantt bars for span timelines (LLM inferences, tool calls, vector lookups).
- Minimum bar width is clamped at 2px to guarantee sub-millisecond trace visibility.
- Nested tree indentations use connected guides with 1px `#323248` lines.

### Inputs & Search Filters
- Dense 28px height, 1px `#323248` borders, and `#19192C` backgrounds. Focus transitions instantly to a 1px `#1496FF` stroke.
- Syntax-aware query filters (e.g., `duration:>200ms status:error agent:planner`) display key-value tokens with JetBrains Mono chips.