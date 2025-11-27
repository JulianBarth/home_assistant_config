# Energy Flow Visualization - Quick Start Guide

## 🚀 Quick Setup (5 minutes)

Follow these steps to get your energy flow visualization up and running.

## Step 1: Install Sankey Chart via HACS (2 minutes)

1. Open Home Assistant
2. Go to **HACS** → **Frontend**
3. Click **"+ EXPLORE & DOWNLOAD REPOSITORIES"**
4. Search for **"Sankey Chart"**
5. Click **Download** and install latest version
6. **Clear browser cache** (Ctrl+Shift+R)

> **Detailed instructions**: See [SANKEY_INSTALLATION.md](SANKEY_INSTALLATION.md)

## Step 2: Verify Configuration (1 minute)

Run the verification script:
```bash
cd /config
python3 verify_energy_flow_setup.py
```

All checks should pass ✓

## Step 3: Restart Home Assistant (1 minute)

1. Go to **Settings** → **System** → **Restart**
2. Wait for restart to complete (~30 seconds)

## Step 4: View Your Energy Flow (1 minute)

1. Navigate to **Battery Management** dashboard
2. Click on **Energy Flow** tab
3. You should see:
   - 🎨 Interactive Sankey chart
   - 📊 Real-time power gauges
   - 🔄 Detailed flow tracking
   - 📈 Historical graphs

## 🎯 What You'll See

### Main Visualization
```
☀️ Solar → 🏠 House
☀️ Solar → 🔋 Battery
☀️ Solar → 🔌 Grid (export)
🔋 Battery → 🏠 House
🔌 Grid → 🏠 House (import)
🔌 Grid → 🔋 Battery (charging)
```

### Color Coding
- 🟡 **Yellow/Amber**: Solar production
- 🟢 **Green**: Battery
- 🔵 **Blue**: Grid connection
- 🔴 **Red**: House consumption
- 🟣 **Purple**: Wallbox/EV charging

## 📱 Using the Dashboard

### Overview Card
Shows current status of all components:
- Total solar production
- Battery state and level
- Grid import/export
- House consumption
- Wallbox power

### Gauges
Visual indicators for:
- Solar Power (0-7000W)
- Battery Level (0-100%)
- Grid Power (-5000W to +5000W)
- House Consumption (0-10000W)

### Flow Details
Individual flow sensors tracking:
- Where your solar energy goes
- Battery charging/discharging
- Grid interaction
- House and EV consumption

### History Graph
2-hour timeline showing:
- Energy flow trends
- Peak usage times
- Solar production patterns
- Battery charging cycles

## 🔧 Troubleshooting

### Sankey Chart Not Showing
```bash
# Clear browser cache completely
Ctrl + Shift + Delete (Chrome/Edge)
Cmd + Shift + Delete (Safari)

# Then refresh
Ctrl + Shift + R
```

### No Data in Chart
1. Check if sensors are working:
   - Go to **Developer Tools** → **States**
   - Search for `sensor.grid_power`
   - Should show a number (not "unavailable")

2. Verify devices are online:
   - Fronius inverter (192.168.178.92)
   - Deye Balkonkraftwerk (192.168.178.78)

### Card Shows Error
1. Verify HACS installation:
   - HACS → Frontend
   - "Sankey Chart" should be listed

2. Check browser console:
   - Press F12
   - Look for errors

## 📖 Learn More

- **[ENERGY_FLOW_SETUP.md](ENERGY_FLOW_SETUP.md)** - Complete setup documentation
- **[ENERGY_FLOW_EXAMPLES.md](ENERGY_FLOW_EXAMPLES.md)** - Usage examples and scenarios
- **[SANKEY_INSTALLATION.md](SANKEY_INSTALLATION.md)** - Detailed installation guide

## 💡 Quick Tips

### Maximize Solar Usage
Monitor **Solar → House** flow:
- High value = Good direct consumption
- Low value = Consider shifting loads

### Track Grid Independence
Watch **Grid Power**:
- Negative = Exporting (earning money)
- Zero = Self-sufficient (optimal)
- Positive = Importing (costing money)

### Optimize EV Charging
Best to worst:
1. ☀️ Solar → Wallbox (free, clean)
2. 🔌 Grid → Wallbox @ low prices (cheap)
3. 🔋 Battery → Wallbox (avoid, wastes storage)

### Battery Strategy
- Charge from excess solar
- Charge from grid at low prices
- Discharge during peak prices
- Keep 20%+ for emergencies

## 🎨 Customization

### Change Colors
Edit `ui-lovelace.yaml`:
```yaml
- entity_id: sensor.fronius_solar_power
  color: '#YOUR_COLOR'  # Change here
```

### Adjust Gauge Ranges
Match your system capacity:
```yaml
- type: gauge
  max: 7000  # Your solar capacity
```

### Add Custom Flows
Create new sensor in `templates.yaml`:
```yaml
- sensor:
    - name: "My Flow"
      state: >
        {{ calculation }}
```

## ✅ Success Checklist

After setup, you should have:
- [x] Sankey Chart installed via HACS
- [x] Energy Flow view visible in dashboard
- [x] Real-time power data showing
- [x] Gauges displaying correctly
- [x] History graphs working
- [x] All sensors have valid data

## 🆘 Need Help?

1. **Check logs**: Settings → System → Logs
2. **Verify sensors**: Developer Tools → States
3. **Review docs**: See documentation files
4. **Test devices**: Ping inverter IPs

## 🚀 Next Steps

Once working:
1. Monitor your energy flows
2. Optimize solar self-consumption
3. Fine-tune battery charging strategy
4. Track cost savings
5. Share your setup!

## 📊 Performance Targets

Aim for:
- **Solar Self-Consumption**: >70%
- **Grid Independence**: >60%
- **Battery Utilization**: 1-2 cycles/day
- **Solar Export**: <30% of production

---

**Ready in 5 minutes! 🎉**

Questions? Check the documentation files or Home Assistant community forums.

**License**: BSD-3-Clause | **Author**: Julian Bartholomeyczik
