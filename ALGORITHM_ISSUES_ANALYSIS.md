# Battery Charging/Discharging Algorithm Issues and Solutions

## Executive Summary

This document identifies critical issues in the battery management algorithm, particularly around the coordination between price-based charging and car-charging-based discharge limiting. Six major issues have been identified with specific solutions proposed.

## Current System Architecture

### Two Independent Automations:
1. **Price-based Battery Charging** (`automations.yaml` lines 24-66)
   - Triggers: Energy price sensors, computed target SoC
   - Actions: Start/stop battery charging
   - Controls: Modbus registers via `forced_full_recharge` script

2. **Car Charging Discharge Limiting** (`automations.yaml` lines 68-103)
   - Triggers: Wallbox state, charging mode
   - Actions: Limit/unlimit battery discharge
   - Controls: Modbus registers via `set_limited_discharge` script

### Problem: No Coordination Between Automations

Both automations independently control the same hardware (Fronius inverter) via the same control mechanism (StorCtl_Mod switch + Modbus registers).

---

## Issue 1: State Conflict Between Charging and Discharge Limiting

### Problem Description

**Scenario:** Low energy prices occur while car is charging
- Price-based automation: Wants to charge battery (calls `forced_full_recharge`)
- Car charging automation: Wants to limit discharge (calls `set_limited_discharge`)

**What happens:**
1. Both automations enable `StorCtl_Mod` switch
2. Both try to write to Modbus registers 40365 (OutWRte) and 40366 (InWRte)
3. Race condition: Whichever runs last "wins"
4. Result is unpredictable and depends on timing

### Modbus Register Conflicts

**forced_full_recharge** (for charging):
```yaml
address: 40365  # OutWRte - Prevent discharge
value: 57536    # Negative value (65536 - 8000)

address: 40366  # InWRte - Allow maximum charge
value: 10000    # 100% charge rate
```

**set_limited_discharge** (for car charging):
```yaml
address: 40365  # OutWRte - Limit discharge to 10%
value: 1000     # 10% discharge rate

address: 40366  # InWRte - Allow full charge
value: 10000    # 100% charge rate
```

**Conflict:** Register 40365 has competing values (57536 vs 1000)

### Impact

- **Unpredictable behavior**: System state depends on timing
- **Inefficient operation**: Wrong mode may be active
- **Energy waste**: Could charge when it shouldn't or vice versa
- **Battery wear**: Rapid mode switching if automations trigger repeatedly

### Proposed Solution

**Add coordination layer with state machine:**

```yaml
# New sensor to determine priority mode
- sensor:
    - name: "Battery Control Mode"
      unique_id: battery_control_mode
      state: >
        {% set car_charging = is_state('sensor.wattpilot_carconnected', 'charging') %}
        {% set wallbox_not_eco = not is_state('select.wattpilot_charging_mode', 'Eco') %}
        {% set should_charge = is_state('binary_sensor.should_start_charging', 'on') %}
        {% set automation_on = is_state('input_boolean.battery_automation_on', 'on') %}
        {% set manual_charge = is_state('input_boolean.manual_battery_charge', 'on') %}
        
        {# Priority order: Manual > Car Charging > Price Charging > Normal #}
        {% if manual_charge %}
          manual_charging
        {% elif car_charging and wallbox_not_eco and automation_on %}
          {% if should_charge %}
            car_and_battery_charging
          {% else %}
            car_charging_only
          {% endif %}
        {% elif should_charge and automation_on %}
          battery_charging
        {% else %}
          normal
        {% endif %}
```

**New unified control automation:**

