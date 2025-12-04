# Battery Hold SOC Feature Documentation

## Overview

This document describes the new **Hold SOC** (State of Charge) feature that allows the battery to remain steady at a specific SOC level without cycling between charging and discharging. This approach is more efficient than the traditional method of alternating between charging and discharging to maintain a target SOC.

## Problem Statement

The previous system maintained battery SOC by cycling between charging and discharging states:
- When SOC dropped below target: Start charging
- When SOC reached target: Stop charging
- Result: Battery would continuously charge/discharge around the target, causing:
  - Energy losses due to round-trip inefficiency (~10% loss)
  - Increased battery wear from cycling
  - Higher power draw from grid during charge cycles

## Solution: Hold SOC Mode

The Hold SOC mode tells the inverter to keep the battery at its current level by:
- Setting both charge rate (InWRte) to 0%
- Setting both discharge rate (OutWRte) to 0%
- Enabling Storage Control Mode (StorCtl_Mod = 3)

This causes the battery to enter a "HOLDING" state where it neither charges nor discharges.

## Modbus Registers

### Key Registers for Hold SOC

| Register | Name | Description | Values |
|----------|------|-------------|---------|
| 40358 | StorCtl_Mod | Storage Control Mode | 0=Off, 3=On |
| 40364 | ChaSt | Charging State | 1=OFF, 2=EMPTY, 3=DISCHARGING, 4=CHARGING, 5=FULL, **6=HOLDING**, 7=TESTING |
| 40365 | OutWRte | Discharge Rate | 0-10000 (0-100% in 0.01% increments) |
| 40366 | InWRte | Charge Rate | 0-10000 (0-100% in 0.01% increments) |
| 40360 | MinRsvPct | Minimum Reserve % | Minimum SOC level (scaled) |

### Related Registers (Reference)

| Register | Name | Description |
|----------|------|-------------|
| 40361 | Battery SOC | Current State of Charge (scaled 0-10000) |
| 40355 | WChaMax | Maximum Allowed Discharge Power |

## Implementation

### New Scripts Added

#### 1. `hold_battery_soc`
Primary hold SOC script that sets both charge and discharge to 0%.

```yaml
hold_battery_soc:
  alias: "Hold Battery SOC"
  description: "Keep battery steady at current SOC (most efficient - no cycling)"
  sequence:
    - service: switch.turn_on
      target:
        entity_id: switch.StorCtl_Mod
    - service: modbus.write_register
      data:
        hub: fronius1
        unit: 1
        address: 40365
        value: 0  # Disable discharge
    - service: modbus.write_register
      data:
        hub: fronius1
        unit: 1
        address: 40366
        value: 0  # Disable charge
```

**Use when:** You want maximum efficiency and the battery to stay completely steady.

#### 2. `hold_battery_soc_minimal`
Alternative hold SOC script with 1% charge/discharge allowance for minor adjustments.

```yaml
hold_battery_soc_minimal:
  alias: "Hold Battery SOC (Minimal Rate)"
  description: "Keep battery steady with minimal 1% charge/discharge allowance"
  sequence:
    - service: switch.turn_on
      target:
        entity_id: switch.StorCtl_Mod
    - service: modbus.write_register
      data:
        hub: fronius1
        unit: 1
        address: 40365
        value: 100  # 1% discharge
    - service: modbus.write_register
      data:
        hub: fronius1
        unit: 1
        address: 40366
        value: 100  # 1% charge
```

**Use when:** You want the battery to stay mostly steady but allow minor corrections if SOC drifts slightly.

## Testing Scripts

### Test Functions

Before deploying hold SOC in your main automation, use these test scripts to verify proper operation:

#### 1. `test_hold_soc_zero_rates`
Tests hold SOC with zero charge/discharge rates.

**How to test:**
1. Run the script from Home Assistant
2. Monitor battery SOC and charging state for 5-10 minutes
3. Verify:
   - Battery SOC stays steady (±1%)
   - Charging State shows "HOLDING" or "OFF"
   - Battery is not actively charging or discharging
4. Run `stop_hold_soc_test` to restore normal operation

#### 2. `test_hold_soc_minimal_rates`
Tests hold SOC with 1% minimal rates.

**How to test:**
1. Run the script from Home Assistant
2. Monitor battery SOC and charging state for 5-10 minutes
3. Verify:
   - Battery SOC stays mostly steady (±2%)
   - Small adjustments may occur but no active cycling
4. Run `stop_hold_soc_test` to restore normal operation

#### 3. `stop_hold_soc_test`
Stops any hold SOC test and restores normal battery operation.

**Always run this** after completing your tests to ensure the battery returns to normal automated control.

#### 4. `verify_hold_soc_status`
Displays current battery status and modbus register values.

**Use this to:**
- Check if hold mode is active
- Verify register values are correct
- Troubleshoot issues

Expected values when hold mode is active:
- StorCtl_Mod: 3 (ON)
- Charging State: HOLDING or OFF
- Discharge Rate: 0% or very low
- Charge Rate: 0% or very low

## Usage Guide

### Testing Phase (Before Algorithm Integration)

