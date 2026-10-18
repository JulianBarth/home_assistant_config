# Bug review — 17 October 2026

Initial read-only review of production YAML, existing tests and the running
Home Assistant instance, followed by corrections authorized by the user.
BUG-01 through BUG-03 were corrected previously. The latest iterative review
reproduced BUG-04 through BUG-07, then corrected them with regression tests.
The reproduction descriptions below refer to the behavior before correction.

## Reproduced findings

### BUG-01 — P1: disabling automation can leave forced charging active

Location: `automations.yaml`, Unified Battery Control Coordinator.

Start with automatic forced battery charging below target while the car is
charging in Default mode. Turn `input_boolean.battery_automation_on` off.
The mode becomes `normal`, but the release condition requires
`car_charging_stable` to have been off for more than three minutes. It therefore
executes no release actions while the car continues charging. The simulated
inverter retains OutWRte=-80%, InWRte=100%, and the charging flag remains on,
despite automation being disabled. Repeated coordinator runs do not help until
another stop condition occurs or the car stops.

Correction: a master-switch change directly triggers the coordinator. An
explicit master-off cleanup branch bypasses car debounce while preserving the
intentional manual-charge override and the higher-priority grid safety gate.

Test: `ControlTransitionTests.test_disable_automation_releases_forced_charge_while_car_charges`.

### BUG-02 — P2: a stale validity flag permits charging with missing raw SOC

Location: `scripts.yaml`, `charge_battery_to_target` entry condition.

With inverter validity and grid readiness still on, replace the raw SOC with
`unavailable` before calling the script. The entry condition converts it to zero
and proceeds with the full forced-charge request. The test starts from normal
register values and observes OutWRte changing to -80% and the charging flag
turning on.

This demonstrates a guard weakness when the raw reading and derived validity
flag disagree. It does not establish that this timing occurred on the live
instance. The normal validity/grid interlocks should subsequently cancel the
request; the offline harness does not model their event scheduling.

Correction: the script checks that raw SOC is greater than zero and no more
than 10000, and that the target is greater than zero and no more than 100.
Missing, nonnumeric, nonfinite and out-of-range inputs cannot start charging.

Test: `ControlTransitionTests.test_missing_raw_soc_cannot_start_charge_with_stale_validity_flag`.

### BUG-03 — P2: discharge fallback counts exported power as house demand

Location: `templates.yaml`, Discharge Limit Percentage fallback.

When the smoothed house-load sensor is unavailable, the fallback clamps grid
power to zero before adding inverter output. Example: 6 kW inverter output,
2 kW export, and 3 kW wallbox charging imply 1 kW house demand. For a 10 kW
battery power base and the configured 15% margin, the intended limit is 11.5%.
The template returns 34.5%, allowing three times as much discharge. The primary
`House Consumption` template already uses signed grid power; the fallback does
not. Its fallback also omits balcony generation.

Correction: the fallback uses the same signed power balance as
`House Consumption`, includes balcony AC generation, and clamps only the final
house demand.

Test: `DischargeFallbackTests.test_export_fallback_counts_only_actual_house_demand`.

## BUG-04 — P2: raw SoC loss does not release an already-running forced charge

Status: **corrected; validation and deployment recorded below**.

Locations: `templates.yaml`, Should Stop Charging; `scripts.yaml`,
`charge_battery_to_target`; Unified Battery Control Coordinator.

The previously corrected BUG-02 blocks a new charge request when raw SoC is
invalid. It does not cancel an existing request. To reproduce, use the real
YAML action sequences to start charging at 50% toward 80%, then replace raw
SoC with `unavailable`, `unknown`, or `nan`, while the derived
`inverter_data_valid` flag still reads `on` and grid permission is still on.
Run the coordinator again.

For both manual and automatic charging, OutWRte remains -8000 (-80%) and
InWRte remains 10000 (100%); StorCtl and the charging flag remain on. The
stop template checks the derived validity flag rather than directly validating
raw SoC. Missing SoC becomes zero in that stop comparison; `nan` does not
satisfy the target comparison. The charge script's raw-data condition prevents
new register writes but does not undo the command already installed.

The new tests assert release back to regular registers (10000, 10000), storage
control off, and the charging flag off. The register assertion fails in all
six combinations (two modes by three invalid raw values), after successful
setup assertions establish that the production scripts actually started a charge.

