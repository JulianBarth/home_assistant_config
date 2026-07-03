# Car Smart Charging — Solar-Backed Boost & Cheap Grid Windows

Improved car (Cupra Born @ Fronius Wattpilot) charging algorithm layered on top of
the existing battery optimization. Two independent mechanisms, coordinated by the
`Car Smart Charging Coordinator` automation. **Cheap-grid takes precedence over boost.**

## 1. Solar-Backed Boost ("the sun will refill it anyway")

**Problem:** In Eco mode the Wattpilot only charges from live PV surplus. On a
morning with a strong forecast the car sits idle for hours even though the home
battery holds energy that the coming sun is guaranteed to replace.

**Solution:** When the forecast shows today's remaining solar will refill whatever
we lend, the Wattpilot's **native Boost** is enabled (`switch.wattpilot_boost`).
Boost charges the car from the home battery *while the charger stays in Eco*, and
the Wattpilot itself stops discharging at `number.wattpilot_boost_discharges_until`
(set to the computed floor SoC) — a hardware-enforced stop independent of HA.

### Budget calculation (`sensor.car_boost_energy_budget`, Wh)

The lendable energy is the **minimum of three constraints** (never below 0):

| # | Constraint | Meaning |
|---|-----------|---------|
| 1 | `soc_wh − floor_wh` | Battery may not drop below the boost floor now |
| 2 | `soc_wh + solar_surplus − needed_at_sunset` | After the solar refill, tonight (overnight consumption + reserve + safety margin) must still be covered |
| 3 | `solar_surplus` | The coming sun must actually refill the loan — this is the core "sun will re-charge the battery" requirement |

with
- `solar_surplus = max(0, remaining_solar_today × confidence − house_consumption_until_sunset)`
- `house_consumption_until_sunset` from the existing day/night rate + wake-hour usage-pattern helpers
- `needed_at_sunset = reserve + overnight consumption (night rate, tomorrow's wake hour, breakfast gap) + safety margin`
- `floor = max(car_boost_min_soc, soc_target_default + 5)`

Constraint 3 makes the budget 0 in the evening/night (no sun coming today), so
boost naturally only runs between (pre-)morning and early afternoon. Debug JSON
with all intermediate values and a `decision_reason` lives in the sensor's
`calculation_data` attribute (same pattern as `sensor.battery_optimization_data`).

### Start conditions (`binary_sensor.car_boost_viable`)

- master switch `input_boolean.car_smart_charging_on` on
- car plugged in, charging mode = **Eco**, car currently drawing < 100 W
- budget ≥ `car_boost_min_budget_wh` (to start; a running boost continues until the budget is fully spent — hysteresis against flapping)
- battery not busy (no charging/hold/manual flags), inverter data valid, SoC ≥ floor + 3 %
- not suppressed (see watchdog)

During boost the charger stays in Eco, so `binary_sensor.car_charging_stable`
stays **off** and the battery car-protection (discharge clamp) does not engage —
the battery is intentionally free to discharge into the car.

### Stop conditions

Any of: budget spent, floor reached (Wattpilot native stop), car unplugged,
battery automation takes over (`battery_charging_active` on), viability lost,
master off, HA restart (startup reset), cheap grid window opening.
On stop `number.wattpilot_max_charging_current` is restored to 16 A.

### No-power watchdog

If boost is active ≥ 15 min but the car draws < 100 W (typically: car already
full), boost is stopped and `input_boolean.car_boost_suppressed` set. Replugging
the car clears the suppression.

## 2. Cheap Grid Windows (price optimization)

When Tibber prices are **negative**, or the current price is both in the bottom
`car_cheap_grid_percentile` % of the next 12 h **and** below the absolute ceiling
`car_cheap_grid_max_price_ct`, the coordinator switches the charging mode
**Eco → Default**. The existing battery car-protection then takes over as designed:
house from battery, car from grid. When the window closes (with hysteresis:
percentile +15 points / ceiling +2 ct) the mode is switched back to Eco.

If the mode is changed manually while a window is active, the coordinator detects
the override, releases its claim, and does not touch the charger again.

## Entities added

**Helpers** (in [configuration.yaml](configuration.yaml)) — no `initial:` per repo
convention, so they start at their **minimum** on first deploy, which is the safe
direction for every one of them. Set the recommended values once via UI:

| Helper | Recommended | Notes |
|--------|-------------|-------|
| `input_boolean.car_smart_charging_on` | on | Master switch — **off after deploy**, enable to activate |
| `input_number.car_boost_min_soc` | 30 % | Battery floor for lending |
| `input_number.car_boost_min_budget_wh` | 2000 Wh | Minimum budget to start a boost |
| `input_number.car_boost_solar_confidence_pct` | 70 % | Forecast discount (covers Solcast error + losses) |
| `input_number.car_boost_charging_current_a` | 6 A | ≈ 4.1 kW @ 3 phases — keeps draw within battery + PV capability; restored to 16 A (hardcoded) after boost |
| `input_number.car_cheap_grid_percentile` | 10 % | Window opens at/below this percentile |
| `input_number.car_cheap_grid_max_price_ct` | 15 ct | Absolute ceiling (percentile alone is misleading on expensive days) |

**Template entities** (in [templates.yaml](templates.yaml)):
`sensor.car_boost_energy_budget` (+ `floor_soc`, `calculation_data` attributes),
`binary_sensor.car_boost_viable`, `binary_sensor.car_cheap_grid_window`.

**Automations** (in [automations.yaml](automations.yaml)):
`Car Smart Charging Coordinator`, `Car Boost No-Power Watchdog`,
`Car Boost Suppression Reset`, `Reset Car Smart Charging on Startup`.

## Interaction with the battery algorithm

- **Boost** runs only when the battery flags are idle; if
  `input_boolean.battery_charging_active` turns on mid-boost the coordinator
  stops the boost immediately (a grid-charging battery must not be drained into
  the car at the same time).
- **Cheap grid** deliberately *uses* the existing `car_charging_only` protection
  (mode ≠ Eco + charging ⇒ dynamic discharge limit) — no new battery-side logic.
- The surplus-discharge policy (`sensor.battery_surplus_discharge_power`) is
  untouched; it covers the evening/night case, boost covers the pre-solar case.
  Constraint 3 guarantees the two cannot both claim the same energy: boost's
  budget is zero whenever no more sun is coming today.

## Logging

Coordinator events append JSONL lines to `/config/battery_algorithm.log` with
`"type":"car"` and `event` ∈ `boost_start | boost_stop | boost_suppressed |
cheap_grid_start | cheap_grid_stop`, including the full budget calculation on
boost start. Filter with `jq 'select(.type=="car")'`.

## Rollout

1. Deploy config, restart HA (new helpers + template entities).
2. Set helper values per the table above (they start at minimum = inert) —
   dashboard **Configuration → 🚗 Car Charging Settings** has all sliders with
   the recommended values in their labels.
3. Turn on `input_boolean.car_smart_charging_on` (same card, also in Overview
   Quick Controls). Live status + budget breakdown: **Charging Logic** view.
4. Watch the first sunny morning: expect `boost_start` in the log when the car
   is plugged in Eco with no surplus yet and the budget clears 2 kWh.
