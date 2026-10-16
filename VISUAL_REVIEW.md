# Visual review — 16 October 2026

## Scope and evidence

Reviewed all eight views in `ui-lovelace.yaml`, the custom energy-flow card, preview, frontend resource configuration, and existing UI documentation. Inspected the supplied desktop preview and the running local preview at 390 × 844 in light and dark modes, including missing telemetry. The full authenticated Home Assistant dashboard was not rendered; findings about its layout are based on YAML. No operational configuration or dashboard code was changed.

## Overall direction

Use the energy-flow card as the visual starting point: restrained surfaces, clear numbers, consistent device colors, and thin outline icons. Its normal-state design is much more cohesive than the surrounding dashboard definitions. Preserve its keyboard interactions, reduced-motion support, explicit unavailable readings, and theme inheritance.

The largest improvement will come from reducing repetition and establishing a clear reading order. Daily monitoring, explaining automated decisions, configuration, and troubleshooting currently compete for attention.

## Prioritized findings

| Priority | Finding and evidence | Suggested change |
| --- | --- | --- |
| High | Phone offline state visibly overflows device cards and crowds footer values. The container rule in `www/energy-flow-card.js:64` sets `.node strong` to 27px after `.missing strong` sets 16px. | Add a mobile missing-value rule after the general mobile typography; use a short visible placeholder with a clear unavailable label. Allow the footer to become one column when labels need space. Test long labels and increased text size. |
| High | `PARTIAL DATA` retains the same green pill as healthy readings (`www/energy-flow-card.js:60` and `:66`). The unavailable battery bar also resembles an empty battery. | Use an amber icon and badge for partial telemetry and a neutral unknown battery track. Distinguish unknown SoC from 0%. Consider stale-data status only with a reliable freshness signal; unchanged values alone do not establish staleness. |
| High | Overview repeats SoC, power, mode, and target across flow, gauges, status, and decision Markdown (`ui-lovelace.yaml:18–92`). | Retain one primary flow visualization, a compact current-status row, one sentence explaining the decision, the price outlook, and a small controls group. Move calculation tables into decision details. |
| High | Quick Controls renders operational flags as ordinary input-boolean entities (`ui-lovelace.yaml:197–218`). Charging Active, Discharge Limited, Car Solar Boost Active, and Car Cheap Grid Active visually resemble intentional user controls. | Show these flags as read-only status indicators. Keep user intent controls distinct: automation enabled, manual charging, target, and smart car charging. Hide the manual target unless manual charging is relevant. |
| Medium | Eight top-level views include Debug and Algorithm Debug. Energy Flow repeats the Overview visualization (`ui-lovelace.yaml:13`, `:254`, `:873`, `:1052`). | Use four primary destinations: Overview, Energy, Charging, Settings. Energy contains flow details and solar; Charging contains battery/car decisions and history. Link to diagnostic subviews from Settings. |
| Medium | Overview uses default view layout; Energy Flow uses a panel with a vertical stack. The custom card changes layout at its container width, so it may render its tall mobile form within a narrow desktop column. | Evaluate a Sections layout with an explicitly wide flow region and predictable section order. Use one column on phones and two or three on wider screens. Verify inside Home Assistant; the standalone preview does not establish desktop dashboard placement. |
| Medium | Price units and visual conventions vary. Overview charts use ct/kWh, while entity lists expose raw sensor units; Profitability Factors combines price entities with a percentile (`ui-lovelace.yaml:565`). | Present prices consistently in ct/kWh, energy in kWh, power adaptively in W/kW, and SoC as whole percentages. Keep price and percentile on separate plots or clearly labeled axes. Convert display values without changing calculation units. |
| Medium | Price vs Charging Decision overlays two broad state areas with three numeric series (`ui-lovelace.yaml:501–562`). Solar Forecast Impact mixes energy with binary flags (`:579`). | Put mode transitions in a slim timeline below the numeric chart. Use aligned time ranges and a clear now marker. Keep stepped price/target lines and distinguish forecast from actual using line style as well as color. |
| Medium | Solar uses a red low-production gauge and different maximums between Overview (7000 W) and Solar (6800 W), at `ui-lovelace.yaml:35` and `:318`. | Show generation as a neutral or amber power tile; nighttime zero is expected. Reserve red for faults. If gauges remain, use a consistent, explicitly justified scale. Keep battery low-charge warnings separate from generation colors. |
| Medium | Car settings have long instructional row names; the first battery settings card combines targets, prices, consumption, and hardware (`ui-lovelace.yaml:731–771`, `:810–841`). | Split into short groups: Battery reserve, Price rules, Household schedule, Car solar boost, Cheap-grid charging, Hardware. Put explanations below controls; display wake/sleep settings as readable times rather than decimal hours. |
| Medium | Manual scripts and Modbus actions are presented as similar list rows (`ui-lovelace.yaml:782`, `:1015`). | Separate everyday overrides from advanced service actions. Use explicit action labels and visible active-override state. For actions such as forced full recharge, describe the effect in an action-specific confirmation. |
| Low | Emoji titles mix with MDI device icons. Technical terms and internal flags appear in everyday views. Debug still emphasizes Sankey although the visible diagram was replaced (`ui-lovelace.yaml:884`). | Standardize on outline icons and short sentence-case headings. Use one interface language. Rewrite algorithm explanations in ordinary language and rename legacy diagnostics to describe the sensors they actually check. |

