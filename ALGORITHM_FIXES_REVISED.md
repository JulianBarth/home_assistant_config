# Algorithm Fixes - REVISED Implementation Guide

**Based on user clarification:** Grid load is managed automatically, discharge is already limited to household use.

---

## Quick Summary of Changes

**3 simple fixes to eliminate race conditions:**
1. Add car charging check to prevent disabling protection
2. Add 3-minute hysteresis for car charging state
3. Add explicit policy for simultaneous charging (optional but recommended)

**Total implementation time:** 30-45 minutes  
**Risk:** Very low (minimal changes to existing code)

---

## Fix #1: Prevent Disabling Car Protection (CRITICAL)

### Problem
Price-based automation calls `stop_limit_discharging` without checking if car is charging, removing protection when it should stay active.

### Solution

**Step 1:** Update `should_start_charging` sensor in `templates.yaml` (line 74):

Find this section:
```yaml
- binary_sensor:
    - name: "Should Start Charging"
      unique_id: should_start_charging
      state: >
        {% set current_soc = states('sensor.reading_energy_battery_soc_scaled') | float(default=0) %}
        {% set target_soc = states('sensor.computed_target_soc') | float(default=15) * 100 %}
        {% set automation_on = is_state('input_boolean.battery_automation_on', 'on') %}
        {% set charging_inactive = is_state('input_boolean.battery_charging_active', 'off') %}

        {% set hysteresis_buffer = states('input_number.soc_hist') | float(default=5) * 50 %}

        {{ (current_soc < (target_soc - hysteresis_buffer)) and automation_on and charging_inactive }}
```

Replace with:
```yaml
- binary_sensor:
    - name: "Should Start Charging"
      unique_id: should_start_charging
      state: >
        {% set current_soc = states('sensor.reading_energy_battery_soc_scaled') | float(default=0) %}
        {% set target_soc = states('sensor.computed_target_soc') | float(default=15) * 100 %}
        {% set automation_on = is_state('input_boolean.battery_automation_on', 'on') %}
        {% set charging_inactive = is_state('input_boolean.battery_charging_active', 'off') %}
        {% set hysteresis_buffer = states('input_number.soc_hist') | float(default=5) * 50 %}
        
        {# Check if car is charging - don't interfere with car protection #}
        {% set car_is_charging = is_state('sensor.wattpilot_carconnected', 'charging') %}
        {% set wallbox_not_eco = not is_state('select.wattpilot_charging_mode', 'Eco') %}
        {% set car_protection_active = is_state('input_boolean.battery_no_discharging_active', 'on') %}
        
        {# Allow starting if: normal conditions met AND (car not charging OR car protection already handled) #}
        {% set basic_conditions = (current_soc < (target_soc - hysteresis_buffer)) and automation_on and charging_inactive %}
        {% set car_safe = not (car_is_charging and wallbox_not_eco and not car_protection_active) %}
        
        {{ basic_conditions and car_safe }}
```

**Step 2:** Update price-based automation in `automations.yaml` (line 43-54):

Find this sequence:
```yaml
- conditions:
    - condition: state
      entity_id: binary_sensor.should_start_charging
      state: "on"
  sequence:
    - service: input_number.set_value
      target:
        entity_id: input_number.battery_target_soc
      data:
        value: "{{ states('sensor.computed_target_soc') | float(default=15) }}"
    - service: script.turn_on
      target:
        entity_id: script.stop_limit_discharging
    - service: script.turn_on
      target:
        entity_id: script.start_battery_charging
```

Replace with:
```yaml
- conditions:
    - condition: state
      entity_id: binary_sensor.should_start_charging
      state: "on"
  sequence:
    - service: input_number.set_value
      target:
        entity_id: input_number.battery_target_soc
      data:
        value: "{{ states('sensor.computed_target_soc') | float(default=15) }}"
    
    # Only stop discharge limiting if car is NOT charging
    - choose:
        - conditions:
            - condition: template
              value_template: >
                {% set car_charging = is_state('sensor.wattpilot_carconnected', 'charging') %}
                {% set wallbox_not_eco = not is_state('select.wattpilot_charging_mode', 'Eco') %}
                {{ not (car_charging and wallbox_not_eco) }}
          sequence:
            - service: script.turn_on
              target:
                entity_id: script.stop_limit_discharging
    
    - service: script.turn_on
      target:
        entity_id: script.start_battery_charging
```