Three additional tests pass: valid SoC preserves an ongoing charge, target
completion stops without price data, and setting the derived validity flag off
releases an ongoing charge. This bounds the finding: it concerns the interval
before dependent entities agree. The harness does not emulate Home Assistant's
scheduler or measure that interval; this is not evidence of a sustained live
incident, physical overcharge, or bypass of the inverter/BMS protections.

Regression: `RunningChargeTelemetryTests.test_raw_soc_loss_stops_existing_charge_before_validity_flag_updates`
in `tests/test_control_edge_cases.py`.

Correction: the coordinator validates raw SoC and derived inverter validity
before choosing any charging or car-limit branch. The stop sensor also validates
raw SoC directly. A template edge trigger reacts to invalid raw SoC without
waiting for the derived flag. Eight invalid raw values, including numeric range
and nonfinite cases, are covered in both manual and automatic charging. A car
protection case confirms invalid SoC fully releases controls instead of replacing
forced charge with another discharge restriction. A further queued-watchdog
regression reproduced a limit being reapplied after cleanup in four subcases;
the dynamic discharge script now rechecks raw SoC and inverter validity at
execution time, so it cannot undo the coordinator release.

## Live evidence from the initial review

Checked around 08:22 Europe/Berlin on 17 October:

- Home Assistant Core reports 2026.10.1. CPU usage was 0.58%; memory 14.98%.
- SHA-256 checksums of deployed `configuration.yaml`, `templates.yaml`,
  `automations.yaml`, `scripts.yaml` and `tools/battery_log.py` exactly match the
  local project. Matching files do not by themselves prove all templates are
  currently loaded, but the live logger is emitting the current schema.
- The 08:15 battery log reports SOC 29.3% raw, mode `normal`, forced-charge and
  discharge-limit flags false, StorCtl off, valid cached prices and 96 slots
  for today. None of the reproduced defects was observed actively occurring in
  that snapshot.
- At 03:22 on 17 October, pymodbus rejected responses with a mismatched
  transaction ID. At 03:53, Wattpilot logged a connection reset. Solarman logged
  an inverter-data timeout at 18:44 on 16 October. These support testing missing
  readings and recovery, but do not prove the three code findings occurred.
- Earlier logs on 12 October show Solcast HTTP 429 retries exhausting all ten
  attempts. This is historical evidence of forecast failures, not evidence of
  a current outage.
- Startup warnings on 16 October identify incorrect entity domains in the
  installed ENTSO-E custom integration and warn of incompatibility with Home
  Assistant 2027.5. This integration is outside the code present in this repo.

No complete fresh entity-state API snapshot was obtained. Current battery
observations above come from the instance's structured log, not restored-state
files. Provider recovery and physical backup operation were not tested.

## Test results

Added 16 behavioral tests in `tests/test_control_edge_cases.py`. Before fixes,
the three defect reproductions were verified to fail their assertions, without
setup errors. All expected-failure markers have been removed. Additional
coverage rejects invalid SOC and targets and checks balcony generation.

Full Python suite: **57 tests, all pass**. Existing JavaScript
energy-flow scenarios also pass. These are offline checks against real YAML
templates/action sequences; they do not validate HA scheduling, network behavior,
device firmware or physical safety.

## BUG-05 — invalid manual target can default to 80% or retain a charge

Before correction, a missing manual-target helper was converted to 80%, which
could start a charge never represented by a valid current target. Other invalid
values could leave an already-installed charging request active. The raw target
checks in the lower-level charge script came too late: the coordinator either
substituted the fallback or attempted to write an invalid target helper first.

Two regressions reproduced ten failing subcases across new and ongoing manual
requests. Missing, unknown, nonfinite and out-of-range targets are now rejected
by the coordinator before branch selection, clearing the manual request and
restoring regular controls. The stop sensor independently checks target validity.
Valid target boundaries of 1% and 100% remain supported. These simulations model
unavailable or corrupt helper state; they do not claim the normal number UI
permits entering invalid values.

Tests: `ManualTargetValidityTests` in `tests/test_control_edge_cases.py`.

## BUG-06 — cancelled Wattpilot setup leaks a reconnect worker

