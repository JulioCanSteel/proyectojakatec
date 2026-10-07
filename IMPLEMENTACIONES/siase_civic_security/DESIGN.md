---
name: SIASE Civic Security
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#434655'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#737686'
  outline-variant: '#c3c6d7'
  surface-tint: '#0053db'
  primary: '#004ac6'
  on-primary: '#ffffff'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#b4c5ff'
  secondary: '#565e74'
  on-secondary: '#ffffff'
  secondary-container: '#dae2fd'
  on-secondary-container: '#5c647a'
  tertiary: '#ab0b1c'
  on-tertiary: '#ffffff'
  tertiary-container: '#cf2c30'
  on-tertiary-container: '#ffecea'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#dae2fd'
  secondary-fixed-dim: '#bec6e0'
  on-secondary-fixed: '#131b2e'
  on-secondary-fixed-variant: '#3f465c'
  tertiary-fixed: '#ffdad7'
  tertiary-fixed-dim: '#ffb3ad'
  on-tertiary-fixed: '#410004'
  on-tertiary-fixed-variant: '#930013'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '800'
    lineHeight: 44px
  display-lg-mobile:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '800'
    lineHeight: 36px
  headline-lg:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
  headline-md:
    fontFamily: Inter
    fontSize: 22px
    fontWeight: '700'
    lineHeight: 28px
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  title-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 22px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 14px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-mobile: 0.75rem
  margin: 1.5rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style

The design system is constructed for mission-critical civic intelligence, high-stakes municipal response, and personal citizen safety. It embodies an institutional authority softened by radical clarity, responsiveness, and calm urgency. The interface minimizes cognitive friction under acute stress, providing immediate situational comprehension across dense urban environments.

The visual direction merges **Modern Civic-Tech** with **High-Contrast Utilitarianism**:
- **Clarity Over Ornamentation:** Visual density is managed through strict spatial rhythm and structural borders rather than heavy illustrative clutter.
- **Urgent Hierarchy:** Color is deployed as a functional state machine—amber cautions, emerald confirmations, and acute crimson panics stand out aggressively against deeply grounded slate-navy surfaces.
- **Empowering Tactility:** Interactive elements carry generous physical clearance, bold contrasts, and unambiguous affordances designed for one-handed operation during mobility or physical distress.

## Colors

The color architecture is built around immediate legibility, strict AAA accessibility compliance, and unmistakable emergency feedback loops.

### Key Palettes & State Tokens
- **Civic Primary (`#2563EB`):** Used for verified civic actions, interactive highlights, primary progress bars, and authoritative interaction points.
- **Civic Anchor & Dark Accent (`#0F172A`):** Deep navy slate providing grounding structural contrast for app bars, bottom sheets, headers, and mission-control data cards.
- **Emergency Crimson (`#EF4444`):** Restricted solely to panic triggers, live threat beacons, acute SOS activations, and high-severity incident broadcasts.
- **Cautionary Amber (`#F59E0B`):** Denotes impending hazards, geo-fenced perimeters, warnings, and unverified citizen reports pending dispatch triage.
- **Safe Emerald (`#10B981`):** Signifies resolved events, active patrol safe-zones, confirmed citizen safety status ("I am safe"), and operational field personnel.
- **Neutral Foundation:** Anchored in a refined slate spectrum (`#0F172A` to `#F8FAFC`). Light mode uses a clinical white-slate canvas (`#F8FAFC`) with razor-sharp borders (`#E2E8F0`), preventing optical glare under direct daylight.

### Semantic Application Rules
1. Never mix status pigments: amber and crimson must never share a single component frame.
2. Background tints for status components must maintain a strict 10% opacity wash of their respective status hue to guarantee 7:1 contrast ratios with text overlays.

## Typography

The typography uses Inter across all levels to maintain extreme legibility under adverse conditions (glare, reduced vision, physical motion). Its tall x-height, wide apertures, and distinct glyph designs prevent misread coordinates, street names, and critical alert instructions.

### Hierarchy & Usage
- **Display & Large Headlines:** Used for SOS countdown screens, single-action alert headers, and primary biometric validation screens.
- **Headlines & Titles:** Set with tighter tracking (-0.02em) in semi-bold and bold weights to organize dynamic incident streams, alert summaries, and municipal bulletins.
- **Body:** Neutral slate (`#334155` on light) optimized for scanning field notes, legal notices, and multi-step evacuation procedures.
- **Labels & Microcopy:** Crisp, medium-to-bold weights used for timestamps, live telemetry, GPS coordinates, and acute alert badges. Label microcopy (`label-sm`) employs uppercase styling with +0.05em tracking for rapid peripheral identification.

## Layout & Spacing

The layout is built around a mobile-first, single-column fluid constraint with strict vertical flow and anchored thumb zones for life-safety interactions.

### Layout Model
- **Grid Architecture:** 4-column fluid layout on mobile (360px–599px) with 12px gutters and 16px margins; 8-column layout on tablet views with 16px gutters and 24px margins.
- **Ergonomic Safe Zones:** Primary panic, trigger, and report interactions are permanently anchored in the bottom 35% of the mobile viewport ("Active Reach Zone"). Information feeds and passive map layers populate the upper 65%.
- **Spacing Scale:** Built on a rigorous 4px baseline rhythm (`space-xs` = 4px, `space-sm` = 8px, `space-md` = 16px, `space-lg` = 24px, `space-xl` = 32px).
- **Target Spacing:** Every actionable component (SOS button, pin report, toggle) reserves a minimum physical touch footprint of 48×48px, padded by at least 8px (`space-sm`) of boundary clearance to eliminate mis-taps during transit or emergencies.

