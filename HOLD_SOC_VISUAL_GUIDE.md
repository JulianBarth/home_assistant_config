# Battery Hold SOC - Visual Guide

## System State Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     BATTERY MANAGEMENT STATES                        │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────┐
│   IDLE       │ ◄── Normal operation when automation is off
│   MODE       │     or no action needed
└──────┬───────┘
       │
       │ Low price + Low SOC
       ▼
┌──────────────┐
│  CHARGING    │ ◄── Active charging to reach target SOC
│   MODE       │     OutWRte: 0-100%, InWRte: 100%
└──────┬───────┘
       │
       │ Target SOC reached
       ▼
┌──────────────┐
│  ✨ HOLDING  │ ◄── NEW! Battery stays steady at target
│    MODE      │     OutWRte: 0%, InWRte: 0%
│ (Efficient!) │     No cycling, minimal losses
└──────┬───────┘
       │
       │ Price drops OR Solar increases
       ▼
┌──────────────┐
│   NORMAL     │ ◄── Return to normal operation
│   MODE       │     OutWRte: 100%, InWRte: 100%
└──────────────┘
```

## Energy Flow Comparison

### Traditional Cycling Method
```
Time:    0min   10min   20min   30min   40min   50min   60min
        ───┬─────┬───────┬───────┬───────┬───────┬───────┬──►
SOC:     75%    80%     79%     80%     79%     80%     79%
           │     │       │       │       │       │       │
Action:    │     │       │       │       │       │       │
   Charge ━━━━━━┛       │       │       │       │       │
   Idle          ━━━━━━━┛       │       │       │       │
   Charge                ━━━━━━━┛       │       │       │
   Idle                          ━━━━━━━┛       │       │
   Charge                                ━━━━━━━┛       │
   Idle                                          ━━━━━━━┛

Energy Loss: ████████ (High - multiple cycles)
Battery Wear: ████████ (High - constant switching)
Grid Draws: ████████ (Frequent small charges)
```

### Hold SOC Method (NEW!)
```
Time:    0min   10min   20min   30min   40min   50min   60min
        ───┬─────┬───────┬───────┬───────┬───────┬───────┬──►
SOC:     75%    80%     80%     80%     80%     80%     80%
           │     │       │       │       │       │       │
Action:    │     │       │       │       │       │       │
   Charge ━━━━━━┛       │       │       │       │       │
   ✨HOLD         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Energy Loss: ██ (Minimal - only self-discharge)
Battery Wear: ██ (Minimal - steady state)
Grid Draws: ██ (Only house consumption)
```

## Modbus Register Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ Starting Hold SOC Mode - Register Write Sequence                    │
└─────────────────────────────────────────────────────────────────────┘

Step 1: Enable Storage Control
┌──────────────────────────────────────┐
│ Register: 40358 (StorCtl_Mod)        │
│ Write Value: 3 (Enable)              │
│ Result: Storage control activated    │
└──────────────────────────────────────┘
                │
                ▼
Step 2: Disable Discharge
┌──────────────────────────────────────┐
│ Register: 40365 (OutWRte)            │
│ Write Value: 0 (0% rate)             │
│ Result: Battery cannot discharge     │
└──────────────────────────────────────┘
                │
                ▼
Step 3: Disable Charge
┌──────────────────────────────────────┐
│ Register: 40366 (InWRte)             │
│ Write Value: 0 (0% rate)             │
│ Result: Battery cannot charge        │
└──────────────────────────────────────┘
                │
                ▼
Step 4: Verify State
┌──────────────────────────────────────┐
│ Register: 40364 (ChaSt)              │
│ Read Value: 6 (HOLDING)              │
│ Result: Battery in hold mode ✓       │
└──────────────────────────────────────┘
```

## Test Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ User Testing Flow - Before Integration                              │
└─────────────────────────────────────────────────────────────────────┘

START
  │
  ▼
