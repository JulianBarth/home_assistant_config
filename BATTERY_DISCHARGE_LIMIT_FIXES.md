# Battery Discharge Limit — Root Cause & Fixes

Date: 2026-07-03
Status: implemented (working tree, not yet committed/deployed) — see changelog below

## Problem

During car charging the battery is supposed to cover only the house load
("House from battery, Car from grid"), enforced via SunSpec storage model 124
registers on the Fronius Symo Gen24 Plus 6.0. Log analysis
(`battery_algorithm-5.log`, 68 days) showed the battery discharging 3–6 kW
into the car on essentially every substantial evening/night car session
(e.g. 2026-06-27 22:45→01:15: SoC 76%→41% at ~4.3 kW while the computed
limit was 8–20%).

## Live test evidence (2026-07-03, 20:47–20:54)

Registers read directly via Modbus TCP while the car charged:

```
20:47:55  StorCtl=0  OutWRte=100%   batt_discharge 5799 W   ← no limit active
20:48:55  StorCtl=0  OutWRte=100%   batt_discharge 5798 W
20:49:25  StorCtl=3  OutWRte=33.4%  batt_discharge 3417 W   ← automation asserted
20:50:56  StorCtl=3  OutWRte= 7.4%  batt_discharge  761 W
20:51:26  StorCtl=3  OutWRte=32.7%  batt_discharge 3357 W   ← limit oscillates
20:53:57  StorCtl=3  OutWRte= 9.3%  batt_discharge  951 W
```

Key register facts (read 2026-07-03):

| Register | Addr | Value | Meaning |
|---|---|---|---|
| WChaMax | 40355 | **10240 W** | % base for OutWRte/InWRte (SF at 40371 = 0) |
| StorCtl_Mod | 40358 | 0 or 3 | 0 = inverter ignores OutWRte/InWRte entirely |
| OutWRte | 40365 | 0.01 % units | discharge cap, enforced within seconds, ±1 % accurate |
| InOutWRte_RvrtTms | 40368 | 0 | inverter does NOT auto-revert writes |

## Root causes

1. **Enforcement works perfectly when commanded** (OutWRte × 10240 W matched
   observed battery power exactly). The failures are orchestration:
   `StorCtl_Mod` is 0 during the first minutes of every session (hysteresis
   delay of `binary_sensor.car_charging_stable` + 5-min automation cadence)
   and after every mode flap, because the release path writes StorCtl=0 and
   nothing re-asserts the limit until the next trigger.
2. **HA cannot see the failure**: the `StorCtl_Mod` modbus switch has no
   `verify:` block, so its state is optimistic (last command, not reality).
   The algorithm log's `storctl` field therefore reported "on" while the
   register was 0.
3. **Wrong % base**: `sensor.discharge_limit_percentage`
   (templates.yaml, `battery_max_power = 6000`) computes the limit against
   6 kW but the inverter enforces against WChaMax = 10240 W → every cap is
   1.7× looser than intended.
4. **Noisy limit**: house load is derived as `grid + ac_output − wallbox`
   from sensors sampled at different moments; car power fluctuations leak in
   and the limit swings 7 % ↔ 33 % within 30 s.
5. **Hair-trigger release**: `binary_sensor.car_charging_stable` drops to
   `off` instantly on any wallbox flicker (hysteresis applies only to
   turn-on), the mode goes `normal`, the release branch sets StorCtl=0 and
   OutWRte=100 %, and the battery is unprotected until the flap resolves.

## Fixes

### Fix 1 — Watchdog: re-assert limit every minute during car charging
New automation in `automations.yaml`:
- Trigger: `time_pattern` every 1 minute.
- Condition: `sensor.battery_control_mode` is `car_charging_only`.
- Action: run `script.set_dynamic_discharge_limit`.
Unconditional re-assert (2 register writes + switch-on per minute is
harmless) closes both the session-start gap and the post-flap gap.
Additionally: a second automation that sends a notification (same style as
existing notify automations) when `sensor.percent_max_discharge_rte` exceeds
`sensor.discharge_limit_percentage` by more than 5 points for 5 consecutive
minutes while in `car_charging_only` — this alerts if enforcement ever fails
again for a different reason.

