# Battery operational corrections

The battery controller distinguishes confirmed grid availability, island operation and uncertain readings. Missing telemetry releases forced charging and discharge restrictions and blocks grid-dependent car charging. Grid permission returns only after five continuous minutes of valid readings. See [GRID_CONNECTION_POLICY.md](GRID_CONNECTION_POLICY.md).

Solar planning uses tomorrow's forecast after the evening sleep cutoff and today's remaining forecast after midnight. Evening bridge calculations use the next morning's weekday/weekend wake time. Invalid raw SOC makes the displayed SOC unavailable rather than reporting an empty battery.

House load uses signed grid power, hybrid inverter AC output and balcony AC generation, less wallbox load. Export reduces household consumption. Battery power is estimated from the hybrid inverter's own DC generation and AC output; balcony generation is not battery DC input. Grid-to-battery power is capped by positive grid import, inverter AC import and battery charging power. These are estimates from asynchronously sampled sensors, not billing measurements.

The price cache labels its arrays by local calendar date. The cycle tracker integrates the previous grid-charge power over short intervals, splits tariff boundaries and compares against the matching date's average price. Gaps over two minutes and downtime are not extrapolated; their duration is reported in `unmeasured_seconds`. Monthly totals accrue as intervals are measured, so a cycle crossing midnight does not move its entire energy into the new month. Completed-cycle counts belong to the month in which the cycle ends. The current sensor value follows its data attribute on the next update.

Accounting version 2 starts a new baseline. Earlier totals are preserved in `legacy_totals`; they included solar contribution and cannot be combined with the corrected estimates. `measured_since` identifies the start of the corrected series. Compatibility fields named `saved_eur` represent a gross daily-average tariff comparison only. The dashboard calls this a price advantage; it is not net savings after losses, wear or export opportunity cost. Restarted/interrupted cycles are not represented as completed cycles.

The command-line logger validates JSON, writes the complete record including its newline, and serializes writers and monthly rotation with the same file lock. Rotation refuses to overwrite an existing archive. The Python script must be installed alongside the YAML at `/config/tools/battery_log.py`.

## Validation and deployment

Run `python -m unittest discover -s tests -v` using `tests/requirements.txt`. Scenarios cover grid uncertainty, manual charging and register-write order, midnight forecast selection, weekday/weekend transitions, export and mixed-source power, interval tariffs, missing telemetry, monthly rollover, legacy accounting migration, and concurrent logging/rotation.

Deploy `configuration.yaml`, `templates.yaml`, `scripts.yaml`, `automations.yaml`, `ui-lovelace.yaml` and `tools/battery_log.py` together after backing up the installation. Run Home Assistant's configuration check before restarting. Verify valid inverter/price data, normal battery control, wallbox Eco and the five-minute grid recovery gate after startup. A configuration check and offline tests do not substitute for a physical backup-power test.

External Tibber realtime capability and provider throttling cannot be repaired by changing charge targets. Keep existing integrations and credentials out of source control, and verify fresh measurements before declaring provider recovery.

References: [command-line notify input and reload](https://www.home-assistant.io/integrations/command_line/), [template availability and triggers](https://www.home-assistant.io/integrations/template/).
