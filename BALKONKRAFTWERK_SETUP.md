# Balkonkraftwerk Setup Guide

## Device Information
- **Name**: Deye Micro Wechsel 1
- **Type**: 800W Micro Inverter
- **IP Address**: 192.168.178.78
- **MAC Address**: 40:2A:8F:34:72:CA
- **Logger Serial**: 3966925526
- **Micro Wechsel Richter**: 23110303D1

## What Has Been Done

### 1. Modbus Configuration (`modbus.yaml`)
Added a new Modbus TCP connection to communicate with the Deye micro inverter. The following sensors have been configured:

- **deye_ac_power**: Current power output in Watts (updated every 10 seconds)
- **deye_daily_energy**: Total energy produced today in kWh (updated every 30 seconds)
- **deye_grid_voltage**: Grid voltage in Volts (updated every 30 seconds)
- **deye_grid_frequency**: Grid frequency in Hz (updated every 30 seconds)
- **deye_temperature**: Inverter temperature in °C (updated every 60 seconds)

### 2. Template Sensors (`templates.yaml`)
Created user-friendly template sensors:

- **Balkonkraftwerk Power**: Displays current power output
- **Balkonkraftwerk Daily Energy**: Shows daily energy production
- **Balkonkraftwerk Status**: Shows status (Producing/Idle/Offline)
- **Balkonkraftwerk Online**: Binary sensor for connectivity status

### 3. UI Dashboard (`ui-lovelace.yaml`)
Added Balkonkraftwerk monitoring to the Home Assistant dashboard:

- **Overview Tab**: New card showing current power, daily energy, status, and technical details
- **Monitoring Tab**: 24-hour history graph of power output and temperature

### 4. Documentation (`README.md`)
Updated the project documentation to include the Deye Micro Wechsel 1 in the hardware setup.

## What You Need to Do

### Step 1: Verify Modbus TCP Access
Before deploying this configuration, verify that your Deye micro inverter is accessible via Modbus TCP:

1. Ensure the inverter's logger is connected to your network at IP `192.168.178.78`
2. Verify that Modbus TCP is enabled on the logger (usually port 502)
3. You may need to configure the logger's WiFi settings or enable Modbus via the Solarman app

### Step 2: Test the Configuration Locally
1. Copy the modified files to your Home Assistant configuration directory
2. Check the configuration: `Settings` → `System` → `Check Configuration`
3. If the check passes, restart Home Assistant

### Step 3: Verify Sensor Data
After restart, check if the sensors are receiving data:
1. Go to `Developer Tools` → `States`
2. Search for `sensor.deye_` to see all Deye sensors
3. Verify that they show actual values (not "unavailable" or "unknown")

### Step 4: Adjust Modbus Registers (If Needed)
If the sensors show incorrect values or are unavailable, you may need to adjust the Modbus register addresses. Common alternatives for Deye/Solis inverters:

- **AC Power**: Address 0, 4, or 13
- **Daily Energy**: Address 60, 62, or 70
- **Grid Voltage**: Address 49, 51, or 73
- **Grid Frequency**: Address 50 or 52
- **Temperature**: Address 90 or 93

You can find the correct registers in:
- The Deye/Solis Modbus documentation
- The Solarman app (if it shows live data, Modbus should work)
- HACS integrations like "Solarman" which may have the correct register map

### Step 5: Customize the Dashboard (Optional)
You can customize the Balkonkraftwerk card in `ui-lovelace.yaml` to:
- Change the display order
- Add or remove sensors
- Adjust the history graph time range
- Add alerts for low production

## Troubleshooting

### Sensors Show "Unavailable"
**Possible Causes:**
1. Modbus TCP is not enabled on the logger
2. The IP address is incorrect
3. Firewall is blocking port 502
4. The Modbus register addresses are wrong for your specific model

**Solutions:**
- Ping the IP address to verify connectivity: `ping 192.168.178.78`
- Use a Modbus testing tool (like `mbpoll`) to test the connection
- Check the Solarman app to see if data is being logged
- Consult the Deye/Solis Modbus protocol documentation for your inverter model

### Incorrect Values
If sensors show values but they seem incorrect:
- Check the `scale` parameter in `modbus.yaml` (multiplier for the raw value)
- Verify the `data_type` (uint16, int16, float32, etc.)
- Try different register addresses

### Alternative Integration Methods
If Modbus TCP doesn't work, consider:
1. **HACS Integration**: Install "Solarman" or "Deye" integration from HACS
2. **REST API**: Some loggers expose a REST API on port 8899
3. **MQTT**: Configure the logger to publish data via MQTT

## Additional Resources
- [Deye Inverter Modbus Protocol](https://github.com/home-assistant/core/issues/xxxx)
- [Solarman Integration for HACS](https://github.com/StephanJoubert/home_assistant_solarman)
- [Home Assistant Modbus Documentation](https://www.home-assistant.io/integrations/modbus/)

## Contact
If you have issues or need to adjust the configuration, the register addresses in `modbus.yaml` can be modified without affecting other parts of the system.
