# Battery Management System UI Dashboard

## Overview Tab

```
╔══════════════════════════════════════════════════════════════════════╗
║  🔋 Battery Management System                                        ║
║  Automated battery charging and discharging control                  ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║  BATTERY STATUS                                                       ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │ Battery State of Charge      ██████████░░░░░░░   75%        │   ║
║  │ Charging State                CHARGING                       │   ║
║  │ Charging Active              ⚡ ON                          │   ║
║  │ Discharge Limited            🔒 OFF                         │   ║
║  │ Target SoC                   ━━━━━━━━━━━━━━━━   80%        │   ║
║  └─────────────────────────────────────────────────────────────┘   ║
║                                                                       ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │                    BATTERY LEVEL GAUGE                       │   ║
║  │                                                              │   ║
║  │                         ┌───────┐                           │   ║
║  │                      ╱           ╲                          │   ║
║  │                     │      75%    │                         │   ║
║  │                      ╲           ╱                          │   ║
║  │                         └───────┘                           │   ║
║  │         RED (0-20)  YELLOW (20-50)  GREEN (50-100)         │   ║
║  └─────────────────────────────────────────────────────────────┘   ║
║                                                                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  AUTOMATION CONTROL                                                   ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │ Automation Enabled           ⚙️  ON                         │   ║
║  │ Manual Charge                🔋 OFF                         │   ║
║  │ ───────────────────────────────────────────────────────────  │   ║
║  │ Manual Target SoC            ━━━━━━━━━━━━━━━━   80%        │   ║
║  └─────────────────────────────────────────────────────────────┘   ║
║                                                                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  ENERGY PRICES (TIBBER)                                               ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │ Current Price                28.5 Cent/kWh                   │   ║
║  │ Price Percentile (12h)       📊 35%                         │   ║
║  │ Average (12h)                31.2 Cent/kWh                   │   ║
║  │ Lowest (12h)                 24.1 Cent/kWh                   │   ║
║  │ Lowest (24h)                 22.8 Cent/kWh                   │   ║
║  │ Highest (24h)                42.3 Cent/kWh                   │   ║
║  │ ───────────────────────────────────────────────────────────  │   ║
║  │ Price is Lowest              ✗ OFF                          │   ║
║  │ Price is Lowest (12h)        ✗ OFF                          │   ║
║  │ Price in Bottom 25%          ✓ ON                           │   ║
║  └─────────────────────────────────────────────────────────────┘   ║
║                                                                       ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │                    PRICE HISTORY (24h)                       │   ║
║  │  45├─────────────────────────────────────────────────────┤  │   ║
║  │    │                           ╱╲                         │  │   ║
║  │  35├──────────────────╱───────╱  ╲──────────────────────┤  │   ║
║  │    │                 ╱            ╲                       │  │   ║
║  │  25├────────╱───────╱              ╲────────╱────────────┤  │   ║
║  │    │       ╱                          ╲    ╱             │  │   ║
║  │  15├──────────────────────────────────╲──╱──────────────┤  │   ║
║  │    └───────────────────────────────────────────────────┘  │   ║
║  │     00:00    06:00    12:00    18:00    24:00             │   ║
║  └─────────────────────────────────────────────────────────────┘   ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Charging Logic Tab

```
╔══════════════════════════════════════════════════════════════════════╗
║  CHARGING DECISION LOGIC                                              ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │ Should Start Charging        ✓ ON                           │   ║
║  │ Should Stop Charging         ✗ OFF                          │   ║
║  │ Computed Target SoC          80%                            │   ║
║  │ ───────────────────────────────────────────────────────────  │   ║
║  │ SoC Threshold (High)         45%                            │   ║
║  │ SoC Threshold (Low)          85%                            │   ║
║  │ Current SoC (Normalized)     0.75                           │   ║
║  └─────────────────────────────────────────────────────────────┘   ║
║                                                                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  SOLAR FORECAST                                                       ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │ Expected Sun Low             ✓ ON                           │   ║
║  │ Expected Sun Very Low        ✗ OFF                          │   ║
║  │ Remaining Today              12,500 Wh                       │   ║
║  │ Forecast Next Hours          6,800 Wh                        │   ║
║  └─────────────────────────────────────────────────────────────┘   ║
║                                                                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  WALLBOX (CAR CHARGING)                                               ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │ Car Status                   charging                        │   ║
║  │ Charging Mode                Default                         │   ║
║  └─────────────────────────────────────────────────────────────┘   ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Configuration Tab