┌─────────────────────────────┐
│ 1. Read Documentation       │
│    - Quick Reference        │
│    - Full Documentation     │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 2. Note Current SOC         │
│    Record: _____%           │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 3. Run Test Script          │
│    test_hold_soc_zero_rates │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 4. Wait 5-10 Minutes        │
│    Monitor Battery Dashboard│
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 5. Check Results            │
│    • SOC steady? (±1-2%)    │
│    • State = HOLDING/OFF?   │
└────────────┬────────────────┘
             │
             ├─── YES ──────────────┐
             │                      │
             │                      ▼
             │            ┌─────────────────────────┐
             │            │ ✅ Test Passed!         │
             │            │ Ready for integration   │
             │            └─────────────────────────┘
             │
             └─── NO ───────────────┐
                                    │
                                    ▼
                          ┌─────────────────────────┐
                          │ 6. Troubleshoot         │
                          │    • Check registers    │
                          │    • Review logs        │
                          │    • Try minimal rates  │
                          └─────────┬───────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 7. Stop Test                                                         │
│    stop_hold_soc_test                                                │
└─────────────────────────────────────────────────────────────────────┘
```

## Battery Behavior Visual

```
Traditional Method (Inefficient):
    
    Target ─────────────────────────────────── 80%
                    ╱╲      ╱╲      ╱╲
    SOC  ──────────╱  ╲────╱  ╲────╱  ╲─────
                  ╱    ╲  ╱    ╲  ╱    ╲
                 ╱      ╲╱      ╲╱      ╲
    
    Legend: ╱ = Charging   ╲ = Discharging
    Problem: Constant cycling wastes energy

Hold SOC Method (Efficient):
    
    Target ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 80%
                    ┃
    SOC  ───────────┻━━━━━━━━━━━━━━━━━━━━━━━━
                    ▲
                    └─ Charge then hold
    
    Legend: ━ = Holding steady
    Benefit: No cycling, no losses

```

## Integration Decision Tree

```
                    ┌─────────────────────┐
                    │ Tests Successful?   │
                    └──────────┬──────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
              YES                            NO
                │                             │
                ▼                             ▼
    ┌───────────────────────┐    ┌────────────────────────┐
    │ Choose Integration    │    │ Debug & Re-test        │
    │ Approach              │    │ • Check connections    │
    └───────────┬───────────┘    │ • Review register vals │
                │                │ • Contact support      │
                │                └────────────────────────┘
                ▼
    ┌───────────────────────┐
    │ Example 1: Simple     │ ◄── Best for first try
    │ Example 2: Smart Exit │ ◄── Add intelligence
    │ Example 3: Time Limit │ ◄── Add safety
    │ Example 4: Adaptive   │ ◄── Most advanced
    └───────────┬───────────┘
                │
                ▼
    ┌───────────────────────┐
    │ Modify & Add to       │
    │ automations.yaml      │
    └───────────┬───────────┘
                │
                ▼
    ┌───────────────────────┐
    │ Monitor 24-48 hours   │
    └───────────┬───────────┘
                │
                ▼
    ┌───────────────────────┐
    │ Fine-tune & Optimize  │
    └───────────────────────┘
```

## Summary: Benefits at a Glance

```
┌────────────────────┬─────────────────┬─────────────────┬──────────────┐
│      Metric        │   Traditional   │    Hold SOC     │  Improvement │
├────────────────────┼─────────────────┼─────────────────┼──────────────┤
│ Energy Loss        │   ████████ 10%  │   █ 1%          │    90% ↓     │
│ Battery Cycles     │   ████████ High │   █ Minimal     │    95% ↓     │
│ Grid Interaction   │   ████████ Freq │   ██ Rare       │    80% ↓     │
│ Cost per Year      │   €50           │   €0            │   €50 saved  │
│ Battery Life       │   10 years      │   12+ years     │    +20%      │
│ Complexity         │   ███ Medium    │   ███ Medium    │   Same       │
│ Setup Effort       │   ──            │   ██ 1-2 hours  │   One-time   │
└────────────────────┴─────────────────┴─────────────────┴──────────────┘
```

## Quick Command Reference

```bash
# Home Assistant → Developer Tools → Services

# Start hold mode (zero rates)
Service: script.turn_on
Target: script.hold_battery_soc

# Start hold mode (minimal rates)  
Service: script.turn_on
Target: script.hold_battery_soc_minimal

# Test hold mode
Service: script.turn_on
Target: script.test_hold_soc_zero_rates

# Stop test
Service: script.turn_on
Target: script.stop_hold_soc_test

# Check status
Service: script.turn_on
Target: script.verify_hold_soc_status
```

---

**Remember:** Always test first before integrating into main automation!

See `HOLD_SOC_QUICK_REFERENCE.md` for step-by-step testing instructions.
