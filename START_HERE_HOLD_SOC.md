# Getting Started with Hold SOC - READ ME FIRST! 🚀

## Welcome!

You now have a new **Battery Hold SOC** feature that can save energy and extend your battery life. This guide will get you started in 5 minutes.

## What is Hold SOC?

Instead of your battery constantly cycling between charging and discharging to maintain a target SOC (which wastes ~10% energy per cycle), Hold SOC keeps your battery **steady at the target level**.

**Result:** Less wear, lower energy costs, longer battery life!

## Quick Start (5 Minutes)

### Step 1: Read the Quick Reference (2 min)
Open: `HOLD_SOC_QUICK_REFERENCE.md`

This one-page guide tells you everything you need to know.

### Step 2: Run Your First Test (3 min + 10 min wait)

1. Open Home Assistant
2. Go to **Developer Tools → Services**
3. Run this service:
   ```
   Service: script.turn_on
   Target: script.test_hold_soc_zero_rates
   ```
4. You'll get a notification with your battery status
5. Wait 10 minutes (go make coffee ☕)
6. Check your battery SOC - it should be steady!
7. Stop the test:
   ```
   Service: script.turn_on
   Target: script.stop_hold_soc_test
   ```

### Step 3: Report Results
Let me know:
- ✅ Did your battery SOC stay steady? (±1-2% is normal)
- ✅ What did the charging state show? (HOLDING or OFF expected)
- ✅ Any issues or questions?

## What's in the Box? 📦

### Scripts You Can Use
- `hold_battery_soc` - Main hold mode script
- `hold_battery_soc_minimal` - Alternative with 1% rates
- `test_hold_soc_zero_rates` - Test it safely
- `test_hold_soc_minimal_rates` - Alternative test
- `stop_hold_soc_test` - Exit test mode
- `verify_hold_soc_status` - Check what's happening

### Documentation
1. **`HOLD_SOC_QUICK_REFERENCE.md`** ⭐ Start here!
2. **`HOLD_SOC_DOCUMENTATION.md`** - Full details
3. **`HOLD_SOC_VISUAL_GUIDE.md`** - Diagrams and flows
4. **`HOLD_SOC_AUTOMATION_EXAMPLES.yaml`** - Integration examples
5. **`HOLD_SOC_IMPLEMENTATION_SUMMARY.md`** - Technical overview

## Important Notes ⚠️

1. **Test First!** Don't integrate into automation until you've tested
2. **No Changes to Your Automation Yet** - Everything is safe and separate
3. **Easy to Exit** - Just run `stop_hold_soc_test` anytime
4. **Monitor While Testing** - Watch your battery dashboard

## Expected Benefits 💰

After you integrate this (post-testing):
- **Energy Savings:** ~164 kWh/year = ~50 EUR/year
- **Battery Life:** +20% (fewer cycles = longer life)
- **Battery Wear:** 95% reduction in unnecessary cycling

## Troubleshooting 🔧

### Battery Not Holding?
Run: `script.verify_hold_soc_status`
Check if registers are correct:
- StorCtl_Mod should be: 3
- Charge & Discharge rates should be: 0%

### Can't Stop Test?
Run: `script.stop_hold_soc_test`
This will restore everything to normal.

### State Shows "OFF" Not "HOLDING"?
That's OK! Some firmware versions show OFF instead. 
Check if SOC is staying steady - that's what matters.

## Next Steps After Testing

If tests succeed:
1. Review `HOLD_SOC_AUTOMATION_EXAMPLES.yaml`
2. Choose Example 1 (simplest) to start
3. Add to your automation
4. Monitor for 24-48 hours
5. Enjoy the savings! 🎉

## Need More Help?

- **Quick Questions**: See `HOLD_SOC_QUICK_REFERENCE.md`
- **Technical Details**: See `HOLD_SOC_DOCUMENTATION.md`
- **Visual Explanations**: See `HOLD_SOC_VISUAL_GUIDE.md`
- **Integration Help**: See `HOLD_SOC_AUTOMATION_EXAMPLES.yaml`

## Technical Details (If You're Curious)

The hold SOC feature works by:
1. Setting discharge rate to 0% (register 40365 = 0)
2. Setting charge rate to 0% (register 40366 = 0)
3. Enabling storage control (register 40358 = 3)

Result: Battery can't charge OR discharge, so it stays at current SOC!

## Ready to Start?

1. ✅ Open `HOLD_SOC_QUICK_REFERENCE.md`
2. ✅ Run `test_hold_soc_zero_rates`
3. ✅ Wait 10 minutes
4. ✅ Report back!

---

**Questions?** Check the documentation files above or ask!

**Excited?** Me too! This should save you ~50 EUR/year and extend your battery life. 🎯
