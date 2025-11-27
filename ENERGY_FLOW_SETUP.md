# Energy Flow Visualization Setup Guide

## Overview

This document describes the energy flow visualization feature that provides a comprehensive real-time view of energy distribution in your home automation system.

## Components Visualized

### Energy Sources
1. **Fronius Solar** - Main solar system (up to 6 kW)
2. **Balkonkraftwerk** - Deye balcony power plant (800W)
3. **Grid** - Connection to electrical grid (import/export)
4. **Battery** - BYD battery pack storage

### Energy Consumers
1. **House** - General household consumption
2. **Wallbox** - Wattpilot EV charging station

## Features

### 1. Sankey Chart Visualization
- Interactive energy flow diagram
- Real-time power flow between components
- Color-coded energy paths:
  - **Amber/Yellow**: Solar production
  - **Blue**: Grid connection
  - **Green**: Battery storage
  - **Red**: House consumption
  - **Purple**: Wallbox/EV charging

### 2. Real-Time Power Status
- Current power levels for all components
- Battery state and charge level
- Grid import/export status
- Individual consumption monitoring

### 3. Energy Flow Gauges
- Visual gauges for key metrics:
  - Solar power production (0-7000W)
  - Battery level (0-100%)
  - Grid power (-5000W to +5000W)
  - House consumption (0-10000W)

### 4. Detailed Flow Tracking
Individual sensor tracking for:
- Solar → House (direct consumption)
- Solar → Battery (storage)
- Solar → Grid (export)
- Battery → House (discharge)
- Grid → Battery (charging)
- Grid → House (import)

### 5. Historical Data
- 2-hour history graph
- 30-second refresh interval
- Tracks all major energy flows

## Installation

### Prerequisites

1. **Custom Card**: Sankey Chart
   ```bash
   # Install via HACS
   # 1. Go to HACS → Frontend
   # 2. Search for "Sankey Chart"
   # 3. Install the card
   ```

2. **Sensors**: All required sensors are configured in `templates.yaml`

### Configuration Files

#### 1. `configuration.yaml`
The Sankey chart resource is added to Lovelace resources:
```yaml
lovelace:
  mode: yaml
  resources:
    - url: /hacsfiles/lovelace-sankey-chart/sankey-chart.js
      type: module
```

#### 2. `templates.yaml`
Energy flow sensors are defined:
- `sensor.grid_power` - Grid import/export power
- `sensor.battery_power` - Battery charge/discharge power
- `sensor.house_consumption` - House power consumption
- `sensor.solar_to_battery` - Solar charging battery
- `sensor.solar_to_house` - Solar powering house
- `sensor.solar_to_grid` - Solar exported to grid
- `sensor.battery_to_house` - Battery powering house
- `sensor.grid_to_house` - Grid powering house
- `sensor.grid_to_battery` - Grid charging battery
- `sensor.wallbox_power` - Wallbox consumption

#### 3. `ui-lovelace.yaml`
New "Energy Flow" view added with:
- Sankey chart visualization
- Real-time status entities
- Energy flow gauges
- Detailed flow tracking
- Historical graphs
- System architecture documentation

## Usage

### Accessing the Dashboard
1. Open Home Assistant
2. Navigate to "Battery Management" dashboard
3. Click on "Energy Flow" tab

### Understanding the Visualization

#### Sankey Chart
- **Flow width**: Represents power magnitude (thicker = more power)
- **Flow direction**: Shows energy movement between components
- **Colors**: Identify energy sources and consumers

#### Status Indicators
- **Green values**: Export/production
- **Red values**: Import/consumption
- **Yellow values**: Charging
- **Blue values**: Grid interaction

### Interpreting Energy Flows

#### Common Scenarios

**1. Daytime Solar Production (Excess)**
```
Solar → House (direct use)
Solar → Battery (storage)
Solar → Grid (export excess)
```

**2. Daytime Solar Production (Insufficient)**
```
Solar → House (partial)
Grid → House (supplement)
```

**3. Nighttime / No Solar**
```
Battery → House (discharge)
Grid → House (if battery low)
```

**4. Battery Charging (Low Prices)**
```
Grid → Battery (smart charging)
Solar → House (if available)
```