1. **Initial Test - Zero Rates**
   ```
   1. Note current battery SOC
   2. Run: script.test_hold_soc_zero_rates
   3. Wait 10 minutes
   4. Check: Battery SOC should be unchanged (±1%)
   5. Run: script.stop_hold_soc_test
   ```

2. **Alternative Test - Minimal Rates**
   ```
   1. Note current battery SOC
   2. Run: script.test_hold_soc_minimal_rates
   3. Wait 10 minutes
   4. Check: Battery SOC mostly steady (±2%)
   5. Run: script.stop_hold_soc_test
   ```

3. **Verify Status**
   ```
   Run: script.verify_hold_soc_status
   Check notification for current values
   ```

### Integration into Automation

After successful testing, the hold SOC scripts can be integrated into the battery automation algorithm. The recommended approach:

**Current Approach (Less Efficient):**
```
Target SOC = 80%
Current SOC = 75% → Start charging → SOC reaches 80% → Stop charging
SOC drifts to 79% → Nothing happens
SOC drifts to 78% → Start charging again
Result: Constant cycling, energy loss
```

**New Hold SOC Approach (Efficient):**
```
Target SOC = 80%
Current SOC = 75% → Start charging → SOC reaches 80% → Switch to HOLD mode
Battery stays at 80% without cycling
Result: No cycling, no energy loss, reduced wear
```

## Integration Example

Here's how to modify the charging automation to use hold SOC:

```yaml
# When target SOC is reached, switch to hold mode instead of stopping
- alias: "Switch to Hold Mode When Target Reached"
  trigger:
    - platform: template
      value_template: >
        {{ states('sensor.batterie_soc') | float >= 
           states('input_number.battery_target_soc') | float }}
  condition:
    - condition: state
      entity_id: input_boolean.battery_charging_active
      state: "on"
  action:
    # Switch from charging to holding
    - service: script.turn_on
      target:
        entity_id: script.hold_battery_soc
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.battery_charging_active
    - service: input_boolean.turn_on
      target:
        entity_id: input_boolean.battery_holding_active  # New flag
```

## Efficiency Comparison

### Traditional Cycling Method
- Battery cycles around target SOC
- Round-trip efficiency: ~90%
- Energy loss per cycle: ~10%
- Battery wear: Higher due to constant cycling
- Grid interaction: Continuous small draws

### Hold SOC Method
- Battery stays steady at target SOC
- No round-trip losses
- Energy loss: Minimal (only self-discharge)
- Battery wear: Minimal (no cycling)
- Grid interaction: Only when needed

**Example Savings:**
- Traditional: 5 kWh charged/discharged per day = 0.5 kWh lost
- Hold SOC: 5 kWh charged once, held = ~0.05 kWh lost (self-discharge)
- **Savings: ~0.45 kWh/day = ~164 kWh/year**

At 30 cents/kWh: **~50 EUR/year savings**

## Troubleshooting

### Issue: Battery not holding, still charging/discharging

**Check:**
1. Run `verify_hold_soc_status` - are rates set to 0?
2. Is StorCtl_Mod active (value = 3)?
3. Is another automation overriding the hold commands?

**Fix:**
- Ensure no conflicting automations are running
- Verify modbus connection is stable
- Check inverter firmware supports hold mode

### Issue: Charging State not showing "HOLDING"

**Note:** Some firmware versions may show "OFF" instead of "HOLDING" when rates are 0. This is normal.

**Verify:** Check that SOC is actually steady even if state shows "OFF"

### Issue: Battery slowly drifting from target SOC

**Solution:** Use `hold_battery_soc_minimal` instead of `hold_battery_soc`
- The 1% rates allow minor corrections
- Battery will self-adjust small drifts

### Issue: Can't exit hold mode

**Fix:** Run `stop_hold_soc_test` or `set_regular_charge`
- This restores normal rates and disables StorCtl_Mod

## Safety Considerations

1. **Always test first** before integrating into main automation
2. **Monitor battery** during initial tests to ensure proper behavior
3. **Set timeout** in automation to exit hold mode after certain period
4. **Emergency override** should be available to restore normal operation
5. **Don't use hold mode** when:
   - Battery SOC is critically low (< 10%)
   - Solar production is high (battery should accept charge)
   - Grid prices are very favorable (should charge opportunistically)

## Future Enhancements

Potential improvements to the hold SOC feature:

1. **Adaptive Hold**: Automatically adjust hold behavior based on:
   - Solar forecast
   - Price predictions
   - Historical usage patterns

2. **Smart Exit**: Exit hold mode when:
   - Prices drop significantly
   - Solar production increases
   - Home consumption changes

3. **Hysteresis**: Add SOC tolerance band (e.g., hold between 78-82% when target is 80%)

4. **Logging**: Track hold mode efficiency and savings

## References

- Fronius Symo Gen24 Modbus TCP Documentation
- SunSpec Alliance Modbus Interface Specifications
- Home Assistant Modbus Integration Documentation

## Credits

Implementation based on analysis of Fronius Gen24 Modbus registers and testing with BYD Battery Pack.

## License

SPDX-License-Identifier: BSD-3-Clause

Copyright (c) 2024, Julian Bartholomeyczik
All rights reserved.
