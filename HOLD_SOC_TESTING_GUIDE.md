# Hold SOC Testing Guide

## Overview

This guide helps you test the new "Hold SOC" battery control functionality before deploying it to your production automations. The hold SOC feature is more efficient than alternating between charging and discharging to maintain a target State of Charge (SoC).

## What is Hold SOC?

**Current Method (Inefficient):**
- Battery charges when SoC drops below target
- Battery discharges when SoC exceeds target
- This cycling causes energy losses due to battery inefficiency

**New Method (Efficient):**
- Battery enters "HOLDING" state
- Minimal charge/discharge rates prevent cycling
- Battery stays stable at current SoC with minimal energy loss

## How It Works

The hold SOC functionality uses Modbus registers to control the Fronius Gen24 Plus inverter:

- **Register 40358 (StorCtl_Mod)**: Enables external battery control (value: 3)
- **Register 40365 (OutWRte)**: Discharge rate in 0.01% increments
- **Register 40366 (InWRte)**: Charge rate in 0.01% increments

To hold the battery at target SoC while allowing solar charging:
1. Enable external control (StorCtl_Mod = ON)
2. Set discharge rate to 1% (value: 100) - prevents discharge below target
3. Set charge rate to 100% (value: 10000) - allows solar charging

This setting prevents the battery from discharging below target while still accepting solar power for charging.

## Testing Procedure

### Prerequisites

1. Access to Home Assistant UI
2. Ability to call scripts (Developer Tools → Services)
3. Ability to monitor sensors (Home Assistant dashboard)
4. Battery SoC should be at a reasonable level (20-80%)

### Step 1: Check Initial Status

**Script to Run:** `script.test_hold_soc_status`

**How to Run:**
1. Go to Developer Tools → Services
2. Select service: `script.test_hold_soc_status`
3. Click "CALL SERVICE"

**What to Check:**
- Note current Battery SoC
- Note current Charging State
- Note current Battery Power
- Verify StorCtl_Mod is currently OFF

**Expected Values (Before Test):**
```yaml
Battery SoC: [your current SoC]%
Charging State: OFF, CHARGING, or DISCHARGING
ChaSt Value: 1, 3, 4, or 5
Battery Power: [varies based on current state]
StorCtl_Mod: off
```

### Step 2: Enable Hold SOC Mode

**Script to Run:** `script.test_hold_soc_enable`

**How to Run:**
1. Go to Developer Tools → Services
2. Select service: `script.test_hold_soc_enable`
3. Click "CALL SERVICE"

**What Happens:**
- Script enables external battery control
- Sets charge and discharge rates to 1%
- Creates a notification with instructions

**Expected Behavior (Wait 2-3 minutes):**
```yaml
Charging State: HOLDING
ChaSt Value: 6
Battery Power: ~0W (±100W is acceptable)
StorCtl_Mod: on
Discharge Rate: 1%
Charge Rate: 1%
Battery SoC: Should remain stable (±1% variation over 10 minutes is normal)
```

### Step 3: Monitor the Battery

**Duration:** 10-15 minutes

**What to Monitor:**
1. **sensor.charging_state** - Should show "HOLDING"
2. **sensor.batterie_soc** - Should remain relatively stable
3. **sensor.battery_power** - Should be near 0W
4. **sensor.reading_energy_main_meter** - Grid power should reflect only home consumption

**Script to Check Status:** `script.test_hold_soc_status`
- Run this every 3-5 minutes to monitor progress
- Check the notification panel for status updates

### Step 4: Disable Hold SOC Mode

**Script to Run:** `script.test_hold_soc_disable`

**How to Run:**
1. Go to Developer Tools → Services
2. Select service: `script.test_hold_soc_disable`
3. Click "CALL SERVICE"

**What Happens:**
- Script restores normal charge/discharge rates (100%)
- Disables external battery control
- Creates a notification confirming deactivation

**Expected Behavior (Wait 2-3 minutes):**
```yaml
Charging State: Normal operation (OFF, CHARGING, or DISCHARGING based on system needs)
StorCtl_Mod: off
Battery Power: Returns to normal operation
Battery SoC: Will change based on solar production and consumption
```

## Troubleshooting

### Issue: Battery Does Not Enter HOLDING State

**Possible Causes:**
1. Modbus communication issue
2. Battery is actively needed (high consumption or solar charging)
3. Register values not properly set

