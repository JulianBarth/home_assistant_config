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

### Step 0: Check If You Need a Modbus Converter

**Most modern Deye/Solarman loggers DO NOT need a converter** if they have WiFi connectivity. The logger acts as a Modbus TCP gateway.

**Check your logger capabilities:**
1. Try accessing `http://192.168.178.78` in a browser - if you see a web interface, Modbus TCP is likely supported
2. Check if the Solarman app shows real-time data via WiFi (not just cloud) - this indicates Modbus TCP capability
3. Logger serial 3966925526 suggests an IGEN-Tech/Solarman logger which typically supports Modbus TCP natively

**If your logger only has RS485 (no WiFi or WiFi-only cloud):**
- You'll need a **Modbus RTU-to-TCP converter** (e.g., Waveshare RS485-to-Ethernet, USR-TCP232-410S)
- Or use the **HACS "Solarman" integration** instead (cloud-based, no hardware needed)

**If unsure:** Try the configuration as-is first. If sensors show "unavailable", you may need a converter or alternative integration method.

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
1. Modbus TCP is not enabled/supported on the logger
2. Logger requires a Modbus RTU-to-TCP converter (if it only has RS485)
3. The IP address is incorrect
4. Firewall is blocking port 502
5. The Modbus register addresses are wrong for your specific model

**Solutions:**
- Ping the IP address to verify connectivity: `ping 192.168.178.78`
- Try accessing the web interface: `http://192.168.178.78`
- Use a Modbus testing tool (like `mbpoll`) to test the connection
- Check the Solarman app to see if data is being logged
- If logger only supports RS485: Add a Modbus RTU-to-TCP converter or use HACS integration
- Consult the Deye/Solis Modbus protocol documentation for your inverter model

### Incorrect Values
If sensors show values but they seem incorrect:
- Check the `scale` parameter in `modbus.yaml` (multiplier for the raw value)
- Verify the `data_type` (uint16, int16, float32, etc.)
- Try different register addresses

### Alternative Integration Methods
If Modbus TCP doesn't work or you need a hardware converter, consider these alternatives:

#### 1. HACS "Solarman" Integration (Recommended if no Modbus TCP)
**Advantages:** No hardware converter needed, works via cloud API
**Setup:**
1. Install HACS if not already installed
2. Add custom repository: `https://github.com/StephanJoubert/home_assistant_solarman`
3. Install "Solarman" integration
4. Configure with your logger serial: `3966925526`
5. Remove/comment out the Modbus configuration in `modbus.yaml`

#### 2. Modbus RTU-to-TCP Converter
**Use if:** Logger only has RS485 port
**Hardware:** Waveshare RS485-to-Ethernet, USR-TCP232-410S, or similar
**Setup:**
1. Connect converter to inverter's RS485 port
2. Configure converter's IP address (e.g., 192.168.178.79)
3. Update `modbus.yaml` to point to converter's IP
4. Keep current register configuration

#### 3. REST API
**Use if:** Logger exposes REST API (some models on port 8899)
**Note:** Less common, requires custom REST sensors in `configuration.yaml`

#### 4. MQTT
**Use if:** Logger supports MQTT publishing
**Note:** Requires MQTT broker and logger configuration

## Additional Resources
- [Deye Inverter Modbus Protocol](https://github.com/home-assistant/core/issues/xxxx)
- [Solarman Integration for HACS](https://github.com/StephanJoubert/home_assistant_solarman)
- [Home Assistant Modbus Documentation](https://www.home-assistant.io/integrations/modbus/)

## Contact
If you have issues or need to adjust the configuration, the register addresses in `modbus.yaml` can be modified without affecting other parts of the system.
