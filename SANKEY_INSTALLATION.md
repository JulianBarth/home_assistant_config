# Sankey Chart Card Installation Guide

## Prerequisites

Before installing the Sankey Chart card, ensure you have:
1. Home Assistant installed and running
2. HACS (Home Assistant Community Store) installed
3. Access to Home Assistant as an administrator

## Step 1: Install HACS (if not already installed)

If you don't have HACS installed yet:

1. Visit https://hacs.xyz/docs/setup/download
2. Follow the installation instructions for your setup
3. Restart Home Assistant
4. Complete HACS configuration through the UI

## Step 2: Install Sankey Chart Card via HACS

### Method 1: Through HACS UI (Recommended)

1. **Open HACS**
   - Go to Home Assistant
   - Click on "HACS" in the sidebar
   - Or navigate to: http://your-ha-ip:8123/hacs/dashboard

2. **Navigate to Frontend**
   - Click on "Frontend" tab in HACS

3. **Search for Sankey Chart**
   - Click the "+ EXPLORE & DOWNLOAD REPOSITORIES" button
   - Search for "sankey chart" or "lovelace-sankey-chart"
   - Click on "Sankey Chart" by MindFreeze

4. **Install the Card**
   - Click "Download" button
   - Select the latest version
   - Click "Download" again to confirm

5. **Refresh Browser**
   - Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
   - Refresh the page

### Method 2: Manual Installation

If HACS is not available, you can install manually:

1. **Download the files**
   ```bash
   cd /config/www/
   mkdir -p community/lovelace-sankey-chart
   cd community/lovelace-sankey-chart
   wget https://github.com/MindFreeze/ha-sankey-chart/releases/latest/download/ha-sankey-chart.js
   ```

2. **Add resource in Home Assistant**
   - Go to Settings → Dashboards → Resources
   - Click "+ ADD RESOURCE"
   - URL: `/local/community/lovelace-sankey-chart/ha-sankey-chart.js`
   - Resource type: JavaScript Module
   - Click "CREATE"

## Step 3: Verify Installation

1. **Check Resources**
   - Configuration should already have the resource:
   ```yaml
   lovelace:
     mode: yaml
     resources:
       - url: /hacsfiles/lovelace-sankey-chart/ha-sankey-chart.js
         type: module
   ```

2. **Check HACS**
   - Go to HACS → Frontend
   - Verify "Sankey Chart" appears in your installed integrations

3. **Test the Card**
   - Navigate to the Energy Flow dashboard
   - You should see the Sankey chart visualization
   - If not visible, check browser console for errors (F12)

## Step 4: Configuration (Already Done)

The configuration has been added to your system:

- **Resource**: Added to `configuration.yaml`
- **Sensors**: Added to `templates.yaml`
- **Dashboard**: Added to `ui-lovelace.yaml`

## Troubleshooting

### Card Not Showing

**Problem**: Sankey chart card not displaying

**Solutions**:
1. Clear browser cache completely
   ```
   Chrome/Edge: Ctrl+Shift+Delete
   Firefox: Ctrl+Shift+Delete
   Safari: Cmd+Option+E
   ```

2. Restart Home Assistant
   - Go to Settings → System → Restart

3. Check browser console (F12)
   - Look for errors related to "sankey" or "custom:sankey-chart"

4. Verify file exists
   ```bash
   ls -la /config/www/community/lovelace-sankey-chart/
   ```

### "Custom element doesn't exist" Error

**Problem**: Error message "Custom element doesn't exist: sankey-chart"

**Solutions**:
1. Ensure HACS installation completed successfully
2. Verify resource is loaded:
   - Go to Developer Tools → States
   - Search for "lovelace"
   - Check resources list

3. Re-install the card:
   - HACS → Frontend
   - Click on Sankey Chart
   - Click "Redownload"

4. Hard refresh browser:
   - Ctrl+Shift+R (Windows/Linux)
   - Cmd+Shift+R (Mac)

