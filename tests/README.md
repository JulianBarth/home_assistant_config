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
fallback power balances including balcony generation. The defects documented in
[`BUG_REVIEW.md`](../BUG_REVIEW.md) are corrected and all 57 Python tests pass
without expected-failure markers. The JavaScript scenarios also pass.

The harness is deliberately smaller than Home Assistant. Passing tests do not
replace its configuration check, observation of fresh live telemetry, or a
physical backup-power test.
