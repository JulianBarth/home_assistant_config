# Hold SOC Implementation Example

## Overview

This document provides a concrete example of how to integrate the Hold SOC functionality into your existing battery control automations. This replaces the inefficient charge/discharge cycling with a more efficient holding pattern.

## Problem Statement

**Current behavior:** When the battery reaches the target SoC, the system either:
1. Continues to charge slightly above target, then must discharge
2. Stops charging, drops below target, then must charge again

This cycling wastes energy due to battery round-trip efficiency losses (~10% energy loss per cycle).

**Improved behavior with Hold SOC:** When the battery is at or near the target SoC, activate holding mode to minimize cycling and energy losses.

## Integration Options

### Option 1: Add Hold Mode to Unified Battery Control Coordinator (Recommended)

This integrates hold functionality into your existing automation framework.

#### Step 1: Add a new binary sensor to detect when battery should hold

Add this to your `templates.yaml`:

```yaml
- binary_sensor:
    - name: "Should Hold Battery SOC"
      unique_id: should_hold_battery_soc
      icon: mdi:battery-lock
      state: >
        {% set current_soc = states('sensor.batterie_soc') | float(default=0) %}
        {% set target_soc = states('input_number.battery_target_soc') | float(default=100) %}
        {% set hold_threshold = states('input_number.soc_hold_threshold') | float(default=2) %}
        {% set automation_on = is_state('input_boolean.battery_automation_on', 'on') %}
        {% set charging_active = is_state('input_boolean.battery_charging_active', 'on') %}
        
        {# Hold battery when we're within threshold of target #}
        {% set in_hold_range = (current_soc >= (target_soc - hold_threshold)) and (current_soc <= (target_soc + hold_threshold)) %}
        
        {{ in_hold_range and automation_on and charging_active }}
```

#### Step 2: Add configuration for hold threshold

Add this to your `configuration.yaml` under `input_number:`:

```yaml
  soc_hold_threshold:
    name: SoC Hold Threshold
    initial: 2
    min: 0.5
    max: 5
    step: 0.5
    unit_of_measurement: "%"
    icon: mdi:battery-lock
```

#### Step 3: Add Hold Mode to Unified Battery Control Coordinator

Modify the `automations.yaml` "Unified Battery Control Coordinator" automation to include a hold mode:

```yaml
- alias: "Unified Battery Control Coordinator"
  description: "Single automation to coordinate all battery control modes"
  trigger:
    # Trigger on mode changes
    - platform: state
      entity_id: sensor.battery_control_mode
    # Trigger on SoC changes (for stop conditions and hold conditions)
    - platform: state
      entity_id:
        - binary_sensor.should_stop_charging
        - binary_sensor.should_hold_battery_soc
        - sensor.computed_target_soc
    # Fallback check every 5 minutes
    - platform: time_pattern
      minutes: "/5"
  action:
    - choose:
        # Mode 1: Manual Charging (Highest Priority)
        - conditions:
            - condition: state
              entity_id: sensor.battery_control_mode
              state: "manual_charging"
            - condition: state
              entity_id: binary_sensor.should_hold_battery_soc
              state: "off"
          sequence:
            - service: input_number.set_value
              target:
                entity_id: input_number.battery_target_soc
              data:
                value: "{{ states('input_number.manual_charge_target_soc') | float(default=80) }}"
            - service: script.turn_on
              target:
                entity_id: script.forced_full_recharge
            - service: switch.turn_on
              target:
                entity_id: switch.StorCtl_Mod
            - service: input_boolean.turn_on
              target:
                entity_id: input_boolean.battery_charging_active

        # NEW MODE: Hold Battery at Target SOC (High Priority)
        - conditions:
            - condition: state
              entity_id: binary_sensor.should_hold_battery_soc
              state: "on"
          sequence:
            - service: script.turn_on
              target:
                entity_id: script.hold_battery_soc
            - service: notify.mobile_app_f4gdn4ry0gpq_2
              data:
                message: "Battery holding at {{ states('sensor.batterie_soc') }}% (target: {{ states('input_number.battery_target_soc') }}%)"
                title: "Battery Hold Active"

        # Mode 2: Car + Battery Charging
        - conditions:
            - condition: state
              entity_id: sensor.battery_control_mode
              state: "car_and_battery_charging"
            - condition: state
              entity_id: binary_sensor.should_stop_charging
              state: "off"
          sequence:
            - service: input_number.set_value
              target:
                entity_id: input_number.battery_target_soc
              data:
                value: "{{ states('sensor.computed_target_soc') | float(default=15) }}"
            - service: script.turn_on
              target:
                entity_id: script.charge_battery_limit_discharge

        # ... rest of modes remain the same ...
```

