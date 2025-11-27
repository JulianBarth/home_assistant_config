# Energy Flow Visualization - Implementation Summary

## Overview

This document summarizes the implementation of the energy flow visualization feature for the Home Assistant battery management system.

## What Was Implemented

### 1. Energy Flow Sensors (templates.yaml)

Created 10 new template sensors to track energy flows:

| Sensor | Purpose | Unit |
|--------|---------|------|
| `sensor.grid_power` | Grid import/export | W |
| `sensor.battery_power` | Battery charge/discharge | W |
| `sensor.house_consumption` | House power consumption | W |
| `sensor.solar_to_battery` | Solar → Battery flow | W |
| `sensor.solar_to_house` | Solar → House flow | W |
| `sensor.solar_to_grid` | Solar → Grid export | W |
| `sensor.battery_to_house` | Battery → House discharge | W |
| `sensor.grid_to_house` | Grid → House import | W |
| `sensor.grid_to_battery` | Grid → Battery charging | W |
| `sensor.wallbox_power` | Wallbox consumption | W |

### 2. Sankey Chart Integration (configuration.yaml)

- Added Sankey Chart resource to Lovelace configuration
- Resource URL: `/hacsfiles/lovelace-sankey-chart/sankey-chart.js`

### 3. Energy Flow Dashboard (ui-lovelace.yaml)

Created new "Energy Flow" view with:

