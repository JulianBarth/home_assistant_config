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
- `floor = max(car_boost_min_soc, soc_target_default + 5) + car_boost_floor_margin_pct`

The **floor load margin** exists because the BMS reports SoC ~10–15 %-points too
high while discharging at boost power (~4 kW): on 2026-07-07 the Wattpilot stop
fired at an indicated 20 %, but after the load dropped the resting SoC turned out
to be 5 %. The margin is applied inside `floor_soc`, so the budget (constraint 1),
the viability checks and the hardware stop all use the same protected value.

Constraint 3 makes the budget 0 in the evening/night (no sun coming today).
**Note:** it does *not* prevent midnight starts — Solcast's "remaining today"
rolls over at 00:00, making the budget *largest* at midnight (observed 2026-07-04
and 2026-07-07: boost drained the battery at 00:00 and the house then imported
grid power all night). Starting is therefore additionally time-gated in
`car_boost_viable`: **from 2 h before sunrise until 15:00**. Debug JSON
with all intermediate values and a `decision_reason` lives in the sensor's
`calculation_data` attribute (same pattern as `sensor.battery_optimization_data`).

### Start conditions (`binary_sensor.car_boost_viable`)

- master switch `input_boolean.car_smart_charging_on` on
- car plugged in, charging mode = **Eco**, car currently drawing < 100 W
- car state ≠ `Complete` (a full car just flaps boost on/off until the watchdog
  suppresses it — observed 2026-07-04 00:00)
- time of day within the start window: **sunrise − 2 h … 15:00** (a running
  boost is not gated and continues until its budget is spent)
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
| `input_number.car_boost_min_soc` | 30 % | Battery floor for lending (min raised to 20 after the 2026-07-07 incident — deploy-at-min left it at 10) |
| `input_number.car_boost_floor_margin_pct` | 10 % | Added on top of the floor everywhere; compensates SoC reading high under discharge load |
| `input_number.car_boost_min_budget_wh` | 2000 Wh | Minimum budget to start a boost (min raised to 1000 — deploy-at-min left it at 500) |
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

## Grid outage / Inselbetrieb (added 2026-07-11)

The GEN24 full-backup powers the whole house in an island — including HA and
the Wattpilot. The Wattpilot itself has **no island awareness**: outside Eco it
keeps charging from battery + PV until the battery is empty or the inverter
overload-trips (~3.68 kW/phase sustained, battery discharge DC-limited). Eco
surplus charging is dead in an island anyway (needs the Smart Meter, which sits
on the grid side and loses power).

**Detection** — `binary_sensor.grid_available` (off = island), from two
independent signals, 1 min debounce for loss / 5 min for return:

1. `sensor.grid_frequency` (new Modbus reg 40093, float32 — verified live
   50.02 Hz on 2026-07-11): the GEN24 runs its island at ~53 Hz; ≥ 51.5 Hz ⇒
   island. Grid never leaves 49.8–50.2 Hz.
2. Smart Meter loss: `sensor.reading_energy_main_meter` unavailable while
   `binary_sensor.inverter_data_valid` stays on.

If the whole Modbus link is down, both signals are silent and the sensor
fail-opens to "grid ok" — that case is already covered by the
`inverter_data_valid` gates everywhere.

**On island (Grid Outage Guard automation + template gates):**

- Cheap grid window forced/held closed (`grid_ok` gate in the window sensor —
  cached Tibber prices stay valid in an outage, so this must be explicit);
  wallbox forced back to Eco, even if Default was set manually.
- Boost floor jumps to `input_number.car_boost_island_floor_soc` (recommended
  80 %, slider in 🚗 Car Charging Settings; starts at its safe min 60 on first
  deploy): solar-backed boost remains the **only** way to charge the car in an
  island, and only above that floor. A running boost gets its Wattpilot
  hardware stop rewritten to the island floor immediately.
- Battery force-charge / hold / prevent-discharge are stopped and blocked
  (`should_start/stop_charging`, `should_hold_battery_soc`,
  `should_prevent_discharge`): a charge command or discharge limit would starve
  the island and trip the inverter.

**Recovery is declarative:** once `grid_available` has been on again for 5
minutes, floors and window sensors recompute and the coordinators re-enter
whatever state is then appropriate (an open cheap window resumes by itself).
Log events: `"type":"grid"`, `event` ∈ `island_detected | grid_restored`.

**Untestable until a real outage/test:** that the meter registers actually go
`unavailable` (vs. stale) and that the island really sits at 53 Hz. Watch
`sensor.grid_frequency` after deploy (should read ~50.0) and verify both
signals during the next backup-power test (main breaker off).

## Logging

Coordinator events append JSONL lines to `/config/battery_algorithm.log` with
`"type":"car"` and `event` ∈ `boost_start | boost_stop | boost_suppressed |
cheap_grid_start | cheap_grid_stop`, including the full budget calculation on
boost start. Filter with `jq 'select(.type=="car")'`.

`connection_wh` in stop events is `sensor.wattpilot_connection_charged` — the
energy charged **since the car was plugged in**, not per boost/window session
(it was misleadingly named `session_wh` until 2026-07-07).

## Rollout

1. Deploy config, restart HA (new helpers + template entities).
2. Set helper values per the table above (they start at minimum = inert) —
   dashboard **Configuration → 🚗 Car Charging Settings** has all sliders with
   the recommended values in their labels.
3. Turn on `input_boolean.car_smart_charging_on` (same card, also in Overview
   Quick Controls). Live status + budget breakdown: **Charging Logic** view.
4. Watch the first sunny morning: expect `boost_start` in the log when the car
   is plugged in Eco with no surplus yet and the budget clears 2 kWh.
