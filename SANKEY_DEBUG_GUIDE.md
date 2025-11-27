# Sankey Chart Debug Guide

## ⚠️ If Sankey Chart Shows "Configuration Error" or Doesn't Render

If you see a "Configuration Error" (Konfigurationsfehler) or the Sankey chart doesn't appear at all, the debug panels below the chart may not be accessible. Follow these steps instead:

### Step 1: Check Browser Console

1. **Open Browser Developer Tools**
   - Press **F12** (Windows/Linux) or **Cmd+Option+I** (Mac)
   - Or right-click → "Inspect" → Go to "Console" tab

2. **Look for Error Messages**
   - Red error messages about "sankey-chart"
   - YAML configuration errors
   - Missing entity errors
   - Custom element errors

3. **Common Configuration Errors**:
   - `Cannot read properties of undefined` → Missing or incorrect entity references
   - `Custom element doesn't exist: sankey-chart` → Card not installed/loaded (see [SANKEY_INSTALLATION.md](SANKEY_INSTALLATION.md))
   - `Entity not found` → Referenced sensor doesn't exist
   - YAML syntax errors → Check indentation and structure in `ui-lovelace.yaml`

### Step 2: Access Debug Panels Directly

Even if the Sankey chart doesn't render, the debug panels should still be visible below it:

1. **Navigate to Energy Flow tab** (chart-sankey icon in sidebar)
2. **Scroll down** - Even if chart area is blank/empty, keep scrolling
3. **Look for "🔍 Sankey Chart Status" panel** - It should still appear below
4. **Check entity states** - This shows if the problem is configuration or entity availability

### Step 3: Verify Entity Availability

Use Developer Tools to check if all required entities exist:

1. Go to **Developer Tools → States**
2. Search for and verify these entities exist:
   - `sensor.total_solar_power`
   - `sensor.grid_power`
   - `sensor.battery_power`
   - `sensor.solar_to_house`
   - `sensor.solar_to_battery`
   - `sensor.solar_to_grid`
   - `sensor.grid_to_house`
   - `sensor.grid_to_battery`
   - `sensor.battery_to_house`
   - `sensor.house_consumption`

3. If any entities are **missing** (not found in States):
   - Check `templates.yaml` has all sensor definitions
   - Reload template entities: **Developer Tools → YAML → Reload Template Entities**
   - Check Home Assistant logs for template errors

### Step 4: Validate YAML Configuration

1. **Check YAML Syntax**
   - Go to **Developer Tools → YAML → Check Configuration**
   - Look for any configuration errors
   - Pay attention to `ui-lovelace.yaml` errors

2. **Common YAML Issues in Sankey Chart**:
   - Incorrect indentation (must use 2 spaces, not tabs)
   - Missing colons after keys
   - Entity IDs don't match actual sensors
   - Incorrect `children:` references
   - Missing `entity_id:` vs `entity:` confusion

3. **Review Sankey Chart Structure** in `ui-lovelace.yaml`:
   ```yaml
   - type: custom:sankey-chart
     sections:
       - entities:
           - entity_id: sensor.name  # Must match exactly
             children:
               - sensor.child_name  # Must exist
   ```

### Step 5: Hard Refresh and Clear Cache

Configuration errors sometimes persist in browser cache:

1. **Hard Refresh**:
   - **Chrome/Edge**: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
   - **Firefox**: Ctrl+Shift+R or Cmd+Shift+R
   - **Safari**: Cmd+Option+R

2. **Clear Browser Cache**:
   - Chrome/Edge: Ctrl+Shift+Delete
   - Firefox: Ctrl+Shift+Delete
   - Safari: Cmd+Option+E
   - Select "Cached images and files"
   - Clear data and reload

3. **Restart Home Assistant** if changes made to YAML files:
   - Settings → System → Restart

---

## Quick Reference (For Working Sankey Charts)

### How to Check Sankey Status

1. **Open Home Assistant**
2. **Navigate to "Energy Flow" tab** (chart-sankey icon)
3. **Scroll down past the Sankey chart**
4. **Look at "🔍 Sankey Chart Status" panel**

### Status Indicators