**Solutions:**
- Check Fronius inverter connectivity (IP: 192.168.178.92)
- Verify modbus integration is working: Check `sensor.ChaSt` availability
- Try running `test_hold_soc_enable` again
- Check Home Assistant logs for Modbus errors

### Issue: Battery SoC Still Changes Significantly

**Possible Causes:**
1. Home consumption is very high or very low
2. Solar production is significantly affecting the battery
3. Minimal charge/discharge rates (1%) may need adjustment

**Solutions:**
- This is somewhat expected if consumption/production is high
- Consider testing during stable conditions (evening with moderate consumption)
- If SoC varies more than ±2% in 10 minutes, the holding is still more efficient than cycling

### Issue: Cannot Return to Normal Operation

**Solutions:**
1. Run `script.test_hold_soc_disable` again
2. Manually toggle `switch.StorCtl_Mod` to OFF in Home Assistant
3. Restart Home Assistant if needed
4. As a last resort, restart the Fronius inverter

### Issue: Modbus Register Values Not Changing

**Solutions:**
- Check that no other automation is overriding the values
- Verify you have write permissions to the Modbus registers
- Check the Fronius inverter is not in a protected mode

## Test Results Documentation

After completing the test, document your results:

### Test Log Template

```
Date/Time: _______________
Initial Battery SoC: _____%
Test Duration: _____ minutes

Results:
- Did battery enter HOLDING state? YES / NO
- ChaSt Value during hold: _____
- Battery Power during hold: _____ W
- SoC variation during 10-minute hold: _____ %
- Any errors or issues: _________________

Conclusion:
- Test PASSED / FAILED
- Ready for production use: YES / NO
- Notes: _________________________________
```

## Next Steps After Successful Testing

Once you've verified the hold SOC functionality works correctly:

1. **Review the production script:** `script.hold_battery_soc`
2. **Integrate into automations:** Update your battery control automations to use hold mode instead of cycling
3. **Monitor efficiency:** Track battery cycles and solar charging during hold mode
4. **Optimize settings:** The discharge rate of 1% prevents drain while 100% charge rate allows solar charging

## Integration Example

To integrate hold SOC into your battery automation:

```yaml
# Example: Hold battery during certain conditions
- alias: "Hold Battery at Target SoC"
  trigger:
    - platform: template
      value_template: >
        {% set current_soc = states('sensor.batterie_soc') | float %}
        {% set target_soc = states('input_number.battery_target_soc') | float %}
        {{ (current_soc >= target_soc - 2) and (current_soc <= target_soc + 2) }}
  action:
    - service: script.hold_battery_soc
```

## Technical Details

### Modbus Register Reference

| Register | Name | Description | Hold Mode Value |
|----------|------|-------------|----------------|
| 40358 | StorCtl_Mod | Storage Control Mode | 3 (external control) |
| 40365 | OutWRte | Discharge Rate | 100 (1%) - prevents discharge |
| 40366 | InWRte | Charge Rate | 10000 (100%) - allows solar charging |
| 40364 | ChaSt | Charging State | 4 (CHARGING) or 6 (HOLDING) |

### Charging State Values

| Value | State | Description |
|-------|-------|-------------|
| 1 | OFF | Battery not active |
| 2 | EMPTY | Battery depleted |
| 3 | DISCHARGING | Battery providing power |
| 4 | CHARGING | Battery receiving power |
| 5 | FULL | Battery at 100% |
| 6 | HOLDING | Battery holding current SoC |
| 7 | TESTING | Diagnostic mode |

## Support

If you encounter issues during testing:

1. Check the Home Assistant logs (Settings → System → Logs)
2. Verify Modbus integration is working properly
3. Ensure Fronius inverter firmware is up to date
4. Review this guide's troubleshooting section
5. Document the issue and test results for further investigation

## Safety Notes

- Always test during safe conditions (battery SoC 20-80%)
- Monitor the system during initial tests
- Keep the test duration short (10-15 minutes) for initial validation
- Have the disable script ready if needed
- Do not test during critical times (e.g., grid outages, peak demand)

---

**Version:** 1.0  
**Last Updated:** 2025-12-04  
**Compatible With:** Fronius Gen24 Plus 6.0, Home Assistant with Modbus integration