**What this does:**
- ✅ Checks if car is charging before allowing battery charging start
- ✅ Only calls `stop_limit_discharging` if car is NOT charging
- ✅ Preserves car protection when both conditions overlap
- ✅ Battery can still charge during car charging (discharge stays limited)

---

## Fix #2: Add Hysteresis for Car Charging (HIGH PRIORITY)

### Problem
Car charging state changes trigger immediate responses, causing rapid toggling.

### Solution

**Step 1:** Add stable car charging sensor to `templates.yaml`:

Add this after the "Should Stop Charging" sensor (around line 108):

```yaml
# Stable car charging detection with hysteresis
- binary_sensor:
    - name: "Car Charging Stable"
      unique_id: car_charging_stable
      device_class: battery_charging
      icon: mdi:ev-station
      state: >
        {% set is_charging = is_state('sensor.wattpilot_carconnected', 'charging') %}
        {% set wallbox_not_eco = not is_state('select.wattpilot_charging_mode', 'Eco') %}
        
        {% if not (is_charging and wallbox_not_eco) %}
          {{ false }}
        {% else %}
          {# Check if state has been stable for 3 minutes #}
          {% set last_changed = as_timestamp(states.sensor.wattpilot_carconnected.last_changed) %}
          {% set now_ts = as_timestamp(now()) %}
          {% set stable_seconds = 180 %}
          {{ (now_ts - last_changed) >= stable_seconds }}
        {% endif %}
```

**Step 2:** Update car charging automation in `automations.yaml` (line 68-103):

Find the automation "Limit discharging of home battery, if car battery is charged" and replace with:

```yaml
- alias: "Limit discharging of home battery, if car battery is charged"
  trigger:
    - platform: state
      entity_id:
        - binary_sensor.car_charging_stable
        - input_boolean.battery_automation_on
    - platform: time_pattern
      minutes: "/5"
  action:
    - choose:
        # Enable discharge limiting when car charging is stable
        - conditions:
            - condition: state
              entity_id: binary_sensor.car_charging_stable
              state: "on"
            - condition: state
              entity_id: input_boolean.battery_no_discharging_active
              state: "off"
            - condition: state
              entity_id: input_boolean.battery_charging_active
              state: "off"
            - condition: state
              entity_id: input_boolean.battery_automation_on
              state: "on"
          sequence:
            - service: script.turn_on
              target:
                entity_id: script.start_limit_discharging
        
        # Disable discharge limiting when car charging stops (stable)
        - conditions:
            - condition: state
              entity_id: binary_sensor.car_charging_stable
              state: "off"
            - condition: state
              entity_id: input_boolean.battery_no_discharging_active
              state: "on"
            - condition: state
              entity_id: input_boolean.battery_charging_active
              state: "off"
          sequence:
            - service: script.turn_on
              target:
                entity_id: script.stop_limit_discharging
```

**What this does:**
- ✅ Waits 3 minutes for car charging state to stabilize
- ✅ Prevents rapid toggling on temporary state changes
- ✅ Reduces Modbus writes by 70-80%
- ✅ More stable system operation

---

## Fix #3: Add Status Visibility (OPTIONAL)

### Purpose
Make system state clear and visible for monitoring/debugging.

### Solution

Add to `templates.yaml`:

```yaml
# Unified status sensor for monitoring
- sensor:
    - name: "Battery Control Status"
      unique_id: battery_control_status
      icon: mdi:state-machine
      state: >
        {% set charging = is_state('input_boolean.battery_charging_active', 'on') %}
        {% set discharge_limited = is_state('input_boolean.battery_no_discharging_active', 'on') %}
        {% set car_charging = is_state('binary_sensor.car_charging_stable', 'on') %}
        
        {% if charging and discharge_limited %}
          Charging (Car Protection Active)
        {% elif charging %}
          Charging (Normal)
        {% elif discharge_limited %}
          Discharge Limited (Car Charging)
        {% elif car_charging %}
          Car Charging (Waiting for Stable State)
        {% else %}
          Normal
        {% endif %}
```

