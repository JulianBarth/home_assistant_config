# Responsive energy dashboard

Updated 16 October 2026. Current usage and installation instructions are in [UI_DASHBOARD_GUIDE.md](UI_DASHBOARD_GUIDE.md).

## Implemented

- Four primary destinations with explicit links to Solar, History, Diagnostics, Algorithm details, and Manual service actions.
- Responsive native Sections layouts: a wide primary area on desktop and a single reading order on phones.
- Compact Overview device grid; expanded connected flow on the Energy tab.
- Read-only summary for SoC, effective target, price, operating mode, and the current decision.
- Phone-specific unavailable-value typography; stacked footer metrics avoid collisions.
- Amber partial-data indicator and a hatched unknown-SoC track. Missing data never looks like a healthy zero reading.
- Shorter settings labels with separate explanations and grouped preferences.
- Theme-aware surfaces, text, borders, warnings, and native cards.
- Keyboard device actions, restored focus after telemetry updates, and reduced-motion support for flow animation.

## Local visual checks

The local preview provides seven illustrative scenarios, a light/dark toggle, compact/expanded layouts, and a narrow-column control. Use 360px and 390px phone widths, 768px tablet width, and 1440px desktop width. Native dashboard placement and charts must additionally be checked in an authenticated Home Assistant browser.

The preview is a development fixture using the real custom elements, not a live energy feed.