### Card Shows but No Data

**Problem**: Sankey chart displays but shows no energy flows

**Solutions**:
1. Check sensor states:
   - Go to Developer Tools → States
   - Search for sensors:
     - `sensor.grid_power`
     - `sensor.battery_power`
     - `sensor.house_consumption`
     - `sensor.fronius_solar_power`
     - `sensor.balkonkraftwerk_power`

2. Verify sensors have valid values:
   - Should be numbers (W)
   - Should not be "unavailable" or "unknown"

3. Check Modbus connection:
   - Fronius inverter should be reachable
   - Check IP: 192.168.178.92

4. Check Deye inverter:
   - Balkonkraftwerk should be online
   - Check IP: 192.168.178.78

### YAML Configuration Errors

**Problem**: Home Assistant won't start or shows configuration errors

**Solutions**:
1. Validate YAML syntax:
   ```bash
   # Check configuration
   ha core check
   ```

2. Review Home Assistant logs:
   - Settings → System → Logs
   - Look for YAML parsing errors

3. Common issues:
   - Incorrect indentation (use 2 spaces)
   - Missing colons
   - Quotes in wrong places

4. Restore from backup if needed:
   - Settings → System → Backups

## Advanced Configuration

### Customizing the Chart

Edit `ui-lovelace.yaml` to customize:

```yaml
- type: custom:sankey-chart
  title: My Custom Energy Flow
  height: 800  # Increase height
  wide: true
  # ... rest of configuration
```

### Adding More Flows

Add additional flow sensors in `templates.yaml`:

```yaml
- sensor:
    - name: "My Custom Flow"
      unique_id: my_custom_flow
      unit_of_measurement: W
      device_class: power
      state_class: measurement
      state: >
        # Your calculation here
        {{ 0 }}
```

### Color Customization

Change colors in the Sankey chart configuration:

```yaml
entities:
  - entity_id: sensor.fronius_solar_power
    name: Fronius Solar
    color: '#YOUR_HEX_COLOR'  # Change this
```

## Alternative: Power Flow Card Plus

If Sankey Chart doesn't work, consider alternatives:

1. **Power Flow Card Plus**
   - HACS → Frontend
   - Search for "Power Flow Card Plus"
   - Simpler but less detailed

2. **Energy Flow Card**
   - HACS → Frontend
   - Search for "Energy Flow Card"
   - Another alternative visualization

## Updating the Card

To update to a newer version:

1. Go to HACS → Frontend
2. Click on "Sankey Chart"
3. Click "Update" if available
4. Clear browser cache
5. Restart Home Assistant

## Support Resources

### Official Documentation
- Sankey Chart: https://github.com/MindFreeze/ha-sankey-chart
- HACS: https://hacs.xyz/docs/basic/getting_started

### Home Assistant Community
- Forum: https://community.home-assistant.io/
- Discord: https://discord.gg/home-assistant

### Project Documentation
- [ENERGY_FLOW_SETUP.md](ENERGY_FLOW_SETUP.md) - Complete setup guide
- [ENERGY_FLOW_EXAMPLES.md](ENERGY_FLOW_EXAMPLES.md) - Usage examples
- [README.md](README.md) - Project overview

## Version Compatibility

- **Home Assistant**: 2023.1 or newer
- **HACS**: 1.30.0 or newer
- **Sankey Chart**: Latest version from HACS

Tested with:
- Home Assistant Core 2024.x
- HACS 1.34.0
- Sankey Chart 1.x

## Security Notes

- Sankey Chart is a frontend-only component
- No external connections required
- Data stays within your local network
- Review code if concerned: https://github.com/MindFreeze/ha-sankey-chart

## License

- Sankey Chart: MIT License
- This configuration: BSD-3-Clause (see LICENSE.txt)

---

**Last Updated**: 2024
**Author**: Julian Bartholomeyczik
