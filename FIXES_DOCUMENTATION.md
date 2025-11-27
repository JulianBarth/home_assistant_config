# Bug Fixes Documentation

This document describes the fixes applied to address two critical issues in the Home Assistant configuration.

## Issue 1: rpi_power Binary Sensor Error

### Problem
The Home Assistant log showed the following error:

```
Logger: homeassistant.components.binary_sensor
Source: helpers/entity_platform.py:807
Integration: Binärsensor (Binary Sensor)

rpi_power: Error on device update!
Traceback (most recent call last):
  File "/usr/src/homeassistant/homeassistant/helpers/entity_platform.py", line 807, in _async_add_entity
    await entity.async_device_update(warning=False)
  File "/usr/src/homeassistant/homeassistant/helpers/entity.py", line 1316, in async_device_update
    await hass.async_add_executor_job(self.update)
  File "/usr/local/lib/python3.13/concurrent/futures/thread.py", line 59, in run
    result = self.fn(*self.args, **self.kwargs)
  File "/usr/src/homeassistant/homeassistant/components/rpi_power/binary_sensor.py", line 53, in update
    value = self._under_voltage.get()
            ^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'NoneType' object has no attribute 'get'
```

### Root Cause
The `rpi_power` integration is a built-in Home Assistant component that monitors Raspberry Pi power supply issues by checking for undervoltage conditions. The error occurs when:

1. The integration is automatically loaded by Home Assistant's `default_config`
2. The hardware doesn't support the required voltage monitoring features
3. The `_under_voltage` attribute remains `None` because initialization fails
4. The integration tries to call `.get()` on `None`, causing the AttributeError

### Solution
Disabled the `rpi_power` integration by adding an empty configuration section to `configuration.yaml`:

```yaml
# Disable rpi_power integration due to hardware compatibility issues
# The integration is trying to monitor Raspberry Pi power supply but
# the hardware doesn't support the necessary voltage monitoring
rpi_power:
```

This tells Home Assistant to skip loading the integration, preventing the error from occurring.

### Files Changed
- `configuration.yaml`: Added `rpi_power:` configuration to disable the integration

## Issue 2: Sankey Chart Configuration Error

### Problem
The Sankey visualization reported "Konfigurationsfehler" (Configuration Error) in the UI instead of displaying the energy flow diagram.

### Root Cause
The Sankey chart configuration had structural issues:

1. **Missing children relationships**: Solar entities (Fronius and Balkonkraftwerk) didn't define children, so no flows could be visualized
2. **Incorrect structure**: The configuration didn't properly map energy sources to intermediate flows and then to consumers
3. **Complex flow logic**: The original configuration tried to model too many direct connections without intermediate tracking

### Solution
Restructured the Sankey chart configuration to use a proper 3-section layout:

#### Section 1: Primary Energy Sources
- `sensor.total_solar_power`: Combined solar production (Fronius + Balkonkraftwerk)
- `sensor.grid_power`: Grid import/export
- `sensor.battery_power`: Battery charge/discharge

Each source defines its children (the flow sensors it feeds into).

#### Section 2: Energy Distribution
Intermediate flow sensors that track how energy moves:
- `sensor.solar_to_house`: Solar powering house
- `sensor.solar_to_battery`: Solar charging battery
- `sensor.solar_to_grid`: Solar exported to grid
- `sensor.grid_to_house`: Grid powering house
- `sensor.grid_to_battery`: Grid charging battery
- `sensor.battery_to_house`: Battery powering house

These sensors connect sources to final consumers.

#### Section 3: Final Consumption
- `sensor.house_consumption`: House power consumption

### Configuration Structure
```yaml
- type: custom:sankey-chart
  title: 🔋 Energy Flow Visualization
  sections:
    # Section 1: Sources with children pointing to Section 2
    - entities:
        - entity_id: sensor.total_solar_power
          children:
            - sensor.solar_to_house
            - sensor.solar_to_battery
            - sensor.solar_to_grid
        # ... other sources
    
    # Section 2: Distribution with children pointing to Section 3
    - entities:
        - entity_id: sensor.solar_to_house
          children:
            - sensor.house_consumption
        # ... other flows
    
    # Section 3: Final consumers (no children)
    - entities:
        - entity_id: sensor.house_consumption
```

### Files Changed
- `ui-lovelace.yaml`: Restructured Sankey chart configuration with proper 3-section layout

## Testing and Validation

### Pre-Deployment Checks
1. ✅ YAML syntax validated for `ui-lovelace.yaml`
2. ✅ Configuration structure follows Sankey chart documentation
3. ✅ All referenced sensors verified to exist in `templates.yaml`:
   - Primary sources: `sensor.total_solar_power`, `sensor.grid_power`, `sensor.battery_power`
   - Flow sensors: `sensor.solar_to_house`, `sensor.solar_to_battery`, `sensor.solar_to_grid`, `sensor.grid_to_house`, `sensor.grid_to_battery`, `sensor.battery_to_house`
   - Consumers: `sensor.house_consumption`

### Post-Deployment Validation Required
The following should be verified after deploying these changes:

1. **rpi_power Fix**:
   - [ ] Home Assistant restarts without the rpi_power error
   - [ ] No new errors appear in the log
   - [ ] System health check shows no issues

2. **Sankey Chart Fix**:
   - [ ] Navigate to Battery Management → Energy Flow view
   - [ ] Verify Sankey chart displays without "Konfigurationsfehler"
   - [ ] Check that energy flows are visualized correctly
   - [ ] Verify real-time updates work as sensors change

## Additional Notes

### Alternative Approaches Considered

#### For rpi_power Issue
1. **Fix the integration code**: Would require maintaining a custom component - rejected as too complex
2. **Remove from default_config**: Would require disabling all default integrations - rejected as too invasive
3. **Disable via UI**: Not possible as the integration auto-loads - rejected
4. **Selected approach**: Disable via empty YAML configuration - simple and effective

#### For Sankey Chart Issue
1. **Two-section simple layout**: Would lose detailed flow tracking - rejected
2. **Four-section with more detail**: Would be too complex and hard to read - rejected
3. **Selected approach**: Three-section with sources → flows → consumption - balances detail and clarity

### Future Improvements

1. **Sankey Chart Enhancements**:
   - Add Wallbox as a separate consumer in Section 3
   - Consider adding a "remaining" sensor to show unaccounted energy
   - Add color coding based on energy price or efficiency
   - Consider using `connection_entity_id` for more precise flow tracking

2. **Monitoring**:
   - Monitor Home Assistant logs for any new errors
   - Track Sankey chart performance with large sensor values
   - Consider adding alerts for configuration validation failures

## References

- [Home Assistant rpi_power Integration](https://www.home-assistant.io/integrations/rpi_power/)
- [Sankey Chart Card Documentation](https://github.com/MindFreeze/ha-sankey-chart)
- [Home Assistant YAML Configuration](https://www.home-assistant.io/docs/configuration/)

## Change History

- **2024-11-27**: Initial fixes for rpi_power error and Sankey chart configuration
  - Disabled rpi_power integration
  - Restructured Sankey chart to 3-section layout
  - Validated YAML syntax
