# Energy Flow Visualization Examples

## System Overview

This document provides visual examples and descriptions of the energy flow visualization feature.

## Energy Flow Diagram

```
                    ☀️ SOLAR PRODUCTION
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
    Fronius              Deye                   │
   (6.0 kW)          Balkonkraftwerk            │
                         (800W)                 │
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                    Total Solar Power
                    (up to 6.8 kW)
                            │
                            ↓
        ┌───────────────────────────────────────┐
        │         ENERGY DISTRIBUTION           │
        │         (Fronius Gen24 6.0)           │
        └───────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ↓                   ↓                   ↓
    🔋 BATTERY          🏠 HOUSE           🔌 GRID
    (BYD Pack)       (Consumption)      (Import/Export)
        │                   │
        │                   ├─→ General Load
        │                   └─→ 🚗 Wallbox (Wattpilot)
        │
        └─→ Storage / Supply
```

## Energy Flow States

### 1. Sunny Day - Excess Solar Production
```
☀️ Solar: 5000W
├─→ House: 2000W (direct)
├─→ Battery: 1500W (charging)
└─→ Grid: 1500W (export)

🔋 Battery: CHARGING (50% → 80%)
🏠 House: 2000W
🔌 Grid: -1500W (export)
```

### 2. Sunny Day - Moderate Solar Production
```
☀️ Solar: 2500W
├─→ House: 2000W (direct)
└─→ Battery: 500W (charging)

🔋 Battery: CHARGING (60% → 70%)
🏠 House: 2000W
🔌 Grid: 0W (balanced)
```

### 3. Cloudy Day - Low Solar Production
```
☀️ Solar: 500W
└─→ House: 500W (partial)

🔋 Battery: DISCHARGING → 1000W → House
🔌 Grid: 500W → House (import)

🏠 House: 2000W (500 solar + 1000 battery + 500 grid)
```

### 4. Night - No Solar
```
☀️ Solar: 0W

🔋 Battery: DISCHARGING → 1800W → House
🔌 Grid: 200W → House (import)

🏠 House: 2000W (1800 battery + 200 grid)
```

### 5. EV Charging - Day
```
☀️ Solar: 4000W
├─→ House: 1500W
└─→ Wallbox: 2500W

🔋 Battery: HOLDING
🏠 House: 1500W
🚗 Wallbox: 2500W
🔌 Grid: 0W
```

### 6. EV Charging + Grid Charging (Low Prices)
```
☀️ Solar: 0W (night)

🔌 Grid: 7000W
├─→ Wallbox: 5000W
└─→ Battery: 2000W (charging)

🏠 House: 1000W (from battery discharge at low rate)
🔋 Battery: CHARGING (40% → 80%)
```

## UI Components

### Sankey Chart
The main visualization showing:
- **Width of flow lines**: Proportional to power (W)
- **Color coding**:
  - 🟡 Amber/Yellow: Solar production
  - 🔵 Blue: Grid connection
  - 🟢 Green: Battery
  - 🔴 Red: House consumption
  - 🟣 Purple: Wallbox/EV

### Status Cards
Real-time status showing:
```
☀️ Total Solar:     3500 W
🔋 Battery:         Charging 65%
🔌 Grid:            -500 W (Export)
🏠 House:           2000 W
🚗 Wallbox:         0 W
```

### Gauges
Visual representations:
- Solar Power: 0-7000W (green when producing)
- Battery Level: 0-100% (green >50%, yellow 20-50%, red <20%)
- Grid Power: -5000W to +5000W (green export, red import)
- House Consumption: 0-10000W

### Energy Flow Details
Individual flow sensors:
```
Solar → House:          2000 W
Solar → Battery:        1000 W
Solar → Grid:           500 W
Battery → House:        0 W
Grid → Battery:         0 W
Grid → House:           0 W
```

## Calculation Logic

### Grid Power
```
Positive value: Import from grid
Negative value: Export to grid
Zero: Balanced / Self-sufficient
```

### Battery Power
```
CHARGING state:
  Battery Power = (Grid + Solar - AC Output)
  
DISCHARGING state:
  Battery Power = -(AC Output - Solar - Grid)
  
Other states:
  Battery Power = 0
```

### House Consumption
```
House = Total AC Output - Wallbox Power
```

### Solar Flows
```
Solar to House:
  - During discharge/holding: min(Solar, House consumption)
  - During charging: 0

Solar to Battery:
  - During charging: max(Solar, 0)
  - Other times: 0

Solar to Grid:
  - When Grid < 0 (export): abs(Grid)
  - Other times: 0
```

## Use Cases

### Optimizing Self-Consumption
Monitor the **Solar → House** flow to maximize direct solar usage:
- High value = Good self-consumption
- Low value = Consider load shifting

### Battery Management
Watch **Grid → Battery** and **Solar → Battery**:
- Charging during low prices (grid)
- Charging from excess solar
- Avoid charging during peak prices

### Grid Independence
Track **Grid Power**:
- Negative = Exporting (earning)
- Near zero = Self-sufficient (optimal)
- Positive = Importing (costs)

### EV Charging Coordination
Monitor **Wallbox** interaction:
- Best: Solar → Wallbox
- Good: Grid → Wallbox (during low prices)
- Avoid: Battery → Wallbox (unless configured)

## Performance Indicators

### Self-Sufficiency Rate
```
Self-Sufficiency = (Solar Direct + Battery Use) / Total Consumption
Target: >70% daily average
```

### Solar Usage Rate
```
Solar Usage = (Solar to House + Solar to Battery) / Total Solar
Target: >90% (minimize grid export)
```

### Battery Efficiency
```
Efficiency = Energy Discharged / Energy Charged
Expected: 85-95% (round-trip)
```

## Troubleshooting

### All Zeros
- Check Modbus connection (Fronius)
- Verify Deye inverter online
- Check template sensor states

### Negative House Consumption
- Indicates calculation error
- Review AC output sensor
- Check Wallbox power sensor

### Battery Power Incorrect
- Verify charging state sensor
- Check energy balance calculation
- Review grid meter readings

### Flows Don't Add Up
- Normal: Some energy loss in conversions
- Large discrepancy: Check sensor polling intervals
- Negative flows: Review calculation logic

## Future Visualizations

Planned enhancements:
- Energy cost overlay (€/kWh)
- Carbon footprint (CO2 saved)
- Daily/monthly summaries
- Efficiency metrics
- Predictive flow modeling
- Mobile-optimized view

## Reference

For implementation details, see:
- [ENERGY_FLOW_SETUP.md](ENERGY_FLOW_SETUP.md) - Setup guide
- [templates.yaml](templates.yaml) - Sensor definitions
- [ui-lovelace.yaml](ui-lovelace.yaml) - UI configuration

---

**Note**: This is a living document. Update as the system evolves and new use cases are discovered.