```yaml
- alias: "Unified Battery Control"
  description: "Coordinates all battery control modes with priority"
  trigger:
    - platform: state
      entity_id: sensor.battery_control_mode
  action:
    - choose:
        # Manual charging - highest priority
        - conditions:
            - condition: state
              entity_id: sensor.battery_control_mode
              state: "manual_charging"
          sequence:
            - service: script.turn_on
              target:
                entity_id: script.forced_full_recharge
            - service: switch.turn_on
              target:
                entity_id: switch.StorCtl_Mod
        
        # Car charging + low prices = charge battery but limit discharge
        - conditions:
            - condition: state
              entity_id: sensor.battery_control_mode
              state: "car_and_battery_charging"
          sequence:
            - service: script.turn_on
              target:
                entity_id: script.charge_battery_limit_discharge
        
        # Car charging only = limit discharge
        - conditions:
            - condition: state
              entity_id: sensor.battery_control_mode
              state: "car_charging_only"
          sequence:
            - service: script.turn_on
              target:
                entity_id: script.set_limited_discharge
        
        # Battery charging only
        - conditions:
            - condition: state
              entity_id: sensor.battery_control_mode
              state: "battery_charging"
          sequence:
            - service: script.turn_on
              target:
                entity_id: script.forced_full_recharge
        
        # Normal operation
      default:
        - service: script.turn_on
          target:
            entity_id: script.set_regular_charge
```

**Benefits:**
- Single automation controls all modes
- Clear priority: Manual > Car + Battery > Car Only > Battery Only > Normal
- No race conditions
- Predictable behavior

---

## Issue 2: Missing Cost-Benefit Analysis

### Problem Description

When car is charging AND grid prices are low, the system may charge the battery without considering:
1. Home consumption during car charging (typically high)
2. Total grid load (car + home + battery)
3. Whether battery charging is actually beneficial given the load

### Current Behavior

**Scenario:** Car charges at 11 kW, home uses 2 kW, battery charges at 5 kW
- Total grid draw: 18 kW
- Grid capacity may be limited
- High simultaneous load may trigger different rate tiers
- No evaluation if battery charging is worth it in this context

### Impact

- **Grid overload risk**: Combined load may exceed connection capacity
- **Rate tier concerns**: Some utilities charge more for high simultaneous load
- **Suboptimal economics**: Charging battery may not be worth it if car is already drawing heavily

### Proposed Solution

**Add load-aware charging decision:**

```yaml
# New binary sensor for intelligent car+battery charging
- binary_sensor:
    - name: "Should Charge Battery During Car Charging"
      unique_id: should_charge_battery_during_car_charging
      state: >
        {% set car_charging = is_state('sensor.wattpilot_carconnected', 'charging') %}
        {% set car_power = states('sensor.wattpilot_charging_power') | float(default=0) %}
        {% set home_power = states('sensor.home_consumption_power') | float(default=0) %}
        {% set battery_charge_rate = 5000 %}  # Typical battery charge rate in watts
        {% set grid_capacity = 20000 %}  # Example: 20 kW grid connection
        {% set current_price = states('sensor.tibber_energy_prices') | float(default=999) %}
        {% set avg_price = states('sensor.tibber_energy_average_price_next_12_hours') | float(default=999) %}
        
        {% set total_load = car_power + home_power + battery_charge_rate %}
        {% set load_within_capacity = total_load < (grid_capacity * 0.9) %}  # 90% safety margin
        {% set price_significantly_low = (current_price * 100) < (avg_price * 0.8) %}  # 20% below average
        
        {{ car_charging and load_within_capacity and price_significantly_low }}
```

**Update control mode sensor to use this:**

```yaml
{% elif car_charging and wallbox_not_eco and automation_on %}
  {% if should_charge and is_state('binary_sensor.should_charge_battery_during_car_charging', 'on') %}
    car_and_battery_charging
  {% else %}
    car_charging_only
  {% endif %}
```

**Benefits:**
- Considers total system load
- Only charges battery during car charging when truly beneficial
- Respects grid capacity limits
- Improves economic efficiency

---

## Issue 3: No Intelligent Discharge During High Prices

### Problem Description

Current system completely blocks discharge when car is charging. This is overly conservative and misses optimization opportunities.

### Missed Opportunity

**Scenario:** Peak evening prices (€0.40/kWh) while car charging
- Current: Battery fully blocked, all energy from grid at €0.40/kWh
- Better: Allow battery to help power home (not car) during expensive periods
- Savings: Could save €2-5 per evening on home consumption

