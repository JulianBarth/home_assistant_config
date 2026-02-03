# Project: Home Assistant Battery Management System

## General Information
- 5-person household in Germany
- Daily consumption: ~14 kWh (varies seasonally)
- Hybrid car charging adds variable load
- The electricity price is variable and changes every 15 minutes (German electricity zone via Tibber)

## System Architecture

### Hardware Components
- **Fronius Gen24 Plus 6.0**: Solar inverter with integrated battery controller
- **BYD Battery Pack**: ~10 kWh capacity home storage
- **Wattpilot Wallbox**: EV charging station with power monitoring
- **Deye Micro Inverter**: 800W balcony power plant (Balkonkraftwerk)
- **Tibber Pulse**: Smart meter for real-time energy monitoring

### Communication
- **Modbus TCP**: Direct communication with Fronius inverter (192.168.178.92:502)
- **REST API**: Tibber price data (15-minute intervals)
- **Local API**: Wattpilot and Deye status

## Key Automations

### Unified Battery Control Coordinator
Single automation that coordinates all battery control modes with clear priority:
1. **Manual Charging** (highest priority)
2. **Car + Battery Charging** (simultaneous charging during very low prices)
3. **Car Charging Only** (discharge limited to protect against EV load)
4. **Battery Charging** (normal grid charging during low prices)
5. **Normal Operation** (default state)

## Important Sensors

### Decision Sensors (Binary)
| Sensor | Purpose |
|--------|---------|
| `binary_sensor.should_start_charging` | Determines if battery should begin charging |
| `binary_sensor.should_stop_charging` | Determines if charging should stop |
| `binary_sensor.should_hold_battery_soc` | Triggers hold mode near target SoC |
| `binary_sensor.should_prevent_discharge` | Prevents discharge when at target |
| `binary_sensor.car_charging_stable` | Hysteresis-protected car charging detection |

### Computed Sensors
| Sensor | Purpose |
|--------|---------|
| `sensor.computed_target_soc` | Smart target based on consumption + solar forecast |
| `sensor.battery_control_mode` | Current operating mode |
| `sensor.discharge_limit_percentage` | Dynamic discharge limit based on price |

## Configuration Parameters

### Battery Settings (`input_number`)
| Parameter | Default | Description |
|-----------|---------|-------------|
| `battery_capacity_wh` | 10000 | Battery capacity in Wh |
| `soc_target_default` | 15% | Minimum SoC to maintain |
| `soc_hist` | 5 | Hysteresis buffer (prevents cycling) |

### Consumption Patterns (5-person household)
| Parameter | Default | Description |
|-----------|---------|-------------|
| `daily_consumption_wh` | 14000 Wh | Total daily consumption |
| `night_consumption_rate_wh` | 280 Wh/h | Consumption during sleep hours |
| `day_consumption_rate_wh` | 850 Wh/h | Consumption during active hours |
| `weekday_wake_hour` | 5.5 | Wake time on weekdays |
| `weekend_wake_hour` | 7.5 | Wake time on weekends |
| `sleep_hour` | 22 | Time when high consumption ends |

### Price Controls
| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_charge_price_cents` | 25 | Never charge above this price (ct/kWh) |
| `low_solar_threshold_wh` | 3000 | Solar forecast below this triggers "winter mode" |

## Modbus Registers

### Key Control Registers (Fronius Gen24)
| Register | Name | Description |
|----------|------|-------------|
| 40358 | StorCtl_Mod | Storage control enable (0=off, 3=on) |
| 40360 | MinRsvPct | Minimum reserve SoC |
| 40361 | SoC | Current battery state of charge (scaled) |
| 40364 | ChaSt | Charging state (1-7) |
| 40365 | OutWRte | Discharge rate (0.01% increments) |
| 40366 | InWRte | Charge rate (0.01% increments) |

### Charging States (ChaSt)
| Value | State |
|-------|-------|
| 1 | OFF |
| 2 | EMPTY |
| 3 | DISCHARGING |
| 4 | CHARGING |
| 5 | FULL |
| 6 | HOLDING |
| 7 | TESTING |

## Algorithm Overview

The charging algorithm uses multiple factors with priority-based decisions:

1. **Negative Price Detection**: Always charge to 100% on negative prices
2. **Price Ceiling**: Never charge above `max_charge_price_cents`
3. **Profitability Check**: Spread between buy/sell must exceed wear cost
4. **Price Falling Detection**: Wait for lower prices (unless in bottom 10%)
5. **Price Percentile Tiers**:
   - ≤10%: Aggressive charging (+20% SoC above calculated need)
   - ≤25%: Full calculated target
   - ≤50%: 80% of target
   - ≤70%: 50% of target (only if large deficit)
6. **Smart Winter Mode**: When solar forecast < `low_solar_threshold_wh`, ignore solar predictions
7. **Energy Deficit**: Calculated from consumption forecast minus usable solar

## Last Updated
2026-02-03

