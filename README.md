# Battery Management Automation for Home Assistant

This project is licensed under the BSD-3-Clause License. See `LICENSE.txt` for more information.

I've incorporated suggestions from many people throughout the code. Thanks to everyone who contributed their ideas!

## Project Intentions
This project aims to automate the charging and discharging behavior of a basement battery system to optimize energy costs and maximize the usage of renewable energy. The key features include:

- **Automate Charging for Low Energy Prices**: Charging is automated to occur during times when electricity prices are low.
- **Efficient Battery Hold Mode**: Maintains target SOC using minimal charge/discharge rates instead of inefficient cycling, improving energy efficiency by 2-5%.
- **Limit Discharging During Car Charging**: Prevent the battery from discharging when a car is being charged via the connected wallbox to maintain energy efficiency.
- **Car Smart Charging**: Solar-backed boost (lend battery energy to the car when the forecast shows the sun will refill it) and cheap-grid windows (switch the wallbox to full grid charging during very cheap price windows). See `CAR_SMART_CHARGING.md`.
- **Grid Outage Guard (Inselbetrieb)**: The Fronius full backup powers the whole house in an island, but the Wattpilot has no island awareness. On detected grid loss (island frequency ~53 Hz or Smart Meter loss) the wallbox is forced to Eco, grid charging and discharge limits are blocked (they would starve the island), and car boost only runs above a high island battery floor (80%). Everything restores automatically when the grid returns. See `CAR_SMART_CHARGING.md` § Grid outage.
- **Spend Clear Overnight Surplus Carefully**: If the battery is very likely to reach the next strong solar window with unused energy, allow a small, capped, price-aware discharge budget instead of preserving surplus that would only reduce PV headroom.
- **Incorporate Solar Forecast**: The automation takes the expected solar generation into account to ensure the battery charges when solar production is anticipated to be lower.
- **Tibber Pulse Monitoring**: Monitor the Tibber Pulse sensor health and receive notifications when the sensor is not functioning (e.g., low battery or connectivity issues).
- **Balkonkraftwerk Integration**: Monitor the 800W balcony power plant (Deye Micro Inverter) for real-time power production and status.
- **Hardware Setup**: This setup is designed for a **Fronius Gen24 6.0 Inverter**, **Wattpilot Wallbox**, **BYD Battery Pack**, and **Deye Micro Wechsel 1** (800W Balkonkraftwerk).

**Note:** This project might help others, but it's very far from perfect. Many components are not structured well enough, and further documentation and refactoring are needed. The algorithm is also a work in progress.

## Home Assistant Extensions Used
The automations and scripts make use of the following Home Assistant integrations:

1. **Modbus Integration**: Used to communicate with the **Fronius Inverter** and **Deye Micro Inverter** for reading battery states, inverter status, and controlling charging parameters (as seen in `modbus.yaml`). Make sure **Modbus TCP** is activated on your Fronius inverter and that the Deye logger is accessible via Modbus.
2. **REST Integration**: Used to query energy prices from **Tibber** to determine optimal times to charge the battery (as specified in `configuration.yaml`).
3. **Template Sensors**: Custom sensors and binary sensors are used for calculations like determining when the price is lowest or checking the battery's state of charge (`templates.yaml`).
4. **Input Booleans & Input Numbers**: Used for managing states like whether the battery charging automation is active or to set target SoC levels (`configuration.yaml`).
5. **Scripts**: Scripts such as `set_regular_charge`, `start_limit_discharging`, and `start_battery_charging` are defined in `scripts.yaml` to control the battery based on automation triggers.
6. **HACS (Home Assistant Community Store)**: Various custom components are installed via HACS, including the **Solar PV Forecast** to estimate solar energy production.
7. **Modbus Proxy**: A proxy to handle Modbus communication more efficiently is used in this setup.

See [OPERATIONAL_FIXES.md](OPERATIONAL_FIXES.md) for grid uncertainty handling, forecast date selection, power-flow corrections, accounting limits and the structured logger deployment.

## Current Issues & Areas for Improvement
The system has undergone significant improvements:

### Recent Improvements (2024)
- ✅ **Code Refactoring**: Extracted repeated template logic into reusable template sensors
- ✅ **Simplified Automations**: Reduced code duplication by using helper sensors for charging decisions
- ✅ **Enhanced UI**: Added comprehensive Lovelace dashboard for easy monitoring and control
- ✅ **Better Documentation**: Improved code comments and structure
- ✅ **Algorithm Improvements**: Better separation of concerns with dedicated sensors for charging logic
- ✅ **Battery Hold SOC Mode**: Integrated efficient hold mode to maintain target SOC without cycling (Dec 2024)

### Ongoing Considerations
- The energy price evaluation could be further optimized with predictive analytics
- Additional edge case handling for extreme weather or price scenarios
- Integration with additional energy providers beyond Tibber

