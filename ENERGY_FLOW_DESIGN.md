# Energy in motion

The Overview and Energy Flow tabs use `www/energy-flow-card.js`, registered as `/local/energy-flow-card.js?v=20261016-1` in `configuration.yaml`. It is a standalone custom element with no new HACS dependencies. The Energy Flow tab uses a panel view for more space, with history and detailed allocations below it.

The diagram shows connections to the shared home electrical system, not an allocation of particular sources to specific consumers. Positive grid power means import; positive battery power means charging. Animated dots reverse for grid export and battery charging. Flows at or below 5 W remain static. House excludes the separately displayed wallbox; total consumption adds them once. Battery power remains an estimate from the existing inverter balance sensor.

The card checks underlying meter, inverter, solar and wallbox readings because some existing wrapper templates substitute zero for missing values. Unavailable inputs do not animate. Device buttons open Home Assistant sensor details and support keyboard navigation. Theme colors inherit from Home Assistant; reduced-motion preferences stop animation. Mobile layouts keep a compact vertical connection spine.

## Verify

- Run `node --check www/energy-flow-card.js` and `node tests/test_energy_flow.cjs`.
- Serve the repository locally and open `previews/energy-flow.html`. It includes illustrative solar-surplus, evening, grid-charging, idle and offline scenarios, plus a light/dark toggle. These are not live readings.
- Validate Home Assistant configuration with `ha core check` after installing the three files. Reload Lovelace resources or restart Home Assistant to register the new module, then refresh the browser.

Implemented using the [Home Assistant custom-card interface](https://contributors.home-assistant.io/frontend/custom-ui/card/).

## Deployment, 16 October 2026

Installed `configuration.yaml`, `ui-lovelace.yaml`, and `www/energy-flow-card.js` after checking the live YAML matched the reviewed files. Home Assistant configuration validation passed. The previous dashboard/configuration were copied to `/config/energy-view-20261016.rollback/` on the server. Home Assistant was restarted to load the module; its HTTP resource returned 200 and matched the local file hash. Browser visual checks cover the local illustrative preview; the live dashboard requires the user's authenticated browser.

To revert, restore `configuration.yaml` and `ui-lovelace.yaml` from that server backup, reload resources or restart Home Assistant, and refresh the browser. The unused custom JavaScript can remain in `www`.
