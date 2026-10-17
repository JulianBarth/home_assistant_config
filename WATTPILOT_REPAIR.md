# Wattpilot connection repair — 17 October 2026

The installed Wattpilot 0.3.9 integration returned from failed setup without
closing its bundled client's reconnect worker. Home Assistant setup retries and
the five-minute reconnect watchdog could therefore accumulate orphan sockets.
The live log contained repeated timeouts, connection resets and authentication
errors. A successful connection after cleanup establishes that the configured
credentials still work; the earlier password errors alone were not sufficient
to establish an incorrect stored password.

## Applied repair

- Every failed `async_ConnectCharger` attempt disconnects its client before
  returning, including incomplete initialization and connection exceptions.
- The bundled client has one reconnect owner, guards against duplicate workers,
  and uses an interruptible stop event instead of an unconditional backoff sleep.
- A new hello resets the initialization flag so cached status cannot make a new
  connection appear initialized prematurely.
- The setup exception path initializes its client variable and awaits cleanup.

Production files changed under `/config/custom_components/wattpilot`:
`__init__.py`, `utils.py`, `wattpilot/src/wattpilot/__init__.py`.
The connection repair preserves credentials, entity IDs and registry entries.

## Verification

Eight behavioral regression tests pass, covering unsuccessful setup cleanup,
repeated failures, successful connection preservation, duplicate connect calls,
shutdown during backoff, and shutdown during an active socket run. All three
Python sources parse. `ha core check` passed before the restart. SHA-256 readback
of all three production files matches the tested files. Home Assistant restarted
successfully. Its normally authenticated browser UI shows
`sensor.wattpilot_carconnected = charging`, with activity recorded at 22:03:35
Europe/Berlin, and the dashboard reports approximately 10.7 kW wallbox power.

The source patch is in `tools/wattpilot-connection-repair.patch`. It is a
zero-context patch against the installation baseline; apply it from the
configuration root using `git apply --unidiff-zero` after checking the target
version and keeping a backup. To test an
extracted copy of the integration without HA or third-party dependencies:

```sh
python3 tools/test_wattpilot_connection.py /path/to/custom_components/wattpilot
```

## Rollback and maintenance

Production rollback archive:
`/config/backups/wattpilot-repair-20261017/baseline.tar`.
Restore its `wattpilot` directory under `/config/custom_components`, run
`ha core check`, and restart Home Assistant if rollback is needed.
An integration/HACS update may overwrite these local corrections; compare its
connection lifecycle with this patch before assuming the repair is retained.

At 22:07:00 the controller logged `car_charging_only`, stable car detection
true, discharge protection true, approximately 10.74 kW wallbox charging,
0 W battery discharge and a 4.6% discharge limit. This verifies the downstream
protection after the configured three-minute hysteresis.

At 22:07:14 grid telemetry separately became `uncertain`; the existing guard
successfully commanded the connected wallbox to Eco. This was not a Wattpilot
disconnection. The final sensor dialog remained available and reported
`complete`. No new Wattpilot connection or authentication errors appeared
in the post-startup log window examined through this check.


## Follow-up: manual Default overridden during grid recovery

The restored connection exposed another existing behavior: the wallbox watchdog
used `grid_control_ready`, which stays off for five minutes after grid readings
recover. At 22:08:54 valid grid evidence returned, but this condition would still
force a manual Default selection back to Eco until the delayed gate opened.

The watchdog now uses the current `grid_connection_status` and triggers on its
changes. Manual Default is allowed when the current status is `grid`. Unknown,
unavailable, uncertain and island readings still enforce Eco. The five-minute
battery and automated cheap-grid recovery gate is unchanged. Regression tests
reproduce manual Default being rejected during valid-grid recovery and verify
that unsafe current evidence takes priority over a stale delayed permission.

Follow-up deployment verified: all 59 Python regression tests pass; `ha core
check` succeeded; live automations SHA-256 matches the reviewed file
`19ac1a33b129b1358125ca0f286c560daed02b87e8cbbc653659535c8b9b6127`.
Automations were reloaded through the normally authenticated HA YAML tools,
without a Core restart. Manual Default was then selected while grid readings
were valid and the five-minute battery gate was still off. It remained Default
after 25 seconds and the car resumed charging at approximately 10.68 kW.
A local verification screenshot is excluded from the public repository.
Rollback automation copy:
`/config/backups/wattpilot-manual-default-20261017/automations.yaml`.