A setup cancellation during initialization raised `asyncio.CancelledError`,
which is outside `Exception` on supported Python versions. Timeout cleanup did
not run, so a reload or shutdown could leave the reconnect worker alive. The
new asynchronous regression failed before correction and verifies that setup
disconnects its client before re-raising cancellation. The production helper now
handles this exit explicitly. Cancellation remains cancellation rather than
being converted into a successful setup or an ordinary retry failure.

Test: `SetupTests.test_cancelled_setup_stops_worker_and_propagates_cancellation`
in `tools/test_wattpilot_connection.py`.

## BUG-07 — successful Wattpilot initialization at the timeout boundary rejected

If authentication and full status became ready on the final allowed one-second
poll, the helper nevertheless rejected the ready client because its timer equaled
the timeout. A new regression reproduced the failure. Removing the redundant
final timer check accepts a connected, initialized client; incomplete status at
the same boundary still fails and disconnects, as a separate test confirms.

Tests: `SetupTests.test_ready_on_final_timeout_tick_is_accepted` and
`SetupTests.test_incomplete_status_on_final_tick_still_disconnects`.

## Latest iterative verification

The controller suite now has 69 passing test methods. The separate installed
Wattpilot-source suite has 11 passing methods, for 80 Python tests overall.
All four new defects were reproduced before their respective corrections. No
expected-failure markers conceal them. The checks model production YAML actions
and the installed connection helper; they do not emulate HA event scheduling or
prove physical inverter/BMS behavior under real faults.

### Deployment verification, 17 October 2026

The coupled YAML/logger files and updated Wattpilot helper were installed with
rollback archive `/config/backups/control-iteration-20261017-01/baseline.tar`.
Home Assistant's configuration validation passed before the restart, and again
after adding the queued-watchdog guard. The final scripts were reloaded through
the normally authenticated YAML tools without another restart. All seven live
file checksums match the tested sources. The cumulative integration patch also
recreates all three repaired integration files byte-for-byte from its baseline.

After restart, the authenticated dashboard showed fresh valid inverter/grid
readings, Grid Control Ready on, manual Default retained, and approximately
10.8 kW car charging. No new template/loading/Wattpilot errors appeared in the
examined post-startup log window. This validates normal operation and installed
code, not live fault injection or physical transfer/BMS behavior.

Release checks: 69 controller tests and 11 connection-helper tests pass; the
JavaScript energy-flow checks and Git whitespace check pass. Staged public files
and reachable Git history were audited for configured secrets and credential
patterns without printing credentials. Private diagnostics and screenshots are
excluded from the commit.

## BUG-08 — delayed discharge watchdog overrides master-off cleanup

A watchdog dispatched before the automation master is disabled can execute
following coordinator cleanup. Its execution-time guard checked grid/SoC
validity but not the master switch, restoring a discharge restriction and
turning StorCtl back on. A regression first failed with OutWRte=1000 instead
of the expected regular 10000. The dynamic script now requires the current
master state to be on before writing registers.

## BUG-09 — invalid discharge percentage reaches the register writer

The script accepted numeric percentages outside the sensor's 1–100% range.
A -80% input produced OutWRte=-8000, requesting forced charging; excessive
values escaped the register range, NaN became zero, and infinities raised a
conversion error. These are corrupt/stale-input simulations, not evidence that
the production sensor emitted such values. The script now validates the range
before conversion and uses its existing 10% fallback for invalid inputs.
Regression cases cover missing, malformed, nonfinite and out-of-range values,
plus valid 1%, 11.5% and 100% commands.

This iteration adds three test methods. Before correction, the reproductions
had six assertion failures and two conversion errors. After correction all
72 Python tests and the JavaScript energy-flow scenarios pass. The offline
harness does not reproduce Home Assistant scheduling or physical hardware.

## 18 October 2026 — related telemetry and permission audit

Following the sleeping-inverter frequency correction (`f079b51`), focused
regressions were written and run before changing production YAML. The initial
new scenarios reproduced 23 failing assertions/subcases. A second test-first
iteration reproduced three failures involving reserve continuation and stale
derived load estimates. These simulations establish code defects; they do not
claim every injected failure occurred on the live installation.

### BUG-10 — healthy grid coupled to battery telemetry

`Grid Connection Status` required the battery SoC validity flag as well as
valid frequency and meter power. Thus battery-only telemetry loss could force
manual wallbox Default back to Eco despite continuing grid evidence. Grid
classification now uses grid measurements; battery command guards still
independently reject missing/invalid raw SoC. The previous policy tests that
expected this unnecessary coupling were corrected.

