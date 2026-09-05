# Home-battery charging: target completion and reduced rate

This describes the current coordinator behavior. Older hold-SoC documents describe earlier implementations.

Manual home-battery charging (`input_boolean.manual_battery_charge`) overrides price optimization and the battery automation switch until `manual_charge_target_soc` is reached. It does not override invalid inverter data or grid loss. Manual Wattpilot charging is separate: reaching the home-battery target does not stop the car or change its charging mode.

The coordinator evaluates stop conditions before charging modes. Manual requests use the manual target directly, including requests made when the battery is already above that target. Automatic charging stops at the stored target or, with valid prices, a lower computed target. Stop targets have no positive hysteresis; adding hysteresis would make a 100% target unreachable. Start hysteresis remains unchanged.

All three charging paths (manual, automatic, and car plus battery) synchronously call `script.charge_battery_to_target` after setting the target helper. Within `battery_hold_threshold` percentage points below targets under 98%, the script requests 50% charging. Targets of 98% or higher retain the existing full-rate policy. The decision uses fresh helper/SoC values, including on the first call, rather than waiting for a dependent template sensor to update.

## Fronius GEN24 hardware behavior

With `StorCtl_Mod=3`, OutWRte and InWRte define a signed power window relative to WChaMax. They do not program an upper SoC cutoff:

| Request | OutWRte | InWRte |
| --- | ---: | ---: |
| Full forced charge | -80% | +100% |
| Reduced forced charge | -50% | +50% |
| Normal rates | +100% | +100% |

The reduced request is 50% of WChaMax, not 50% of the current measured charging power. Actual power remains subject to inverter and BMS limits. This is a two-level charge request, not a replacement for the BMS's own charge taper.

Writes must preserve `-InWRte <= OutWRte`. The full-rate script raises InWRte before applying the -80% floor. The reduced-rate script first widens InWRte to 100% (also allowing entry from a frozen battery), then sets OutWRte to -50%, then narrows InWRte to 50%. Direct script calls wait for writes to finish; queued coordinator runs avoid interrupting a register sequence or dropping a target-completion event during a write.

At completion, forced charging is removed. If car protection is needed, the coordinator applies the dynamic discharge limit directly; otherwise it restores normal rates and disables storage control. It then clears the charging/manual flags. Solar charging and native inverter behavior can continue after forced charging ends. The software cutoff depends on the 15-second SoC polling and command latency, so it is not an exact hardware-enforced upper SoC limit.

References: [Fronius GEN24 Basic Storage Control Model](https://manuals.fronius.com/html/4204102649/en-US.html), [Home Assistant synchronous script calls](https://www.home-assistant.io/integrations/script/#waiting-for-script-to-complete).

## Validation

Install `tests/requirements.txt` into a virtual environment, then run:

```sh
python -m unittest discover -s tests -v
```

The tests render the actual YAML decision templates and interpret the affected action sequences. They cover manual/automatic completion, price overrides, reduced-rate starts, car continuity, grid/data failure, and validity of every intermediate register window. They do not connect to the inverter or emulate Home Assistant's event scheduling. Run Home Assistant configuration validation and observe a charge transition after deployment.