### Current Logic

```yaml
# automations.yaml line 86
{% set wallbox_not_eco = not is_state('select.wattpilot_charging_mode', 'Eco') %}
# If wallbox not in Eco AND car charging = completely block discharge
```

### Impact

- **Higher costs**: Home pays peak prices even with charged battery
- **Suboptimal battery use**: Battery sits full during expensive periods
- **Lost savings**: Misses 10-20% potential optimization

### Proposed Solution

**Add price-aware discharge strategy:**

```yaml
# New sensor for dynamic discharge limit during car charging
- sensor:
    - name: "Discharge Limit During Car Charging"
      unique_id: discharge_limit_during_car_charging
      unit_of_measurement: "%"
      state: >
        {% set current_price = states('sensor.tibber_energy_prices') | float(default=0) %}
        {% set avg_price = states('sensor.tibber_energy_average_price_next_12_hours') | float(default=999) / 100 %}
        {% set battery_soc = states('sensor.batterie_soc') | float(default=0) %}
        
        {# Allow more discharge during expensive periods #}
        {% if current_price > (avg_price * 1.5) and battery_soc > 60 %}
          50  {# Allow 50% discharge rate during very high prices #}
        {% elif current_price > (avg_price * 1.2) and battery_soc > 40 %}
          30  {# Allow 30% discharge rate during high prices #}
        {% else %}
          10  {# Default: 10% discharge limit #}
        {% endif %}
```

**New script for dynamic discharge limiting:**

```yaml
set_dynamic_discharge_limit:
  alias: "Set Dynamic Discharge Limit"
  description: "Adjust discharge limit based on price and battery level"
  sequence:
    - service: modbus.write_register
      data:
        hub: fronius1
        unit: 1
        address: 40365
        value: >
          {% set limit_percent = states('sensor.discharge_limit_during_car_charging') | float(default=10) %}
          {{ (limit_percent * 100) | int }}
    - service: modbus.write_register
      data:
        hub: fronius1
        unit: 1
        address: 40366
        value: 10000
```

**Benefits:**
- Reduces grid consumption during peak prices
- Better battery utilization
- Maintains safety (limits to prevent deep discharge)
- Adapts to price conditions dynamically

---

## Issue 4: Missing Hysteresis in Discharge Limiting

### Problem Description

Battery charging has proper hysteresis (5% default), but discharge limiting has none. This can cause rapid toggling.

### Current Behavior

**Charging (has hysteresis):**
```yaml
# templates.yaml line 87
{% set hysteresis_buffer = states('input_number.soc_hist') | float(default=5) * 50 %}
{{ (current_soc < (target_soc - hysteresis_buffer)) and automation_on and charging_inactive }}
```

**Discharge Limiting (no hysteresis):**
```yaml
# automations.yaml line 82
{{ wallbox_is_charging and charging_not_active and discharge_limited_not_active and automation_on and wallbox_not_eco }}
```

### Impact

**Rapid toggling scenario:**
1. Car connected → wallbox status: "ready"
2. Car starts charging → wallbox status: "charging" → disable discharge
3. Car briefly pauses → wallbox status: "ready" → enable discharge  
4. Car resumes → wallbox status: "charging" → disable discharge
5. Repeat every few minutes

**Consequences:**
- Modbus register churn
- Switch wear
- Inverter stress
- Unpredictable behavior

### Proposed Solution

**Add timer-based hysteresis:**

```yaml
# New input_number for car charging hysteresis
input_number:
  car_charging_hysteresis_minutes:
    name: Car Charging Hysteresis
    initial: 3
    min: 0
    max: 15
    step: 1
    unit_of_measurement: "min"
```

**Update automation with delay protection:**

