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
