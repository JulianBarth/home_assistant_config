# Year-round energy model for Reutlingen

Implemented on 18 October 2026. This replaces the earlier fixed
summer-night profile. It supports the complete calendar and learns from recent
usage throughout the year; it does **not** claim measured winter accuracy from
summer data. Live activation and rollback details belong in the deployment
record; the model itself does not activate or change hardware settings.

## Location and daylight

Use Reutlingen city coordinates **48.492778° N, 9.212500° E**, derived from the
[city's published coordinates](https://www.reutlingen.de/de/Leben/Unsere-Stadt/Daten-Fakten),
with `Europe/Berlin` time. These describe the city, not a surveyed roof location.
The solar calendar uses the fractional-year equations in
[NOAA's solar-position reference](https://gml.noaa.gov/grad/solcalc/solareqns.PDF).
It calculates sunrise, solar noon and sunset for the actual date, including leap
years. Timezone conversion applies CET/CEST, and energy integration advances in
UTC so the clock-change nights have the correct elapsed duration.

Illustrative model times for the 21st of each month in 2026, rounded down to the
minute; these are approximate astronomical boundaries, not promised PV output:

| Month | Sunrise | Solar noon | Sunset | Daylight hours |
|---|---|---|---|---:|
| January | 08:05 | 12:33 | 17:01 | 8.94 |
| March | 06:26 | 12:31 | 18:35 | 12.16 |
| June | 05:20 | 13:24 | 21:28 | 16.13 |
| September | 07:06 | 13:16 | 19:25 | 12.32 |
| December | 08:11 | 12:20 | 16:29 | 8.30 |

There is no fixed 09:00 solar-recovery limit or 13:00 solar-noon assumption.
Roof orientation, terrain, shading, clouds, fog and snow can make useful
generation depart substantially from astronomical daylight. The model credits
only forecast generation; the calendar supplies no invented clear-sky energy.

## Demand throughout the year

`tools/seasonal_model.py` reads the current algorithm log and monthly archives
intersecting the preceding **42 days**, using only observations strictly before
the prediction time. It learns separate hourly means and upper-quartile loads
for weekdays and weekends. Thus actual changes in winter/summer household usage
enter through recent measurements rather than an assumed seasonal multiplier.

For each hour/group, require at least 16 observations across four distinct days.
Blend the observed load with the configured consumption prior, using weight
`min(0.9, n / (n + 40))`. Unobserved hours use the configured prior in full:
currently 320 W asleep and 1,280 W awake, with the weekday/weekend wake helpers
and sleep helper determining the transitions. Changing those helpers changes
the prior; it does not rescale already observed physical power readings.

Training uses signed `grid + inverter AC + balcony - wallbox` power. It rejects
EV loads over 50 W, missing/nonfinite inputs, nonpositive or >15 kW balances,
event-triggered samples and duplicate quarter-hour slots. Old daylight samples
lack balcony telemetry and are excluded. New logger fields preserve raw balcony
power and separate balcony/main-power validity flags, so daytime
learning can grow when those inputs are genuinely available. Dark-hour
samples do not require an online balcony inverter, because balcony generation
is absent then. Daylight samples still require explicitly valid balcony power.

There is no January expiry cliff. As new seasons arrive, the recent window
moves with them. If winter measurements are missing or all inputs are rejected,
the configured rates remain the explicit fallback. **No unmeasured heat-pump,
electric-heating or temperature coefficient is invented.** If those loads vary
faster than the recent window adapts, demand forecasts can still be wrong.

## Weather-aware solar recovery

Use the installation's existing Solcast rooftop forecasts for today and
tomorrow. The input contract follows the integration's documented
[half-hour forecast attributes](https://github.com/BJReplay/ha-solcast-solar#readme):
`period_start`, `pv_estimate` and optional `pv_estimate10`. These powers are in
kW; multiplying by 1,000 and actual interval hours yields Wh.

- The installed freshness entity was verified read-only as
  `sensor.solcast_pv_forecast_zeitpunkt_letzter_api_abruf`.
- Require a valid poll timestamp between zero and 18 hours old. A future,
  missing or stale timestamp grants zero solar credit.
- Where available, use the lower of P10 and the configured confidence fraction
  of P50. Missing P10 uses at most 70% of P50, explicitly labelled a discounted
  estimate rather than a statistical quantile. Invalid supplied P10 is rejected.
- Missing intervals contribute zero, conflicting duplicates are discarded, and
  astronomical darkness contributes zero. Daily kWh totals remain diagnostic
  information and cannot fabricate an hourly production schedule.
- Recovery is the first full forecast hour whose conservative PV power covers
  conservative household demand throughout. It may be later than 09:00 or may
  not occur within the next 24 hours. Without verified recovery, plan a 24-hour
  bridge and disable solar-backed lending.

This consumes existing Solcast data and makes no extra API requests. Forecast
error bands do not guarantee performance under roof snow or local shading.
If the integration does not expose `detailedForecast`, the model safely uses no
solar credit; those attributes must be checked before live activation.

## One model for the three decisions

The model returns one timestamped result containing `battery`, `surplus` and
`car` sections. Existing YAML sensors consume those sections instead of
duplicating the seasonal arithmetic.

**Battery target:** integrate mean net demand until verified recovery, using
the largest cumulative deficit to determine the initial storage needed. The
target is an absolute SOC above the configured reserve. Solar headroom is based
on net future PV surplus after household demand; it cannot cap the target below
the energy required *before* sunrise. Existing tariff profitability, percentile,
manual-control and reserve-recovery behavior continues to select charge actions.
AC demand is converted to required stored energy, and forecast PV refill is
reduced by charge losses. Both directional efficiencies default to **0.95**,
an engineering assumption giving approximately 90% round-trip efficiency,
not a measurement inferred from these usage logs.
The configured low-solar threshold remains effective against conservative
forecast energy; absence of verified recovery is also classified as low solar.
This is a storage-demand model, not a new full tariff-dispatch optimizer.

**Surplus discharge:** use the upper-quartile demand estimate blended with the
prior, the configured safety margin and a strong verified net solar-recovery
requirement. Retain price sensitivity, maximum extra power, telemetry checks and
the current reserve floor. Recheck the available energy against current SOC in
the template, rather than relying only on the five-minute model snapshot.

**Car solar boost:** limit the loan by all four constraints: current boost floor,
remaining conservative solar surplus, ability to cover the following night
after refill, and the energy needed to bridge from now until the next solar
recovery. This fourth constraint prevents tomorrow's sunshine from financing
an unsafe loan tonight. A capacity-limited trajectory also checks the complete
path through the following night: early PV that spills after the battery is
full cannot pay for later household consumption. Loan and extra-discharge
outputs are AC-deliverable Wh; capacity, SOC-derived energy and reserve margins
are storage-side Wh. The existing current-SOC and island floors still apply,
with raw SoC revalidated at decision time even when derived readings are stale.
New boosts may start from two hours before local sunrise until one hour before
sunset, provided the budget and existing permissions allow it. This replaces
the fixed 15:00 cutoff while preserving the midnight-start protection.

The model is **not an outage guarantee**: hardware controls and inverter reserve
protection remain separate. The upper-quartile load and safety margin are risk
allowances, not calibrated probabilities of household energy sufficiency.

## Historical evidence

Replayed 92 complete 22:00–05:00 nights from July through 17/18 October using
actual quarter-hour power snapshots. Each prediction sees only its preceding
42 days; later October nights may use earlier October observations, exactly as
the proposed online model would. This is rolling-origin validation, distinct
from the earlier fixed-profile October holdout experiment.

| Period | Complete nights | Flat 320 W MAE | Adaptive mean MAE | Conservative demand MAE |
|---|---:|---:|---:|---:|
| July | 26 | 473 Wh | 356 Wh | 471 Wh |
| August | 28 | 612 Wh | 392 Wh | 582 Wh |
| September | 24 | 597 Wh | 429 Wh | 507 Wh |
| October | 14 | 647 Wh | 402 Wh | 602 Wh |
| All eligible nights | 92 | **574 Wh** | **393 Wh** | **534 Wh** |

Mean demand MAE improves by **31.5%** overall; October improves by **37.8%**.
The more conservative load path deliberately trades some accuracy for reserve.
Before applying the separate safety margin, demand underpredictions exceeding
700 Wh occurred on five nights for the mean estimate, one for the conservative
estimate and one for the original flat estimate. These counts are not observed
reserve violations or an all-season reliability guarantee.

Only complete eligible quiet nights are evaluated; daytime and EV demand,
winter household behavior and actual PV recovery were not retrospectively
validated. Power snapshots approximate energy. No financial savings, physical
charging improvements or winter accuracy are claimed from these results.

## Integration, operation and verification

The [Home Assistant command-line sensor](https://www.home-assistant.io/integrations/command_line/)
runs the standard-library script every five minutes. Its base64 JSON input
contains sensor data and helpers, with no credentials or arbitrary shell text.
It performs no hardware writes, recorder mutations, network requests or model
file writes. Local replay of the available logs took approximately 0.12 seconds
for one prediction; this is not a timing measurement on the HA device.

The result exposes version, generation timestamp, forecast status, accepted
history samples, learned hour groups and the seasonal calendar. Model data
older than 15 minutes or dated in the future disables optional car lending and
extra discharge; the computed automatic target returns to the configured
reserve. Manual charging and the existing independent reserve-recovery controls
retain their existing permissions and safeguards.

Validation completed locally:

- **137 Python test methods pass**, including the actual rendered command payload
  and the three production consumers, date rollover, all 12 months, all 366 days
  of a leap year, CET/CEST elapsed time, missing/stale/inconsistent forecast data,
  training leakage rejection, loan constraints and raw-input log serialization.
- Existing JavaScript energy-flow scenarios pass; `git diff --check` passes.
- The actual CLI produced valid JSON with the downloaded historical archives.
- Seasonal cloudy/clear scenarios are synthetic tests. Actual winter demand and
  full PV interval replay remain unverified.

Reproduce using an isolated Python environment with `tests/requirements.txt`:

```sh
.venv/bin/python -m unittest discover -s tests -v
node --test tests/test_energy_flow.cjs
.venv/bin/python tools/seasonal_model.py --calendar-year 2026
.venv/bin/python tools/backtest_seasonal_model.py \
  diagnostics/2026-10-18/optimization/config/battery_algorithm*
git diff --check
```

Raw logs, intermediate JSON and previous configuration copies remain in ignored
`diagnostics/`. Activation requires the coupled `configuration.yaml`,
`templates.yaml`, `automations.yaml` and `tools/seasonal_model.py`, a checked live
baseline, rollback copies, HA configuration validation, command-line sensor
activation and fresh model/decision readback. Record the deployment result and
rollback location in ignored diagnostics separately from offline validation.