**5. EV Charging**
```
Solar → Wallbox (if available)
Battery → Wallbox (if configured)
Grid → Wallbox (primary source)
```

## Sensors Details

### Power Calculation Methods

#### Grid Power
- **Source**: `sensor.reading_energy_main_meter`
- **Positive**: Importing from grid
- **Negative**: Exporting to grid

#### Battery Power
- **Calculation**: Energy balance based on charging state
- **CHARGING**: Grid + Solar - AC Output
- **DISCHARGING**: AC Output - Solar - Grid

#### House Consumption
- **Calculation**: Total AC Output - Wallbox Power
- **Purpose**: Separate household from EV charging

#### Solar Production
- **Fronius**: Calculated from DC power strings
- **Balkonkraftwerk**: Direct from Deye inverter
- **Total**: Sum of both systems

## Troubleshooting

### Sankey Chart Not Displaying
1. Verify HACS installation of Sankey Chart card
2. Clear browser cache
3. Restart Home Assistant
4. Check browser console for errors

### Incorrect Values
1. Check sensor availability in Developer Tools
2. Verify Modbus connection to Fronius inverter
3. Confirm Deye inverter connectivity
4. Check Tibber Pulse status

### Missing Data
1. Ensure all integrations are loaded:
   - Modbus (Fronius)
   - Solarman (Deye)
   - Tibber (if using)
   - Wattpilot (if using)
2. Check template sensor calculations in `templates.yaml`
3. Verify network connectivity to devices

## Customization

### Changing Colors
Edit the Sankey chart configuration in `ui-lovelace.yaml`:
```yaml
- entity_id: sensor.fronius_solar_power
  name: Fronius Solar
  color: '#YOUR_COLOR_CODE'
```

### Adjusting Gauge Ranges
Modify gauge `max` values in `ui-lovelace.yaml` to match your system:
```yaml
- type: gauge
  entity: sensor.total_solar_power
  max: 7000  # Adjust to your solar capacity
```

### Adding Components
1. Create sensor in `templates.yaml`
2. Add to Sankey chart `entities` section
3. Add flow tracking sensors as needed

## Advanced Features

### Integration with Automations
The energy flow sensors can be used in automations:
```yaml
# Example: Alert on high grid import
automation:
  - trigger:
      - platform: numeric_state
        entity_id: sensor.grid_to_house
        above: 3000
    action:
      - service: notify.mobile_app
        data:
          message: "High grid import detected: {{ states('sensor.grid_to_house') }}W"
```

### Custom Calculations
Extend `templates.yaml` for additional metrics:
```yaml
- sensor:
    - name: "Solar Self-Consumption Rate"
      unit_of_measurement: "%"
      state: >
        {% set solar = states('sensor.total_solar_power') | float %}
        {% set to_house = states('sensor.solar_to_house') | float %}
        {% if solar > 0 %}
          {{ ((to_house / solar) * 100) | round(1) }}
        {% else %}
          0
        {% endif %}
```

## Performance Considerations

### Update Frequencies
- **Modbus sensors**: 5-20 seconds
- **Template sensors**: Immediate (on state change)
- **UI refresh**: 30 seconds (configurable)

### System Load
- Energy flow calculations are lightweight
- Sankey chart updates on data change
- History graphs use standard HA recording

## Related Documentation
- [README.md](README.md) - Main project documentation
- [UI_DASHBOARD_GUIDE.md](UI_DASHBOARD_GUIDE.md) - Dashboard usage guide
- [BALKONKRAFTWERK_SETUP.md](BALKONKRAFTWERK_SETUP.md) - Balcony power plant setup

## Support

For issues or questions:
1. Check sensor states in Developer Tools → States
2. Review Home Assistant logs for errors
3. Verify device connectivity
4. Check template syntax in `templates.yaml`

## Future Enhancements

Potential improvements:
- Historical energy flow analysis (daily/weekly)
- Energy cost overlay on flows
- Predictive flow visualization
- Mobile-optimized view
- Energy efficiency scoring
- Carbon footprint tracking

## License

SPDX-License-Identifier: BSD-3-Clause

Copyright (c) 2024, Julian Bartholomeyczik
All rights reserved.
