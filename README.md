# Battery Management Automation for Home Assistant

This project is licensed under the BSD-3-Clause License. See `LICENSE.txt` for more information.

I've incorporated suggestions from many people throughout the code. Thanks to everyone who contributed their ideas!

This project is licensed under the BSD-3-Clause License. See `LICENSE.txt` for more information.

## Project Intentions
This project aims to automate the charging and discharging behavior of a basement battery system to optimize energy costs and maximize the usage of renewable energy. The key features include:

- **Automate Charging for Low Energy Prices**: Charging is automated to occur during times when electricity prices are low.
- **Limit Discharging During Car Charging**: Prevent the battery from discharging when a car is being charged via the connected wallbox to maintain energy efficiency.
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

## Current Issues & Areas for Improvement
The system has undergone significant improvements:

### Recent Improvements (2024)
- ✅ **Code Refactoring**: Extracted repeated template logic into reusable template sensors
- ✅ **Simplified Automations**: Reduced code duplication by using helper sensors for charging decisions
- ✅ **Enhanced UI**: Added comprehensive Lovelace dashboard for easy monitoring and control
- ✅ **Better Documentation**: Improved code comments and structure
- ✅ **Algorithm Improvements**: Better separation of concerns with dedicated sensors for charging logic

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
The system now includes a comprehensive Lovelace dashboard (`ui-lovelace.yaml`) with the following views:

**For detailed UI screenshots and usage guide, see [UI_DASHBOARD_GUIDE.md](UI_DASHBOARD_GUIDE.md)**

### Overview
- Real-time battery status and state of charge
- Automation control switches
- Current and forecasted energy prices
- Visual gauge for battery level

### Energy Flow (NEW!)
- **Interactive Sankey chart** showing real-time energy flows
- Visual representation of power distribution between:
  - Solar panels (Fronius + Balkonkraftwerk)
  - Battery storage
  - House consumption
  - Wallbox (EV charging)
  - Grid (import/export)
- Real-time power status with gauges
- Historical energy flow graphs
- Detailed flow tracking for all energy paths

**See [ENERGY_FLOW_SETUP.md](ENERGY_FLOW_SETUP.md) for complete energy flow visualization documentation**

### Charging Logic
- Charging decision indicators (should start/stop charging)
- Solar forecast conditions
- Computed target SoC based on conditions
- Car charging status from Wallbox

### Configuration
- Adjustable SoC targets for different scenarios
- Solar forecast threshold settings
- Manual control scripts for testing and override

### Monitoring
- 24-hour history graphs for battery SoC
- Charging state timeline
- Price and solar forecast correlation
- System health indicators

### Advanced
- Direct Modbus control scripts
- All control flags and debugging information
- System documentation and hardware details

## Getting Started
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

Feel free to raise issues, suggest features, or contribute improvements.