```yaml
- alias: "Limit discharging of home battery, if car battery is charged"
  trigger:
    - platform: state
      entity_id: sensor.wattpilot_carconnected
      to: 'charging'
      for:
        minutes: "{{ states('input_number.car_charging_hysteresis_minutes') | int }}"
    - platform: state
      entity_id: sensor.wattpilot_carconnected
      from: 'charging'
      for:
        minutes: "{{ states('input_number.car_charging_hysteresis_minutes') | int }}"
    # ... rest of automation
```

**Alternative: State-based hysteresis:**

```yaml
# New helper to track stable car charging state
- binary_sensor:
    - name: "Car Charging Stable"
      unique_id: car_charging_stable
      state: >
        {% set charging = is_state('sensor.wattpilot_carconnected', 'charging') %}
        {% set last_changed = as_timestamp(states.sensor.wattpilot_carconnected.last_changed) %}
        {% set now_ts = as_timestamp(now()) %}
        {% set stable_time = 180 %}  # 3 minutes in seconds
        
        {{ charging and (now_ts - last_changed) > stable_time }}
      
    - name: "Car Not Charging Stable"
      unique_id: car_not_charging_stable
      state: >
        {% set not_charging = not is_state('sensor.wattpilot_carconnected', 'charging') %}
        {% set last_changed = as_timestamp(states.sensor.wattpilot_carconnected.last_changed) %}
        {% set now_ts = as_timestamp(now()) %}
        {% set stable_time = 180 %}  # 3 minutes
        
        {{ not_charging and (now_ts - last_changed) > stable_time }}
```

**Benefits:**
- Prevents rapid toggling
- Reduces hardware wear
- More stable operation
- User-configurable delay

---

## Issue 5: Manual Charging Lacks Coordination

### Problem Description

Manual charging (`input_boolean.manual_battery_charge`) doesn't coordinate with car charging automation.

### Current Behavior

**Manual charging automation (line 6-22):**
- Directly calls `start_battery_charging`
- No awareness of car charging state
- Could conflict with discharge limiting

**Potential conflict:**
1. User enables manual charging → battery starts charging
2. Car starts charging → discharge limiting activates
3. Two different Modbus configurations compete

### Impact

- **Unpredictable**: User gets unexpected behavior
- **Conflicts**: Similar to Issue #1
- **Poor UX**: Manual control should be reliable

### Proposed Solution

**Already addressed by Issue #1 solution:**

The priority-based state machine includes manual charging as highest priority:

```yaml
{% if manual_charge %}
  manual_charging
{% elif car_charging and wallbox_not_eco and automation_on %}
  ...
```

**Additional: Inform user of conflicts:**

```yaml
# New notification when manual charge during car charging
- alias: "Notify Manual Charge During Car Charging"
  trigger:
    - platform: state
      entity_id: input_boolean.manual_battery_charge
      to: 'on'
  condition:
    - condition: state
      entity_id: sensor.wattpilot_carconnected
      state: 'charging'
  action:
    - service: notify.mobile_app_f4gdn4ry0gpq_2
      data:
        message: "Manual battery charging activated while car is charging. Battery charging will take priority, but may increase total grid load."
        title: "Battery Control Alert"
```

**Benefits:**
- Clear priority: Manual overrides all automation
- User informed of interactions
- Predictable behavior

---

## Issue 6: Profitability Check Limitations

### Problem Description

Current profitability check is simplistic:

```yaml
# templates.yaml line 125
{% set is_profitable = max_price_24h > (current_price_cents * 1.15) %}
```

**Limitations:**
1. Doesn't account for round-trip efficiency (~90%)
2. Doesn't consider battery wear costs
3. Doesn't factor in time-of-use patterns
4. Ignores discharge opportunities during peaks

### Impact

- **Suboptimal charging**: May charge when not actually profitable
- **Battery wear**: Unnecessary cycles reduce battery life
- **Missed savings**: Could optimize better with more sophisticated analysis

### Proposed Solution

**Enhanced profitability calculation:**