### BUG-11 — invalid SoC accepted by the shared validity sensor

The validity flag accepted positive infinity and raw SoC above 10000, including
65535. It now requires `0 < raw_soc <= 10000`, matching the command-level
guards. Valid 0.01% through 100% readings remain accepted.

### BUG-12 — car charging blocks reserve recovery or invents capacity

The car/battery permission sensor required a cheap tariff even when reserve
recovery was necessary, leaving the battery below reserve while the car charged.
It now permits recovery under the same reserve start threshold as the battery
controller, continuing to the reserve target after the start threshold is
crossed. This still requires capacity headroom. Missing/malformed/nonfinite
power or capacity values no longer default to apparently spare capacity; raw
meter and inverter power must also be present so a stale derived house estimate
cannot hide upstream loss. Nonemergency charging requires valid finite prices.
The suspected currency-unit mismatch was ruled out: the average is already in
Cent/kWh and the existing EUR-to-cent conversion is retained.

### BUG-13 — delayed charge/hold calls can undo cleanup

`hold_battery_soc` did not recheck grid permission, automation master, or raw SoC
when executed. A delayed call after cleanup could restore the discharge
restriction and StorCtl. It now validates those permissions before any write.
`charge_battery_to_target` also rechecks automatic/manual authorization, rejecting
a queued automatic charge after master-off while preserving explicit manual
charging with automatic control disabled.

Verification: 96 Python tests, JavaScript energy-flow scenarios and Git
whitespace checks pass. The new complete reserve transition scenario exercises
9%, 11%, 14%, and 15% SoC with actual production YAML actions, including taper,
target completion, unchanged manual Default and retained car protection.

### BUG-14 — diagnostic templates fail during reload initialization

The 08:16:07 live reload produced two TemplateErrors: `len(None)` in diagnosis
and membership testing against None in recommendations. Source attributes can
briefly be absent while template entities initialize. Five tests were added
first; both missing-attribute subcases reproduced the exact live TypeErrors.
The templates now report diagnostic data unavailable until the source lists
exist, instead of throwing or implying that all measurements are healthy.
Two further failing assertions reproduced partial initialization and invalid-only
readings incorrectly receiving an all-clear recommendation; both now report
the missing or invalid data. Known healthy and unavailable lists retain their reports.
Final verification after this follow-up: 101 Python tests and the JS energy-flow
scenarios pass. This changes diagnostics only, not control permissions.
# Year-round model regression review — 18 October 2026

Nine additional behavioral test methods reproduced defects before production
changes. The first run had three failures and two errors; the telemetry run
had seven failing assertions, including raw-SoC subcases. Evidence is retained
in ignored `diagnostics/2026-10-18/year-model-release/`.

- AC household demand was treated as lossless battery energy. Directional
  efficiency assumptions now convert demand/refill/budget units consistently.
- Gross future PV could finance a car loan even when most early output spills
  from a full battery and later demand exhausts storage. A finite-capacity
  trajectory now limits loans through the following night's recovery.
- Four quarter-hour points could classify recovery as a full hour even when
  sunset precedes that hour's end. The entire hour must precede sunset.
- Non-dictionary inverter/car records could crash demand fitting. Malformed
  measurement objects are now ignored.
- A zero capacity helper caused division by zero in the target template.
  Invalid/nonfinite capacities use a bounded fallback consistent with the model.
- A fresh snapshot and stale derived SoC could leave a positive car budget,
  permit a boost start or advertise extra discharge after raw SoC disappeared.
  Those decisions now reject missing/nonfinite/invalid raw SoC immediately and
  use the lower valid raw/derived value when checking current energy.

A final failing regression found that an unavailable balcony inverter at night
would incorrectly mark healthy household power invalid and eventually prevent
seasonal learning. The logger now separates balcony validity from the main
power balance; dark-hour learning does not need balcony telemetry, while
new daylight samples still require it.

All **137 Python tests** pass after fixes; existing hardware-control tests remain
included. These are offline fault-injection results, not induced live failures.
The release scope includes the reviewed year-round implementation, its data
analysis tools, documentation and regression tests. Deployment is limited to
`configuration.yaml`, `templates.yaml`, `automations.yaml` and
`tools/seasonal_model.py`; unrelated scripts/integrations are unchanged.
