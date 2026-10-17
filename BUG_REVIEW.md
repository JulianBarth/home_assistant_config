# Bug review — 17 October 2026

Initial read-only review of production YAML, existing tests and the running
Home Assistant instance, followed by corrections authorized by the user.
All three findings below are now corrected in the production YAML. The
reproduction descriptions refer to the original code before these corrections.

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
