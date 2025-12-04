# Hold SOC Quick Reference Card

## Quick Test Instructions

### 1. Basic Test (Recommended First)
```
1. Go to Home Assistant → Scripts
2. Run: "TEST: Hold SOC with Zero Rates"
3. Wait 5-10 minutes
4. Check battery SOC - should stay steady
5. Run: "TEST: Stop Hold SOC Test" when done
```

### 2. Verify It Worked
```
Run: "TEST: Verify Hold SOC Status"
Check notification - should show:
✓ Charging State: HOLDING or OFF
✓ Both rates: 0% or very low
✓ StorCtl_Mod: 3 (ON)
```

## Available Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `hold_battery_soc` | Hold at current SOC (0% rates) | Maximum efficiency |
| `hold_battery_soc_minimal` | Hold with 1% rates | Allow minor adjustments |
| `test_hold_soc_zero_rates` | Test zero rate hold | First test |
| `test_hold_soc_minimal_rates` | Test 1% rate hold | Alternative test |
| `stop_hold_soc_test` | Exit test mode | After any test |
| `verify_hold_soc_status` | Check current status | Troubleshooting |

## Key Modbus Registers

| Address | Name | Value for Hold | Description |
|---------|------|----------------|-------------|
| 40358 | StorCtl_Mod | 3 | Enable storage control |
| 40365 | OutWRte | 0 or 100 | Discharge rate (0% or 1%) |
| 40366 | InWRte | 0 or 100 | Charge rate (0% or 1%) |
| 40364 | ChaSt | 6 | Should show HOLDING |

## Expected Behavior

### When Hold SOC Active:
- ✓ Battery SOC stays steady (±1-2%)
- ✓ No active charging or discharging
- ✓ ChaSt shows "HOLDING" or "OFF"
- ✓ Grid draw minimal (only house consumption)

### When Hold SOC NOT Working:
- ✗ Battery SOC changing >3%
- ✗ Active charge/discharge cycles
- ✗ ChaSt shows "CHARGING" or "DISCHARGING"
- ✗ Registers not at expected values

## Integration Steps

After successful testing:

1. **Add hold mode to automation:**
   - Replace `stop_battery_charging` with `hold_battery_soc`
   - When target SOC reached → Switch to hold mode

2. **Add exit conditions:**
   - Exit hold when prices drop significantly
   - Exit hold when solar production increases
   - Exit hold on manual override

3. **Monitor for 24-48 hours:**
   - Check battery behavior
   - Verify efficiency improvements
   - Adjust if needed

## Benefits

| Metric | Traditional Cycling | Hold SOC Mode | Improvement |
|--------|-------------------|---------------|-------------|
| Round-trip loss | ~10% per cycle | Minimal | ~90% reduction |
| Battery wear | High (constant cycling) | Low (steady state) | Significant |
| Energy cost | Higher | Lower | ~50 EUR/year* |
| Grid interaction | Continuous | Only when needed | Reduced |

*Based on typical usage patterns

## Troubleshooting Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| Battery not holding | Run `verify_hold_soc_status` → Check values |
| Can't exit hold mode | Run `stop_hold_soc_test` |
| State shows "OFF" not "HOLDING" | Normal - Check if SOC is steady |
| Battery drifting | Use `hold_battery_soc_minimal` instead |

## Safety Note

⚠️ Always run test scripts first before integrating into main automation!

## Need Help?

See full documentation: `HOLD_SOC_DOCUMENTATION.md`