```
╔══════════════════════════════════════════════════════════════════════╗
║  TARGET SOC SETTINGS                                                  ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │ Target (Very Low Sun)        ━━━━━━━━━━━━━━━━━━   90%      │   ║
║  │ Target (Low Sun)             ━━━━━━━━━━         50%      │   ║
║  │ Target (Default)             ━━━                 15%      │   ║
║  │ SoC Hysteresis               ━                    5%      │   ║
║  └─────────────────────────────────────────────────────────────┘   ║
║                                                                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  SOLAR FORECAST THRESHOLDS                                            ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │ Low Sun Threshold            ━━━━━━━━━━━━━━━  15,000 Wh    │   ║
║  │ Very Low Sun Threshold       ━━━━━━━━          8,000 Wh    │   ║
║  └─────────────────────────────────────────────────────────────┘   ║
║                                                                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  MANUAL CONTROL SCRIPTS                                               ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │ 🔋 Start Charging                                           │   ║
║  │ 🔌 Stop Charging                                            │   ║
║  │ 🔒 Limit Discharge                                          │   ║
║  │ 🔓 Stop Limit Discharge                                     │   ║
║  │ ───────────────────────────────────────────────────────────  │   ║
║  │ ⚙️  Set Regular Charge                                      │   ║
║  │ ⚡ Force Half Recharge                                      │   ║
║  │ ⚡⚡ Force Full Recharge                                    │   ║
║  └─────────────────────────────────────────────────────────────┘   ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Monitoring Tab

```
╔══════════════════════════════════════════════════════════════════════╗
║  BATTERY STATE OF CHARGE (24h)                                        ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │ 100├─────────────────────────────────────────────────────┤  │   ║
║  │    │                                                      │  │   ║
║  │  75├──────────●─────────────────────────────────────────┤  │   ║
║  │    │         ╱ ╲                                         │  │   ║
║  │  50├────────╱   ╲──────────────────────●───────────────┤  │   ║
║  │    │                              ●───╱ ╲───●           │  │   ║
║  │  25├─────────────────────────●──╱         ╲╱           │  │   ║
║  │    │                    ●───╱                            │  │   ║
║  │   0├────────────────────────────────────────────────────┤  │   ║
║  │    └───────────────────────────────────────────────────┘  │   ║
║  │    Battery SoC ●    Target SoC ●                           │   ║
║  └─────────────────────────────────────────────────────────────┘   ║
║                                                                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  CHARGING STATE (24h)                                                 ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │  ON ├─────────────────────────────────────────────────────┤  │   ║
║  │     │  ████░░░░░░░░░░░░░░░███░░░░░░░░░░░░░░░░░░░░░░░░░░  │  │   ║
║  │ OFF ├─────────────────────────────────────────────────────┤  │   ║
║  │     Charging Active                                          │   ║
║  │                                                              │   ║
║  │  ON ├─────────────────────────────────────────────────────┤  │   ║
║  │     │  ░░░░░████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │  │   ║
║  │ OFF ├─────────────────────────────────────────────────────┤  │   ║
║  │     Discharge Limited                                        │   ║
║  └─────────────────────────────────────────────────────────────┘   ║
║                                                                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  SYSTEM HEALTH                                                        ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │ Tibber Pulse Status          ✓ OK                           │   ║
║  │                                                              │   ║
║  │ Active Alerts:                                               │   ║
║  │ • Battery charging notifications                             │   ║
║  │ • Low battery alerts (< 7.5%)                                │   ║
║  │ • Tibber Pulse connectivity issues                           │   ║
║  └─────────────────────────────────────────────────────────────┘   ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Advanced Tab

```
╔══════════════════════════════════════════════════════════════════════╗
║  ADVANCED MODBUS CONTROLS                                             ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │ ⚙️  Set Limited Discharge                                    │   ║
║  │ ⚙️  Half Regular Charge                                      │   ║
║  │ ⚙️  Discharge at Half Rate                                   │   ║
║  └─────────────────────────────────────────────────────────────┘   ║
║                                                                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  ALL CONTROL FLAGS                                                    ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │ battery_charging_active      ⚡ ON                          │   ║
║  │ battery_no_discharging_active 🔒 OFF                        │   ║
║  │ battery_automation_on        ⚙️  ON                         │   ║
║  │ manual_charging_on           🔋 OFF                         │   ║
║  │ manual_battery_charge        🔋 OFF                         │   ║
║  └─────────────────────────────────────────────────────────────┘   ║
║                                                                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  SYSTEM INFORMATION                                                   ║
║                                                                       ║
║  Hardware Setup                                                       ║
║  • Inverter: Fronius Gen24 6.0                                       ║
║  • Battery: BYD Battery Pack                                         ║
║  • Wallbox: Wattpilot                                                ║
║  • Energy Monitor: Tibber Pulse                                      ║
║                                                                       ║
║  Algorithm Features                                                   ║
║  • Dynamic SoC targeting based on solar forecast                     ║
║  • Price-based charging optimization                                 ║
║  • Car charging coordination                                         ║
║  • Hysteresis to prevent charge cycling                              ║
║                                                                       ║
║  Documentation                                                        ║
║  See README.md for complete setup and configuration details.         ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Dashboard Features

### Key Capabilities
1. **Real-time Monitoring**: Live battery state, charging status, and energy prices
2. **Visual Indicators**: Gauges, graphs, and status icons for quick understanding
3. **Control Interface**: Manual overrides and automation toggles
4. **Historical Data**: 24-hour graphs for battery, pricing, and charging patterns
5. **Configuration**: Adjustable thresholds and targets without editing YAML
6. **System Health**: Alerts and sensor status monitoring

### Decision Logic Transparency
The dashboard exposes all intermediate calculations:
- Price percentiles and averages
- Solar forecast evaluations
- SoC thresholds with hysteresis
- Multi-tier charging decision logic

### User Experience
- **Overview Tab**: Quick status check - is everything working?
- **Charging Logic Tab**: Understand why charging started/stopped
- **Configuration Tab**: Adjust behavior to your needs
- **Monitoring Tab**: Analyze patterns over time
- **Advanced Tab**: Deep dive into system internals

This UI provides complete visibility into the battery management system while maintaining ease of use for day-to-day monitoring.