## Proposed Overview reading order

1. A compact status strip: operating mode, battery SoC/target, current price, grid/telemetry health. Show an actionable alert above it when necessary.
2. Energy flow as the main visual. Use a shorter summary variant on phones, with a link to the expanded diagram.
3. A one-sentence decision explanation derived from the existing decision data, plus a Details link. Avoid exposing raw enum names.
4. Price and solar outlook with the next relevant charging window highlighted only when supported by existing decision data.
5. Car status and user controls, keeping system-controlled flags read-only.
6. A compact monthly price-advantage summary and link to history. Preserve its existing caveat about losses, wear, and export opportunity cost.

## Shared visual rules

- Use solar amber, grid blue, battery teal, house coral, and car violet consistently across diagrams, legends, and detail tiles. Use separate semantic warning/error colors.
- Use shared spacing increments such as 8, 16, and 24px, consistent card corners, and restrained borders. Reconcile the custom card with native card styling through shared theme tokens where practical.
- Use large tabular numbers for primary values, readable secondary text, short headings, and a minimum 44px target for frequently used touch actions.
- Keep positive and negative direction explicit with words such as Importing/Exporting and Charging/Discharging. Do not rely on animation or color alone.
- Keep normal states quiet; show explanations and alerts when they affect a decision. Provide plain-language recovery guidance for unavailable telemetry.
- Give the expanded panel a comfortable content width; check that diagrams, histories, and detail cards align on wide screens.

## Suggested implementation order

1. Repair phone missing-data layout and partial-data styling; make operational flags read-only; standardize names and units.
2. Recompose Overview and simplify navigation, preserving links to all technical detail.
3. Standardize chart colors, axes, time ranges, and state timelines.
4. Restructure settings and consolidate diagnostic views and legacy UI documentation.

## Verification for a redesign

Check 360, 390, 768, and 1440px widths inside the actual dashboard; light/dark themes; keyboard focus; reduced motion; increased text size; solar surplus; grid import; battery charging/discharging; car idle/charging; island operation; and missing data. Verify no clipped values, accidental status toggles, inaccessible diagnostics, misleading zeros, or changes to automation behavior.

## Current platform references

- [Sections layout](https://www.home-assistant.io/dashboards/sections/)
- [Views and diagnostic subviews](https://www.home-assistant.io/dashboards/views/)
- [Compact status badges](https://www.home-assistant.io/dashboards/badges/)
- [Dashboard actions and confirmations](https://www.home-assistant.io/dashboards/actions/)

## Implementation status

The reviewed improvements are now implemented locally in `ui-lovelace.yaml`, `www/energy-flow-card.js`, `themes/energy-calm.yaml`, and the frontend resource registration. This includes four primary tabs, linked detail views, a read-only summary, compact phone flow, missing-data and unknown-SoC styling, read-only operational flags, action confirmations, grouped settings, and consistent numeric charts with separate state timelines. All 113 original entity references remain represented.

The custom elements were checked in the running local preview at 360, 390, 601, 768, and 1440px widths, including normal/offline states, and light/dark appearances. Header, device, and metric overflow checks passed. The preview is illustrative; native dashboard placement, controls, and charts require authenticated Home Assistant verification.

The user subsequently approved deployment, commit, and push. The redesign was installed after checking that the live baseline matched the reviewed starting versions. All four installed files matched local source on readback, and Home Assistant configuration validation passed. The dashboard, versioned custom-card module, and existing chart resource returned HTTP 200; the served module matched local source. A rollback copy is retained at `/config/energy-visual-20261016.rollback/`. See `ENERGY_FLOW_DESIGN.md` for the deployment record and rollback steps. Local validation passed 41 Python regression checks plus JavaScript syntax and scenario checks. Full authenticated native-dashboard visual verification remains separate.
