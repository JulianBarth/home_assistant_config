# Historical consumption optimization — 18 October 2026

**Superseded experiment:** the fixed July–September profile described below was
replaced by the rolling, year-round [Reutlingen model](YEAR_ROUND_MODEL.md).
Its 60.3% October result and January expiry describe this earlier experiment,
not the current implementation. The former Jinja macro has been retired.

The battery target, surplus-discharge allowance and car-boost energy budget now
share an hourly overnight consumption forecast fitted to this installation's
usage. On 14 complete October validation nights, the mean absolute energy
forecast error decreased from **646.84 Wh to 256.88 Wh (60.3%)** versus the saved
320 W night setting. This measures forecast accuracy, not electricity savings
or physical charging performance. Changes are local and have not been deployed.

## Evidence and fitting

Read-only SSH collection recovered 19,336 JSON records from the July, August,
September and current October log files. The July archive also contains older
April–June records; these were excluded from calibration. Legacy concatenated
JSON objects were recovered without modifying the source files. There were no
unparseable records. July–18 October contains 10,543 scheduled snapshots.

The saved Home Assistant planning helpers read during this review were:
night 320 Wh/h, day 1,280 Wh/h, weekday wake 05:30, weekend wake 07:30,
sleep 22:00 and battery capacity 10,000 Wh. These are persisted settings,
not a fresh authenticated API state readback.

Older `car.house_w` measurements inflate daytime consumption because exported
power was clamped before the household balance was calculated. Reconstructing
`grid_w + ac_w - wallbox_w` removes that bias, but the historical logs lack
balcony-generation telemetry. Consequently **daytime load, daytime solar
confidence, battery efficiency and tariff thresholds were not recalibrated**.

Training uses July–September scheduled samples at 22:00–05:00, when balcony
generation should be absent. Reject missing/nonfinite power, nonpositive or
implausible (>15 kW) balances and EV power outside 0–50 W. Event-triggered
samples are excluded; duplicate quarter-hour slots are counted once. The mean
of each clock hour is rounded to watts. There are 2,947 accepted training and
validation samples, with 347–358 training samples per hour.

| Hour starting | Forecast W |
|---|---:|
| 22:00 | 408 |
| 23:00 | 287 |
| 00:00 | 241 |
| 01:00 | 227 |
| 02:00 | 217 |
| 03:00 | 223 |
| 04:00 | 214 |

The seven-hour prediction is 1,817 Wh versus 2,240 Wh at 320 W. Partial hours
are integrated by their overlap; the forecast does not apply the current
hour's power to the entire remaining night.

## Chronological validation

Fit hourly means only on samples before 1 October. Evaluate total energy for
complete 22:00–05:00 nights, requiring all 28 distinct quarter-hour slots to
survive the same filters. Omit the night crossing the training/validation
boundary. October data was not used to fit the profile.

| Period | Complete nights | Flat 320 W MAE | Hourly profile MAE | Profile bias |
|---|---:|---:|---:|---:|
| July–September training | 77 | 565.90 Wh | 360.74 Wh | +4.20 Wh |
| October validation | 14 | 646.84 Wh | 256.88 Wh | +223.84 Wh |

Positive bias means overprediction. Validation covers eligible nights through
17/18 October, not a full October or winter. Quarter-hour power snapshots are
an energy estimate, not revenue-grade meter totals. Excluding EV nights limits
the evidence for simultaneous car charging; the profile forecasts household
demand only. Existing reserve floors, safety margins, power caps, raw-telemetry
checks and hardware permission gates remain in place.

## Control changes

- `custom_templates/consumption_forecast.jinja` integrates the calibrated night
  hours and is imported by both control state and explanatory attributes.
- The existing night-consumption helper scales the profile relative to its
  observed 320 W setting: 320 means the fitted profile, 400 means 1.25 times
  that profile. Hours outside 22:00–05:00 retain the configured flat rate.
- Calibration is eligible from 1 October through 31 December 2026. From
  **1 January 2027**, or before the validation period, forecasts revert to the
  configured flat rate until a newly reviewed calibration is supplied.
- Surplus planning before sunrise now selects today's remaining solar forecast.
  Evening planning selects tomorrow's forecast and tomorrow's wake schedule,
  including Friday→Saturday and Sunday→Monday.

The macro uses Home Assistant's documented
[custom template imports](https://www.home-assistant.io/docs/templating/custom-templates/).
Deploy `templates.yaml` and `custom_templates/consumption_forecast.jinja` together;
load/reload custom templates before reloading template entities. A deployment
must compare the current live baseline, preserve rollback copies, run Home
Assistant's configuration check and verify fresh decisions after activation.

## Reproduce and maintain

Raw household logs and aggregate JSON outputs remain in the ignored directory
`diagnostics/2026-10-18/optimization/`. No recorder database was copied or changed.
The analysis tool performs no network calls or hardware writes:

```sh
.venv/bin/python tools/analyze_usage.py \
  diagnostics/2026-10-18/optimization/config/battery_algorithm* \
  --start 2026-07-01 --cutoff 2026-10-01 --baseline 320
.venv/bin/python -m unittest discover -s tests -v
node --test tests/test_energy_flow.cjs
git diff --check
```

For later calibration, collect fresh private logs, move the chronological
cutoff, retain an untouched validation interval and inspect winter coverage
before changing the profile and expiry. The tool prints aggregates; it does
not automatically update the controller or promote a model.

Validation: **113 Python test methods pass**, including 12 new calibration,
integration and boundary tests; JavaScript energy-flow scenarios pass;
`git diff --check` passes. No live activation or savings experiment was performed.
