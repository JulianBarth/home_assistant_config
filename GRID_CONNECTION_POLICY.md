# Grid loss versus missing telemetry

The September 2026 policy replaces the old assumption that losing the smart
meter proves a power cut. August logs contained 16 island detections, including
four at normal frequency and twelve without a frequency reading.

| Grid Connection Status | Evidence | Behavior |
| --- | --- | --- |
| `grid` | 49–51 Hz, numeric meter reading, valid inverter data | Allow grid-dependent controls after five continuous minutes |
| `island` | 51.5–60 Hz, matching this GEN24 installation's tested ~53 Hz backup signature | Release battery restrictions immediately; confirm outage after one minute |
| `uncertain` | Missing, invalid, or contradictory readings | Release battery restrictions, put wallbox in Eco, stop boost; no outage/restoration push |

Zero meter power and negative export power are valid readings. Missing frequency
or meter data never defaults to “grid available”. A plausible high frequency
provides island evidence independently of the smart meter, which loses power in
this installation's backup mode. This is an installation-specific heuristic,
not a universal grid-frequency detector or proof of physical transfer-switch state.

`binary_sensor.grid_available` is unavailable during uncertainty, off for a
confirmed island and on after stable grid recovery. The separate
`binary_sensor.grid_control_ready` revokes permission immediately and requires
five continuous minutes of `grid` readings after any interruption, including
startup. It has no off-delay. This separates protective actions from the
one-minute outage notification debounce.

The battery coordinator releases forced charge, reserve holding and car-only
discharge limits before evaluating normal modes. Manual home-battery charging
is cancelled too. Charge-start, hold, reserve prevention and cheap-grid car
charging all require control permission. The dynamic discharge script checks
permission itself to reject a watchdog call queued before telemetry loss.

The wallbox watchdog enforces Eco even for manual Default charging while grid
availability is uncertain, and retries when the wallbox reconnects. It logs this
as a grid interlock, not an outage. Manual Default is not automatically restored;
cheap-grid automation may resume once its conditions and grid permission hold.
Eco's native solar behavior remains under Wattpilot control. Solar-backed boost
remains possible in a confirmed island under the existing high island SoC floor,
but is blocked during uncertainty and the recovery wait.

The persistent `grid_outage_active` helper ensures data loss/recovery alone does
not generate outage messages. It preserves a confirmed outage across an
unavailable interval or restart and prevents resetting its start timestamp when
island telemetry reappears. Duration remains an estimate from detection and
recovery times, not a physical outage measurement.

The overview exposes grid status and charging permission. Status transitions
are recorded as `connection_status_changed` events for future diagnosis.

## Verification and rollout

Run `python -m unittest discover -s tests -v` with `tests/requirements.txt`.
The offline tests cover normal/zero/export readings, missing signals, abnormal
frequency, island evidence, manual and car-only restrictions, negative prices,
boost suppression and the delayed recovery configuration. They do not emulate
Home Assistant's timer/event scheduling or test physical transfer switching.

Deploy configuration.yaml, templates.yaml, scripts.yaml, automations.yaml and
ui-lovelace.yaml together, validate the configuration in Home Assistant, and
restart to register the new helper and templates. Allow five minutes for grid
permission to become ready. Check a real data-loss/recovery event before relying
on notification timing. No deployment is performed by these repository edits.

Template availability/delay behavior: [Home Assistant template documentation](https://www.home-assistant.io/integrations/template/).