#### Main Sankey Chart
- Interactive energy flow visualization
- Color-coded components:
  - Fronius Solar: Amber (#FFB300)
  - Balkonkraftwerk: Yellow (#FDD835)
  - Grid: Blue (#2196F3)
  - Battery: Green (#4CAF50)
  - House: Red (#FF5722)
  - Wallbox: Purple (#9C27B0)

#### Real-Time Status Cards
- Power status for all components
- Current values with last-changed timestamps
- Grouped by source/destination

#### Energy Flow Gauges
- Solar Power: 0-7000W
- Battery Level: 0-100%
- Grid Power: -5000W to +5000W
- House Consumption: 0-10000W

#### Detailed Flow Tracking
- Individual flow sensors
- Organized by flow type (solar/battery/grid)

#### Historical Graph
- 2-hour power flow history
- 30-second refresh interval
- Tracks all major components

#### System Documentation
- Architecture diagram
- Component descriptions
- Energy flow paths
- Optimization strategies

### 4. Documentation Files

Created comprehensive documentation:

| File | Purpose |
|------|---------|
| `ENERGY_FLOW_SETUP.md` | Complete setup and configuration guide |
| `ENERGY_FLOW_EXAMPLES.md` | Usage examples and scenarios |
| `ENERGY_FLOW_QUICKSTART.md` | 5-minute quick start guide |
| `SANKEY_INSTALLATION.md` | HACS installation instructions |
| `verify_energy_flow_setup.py` | Configuration verification script |

### 5. Updated Documentation

- Updated `README.md` with Energy Flow section
- Added references to new documentation

## Files Modified

1. **templates.yaml** - Added 10 energy flow sensors
2. **configuration.yaml** - Added Sankey Chart resource
3. **ui-lovelace.yaml** - Added Energy Flow view
4. **README.md** - Added Energy Flow documentation

## Files Created

1. **ENERGY_FLOW_SETUP.md** - Setup guide (7.9 KB)
2. **ENERGY_FLOW_EXAMPLES.md** - Usage examples (6.4 KB)
3. **ENERGY_FLOW_QUICKSTART.md** - Quick start (5.1 KB)
4. **SANKEY_INSTALLATION.md** - Installation guide (7.0 KB)
5. **verify_energy_flow_setup.py** - Verification script (7.5 KB)

## Technical Details

### Sensor Calculation Logic

#### Grid Power
```jinja
{{ states('sensor.reading_energy_main_meter') | float(default=0) | round(0) }}
```
- Positive = Import
- Negative = Export

#### Battery Power
```jinja
{% if charging_state == 'CHARGING' %}
  {{ (grid_power + solar_power - ac_output) | abs }}
{% elif charging_state == 'DISCHARGING' %}
  {{ -(ac_output - solar_power - grid_power) }}
{% else %}
  0
{% endif %}
```

#### House Consumption
```jinja
{{ (ac_output - wallbox_power) | abs }}
```

### Data Sources

- **Fronius Inverter**: Modbus TCP (192.168.178.92)
  - Battery SoC
  - AC Output
  - Main Meter
  - DC Power (solar)

- **Deye Balkonkraftwerk**: Solarman (192.168.178.78)
  - Power output
  - Daily energy
  - Grid parameters

- **Wattpilot Wallbox**: Integration
  - Charging power
  - Car status
  - Charging mode

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  SOLAR PRODUCTION                        │
│  ┌──────────────┐              ┌──────────────┐        │
│  │   Fronius    │              │     Deye     │        │
│  │  Gen24 6.0   │              │ Balkonkraft  │        │
│  │   (6 kW)     │              │   (800W)     │        │
│  └──────┬───────┘              └──────┬───────┘        │
│         │                              │                │
│         └──────────────┬───────────────┘                │
└────────────────────────┼────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────┐
│              ENERGY DISTRIBUTION                         │
│            (Fronius Gen24 Inverter)                      │
└─────────────────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ↓               ↓               ↓
    ┌────────┐      ┌────────┐     ┌────────┐
    │Battery │      │ House  │     │  Grid  │
    │  BYD   │      │Consump.│     │ Import/│
    │ Pack   │      │        │     │ Export │
    └────┬───┘      └───┬────┘     └────────┘
         │              │
         │              ├─→ General Load
         │              └─→ Wallbox (Wattpilot)
         │
         └─→ Charge/Discharge
```

## User Experience

### Before Implementation
- No visual representation of energy flows
- Difficult to understand energy distribution
- Hard to optimize consumption patterns

### After Implementation
- Real-time visual energy flow
- Clear understanding of power distribution
- Easy identification of optimization opportunities
- Historical tracking of energy patterns

## Performance Impact

- **Sensor Updates**: ~5-20 second intervals
- **Template Calculations**: Lightweight, immediate
- **UI Rendering**: Minimal impact
- **Storage**: Standard Home Assistant recording

## Dependencies

### Required
- Home Assistant 2023.1+
- Fronius Gen24 inverter (Modbus)
- Deye Balkonkraftwerk (Solarman)
- Template sensors configured

### Recommended
- HACS (Home Assistant Community Store)
- Sankey Chart custom card
- Tibber integration (for price data)
- Wattpilot integration (for EV data)

## Installation Requirements

1. Install HACS (if not already installed)
2. Install Sankey Chart via HACS
3. Restart Home Assistant
4. Clear browser cache
5. Navigate to Energy Flow view

## Testing

All configuration files validated:
- ✅ YAML syntax correct
- ✅ All sensors defined
- ✅ Dashboard view configured
- ✅ Resources properly linked
- ✅ Verification script passes

## Future Enhancements

Potential improvements:
- [ ] Energy cost overlay on flows
- [ ] Daily/weekly energy summaries
- [ ] Predictive flow modeling
- [ ] Mobile-optimized responsive view
- [ ] Carbon footprint tracking
- [ ] Efficiency scoring system
- [ ] Alert system for unusual patterns

## Support & Maintenance

### Documentation
- All features documented
- Examples provided
- Troubleshooting guides included
- Quick start guide available

### Verification
- Automated verification script
- Clear error messages
- Step-by-step troubleshooting

### Community
- Home Assistant forums
- GitHub repository
- Documentation files

## License

- Implementation: BSD-3-Clause License
- Sankey Chart: MIT License (external dependency)
- Home Assistant: Apache License 2.0

## Credits

- **Author**: Julian Bartholomeyczik
- **Project**: Home Assistant Battery Management
- **Year**: 2024

## Changelog

### 2024-11-27 - Initial Implementation
- Added energy flow sensors
- Integrated Sankey Chart
- Created Energy Flow dashboard view
- Added comprehensive documentation
- Created verification script

---

**Implementation Status**: ✅ Complete

**Next Steps for User**:
1. Install Sankey Chart via HACS
2. Restart Home Assistant
3. View Energy Flow dashboard
4. Enjoy real-time energy visualization!

---

**For questions or issues**, refer to:
- [ENERGY_FLOW_QUICKSTART.md](ENERGY_FLOW_QUICKSTART.md)
- [ENERGY_FLOW_SETUP.md](ENERGY_FLOW_SETUP.md)
- [SANKEY_INSTALLATION.md](SANKEY_INSTALLATION.md)
