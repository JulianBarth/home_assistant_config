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
- **Hardware Setup**: This setup is designed for a **Fronius Gen24 6.0 Inverter**, **Wattpilot Wallbox**, and a **BYD Battery Pack**.

**Note:** This project might help others, but it's very far from perfect. Many components are not structured well enough, and further documentation and refactoring are needed. The algorithm is also a work in progress.

## Home Assistant Extensions Used
The automations and scripts make use of the following Home Assistant integrations:

1. **Modbus Integration**: Used to communicate with the **Fronius Inverter** for reading battery states and controlling charging parameters (as seen in `modbus.yaml`). Make sure **Modbus TCP** is activated on your Fronius inverter.
2. **REST Integration**: Used to query energy prices from **Tibber** to determine optimal times to charge the battery (as specified in `configuration.yaml`).
3. **Template Sensors**: Custom sensors and binary sensors are used for calculations like determining when the price is lowest or checking the battery's state of charge (`templates.yaml`).
4. **Input Booleans & Input Numbers**: Used for managing states like whether the battery charging automation is active or to set target SoC levels (`configuration.yaml`).
5. **Scripts**: Scripts such as `set_regular_charge`, `start_limit_discharging`, and `start_battery_charging` are defined in `scripts.yaml` to control the battery based on automation triggers.
6. **HACS (Home Assistant Community Store)**: Various custom components are installed via HACS, including the **Solar PV Forecast** to estimate solar energy production.
7. **Modbus Proxy**: A proxy to handle Modbus communication more efficiently is used in this setup.

## Current Issues & Areas for Improvement
- The logic for determining when to charge or limit discharge could be improved to handle edge cases better.
- The documentation needs more clarity and structuring to make the automation understandable and easier to maintain.
- The current energy price evaluation could be optimized to more precisely determine future price trends.

## File Structure
- **`automations.yaml`**: Contains the main automation logic for managing battery charging and discharging actions, as well as notifications for Tibber Pulse sensor health monitoring.
- **`modbus.yaml`**: Configuration for communication with the Fronius inverter using Modbus.
- **`scripts.yaml`**: Defines the scripts used by the automation to start and stop charging or to limit discharging.
- **`configuration.yaml`**: Main configuration file for Home Assistant, including input booleans, sensors, binary sensors (including Tibber Pulse monitoring), and default integrations.
- **`templates.yaml`**: Template sensors used for custom calculations based on inverter readings and energy prices.
- **`LICENSE.txt`**: BSD-3-Clause license for the project.

## How to Use
1. Ensure all hardware is connected and accessible through Home Assistant.
2. Update the IP addresses and any configuration details as per your network setup.
3. Copy the configuration files into your Home Assistant setup.
4. Modify the energy price thresholds and target SoC settings to fit your specific requirements.

## Getting Started
For anyone wanting to expand or improve the project, start by focusing on:
- **Energy Price Evaluations**: Improve the forecasting mechanism for energy prices and solar generation.
- **Documentation**: Better structure and comments in the YAML files for easier future maintenance.

Feel free to raise issues, suggest features, or contribute improvements.