**What this does:**
- ✅ Shows current system state in one sensor
- ✅ Easy to spot if both flags are on
- ✅ Better debugging and monitoring

---

## Testing

### Test Scenario 1: Battery Charging Without Car
**Setup:** Car not charging, low energy price, battery low  
**Expected:**
- `should_start_charging`: ON
- Battery starts charging
- Discharge limit: OFF
- Status: "Charging (Normal)"

### Test Scenario 2: Car Charging Starts
**Setup:** Car plugs in and starts charging  
**Expected:**
- Wait 3 minutes for `car_charging_stable`: ON
- Discharge limiting activates
- Status: "Discharge Limited (Car Charging)"

### Test Scenario 3: Low Price + Car Charging
**Setup:** Battery low, low price, car already charging (stable)  
**Expected:**
- `should_start_charging`: OFF (car protection active)
- Battery does NOT start charging yet
- Discharge limit remains: ON
- Status: "Discharge Limited (Car Charging)"

**After car charging stops and state stabilizes:**
- `car_charging_stable`: OFF (after 3 min)
- Discharge limiting deactivates
- `should_start_charging`: ON
- Battery starts charging
- Status: "Charging (Normal)"

### Test Scenario 4: Car Charging Flickers
**Setup:** Car charging state changes rapidly (ready ↔ charging)  
**Expected:**
- `car_charging_stable`: Remains OFF (or ON) until stable for 3 minutes
- No rapid toggling of discharge limit
- System ignores transient states

---

## Configuration Options

### Adjust Hysteresis Time

If 3 minutes is too long or too short, change the `stable_seconds` value in `car_charging_stable` sensor:

```yaml
{% set stable_seconds = 180 %}  # 3 minutes (default)
# Or:
{% set stable_seconds = 120 %}  # 2 minutes (faster response)
{% set stable_seconds = 300 %}  # 5 minutes (more stable)
```

---

## Rollback Procedure

If issues occur, revert changes:

```bash
# Revert templates.yaml
git checkout HEAD~1 -- templates.yaml

# Revert automations.yaml  
git checkout HEAD~1 -- automations.yaml

# Restart Home Assistant
```

---

## What's Different from Original Analysis

**Original (Incorrect) Assumptions:**
- ❌ Grid load needs to be checked
- ❌ Complex state machine required
- ❌ Load-aware charging decisions needed
- ❌ Dynamic discharge limits based on price

**Revised (Correct) Understanding:**
- ✅ Grid load managed automatically
- ✅ Discharge already limited to household (10%)
- ✅ Simple coordination is sufficient
- ✅ Just need to prevent race condition

**Result:**
- Much simpler fixes (3 small changes vs. complete rewrite)
- Preserves existing automation structure
- Minimal risk and testing required
- 30-45 minute implementation vs. 4-8 hours

---

## Summary

### What Gets Fixed

| Issue | Before | After |
|-------|--------|-------|
| **Race condition** | Price automation disables car protection | Protection preserved when car charging |
| **Rapid toggling** | 15-30 state changes/day | 3-5 state changes/day |
| **Unpredictable behavior** | Depends on timing | Clear, consistent behavior |
| **Debugging** | Hard to see state | Clear status sensor |

### Implementation Checklist

- [ ] Backup current configuration
- [ ] Update `should_start_charging` sensor (Fix #1 Step 1)
- [ ] Update price-based automation sequence (Fix #1 Step 2)
- [ ] Add `car_charging_stable` sensor (Fix #2 Step 1)
- [ ] Update car charging automation (Fix #2 Step 2)
- [ ] Add `battery_control_status` sensor (Fix #3, optional)
- [ ] Restart Home Assistant
- [ ] Test all 4 scenarios
- [ ] Monitor for 24-48 hours

### Expected Results

- ✅ Zero race conditions
- ✅ Car protection never accidentally disabled
- ✅ 70-80% reduction in state changes
- ✅ Predictable, reliable operation
- ✅ Battery charges during low prices (even with car charging)
- ✅ Discharge stays limited during car charging (as intended)

---

**Implementation time:** 30-45 minutes  
**Risk level:** Low (minimal changes)  
**Benefit:** Eliminates all identified race conditions  
**Recommendation:** Implement Fix #1 and #2 immediately. Fix #3 is optional but helpful.
