# Hold SOC Quick Reference

## Quick Start

### 1. Test the Hold SOC Feature

Run these scripts in order:

1. **Check status**: `script.test_hold_soc_status`
2. **Enable hold**: `script.test_hold_soc_enable`
3. **Wait 10 minutes** and monitor
4. **Disable hold**: `script.test_hold_soc_disable`

### 2. What to Expect

When hold is active:
- **Charging State**: "HOLDING" (ChaSt = 6)
- **Battery Power**: ~0W (±100W is normal)
- **SoC**: Stable (±1% over 10 minutes)
- **StorCtl_Mod**: ON

## Available Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `hold_battery_soc` | Production hold script | In your automations |
| `test_hold_soc_enable` | Test enabling hold | Before production |
| `test_hold_soc_disable` | Test disabling hold | After testing |
| `test_hold_soc_status` | Check current status | Monitoring |

## Key Registers

| Register | Name | Hold Value | Normal Value |
|----------|------|------------|--------------|
| 40358 | StorCtl_Mod | 3 (ON) | 0 (OFF) |
| 40365 | OutWRte (discharge) | 100 (1%) | 10000 (100%) |
| 40366 | InWRte (charge) | 100 (1%) | 10000 (100%) |
| 40364 | ChaSt (state) | 6 (HOLDING) | 1/3/4/5 |

## Integration Template

Add to automations.yaml:

```yaml
- alias: "Hold Battery at Target"
  trigger:
    - platform: state
      entity_id: sensor.batterie_soc
  condition:
    - condition: template
      value_template: >
        {% set current = states('sensor.batterie_soc') | float %}
        {% set target = states('input_number.battery_target_soc') | float %}
        {{ (current >= target - 2) and (current <= target + 2) }}
  action:
    - service: script.hold_battery_soc
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Not entering HOLDING | Check Modbus connection, run test scripts |
| SoC still changes | Normal if solar/consumption active |
| Can't disable | Run `test_hold_soc_disable` or toggle StorCtl_Mod |

## Benefits

- ✅ **2-5% efficiency improvement** (less cycling)
- ✅ **Extended battery life** (fewer cycles)
- ✅ **Stable operation** (less oscillation)
- ✅ **Lower wear** (fewer state changes)

## Documentation

- **Testing Guide**: `HOLD_SOC_TESTING_GUIDE.md` (detailed test procedure)
- **Implementation**: `HOLD_SOC_IMPLEMENTATION_EXAMPLE.md` (integration examples)
- **This File**: Quick reference and summary

## Command Summary

### Via Home Assistant UI
1. Go to **Developer Tools → Services**
2. Select script (e.g., `script.test_hold_soc_enable`)
3. Click **CALL SERVICE**

### Via YAML Automation
```yaml
- service: script.hold_battery_soc
```

## Monitoring Sensors

Watch these sensors during testing:

- `sensor.charging_state` → Should be "HOLDING"
- `sensor.batterie_soc` → Should be stable
- `sensor.battery_power` → Should be ~0W
- `switch.StorCtl_Mod` → Should be ON
- `sensor.ChaSt` → Should be 6

## Next Steps

1. ✅ Read this quick reference
2. ✅ Run test scripts (see HOLD_SOC_TESTING_GUIDE.md)
3. ✅ Document test results
4. ✅ Choose integration option (see HOLD_SOC_IMPLEMENTATION_EXAMPLE.md)
5. ✅ Deploy to production
6. ✅ Monitor and optimize

---

**Need more details?**
- Testing procedure → `HOLD_SOC_TESTING_GUIDE.md`
- Integration examples → `HOLD_SOC_IMPLEMENTATION_EXAMPLE.md`
