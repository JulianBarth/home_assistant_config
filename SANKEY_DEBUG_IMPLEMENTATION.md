# Sankey Debug Feature Summary

## Problem Statement
The entities for the Sankey graph had problems, resulting in no Sankey display at all. There was no easy way to debug what was wrong with the configuration or which entities were causing issues.

## Solution Implemented
A comprehensive debugging system with three layers:
1. **Backend Debug Sensors** - Monitor entity health
2. **UI Debug Panels** - Visual feedback on entity status
3. **Documentation** - Complete troubleshooting guides

---

## 🔧 Technical Implementation

### 1. Debug Sensors (templates.yaml)

#### sensor.sankey_entity_check
**Purpose:** Master health check for all Sankey entities

**State Values:**
- `OK` - All 10 entities are available and valid
- `ERROR` - One or more entities have issues

**Attributes:**
- `unavailable_entities` - List of entities with unavailable/unknown states
- `invalid_entities` - List of entities with non-numeric values
- `total_entities` - Always 10 (total entities monitored)
- `available_count` - Number of entities currently working

**Entities Monitored:**
1. sensor.total_solar_power
2. sensor.grid_power
3. sensor.battery_power
4. sensor.solar_to_house
5. sensor.solar_to_battery
6. sensor.solar_to_grid
7. sensor.grid_to_house
8. sensor.grid_to_battery
9. sensor.battery_to_house
10. sensor.house_consumption

#### sensor.sankey_debug_info
**Purpose:** Detailed diagnostic information

**Attributes:**
- `entity_states` - JSON object with all entity current states
- `diagnosis` - Human-readable description of issues
- `recommendations` - Specific steps to fix detected problems

---

## 📊 UI Components (ui-lovelace.yaml)

### Panel 1: Auto-Appearing Error Alert
**Type:** Conditional markdown card
**Visibility:** Only when `sensor.sankey_entity_check == ERROR`

**Displays:**
- ⚠️ Warning header
- Status (OK/ERROR)
- Count of available entities
- List of unavailable entities with states
- List of invalid value entities
- Specific recommendations based on which entities are affected

**Example Output:**
```
⚠️ Sankey Chart Debug Information

Status: ERROR
Available Entities: 8/10

🔴 Unavailable Entities:
- sensor.fronius_solar_power - State: unavailable
- sensor.battery_power - State: unknown

💡 Recommendations:
- Check Fronius Modbus connection (IP: 192.168.178.92)
- Check charging_state and energy sensors
```

### Panel 2: Status Overview
**Type:** Entities card
**Visibility:** Always visible

**Shows:**
- Entity Check Status (OK/ERROR) with icon
- Available Entities count (X/10)
- Diagnosis message
- Quick status section with 4 main entities:
  - Total Solar Power
  - Grid Power
  - Battery Power
  - House Consumption

**Purpose:** Quick at-a-glance health check

### Panel 3: Detailed Entity Values
**Type:** Entities card
**Visibility:** Always visible

**Shows all entities organized by category:**
- **Primary Sources**
  - Total Solar Power
  - Fronius Solar Power
  - Balkonkraftwerk Power
  - Grid Power
  - Battery Power

- **Flow Sensors (Solar)**
  - Solar → House
  - Solar → Battery
  - Solar → Grid

- **Flow Sensors (Grid)**
  - Grid → House
  - Grid → Battery

- **Flow Sensors (Battery)**
  - Battery → House

- **Final Consumption**
  - House Consumption
  - Wallbox Power

- **Supporting Sensors**
  - Battery Charging State
  - Main Meter Reading
  - Inverter AC Output

Each entity shows:
- Current value
- Last changed timestamp
- State color indication

---

## 📚 Documentation Updates

### SANKEY_INSTALLATION.md
**Added Section:** "Debugging Features"

**Content:**
- Overview of all three debug panels
- Step-by-step guide for using debug tools
- Debug sensor attribute documentation
- Quick troubleshooting flowchart
- Common issue patterns and solutions

### SANKEY_DEBUG_GUIDE.md (NEW)
**Complete debugging reference guide**

**Sections:**
1. Quick Reference - Status indicators table
2. Debug Panels Overview - Detailed explanation
3. Common Issues and Solutions - Step-by-step fixes
4. Using Developer Tools - Advanced debugging
5. Entity Dependencies - Dependency tree diagram
6. Automation for Alerts - Example notification setup
7. Maintenance Checklist - Daily/Weekly/Monthly checks
8. Advanced Usage - Integration with automations

### README.md
**Updated:** Energy Flow section

**Added:**
- Mention of built-in debugging tools
- Link to new SANKEY_DEBUG_GUIDE.md
- Highlight of debugging as a key feature

---

## 🎯 User Benefits