```yaml
# New sensor for comprehensive profitability
- binary_sensor:
    - name: "Battery Charging Is Profitable"
      unique_id: battery_charging_is_profitable
      state: >
        {% set current_price = states('sensor.tibber_energy_prices') | float(default=999) %}
        {% set current_price_cents = current_price * 100 %}
        {% set max_price_24h = states('sensor.tibber_energy_highest_price_next_24_hours') | float(default=0) %}
        {% set avg_price_12h = states('sensor.tibber_energy_average_price_next_12_hours') | float(default=999) %}
        
        {# Constants #}
        {% set round_trip_efficiency = 0.90 %}  # 90% efficient
        {% set battery_wear_cost_per_kwh = 2 %}  # €0.02/kWh wear cost (example)
        {% set min_spread_percent = 1.20 %}  # Need 20% spread minimum
        
        {# Calculate effective cost including losses and wear #}
        {% set effective_charge_cost = current_price_cents + battery_wear_cost_per_kwh %}
        {% set effective_discharge_value = max_price_24h * round_trip_efficiency %}
        
        {# Profitable if: discharge value > charge cost with safety margin #}
        {% set spread_sufficient = effective_discharge_value > (effective_charge_cost * min_spread_percent) %}
        
        {# Also check we're significantly below average (avoid average prices) #}
        {% set below_average = current_price_cents < (avg_price_12h * 0.85) %}
        
        {{ spread_sufficient and below_average }}
```

**Update computed target SoC to use enhanced check:**

```yaml
- sensor:
    - name: "Computed Target SoC"
      state: >
        {% set is_profitable = is_state('binary_sensor.battery_charging_is_profitable', 'on') %}
        
        {% if not is_profitable %}
          {{ states('input_number.soc_target_default') | float(default=15) }}
        {% elif ... %}
          # Rest of logic
```

**Benefits:**
- More accurate profitability assessment
- Accounts for real costs (efficiency, wear)
- Reduces unnecessary cycles
- Better long-term economics

---

## Implementation Priority

### High Priority (Implement First)
1. **Issue #1**: State conflict resolution - Critical for stability
2. **Issue #4**: Hysteresis for discharge limiting - Prevents hardware wear

### Medium Priority (Implement Second)
3. **Issue #2**: Cost-benefit analysis - Improves economics
4. **Issue #3**: Intelligent discharge strategy - Additional savings

### Low Priority (Nice to Have)
5. **Issue #5**: Manual charging coordination - Already partially addressed
6. **Issue #6**: Enhanced profitability - Incremental improvement

---

## Testing Recommendations

### For Each Fix:

1. **Unit Testing**:
   - Test all sensor template logic with mock data
   - Verify state transitions work correctly
   - Check edge cases (sensor unavailable, etc.)

2. **Integration Testing**:
   - Monitor for 48 hours in shadow mode (log decisions without acting)
   - Compare new logic to old logic decisions
   - Verify no conflicts occur

3. **Production Testing**:
   - Enable one fix at a time
   - Monitor for 1 week each
   - Measure: toggle frequency, grid load, costs, battery cycles

### Success Metrics:

- **Stability**: No rapid toggling (<3 state changes per hour)
- **Economics**: 10-20% reduction in grid costs during optimization periods
- **Battery Health**: Reduced cycle count (fewer unnecessary charges)
- **Conflicts**: Zero race conditions or unpredictable states

---

## Summary

The current algorithm has six identified issues stemming from lack of coordination between independent automations. The proposed solutions create a unified, priority-based control system that:

1. Eliminates race conditions via state machine
2. Optimizes costs with load-aware decisions
3. Improves battery utilization with intelligent discharge
4. Increases stability with proper hysteresis
5. Provides clear manual override behavior
6. Enhances profitability calculations

**Implementation of high-priority fixes (#1 and #4) is strongly recommended** as they address stability and hardware protection issues. Medium-priority fixes add significant economic value. Low-priority fixes provide incremental improvements.

## Next Steps

1. Review and approve proposed solutions
2. Implement Issue #1 (state coordination) first
3. Test thoroughly in shadow mode
4. Roll out progressively with monitoring
5. Gather metrics and refine as needed
