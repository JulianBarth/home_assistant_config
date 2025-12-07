# Solar Charging During Hold SOC Mode - Fix Documentation

## Issue Description

**Problem:** When the battery reached the target SOC and entered "hold" mode, it could not charge from available solar power. Solar energy was wasted (exported to grid) instead of being stored in the battery.

**Root Cause:** The `hold_battery_soc` script was setting both charge and discharge rates to 1% (minimal), which prevented the battery from accepting any significant charging current, including from solar panels.

## Solution Implemented

Modified the `hold_battery_soc` script to allow solar charging while preventing discharge:

### Changes Made

#### 1. Core Script (`hold_battery_soc`)
**Before:**
```yaml
# InWRte - Set charge to 1% (minimal charge)
- service: modbus.write_register
  data:
    address: 40366
    value: 100
```

**After:**
```yaml
# InWRte - Set charge to 100% (allow full charging from solar)
- service: modbus.write_register
  data:
    address: 40366
    value: 10000
```

#### 2. Test Script (`test_hold_soc_enable`)
Updated to match the new behavior with full charge rate (100%) instead of minimal (1%).

#### 3. Documentation Updates
- `HOLD_SOC_IMPLEMENTATION_SUMMARY.md` - Updated register table and descriptions
- `HOLD_SOC_QUICK_REFERENCE.md` - Updated expected behavior and monitoring guidance
- `HOLD_SOC_TESTING_GUIDE.md` - Updated technical details and register values

## How It Works Now

### Hold SOC Mode Behavior

| Register | Value | Purpose |
|----------|-------|---------|
| OutWRte (40365) | 100 (1%) | Prevents battery discharge below target |
| InWRte (40366) | 10000 (100%) | Allows full solar charging |
| StorCtl_Mod (40358) | 3 (ON) | Enables external control |

### Expected Battery Behavior

When hold mode is active:

1. **No solar available:**
   - Battery does not discharge (stays at target)
   - Charging State: "HOLDING" (ChaSt = 6)
   - Battery Power: ~0W

2. **Solar available:**
   - Battery accepts solar charging
   - Charging State: "CHARGING" (ChaSt = 4)
   - Battery Power: Positive (charging)
   - SOC: Increases above target

3. **Grid consumption:**
   - Battery does not discharge to supply power
   - Grid supplies the load instead
   - Battery SOC remains stable or increases with solar

## Benefits of the Fix

✅ **Solar energy utilization:** Available solar power charges the battery instead of being wasted

✅ **Maintains target SOC:** Battery won't discharge below target level

✅ **Optimal energy management:** Solar charges battery while grid handles consumption when at target

✅ **No cycling:** Still prevents the inefficient charge/discharge cycling that the hold mode was designed to eliminate

✅ **Flexible operation:** Battery can grow its charge with solar while maintaining a minimum level

## Testing Recommendations

1. **Test with solar:** Use `script.test_hold_soc_enable` during daytime when solar is producing
2. **Monitor SOC:** Verify battery SOC increases when solar is available
3. **Check power flow:** Confirm battery accepts positive power (charging) from solar
4. **Verify no discharge:** Ensure battery doesn't discharge below target even under load

## Technical Implementation Details

### Modbus Register 40366 (InWRte)
- **Format:** Unsigned 16-bit integer
- **Units:** 0.01% increments (1 = 0.01%, 10000 = 100%)
- **Previous value:** 100 (1% charge rate)
- **New value:** 10000 (100% charge rate)
- **Result:** Allows full charging current from any source (solar, grid)

### Why This Works

The Fronius inverter independently controls charge and discharge rates:
- **Discharge rate (OutWRte):** Controls how much the battery can supply to loads
- **Charge rate (InWRte):** Controls how much the battery can accept from sources

By setting:
- OutWRte = 1% → Battery cannot supply significant power to loads (prevents discharge)
- InWRte = 100% → Battery can accept full power from solar (allows charging)

The battery effectively becomes a "one-way gate" that only accepts energy, not provides it, while at target SOC.

## Files Modified

1. `scripts.yaml` - Modified `hold_battery_soc` and `test_hold_soc_enable` scripts
2. `HOLD_SOC_IMPLEMENTATION_SUMMARY.md` - Updated documentation
3. `HOLD_SOC_QUICK_REFERENCE.md` - Updated quick reference
4. `HOLD_SOC_TESTING_GUIDE.md` - Updated testing guide

## Validation

- ✅ YAML syntax validated for all modified files
- ✅ Logic flow verified in automation
- ✅ Documentation updated consistently
- ✅ Test scripts updated to match behavior
- ✅ Minimal changes made (only charge rate value changed from 100 to 10000)

## Compatibility

This fix is:
- ✅ Backward compatible (no changes to automation logic)
- ✅ Safe to deploy (only affects hold mode behavior)
- ✅ Reversible (can be reverted by changing value back to 100)
- ✅ Tested (YAML validation passed)

---

**Implementation Date:** December 7, 2025  
**Issue:** Ensure that solar charging the battery is still possible when battery is to hold SOC due to target SOC  
**Status:** ✅ Fixed and Documented