### Option 2: Standalone Hold SOC Automation (Simpler)

If you prefer a separate, dedicated automation for hold SOC:

Add this to your `automations.yaml`:

```yaml
- alias: "Hold Battery at Target SOC"
  description: "Activate hold mode when battery is at target SoC to prevent cycling"
  trigger:
    # Check when battery SoC changes
    - platform: state
      entity_id: sensor.batterie_soc
    # Check periodically
    - platform: time_pattern
      minutes: "/3"
  condition:
    # Only when automation is enabled
    - condition: state
      entity_id: input_boolean.battery_automation_on
      state: "on"
    # Only when charging is active
    - condition: state
      entity_id: input_boolean.battery_charging_active
      state: "on"
    # Only when not in manual mode
    - condition: not
      conditions:
        - condition: state
          entity_id: input_boolean.manual_battery_charge
          state: "on"
  action:
    - choose:
        # Activate hold when at target
        - conditions:
            - condition: template
              value_template: >
                {% set current_soc = states('sensor.batterie_soc') | float(default=0) %}
                {% set target_soc = states('input_number.battery_target_soc') | float(default=100) %}
                {% set hold_threshold = 2 %}
                {{ (current_soc >= (target_soc - hold_threshold)) and (current_soc <= (target_soc + hold_threshold)) }}
          sequence:
            - service: script.turn_on
              target:
                entity_id: script.hold_battery_soc
            - service: persistent_notification.create
              data:
                title: "Battery Hold Active"
                message: "Battery is holding at {{ states('sensor.batterie_soc') }}% (target: {{ states('input_number.battery_target_soc') }}%)"

        # Resume charging if SoC drops below hold range
        - conditions:
            - condition: template
              value_template: >
                {% set current_soc = states('sensor.batterie_soc') | float(default=0) %}
                {% set target_soc = states('input_number.battery_target_soc') | float(default=100) %}
                {% set hold_threshold = 2 %}
                {{ current_soc < (target_soc - hold_threshold) }}
          sequence:
            - service: script.turn_on
              target:
                entity_id: script.forced_full_recharge
```

## Testing the Integration

### Phase 1: Controlled Test (Required)

Before enabling in production:

1. **Test hold scripts work** (see HOLD_SOC_TESTING_GUIDE.md)
   - Run `script.test_hold_soc_enable`
   - Monitor for 10-15 minutes
   - Verify HOLDING state is achieved
   - Run `script.test_hold_soc_disable`

2. **Document baseline efficiency**
   - Monitor battery over 24 hours with current system
   - Track total charge cycles
   - Note SoC oscillations when near target

### Phase 2: Integration Test

1. **Add the configuration** (choose Option 1 or 2 above)
2. **Restart Home Assistant** to load new configuration
3. **Set a realistic target SoC** (e.g., 50%)
4. **Monitor the automation**:
   - Watch for battery reaching target
   - Verify hold mode activates
   - Check charging state shows "HOLDING"
   - Ensure battery power stays near 0W

### Phase 3: Production Deployment

1. **Enable for normal operation**
2. **Monitor over several days**:
   - Track battery cycles (should decrease)
   - Monitor energy efficiency (losses should decrease)
   - Verify no unexpected behavior
3. **Tune hold threshold** if needed:
   - Increase (e.g., 3%) if battery oscillates too much
   - Decrease (e.g., 1.5%) if hold activates too early

## Expected Improvements

### Energy Efficiency
- **Reduced cycling losses**: ~2-5% improvement in overall battery efficiency
- **Fewer charge/discharge cycles**: Extends battery lifespan
- **More stable SoC**: Less oscillation around target

### Operational Benefits
- **Smoother operation**: No frequent mode switching
- **Better grid stability**: More predictable power draw
- **Reduced wear**: Fewer battery state changes

## Monitoring and Validation

### Key Metrics to Track

1. **Charging State Frequency**
   ```
   Before: CHARGING → DISCHARGING → CHARGING (frequent cycling)
   After: CHARGING → HOLDING (stable)
   ```