| Status | Meaning | Action Required |
|--------|---------|-----------------|
| Chart not rendering | Configuration error | See [Configuration Error section](#️-if-sankey-chart-shows-configuration-error-or-doesnt-render) above |
| ✅ OK | All entities working | None - Sankey should display correctly |
| ❌ ERROR | Some entities unavailable | Check error panel above for details |
| 10/10 Available | All entities operational | None |
| 7/10 Available | 3 entities not working | Fix unavailable entities |

**Note**: If you see "Configuration Error" or the chart doesn't appear at all, scroll to the top of this guide for specific troubleshooting steps.

## Debug Panels Overview

### 1. Auto-Appearing Error Panel
**When it appears:** Only when `sensor.sankey_entity_check` shows ERROR

**What it shows:**
- ⚠️ Warning header
- List of unavailable entities
- List of entities with invalid values
- Specific recommendations for fixing

**Example:**
```
⚠️ Sankey Chart Debug Information

Status: ERROR
Available Entities: 8/10

🔴 Unavailable Entities:
- sensor.fronius_solar_power - State: unavailable
- sensor.battery_power - State: unknown

💡 Recommendations:
- Check Fronius Modbus connection (IP: 192.168.178.92)
- Check charging_state and energy sensors
```

### 2. Sankey Chart Status Panel
**Always visible** - Provides quick status at a glance

**Shows:**
- Entity Check Status: OK or ERROR
- Available Entities: X/10
- Diagnosis message
- Quick status of 4 main entities

### 3. Detailed Entity Values Panel
**Always visible** - Shows all entity values

**Organized by:**
- Primary Sources (Solar, Grid, Battery)
- Flow Sensors (Solar flows, Grid flows, Battery flows)
- Final Consumption
- Supporting Sensors

**Useful for:**
- Verifying actual power values
- Checking when entities last updated
- Identifying stuck sensors

## Common Issues and Solutions

### Issue: "sensor.fronius_solar_power unavailable"

**Cause:** Fronius inverter Modbus connection issue

**Solutions:**
1. Check inverter is powered on
2. Verify IP address is 192.168.178.92
3. Check network connection
4. Restart Modbus integration:
   - Settings → Devices & Services
   - Find "Modbus" integration
   - Click "..." → Reload

### Issue: "sensor.balkonkraftwerk_power unavailable"

**Cause:** Deye inverter offline or not communicating

**Solutions:**
1. Check inverter is powered on (needs sunlight)
2. Verify IP address is 192.168.178.78
3. Check WiFi connection
4. Wait for sunrise if at night
5. Restart integration if needed

### Issue: "sensor.battery_power unavailable"

**Cause:** Depends on multiple sensors

**Solutions:**
1. Check `sensor.charging_state` is available
2. Check `sensor.reading_energy_inverter_ac_output`
3. Check `sensor.reading_energy_main_meter`
4. Verify Fronius connection (battery data comes from inverter)

### Issue: "sensor.grid_power unavailable"

**Cause:** Main meter sensor not available

**Solutions:**
1. Check `sensor.reading_energy_main_meter`
2. Verify Fronius Smart Meter connection
3. Check Modbus configuration

### Issue: Flow sensors unavailable (solar_to_house, etc.)

**Cause:** Dependent on primary source sensors

**Solutions:**
1. Fix primary source sensors first (solar, grid, battery)
2. Wait for template sensors to recalculate
3. Check `sensor.charging_state` is valid
4. Reload template sensors:
   - Developer Tools → YAML → Reload "Template Entities"

## Using Developer Tools

### Check Individual Entity
1. Go to **Developer Tools → States**
2. Search for entity name (e.g., "sensor.fronius_solar_power")
3. Check:
   - State value (should be a number)
   - Last Changed/Updated time
   - Attributes

### Reload Template Sensors
If templates aren't updating:
1. **Developer Tools → YAML**
2. Click **"Reload Template Entities"**
3. Wait 10 seconds
4. Check status again

### Check Logs
1. **Settings → System → Logs**
2. Search for:
   - "template"
   - "modbus"
   - Entity names
3. Look for errors or warnings

## Entity Dependencies

### Primary Sources
These must work first:

```
sensor.fronius_solar_power
  └─ Depends on: Fronius Modbus connection
  └─ Sensors: fronius_dc_power_1, fronius_dc_power_2, fronius_dc_sf

sensor.balkonkraftwerk_power
  └─ Depends on: Deye inverter connection
  └─ Sensors: sensor.inverter_power

sensor.total_solar_power
  └─ Depends on: fronius_solar_power + balkonkraftwerk_power

sensor.grid_power
  └─ Depends on: reading_energy_main_meter

sensor.battery_power
  └─ Depends on: charging_state, inverter_ac_output, main_meter, total_solar_power
```

### Flow Sensors
These depend on primary sources:

```
sensor.solar_to_house
  └─ Needs: total_solar_power, charging_state, house_consumption

sensor.solar_to_battery
  └─ Needs: total_solar_power, charging_state

sensor.solar_to_grid
  └─ Needs: total_solar_power, grid_power

sensor.grid_to_house
  └─ Needs: grid_power, charging_state

sensor.grid_to_battery
  └─ Needs: grid_power, charging_state

sensor.battery_to_house
  └─ Needs: charging_state, battery_power calculation
```

## Automation for Alerts

You can create an automation to notify when issues occur:

```yaml
automation:
  - alias: "Sankey Chart Issue Alert"
    trigger:
      - platform: state
        entity_id: sensor.sankey_entity_check
        to: "ERROR"
        for: "00:05:00"  # Alert after 5 minutes
    action:
      - service: notify.mobile_app
        data:
          title: "Sankey Chart Issue"
          message: >
            {{ state_attr('sensor.sankey_entity_check', 'available_count') }}/10 entities available.
            Check Energy Flow dashboard for details.
```

## Maintenance Checklist

### Daily
- [ ] Check Sankey Chart Status shows "OK"
- [ ] Verify chart displays correctly
- [ ] Check Available Entities shows 10/10

### Weekly
- [ ] Review Detailed Entity Values panel
- [ ] Check all entities have recent timestamps
- [ ] Verify no entities stuck at 0 during production hours

### Monthly
- [ ] Review any recurring unavailable entities
- [ ] Check for pattern in errors (time of day, weather conditions)
- [ ] Update documentation if new issues discovered

## Testing the Debug System

### Simulate Issues
To test if debug panels work:

1. **Disable Modbus integration temporarily**
   - Should show Fronius sensors as unavailable
   - Error panel should appear
   - Recommendations should mention Modbus

2. **Check at night**
   - Solar sensors will naturally be 0 (valid)
   - Should still show as "OK" since 0 is valid

3. **During maintenance**
   - If inverter offline, should detect immediately
   - Clear indication of which system is affected

## Advanced: Using Debug Sensors in Automations

### Example: Restart Integration on Error

```yaml
automation:
  - alias: "Auto-fix Modbus on Sankey Error"
    trigger:
      - platform: state
        entity_id: sensor.sankey_entity_check
        to: "ERROR"
        for: "00:10:00"
    condition:
      - condition: template
        value_template: >
          {{ 'sensor.fronius_solar_power' in 
             state_attr('sensor.sankey_entity_check', 'unavailable_entities') }}
    action:
      - service: homeassistant.reload_config_entry
        target:
          entity_id: sensor.fronius_dc_power_1
```

## Support

### Configuration Errors vs Entity Issues

- **Configuration Error** (Chart doesn't render at all): See [⚠️ Configuration Error section](#️-if-sankey-chart-shows-configuration-error-or-doesnt-render) at the top of this guide
- **Entity Issues** (Chart renders but shows wrong/missing data): Use the debug panels as described in this guide

### If Issues Persist

After following this guide:

1. Check Home Assistant logs (Settings → System → Logs)
2. Verify YAML syntax with YAML validator (Developer Tools → YAML)
3. Ensure Home Assistant is up to date
4. Review [SANKEY_INSTALLATION.md](SANKEY_INSTALLATION.md) for installation issues
5. Check [ENERGY_FLOW_SETUP.md](ENERGY_FLOW_SETUP.md) for setup guidance

---

**Last Updated:** 2024
**Version:** 1.0
**Author:** Julian Bartholomeyczik