## Elevation & Depth

Visual hierarchy relies on **structural layered planes** combined with **subtle, high-precision ambient shadows** rather than dramatic skeuomorphic depth.

### Tonal Stratification
- **Ground Floor (Canvas):** `#F8FAFC` base surface for scrollable operational content.
- **Tier 1 (Surface Cards):** Pure `#FFFFFF` surface framed with a 1px crisp outline (`#E2E8F0`). Elevated by an ambient shadow: `0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04)`.
- **Tier 2 (Floating Action Triggers & Sheets):** Bottom navigation modules, alert notifications, and filter pills carry `0 8px 16px -4px rgba(15, 23, 42, 0.08), 0 4px 6px -2px rgba(15, 23, 42, 0.03)`.
- **Tier 3 (Urgent Modals & Panic Overlays):** Modal dialogs and active incident banners cut through background context using deep 32px diffused navy backdrops (`rgba(15, 23, 42, 0.6)`) paired with high-elevation drop structures (`0 20px 25px -5px rgba(15, 23, 42, 0.18)`).

### Outline & Focus Reinforcement
Cards, inputs, and chips feature crisp 1px borders in standard states. When active, in danger, or focused, the border transitions to a 2px high-visibility ring corresponding to the semantic state (e.g., `#2563EB` for focus, `#EF4444` for emergency triage).

## Shapes

The design system uses a **Soft (Level 1)** geometric shape philosophy. This balances institutional civic reliability with modern digital utility, avoiding childish hyper-rounded aesthetics while eliminating sharp, hostile industrial corners.

### Radii Hierarchy
- **Base Components (`0.25rem` / 4px):** Badges, notification pills, technical metadata tags, progress meters, and inline validation icons.
- **Medium Elements (`0.5rem` / 8px):** Primary buttons, interactive inputs, dropdown selectors, situational chips, and standard list row touch targets.
- **Large Containers (`0.75rem` / 12px):** Incident summary cards, emergency dispatch banners, map overlay drawers, and media preview wrappers.
- **Pill Exception (`9999px`):** Reserved exclusively for live status chips (e.g., "LIVE PATROL", "DISPATCHED"), category selector pills, and floating action anchor handles.

## Components

### Buttons
- **Primary Civic Button:** 48px height, solid `#2563EB` fill, white `label-lg` text, 8px corner radius. In hover/active states, transitions to `#1D4ED8`.
- **Emergency Panic Button:** 64px height or circular 80px floating action target. High-visibility `#EF4444` background with a concentric 4px pulsing ring (`rgba(239, 68, 68, 0.3)`). Bold white typography, reinforced with tactile haptic feedback on press.
- **Secondary Neutral Button:** Crisp border (`#CBD5E1`), pure white surface, `#0F172A` text.
- **Destructive/Critical Action:** Bordered in `#EF4444` with `#EF4444` label on transparent base.

### Chips & Status Badges
- **Emergency / Hazard Chips:** Height 24px, pill-shaped (`9999px`), 1px solid border. 
  - *Critical:* Background `rgba(239, 68, 68, 0.1)`, border `#EF4444`, text `#B91C1C`.
  - *Caution:* Background `rgba(245, 158, 11, 0.1)`, border `#F59E0B`, text `#B45309`.
  - *Verified Safe:* Background `rgba(16, 185, 129, 0.1)`, border `#10B981`, text `#047857`.
- **Interactive Filtering Chips:** 36px touch height, 8px radius, `#F1F5F9` neutral surface. Active selection swaps to `#0F172A` background with crisp white text.

### Form Inputs & Controls
- **Text Inputs:** Minimum 48px height, 8px radius, `#FFFFFF` interior, 1px border (`#CBD5E1`). Focus ring expands to 2px solid `#2563EB` with zero blur offset. Placeholder text in `#94A3B8`.
- **Checkboxes & Radios:** 20×20px container (wrapped in a 48×48px transparent touch boundary). Active state fills `#2563EB` with a high-contrast white glyph.

### Incident Cards & Lists
- **Live Alert Feed Card:** `#FFFFFF` background, 12px radius, 1px solid `#E2E8F0` border. Features an absolute 4px-wide status indicator bar running down the entire left edge (Crimson, Amber, or Emerald) to communicate severity without requiring text parsing.
- **Citizen Directory / Log Lists:** Separated by 1px dividers (`#F1F5F9`), utilizing 56px minimum row heights for frictionless scanning and zero accidental activations.

### Specialized Civic Security Components
- **Broadcast Alert Banner:** Persistent top banner with high-contrast text and a left-aligned warning beacon icon. Pushes underlying view down without masking navigation controls.
- **Geo-Fence Threat Radar Indicator:** Compact HUD overlay component containing real-time distance metrics (e.g., "300m away"), current perimeter status, and quick-dial buttons to municipal emergency relays.