### Immediate Problem Diagnosis
**Before:** Chart doesn't display - no idea why
**After:** Clear indication of which entities are broken

### Self-Service Troubleshooting
**Before:** Need to check Home Assistant logs, Developer Tools, manually inspect each sensor
**After:** Dedicated debug panel shows exactly what's wrong with actionable recommendations

### Preventive Monitoring
**Before:** Only notice issues when chart stops working
**After:** Can monitor entity health proactively, see warnings before complete failure

### Quick Recovery
**Before:** Trial and error to fix issues
**After:** Specific recommendations point to exact fix needed (restart Modbus, check IP address, etc.)

---

## 🔍 How It Works

### Detection Logic
```
For each of 10 Sankey entities:
  1. Check if state is 'unavailable', 'unknown', 'none', or None
     → If yes: Add to unavailable_entities list
  
  2. If available, check if value matches numeric pattern (including negative)
     → If no: Add to invalid_entities list

If unavailable_entities OR invalid_entities have items:
  → Set status to ERROR
Else:
  → Set status to OK
```

### Smart Recommendations
Based on which entities are unavailable:
- Fronius sensors → Check Modbus, IP 192.168.178.92
- Balkonkraftwerk → Check Deye inverter, IP 192.168.178.78
- Grid power → Check main meter sensor
- Battery power → Check charging state and energy sensors
- Flow sensors → Fix primary sources first

### Visual Feedback
- Status panel always visible for quick check
- Error panel auto-appears when needed
- Color coding for entity states
- Last-changed timestamps to spot stale data

---

## 📈 Testing Scenarios

### Scenario 1: All Working
- Status: ✅ OK
- Available: 10/10
- Error panel: Hidden
- Sankey chart: Displays correctly

### Scenario 2: Fronius Offline
- Status: ❌ ERROR
- Available: 8/10 (fronius_solar_power, total_solar_power unavailable)
- Error panel: Visible with Modbus recommendation
- Sankey chart: May show partial data or not display

### Scenario 3: At Night (Valid)
- Status: ✅ OK
- Available: 10/10
- Values: Solar = 0 (valid numeric value)
- Sankey chart: Shows flows from grid/battery only

### Scenario 4: Template Calculation Issue
- Status: ❌ ERROR
- Available: 9/10
- Invalid: 1 entity has non-numeric value
- Error panel: Shows which entity has invalid value

---

## 🚀 Future Enhancements (Not Implemented)

Possible additions for future versions:
- Historical entity availability tracking
- Notification automation templates
- Integration with Home Assistant alerts
- Performance metrics (response time of entities)
- Trend analysis (entities frequently unavailable)
- Auto-remediation actions (restart integrations)

---

## ✅ Validation

### YAML Syntax
- ✅ templates.yaml validated
- ✅ ui-lovelace.yaml validated
- ✅ No syntax errors

### Code Quality
- ✅ Follows Home Assistant template best practices
- ✅ Uses default values in calculations
- ✅ Handles None/null cases
- ✅ Regex pattern for numeric validation

### Documentation
- ✅ Complete user guide (SANKEY_DEBUG_GUIDE.md)
- ✅ Installation docs updated (SANKEY_INSTALLATION.md)
- ✅ README updated with feature
- ✅ Examples and screenshots described

---

## 📋 Files Changed

1. **templates.yaml** (+149 lines)
   - Added sensor.sankey_entity_check
   - Added sensor.sankey_debug_info

2. **ui-lovelace.yaml** (+136 lines)
   - Added conditional error panel
   - Added status overview panel
   - Added detailed entity values panel

3. **SANKEY_INSTALLATION.md** (+96 lines)
   - Added "Debugging Features" section
   - Updated troubleshooting section

4. **SANKEY_DEBUG_GUIDE.md** (NEW, 7547 chars)
   - Complete debugging reference

5. **README.md** (+6 lines)
   - Updated Energy Flow section
   - Added debug guide reference

**Total Changes:** 3 files modified, 1 file created, 381+ lines added

---

## 🎓 Key Learnings

### What Makes Good Debug Tools
1. **Proactive, not reactive** - Show issues before they become critical
2. **Actionable information** - Don't just say "error", say how to fix it
3. **Progressive disclosure** - Simple status always visible, details on demand
4. **Context-aware** - Recommendations based on specific failure patterns
5. **Self-documenting** - UI should guide users without external docs

### Home Assistant Best Practices Applied
1. Template sensors for reusable logic
2. Attributes for rich data without extra entities
3. Conditional cards for clean UI
4. Markdown for formatted debug output
5. Entity organization in logical sections

---

**Implementation Date:** 2024
**Status:** ✅ Complete and Ready for Use
**Tested:** YAML validation passed
**Author:** AI Agent with guidance from problem statement