2. **Battery Power Profile**
   ```
   Before: ±500-2000W oscillation near target
   After: ~0-100W when holding
   ```

3. **SoC Stability**
   ```
   Before: ±2-5% variation over 1 hour
   After: ±0.5-1% variation over 1 hour
   ```

### Dashboard Monitoring

Add these to your Home Assistant dashboard:

```yaml
type: entities
entities:
  - entity: sensor.charging_state
    name: Battery State
  - entity: sensor.batterie_soc
    name: Current SoC
  - entity: input_number.battery_target_soc
    name: Target SoC
  - entity: binary_sensor.should_hold_battery_soc
    name: Hold Mode Active
  - entity: sensor.battery_power
    name: Battery Power
  - entity: switch.StorCtl_Mod
    name: External Control
title: Battery Hold Status
```

## Troubleshooting

### Issue: Hold mode activates but battery still charges/discharges

**Cause:** Solar production or high consumption overrides minimal rates

**Solution:** 
- This is normal behavior - hold minimizes but doesn't eliminate all activity
- Consider testing during stable conditions (evening, moderate consumption)
- If persistent, you may need to adjust the hold range parameters

### Issue: Battery never enters HOLDING state

**Possible causes:**
1. Modbus communication issue
2. Register values not being written correctly
3. Battery has priority discharge/charge commands

**Solutions:**
- Check `sensor.ChaSt` value (should be 6 for HOLDING)
- Verify `sensor.percent_max_discharge_rte` and `sensor.percent_max_charge_rte` show 1%
- Review Modbus integration logs
- Manually call `script.test_hold_soc_enable` to verify basic functionality

### Issue: Hold mode never deactivates

**Cause:** Binary sensor or automation logic issue

**Solution:**
- Check `binary_sensor.should_hold_battery_soc` state
- Verify SoC has moved outside hold range
- Manually call `script.test_hold_soc_disable` if needed
- Review automation traces in Home Assistant

## Advanced Configuration

### Adjustable Hold Rates

Instead of fixed 1% (100), make it configurable:

Add to `configuration.yaml`:
```yaml
input_number:
  battery_hold_rate:
    name: Battery Hold Rate
    initial: 1
    min: 0.5
    max: 5
    step: 0.5
    unit_of_measurement: "%"
    icon: mdi:speedometer
```

Modify `script.hold_battery_soc`:
```yaml
hold_battery_soc:
  alias: "Hold Battery SOC"
  description: "Hold battery at current SOC by minimizing charge/discharge rates"
  sequence:
    - service: modbus.write_register
      data:
        hub: fronius1
        unit: 1
        address: 40365
        value: "{{ (states('input_number.battery_hold_rate') | float * 100) | int }}"
    - service: modbus.write_register
      data:
        hub: fronius1
        unit: 1
        address: 40366
        value: "{{ (states('input_number.battery_hold_rate') | float * 100) | int }}"
    - action: switch.turn_on
      target:
        entity_id: switch.StorCtl_Mod
```

### Time-Based Hold Windows

Only hold during specific times:

```yaml
- alias: "Hold Battery at Target SOC (Time-Based)"
  trigger:
    - platform: state
      entity_id: sensor.batterie_soc
    - platform: time_pattern
      minutes: "/3"
  condition:
    # Only during off-peak hours (example: 22:00-06:00)
    - condition: time
      after: "22:00:00"
      before: "06:00:00"
    # ... other conditions ...
```

## Migration Path

### Step 1: Backup Current Configuration
```bash
# Backup your current files
cp automations.yaml automations.yaml.backup
cp templates.yaml templates.yaml.backup
cp configuration.yaml configuration.yaml.backup
```

### Step 2: Test in Development
1. Test hold scripts manually first
2. Add integration on a non-critical automation
3. Monitor for 24-48 hours

### Step 3: Full Deployment
1. Implement chosen integration option
2. Monitor closely for first week
3. Fine-tune thresholds as needed
4. Remove backup files once stable

## Support and Feedback

Document your results:
- Energy savings achieved
- Operational improvements
- Any issues encountered
- Configuration adjustments made

This helps improve the feature for everyone!

---

**Version:** 1.0  
**Last Updated:** 2025-12-04  
**Tested With:** Fronius Gen24 Plus 6.0, Home Assistant 2024.x
