# Home energy dashboard

Updated 16 October 2026. The dashboard now has four primary tabs, responsive Sections layouts, and an energy-specific light/dark theme. Existing detail URLs remain valid.

## Overview

The read-only summary shows battery charge, the effective manual or smart target, the current price in ct/kWh, the operating mode, and a plain-language explanation of the charging plan. Missing prices remain unavailable rather than appearing as zero.

The energy-flow card shows solar, grid, battery, household, and car power. On a phone, Overview uses a compact device grid. Select a device to open its sensor details. The Energy tab retains the expanded connected diagram.

Controls contain only user preferences: automatic battery charging, manual charging, and smart car charging. The manual target appears while manual charging is enabled. Operational flags such as “charging active” are read-only elsewhere in the dashboard.

Alerts appear for unconfirmed grid conditions, island operation, a paused car boost, or a reported Tibber Pulse problem. The remaining cards show car status, the price/solar outlook, and estimated monthly price advantage. The price-advantage caveat still excludes storage losses, wear, and export opportunity cost.

## Energy

Expanded live flow, two-hour power history, and detailed source/consumer allocations. Links open Solar production and History.

Solar production contains system readings, forecast-versus-actual production, recent generation, and inverter health. Solar zero is a normal state rather than a red gauge warning.

## Charging

Current context, battery charge versus target and price, and a separate charging-mode timeline. Car status and smart-charging decisions remain visible. Detailed calculations preserve the original bridge-period, consumption, forecast, and price analysis.

Numeric power charts use kW, price charts use ct/kWh, and battery charts use %. Forecast flags and operating-state timelines remain separate from numeric series. Source colors match the flow card where practical; targets use dashed neutral lines.

## Settings

Settings are grouped into Battery reserve, Price rules, Household schedule, Car solar boost, Car cheap-grid charging, Solar thresholds, and System parameters. Schedule helpers retain their existing decimal-hour values, with a visible conversion explanation.

System tools link to Diagnostics, Algorithm details, Manual service actions, and History. These are subviews, so they do not occupy the primary tab bar. Every one of the original 113 entity references remains available in the dashboard.

Manual script rows describe their effect in a confirmation. They directly change operating settings; automatic control may subsequently override them. The redesign does not modify scripts, automation priorities, or control thresholds.

## Visual system and local preview

`themes/energy-calm.yaml` defines the view-specific theme. Solar is amber, grid blue, battery teal, house coral, and car violet. Warnings have separate amber treatment with readable light/dark colors. The theme is not selected globally for other dashboards.

`www/energy-flow-card.js` registers both `energy-flow-card` and `energy-status-card`; no new frontend dependency is required. Historical and forecast charts use the existing ApexCharts resource.

Serve this repository over localhost and open `previews/energy-flow.html`. It renders the actual custom elements with illustrative solar, evening, grid charging, idle, unavailable, island, and manual-override states. Appearance controls switch light/dark, compact/expanded, and narrow-column layouts. It does not emulate native Home Assistant controls or historical charts.

## Validation and installation

```sh
node --check www/energy-flow-card.js
node tests/test_energy_flow.cjs
python -m unittest discover -s tests -v
```

Python tests require `tests/requirements.txt`. They cover existing control regressions plus dashboard navigation, read-only flags, action confirmations, and unavailable-data templates.

Install `ui-lovelace.yaml`, `configuration.yaml`, `www/energy-flow-card.js`, and `themes/energy-calm.yaml` together, after backing up the live versions. Run `ha core check`. Reload themes/resources if available, or restart Home Assistant to register the updated resource URL. Refresh the browser afterwards.

The custom-card preview can be inspected without logging in. Full native dashboard rendering requires an authenticated Home Assistant session; configuration validation does not replace that visual check.