## File Structure
- **`automations.yaml`**: Contains the main automation logic for managing battery charging and discharging actions, as well as notifications for Tibber Pulse sensor health monitoring. Now simplified with cleaner condition checking using helper sensors.
- **`modbus.yaml`**: Configuration for communication with the Fronius inverter using Modbus.
- **`scripts.yaml`**: Defines the scripts used by the automation to start and stop charging or to limit discharging. Includes detailed comments explaining Modbus register usage.
- **`configuration.yaml`**: Main configuration file for Home Assistant, including input booleans, sensors, binary sensors (including Tibber Pulse monitoring), and default integrations.
- **`templates.yaml`**: Template sensors used for custom calculations based on inverter readings and energy prices. Now includes helper sensors to reduce code duplication.
- **`ui-lovelace.yaml`**: Comprehensive Lovelace dashboard for battery management with multiple views for overview, charging logic, configuration, monitoring, and advanced controls.
- **`LICENSE.txt`**: BSD-3-Clause license for the project.

## How to Use
1. Ensure all hardware is connected and accessible through Home Assistant.
2. Update the IP addresses and any configuration details as per your network setup.
3. Copy the configuration files into your Home Assistant setup.
4. Modify the energy price thresholds and target SoC settings to fit your specific requirements.
5. Access the Battery Management dashboard from the Home Assistant sidebar for monitoring and control.

## User Interface

The Home energy dashboard uses four primary tabs: **Overview**, **Energy**, **Charging**, and **Settings**. Responsive Sections layouts and a dedicated light/dark theme give the custom energy cards and native controls a shared appearance.

- **Overview:** battery/target/price/mode summary, a plain-language decision, compact phone energy flow, user controls, car status, price/solar outlook, and monthly price advantage.
- **Energy:** expanded flow, recent power history, allocations, and links to Solar and History.
- **Charging:** battery targets and prices, a separate mode timeline, and battery/car decision details.
- **Settings:** grouped preferences plus links to Diagnostics, Algorithm details, Manual service actions, and History.

System-managed flags are read-only. Missing readings remain unavailable; partial telemetry uses warning styling, and unknown SoC is distinct from an empty battery. All original entity references remain accessible in the detail views. Automation behavior is unchanged by the visual redesign.

See [UI_DASHBOARD_GUIDE.md](UI_DASHBOARD_GUIDE.md) for current usage, validation, and installation. [ENERGY_FLOW_DESIGN.md](ENERGY_FLOW_DESIGN.md) documents the diagram's power conventions. The local [energy preview](previews/energy-flow.html) renders the real custom elements with illustrative scenarios.

## Getting Started

### Tests and bug review

The project includes offline tests for battery control, reserve recovery,
grid interlocks, power accounting, logging and dashboard behavior. See
[tests/README.md](tests/README.md) for setup and commands, and
[BUG_REVIEW.md](BUG_REVIEW.md) for the latest findings from code and live-instance
diagnostics and corrections. All regression tests run without expected-failure
markers.

For anyone wanting to expand or improve the project, start by focusing on:
- **Energy Price Evaluations**: The system now includes price percentile analysis and average price tracking for better decision-making.
- **Documentation**: All YAML files now include comprehensive comments for easier maintenance.
- **Algorithm Logic**: The charging algorithm uses a multi-tier approach:
  1. **Primary**: Charge when price is at absolute lowest AND low solar forecast
  2. **Secondary**: Charge when price is low (12h window) AND very low solar forecast
  3. **Opportunistic**: Charge when price is in bottom 25% AND battery very low
  4. **Hysteresis**: Built-in buffer prevents rapid charge cycling

### Algorithm Improvements (2024)
- **Price Percentile Analysis**: Current price is evaluated relative to next 12 hours
- **Average Price Tracking**: Better context for price evaluation
- **Enhanced Hysteresis**: Stop charging includes buffer to prevent cycling
- **Opportunistic Charging**: Additional charging opportunity when prices are good but not optimal
- **Multi-condition Logic**: Three-tier decision system for charging initiation
- **Battery Hold SOC Mode** (December 2024): Efficient state maintenance at target SOC
  - Replaces inefficient charge/discharge cycling with stable hold pattern
  - Uses minimal charge/discharge rates (1% each) when at target
  - Improves energy efficiency by 2-5%
  - Extends battery lifespan through reduced cycle count
  - See `HOLD_SOC_INTEGRATION_COMPLETE.md` for full details
- **Prevent Discharge Mode** (December 2024): Keeps battery at target level
  - Activates when battery reaches computed target SoC
  - Prevents unwanted discharge after charging completes
  - Uses `binary_sensor.should_prevent_discharge` to trigger
- **Dynamic Discharge Limiting** (December 2024): Price-aware discharge control
  - `sensor.discharge_limit_percentage` adjusts based on current price vs average
  - Higher prices allow more discharge (up to 50% during very high prices)
  - Protects battery during car charging (default 10% limit)
  - See `script.set_dynamic_discharge_limit` for implementation
- **Surplus Discharge Budget**: Strong-solar overnight optimization
  - `sensor.battery_surplus_discharge_power` estimates battery energy that is unlikely to be needed before solar production resumes
  - Current electricity price only changes aggressiveness after surplus has been proven
  - Car-charging discharge remains capped by `input_number.battery_surplus_extra_discharge_cap_w`
  - See `BATTERY_SURPLUS_DISCHARGE_POLICY.md` for the intent, guardrails, and tuning guidance

Feel free to raise issues, suggest features, or contribute improvements.

*Last Updated: October 2026*
