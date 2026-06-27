# Battery Surplus Discharge Policy

## Intent

The battery should normally protect the house reserve and avoid feeding car charging. Car charging is reimbursed by the company at market rate, so the automation should not shift a large or unclear part of car energy onto the home battery.

There is one useful exception: on strong-solar nights, the battery can contain more energy than the house will plausibly use before solar production starts again. In that case, preserving all surplus energy is wasteful because the next solar window will recharge the battery and the excess state of charge only reduces PV headroom.

The surplus discharge policy allows a small, capped, price-aware amount of extra battery discharge only when that excess is clear.

## Decision Model

The new `sensor.battery_surplus_discharge_power` calculates an extra discharge allowance in watts.

It estimates:

```text
available_above_reserve_wh =
  max(current_soc - default_reserve_soc, 0) * battery_capacity_wh

surplus_wh =
  available_above_reserve_wh
  - expected_house_consumption_until_solar
  - safety_margin_wh
```

The sensor only produces a non-zero value when all guardrails pass:

- Current time is in the evening-to-solar or night-to-solar window.
- Inverter data is valid.
- Manual charging and active battery charging are off.
- Current SoC is at least 5 percentage points above the reserve.
- Forecast solar recovery is strong enough to refill meaningful battery headroom.
- `surplus_wh` is positive after the safety margin.

## Price Modifier

Electricity price is deliberately a modifier, not the main trigger. The algorithm first proves there is surplus energy, then uses the current price percentile to decide how much of that surplus may be spent.

Policy:

```text
negative price:    0.00  keep car charging on grid
bottom 25% price:  0.15  minimal surplus use
bottom 50% price:  0.35  moderate surplus use
bottom 80% price:  0.50  stronger surplus use
top 20% price:     0.75  strongest capped surplus use
price invalid:     0.25  cautious fallback
```

This keeps company reimbursement burden low when grid energy is cheap, while allowing more surplus use when grid energy is expensive and the battery would otherwise still reach solar start with unused energy.

## Car Charging Integration

The existing car-charging protection remains the baseline:

```text
allowed_battery_power = house_load * 1.15
```

The surplus policy only adds a bounded extra allowance:

```text
allowed_battery_power =
  house_load * 1.15
  + sensor.battery_surplus_discharge_power
```

The resulting power is converted to the Fronius discharge limit percentage by `sensor.discharge_limit_percentage` and applied by `script.set_dynamic_discharge_limit`.

## Tunable Helpers

- `input_number.battery_surplus_safety_margin_wh`
  - Default used by templates: `700 Wh`
  - A value of `0` also falls back to `700 Wh`.
  - Larger values make the policy more conservative.

- `input_number.battery_surplus_extra_discharge_cap_w`
  - Default used by templates: `1000 W`
  - A value of `0` also falls back to `1000 W`.
  - This is the practical fairness cap for extra car-related discharge.

## Operational Notes

Start conservatively:

```text
safety margin: 700-1000 Wh
extra discharge cap: 500-1000 W
```

After one or two summer nights, inspect `battery_algorithm.log`:

- `car.surplus_extra_w`
- morning SoC at solar start
- whether any grid import happened before solar start
- whether car charging caused excessive battery draw

If the battery still reaches solar start far above reserve, increase the extra cap slightly. If it reaches reserve too early, increase the safety margin or reduce the cap.
