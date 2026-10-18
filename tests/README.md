# Running the project tests

From the project root, create an isolated environment and install the two
dependencies pinned in `requirements.txt`:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r tests/requirements.txt
.venv/bin/python -m unittest discover -s tests -v
node --test tests/test_energy_flow.cjs
```

The tests run locally without contacting Home Assistant or changing hardware.
They render production YAML templates, simulate control action sequences and
exercise logger concurrency using temporary files. The action harness checks
that intermediate charge/discharge register values form a valid power window.
Dashboard tests check templates, availability and energy-flow scenarios.

`test_control_edge_cases.py` adds control transitions, reserve recovery, raw SOC
loss with a stale validity flag, invalid SOC/target ranges, and discharge
fallback power balances including balcony generation. The iterative review in [`BUG_REVIEW.md`](../BUG_REVIEW.md) covers corrected
raw-SoC loss, invalid manual targets, setup cancellation and timeout boundary
handling. All **101 controller tests** pass without expected-failure markers.

`GridUncertaintyTests` also reproduces inverter sleep (inverter 0 Hz, meter
50 Hz) through frequency selection, grid classification and manual-wallbox
permission. It covers invalid sources, retained island priority, abnormal
frequency, and the meter's verified SunSpec register mapping.

The harness is deliberately smaller than Home Assistant. Passing tests do not
replace its configuration check, observation of fresh live telemetry, or a
physical backup-power test.

Run only the new ongoing-charge scenarios:

```sh
.venv/bin/python -m unittest discover -s tests -p test_control_edge_cases.py -k RunningChargeTelemetryTests -v
```

The validity-flag recovery case bounds the original reproduction: it showed a
raw-versus-derived telemetry gap, not a demonstrated permanent live failure.

The separate Wattpilot helper tests run against an extracted installation:

```sh
python3 tools/test_wattpilot_connection.py /path/to/custom_components/wattpilot
```

All **11 connection tests** pass against the repaired helper. The source patch
is `tools/wattpilot-connection-repair.patch`; see `WATTPILOT_REPAIR.md` for the
installation baseline and application instructions.

`DischargeCommandBoundaryTests` covers delayed watchdog execution after master-off
and rejects invalid percentages before Modbus register conversion.

The 18 October follow-up adds grid/battery telemetry independence, finite SoC
validation, execution-time charge/hold permission, and simultaneous car/battery
reserve recovery. The reserve scenario runs actual production decisions and
register actions from 9% through the 15% target, retaining manual Default and
car discharge protection. Capacity checks reject invalid load readings and lost
upstream power even when a derived house estimate remains numeric. Signed
import/export readings remain supported; the two tariff sensors intentionally
use EUR/kWh and Cent/kWh and are compared after conversion.

`DiagnosticReloadTests` reproduces the two live errors caused by missing entity
check attributes during reload, verifies an unavailable-data message instead of
an exception or false all-clear, and retains normal healthy/problem reports.