### Fix 2 — `verify:` on the StorCtl_Mod switch
In `modbus.yaml`, add to the `StorCtl_Mod` switch:
```yaml
verify:
  input_type: holding
  address: 40358
  state_on: 3
  state_off: 0
```
Switch state (and the log's `storctl` field) then reflects the actual
register.

### Fix 3 — Correct % base (6000 → WChaMax)
In `sensor.discharge_limit_percentage` (templates.yaml), replace the
hardcoded `battery_max_power = 6000` with the live register value:
`states('sensor.reading_max_allowed_discharge_power') | float(default=10240)`,
guarded so that values < 1000 (unavailable/garbage) fall back to 10240.

### Fix 4 — Smooth the house-load input
- Add a `filter` platform sensor (in `configuration.yaml`, `sensor:` block):
  `sensor.house_consumption_smoothed` = 3-minute time simple moving average
  of `sensor.house_consumption`.
- In `sensor.discharge_limit_percentage`, use the smoothed sensor as house
  load, falling back to the existing `grid + ac_output − wallbox` arithmetic
  when the smoothed sensor is unavailable/unknown.

### Fix 5 — Debounce the full release
In the mode-coordinator automation's release path ("Fully release — no car,
no charging needed"), insert a template condition as the first step: only
proceed when `binary_sensor.car_charging_stable` has been `off` for more than
3 minutes. A brief wallbox flicker then leaves the current limits in place
(the watchdog from Fix 1 re-tightens them within a minute); a genuine end of
charging still releases normally on a later automation run.

## Verification after implementation

1. YAML parses (HA config check).
2. While the car charges: `sensor.percent_max_discharge_rte` tracks
   `sensor.discharge_limit_percentage` within 1 minute; register 40358 = 3.
3. Battery discharge power ≤ limit% × 10240 W (compare with house load).
4. Unplug/replug or wallbox flicker: no 100 %/StorCtl=0 window longer than
   ~60 s.
5. `switch.storctl_mod` in HA matches the register read via Modbus.

## Implementation notes / changelog

Implemented 2026-07-03.

- **automations.yaml**
  - Fix 1: added `"Discharge Limit Watchdog"` (time_pattern every 1 min,
    condition `sensor.battery_control_mode == car_charging_only`, runs
    `script.set_dynamic_discharge_limit`) and
    `"Notify when Discharge Limit Enforcement Fails"` (template trigger with
    `for: "00:05:00"` — fires only when `sensor.percent_max_discharge_rte`
    exceeds `sensor.discharge_limit_percentage` + 5 points *sustained* for
    5 minutes, mode condition `car_charging_only`, notifies via
    `notify.mobile_app_f4gdn4ry0gpq_2` with `tag: battery_discharge_enforcement_failed`,
    `group: battery`, matching the existing notification style). Both appended
    at the end of the file.
  - Fix 5: in `"Unified Battery Control Coordinator"`, inserted a `condition:
    template` as the first step of the inner `default:` ("Fully release — no
    car, no charging needed") requiring `binary_sensor.car_charging_stable`
    to have been `off` for more than 180 s before releasing StorCtl/limits.
- **modbus.yaml**: added a `verify:` block (`input_type: holding`,
  `address: 40358`, `state_on: 3`, `state_off: 0`) to the `StorCtl_Mod`
  switch so its HA state reflects the actual register instead of the last
  optimistic command.
- **templates.yaml**: in `sensor.discharge_limit_percentage` —
  - Fix 3: replaced the hardcoded `battery_max_power = 6000` with
    `states('sensor.reading_max_allowed_discharge_power') | float(default=10240)`,
    falling back to 10240 when the reading is < 1000 (unavailable/garbage).
  - Fix 4: house load now prefers `sensor.house_consumption_smoothed`
    (via `float(default=-1)`, used when `>= 0`), falling back to the
    original `grid + ac_output − wallbox` computation otherwise. The 1.15
    factor and `surplus_extra_power` addition still apply to whichever
    house-load value is selected.
- **configuration.yaml**: added a `platform: filter` sensor
  `"House Consumption Smoothed"` (→ `sensor.house_consumption_smoothed`) in
  the top-level `sensor:` block — 3-minute `time_simple_moving_average` of
  `sensor.house_consumption`, precision 0.

Verified: all four files parse with a YAML loader that tolerates unknown
`!` tags (`!include`, `!secret`) — configuration.yaml (dict), automations.yaml
(list), modbus.yaml (list), templates.yaml (list) all loaded without error.

Review pass (Fable, 2026-07-03): diff checked line-by-line against this spec.
One correction applied: the enforcement-failure alert originally checked the
deviation as an instantaneous condition every 5 minutes; changed to a
template trigger with `for: "00:05:00"` so only a *sustained* deviation
alerts (spec compliance, avoids false alarms during limit oscillation).

## Deployment

- `automations.yaml` / `templates.yaml`: reloadable from the UI
  (Developer Tools → YAML → Reload Automations / Template Entities).
- `modbus.yaml` (verify block) and the new `filter` platform sensor in
  `configuration.yaml`: **require a Home Assistant restart** — neither the
  modbus integration nor sensor platform setup supports YAML reload.
- After restart, run the verification steps above during the next car
  charging session.
