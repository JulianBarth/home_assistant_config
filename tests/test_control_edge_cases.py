"""Behavioral checks of production YAML at control and telemetry boundaries.

Regression coverage for the corrected defects documented in BUG_REVIEW.md.
No test connects to Home Assistant or writes physical inverter registers.
"""
import unittest

from test_battery_control import Rig, SCRIPTS, COORDINATOR, AUTOMATIONS
from test_operational_fixes import SENSORS, TemplateRig


class GridBatteryTelemetryIndependenceTests(unittest.TestCase):
    def test_soc_loss_does_not_revoke_manual_wallbox_permission(self):
        rig = TemplateRig()
        rig.states.update({'sensor.grid_frequency': '50',
                           'sensor.reading_energy_main_meter': '11000',
                           'sensor.reading_energy_battery_soc_scaled': 'unavailable',
                           'binary_sensor.inverter_data_valid': 'off',
                           'select.wattpilot_charging_mode': 'Default'})
        status = rig.render(SENSORS['Grid Connection Status']['state'])
        self.assertEqual(status, 'grid')
        rig.states['sensor.grid_connection_status'] = status
        watchdog = next(a for a in AUTOMATIONS
                        if a['alias'] == 'Grid Outage Wallbox Watchdog')
        self.assertFalse(rig.condition(watchdog['condition']))
        # Battery controls still independently release on missing raw SoC.
        rig.coordinate()
        self.assertEqual(rig.states('switch.storctl_mod'), 'off')
        self.assertEqual(rig.registers, {40365: 10000, 40366: 10000})

    def test_inverter_validity_rejects_nonfinite_and_out_of_range_soc(self):
        rig = Rig()
        for raw in ['nan', 'inf', '-inf', '10001', '65535', '0', '-1',
                    'unknown', 'unavailable', 'bad']:
            with self.subTest(raw=raw):
                rig.states['sensor.reading_energy_battery_soc_scaled'] = raw
                self.assertFalse(rig.truth(rig.render(SENSORS['Inverter Data Valid']['state'])))

    def test_inverter_validity_accepts_physical_soc_range(self):
        rig = Rig()
        for raw in ['1', '610', '5000', '10000']:
            with self.subTest(raw=raw):
                rig.states['sensor.reading_energy_battery_soc_scaled'] = raw
                self.assertTrue(rig.truth(rig.render(SENSORS['Inverter Data Valid']['state'])))


class CarBatteryChargingPermissionTests(unittest.TestCase):
    def rig(self, *, soc='5000', price='0.10', average='20'):
        rig = TemplateRig()
        rig.states.update({'sensor.reading_energy_battery_soc_scaled': soc,
                           'input_boolean.battery_charging_active': 'off',
                           'sensor.reading_energy_main_meter': '11500',
                           'sensor.reading_energy_inverter_ac_output': '0',
                           'sensor.wattpilot_charging_power': '11000',
                           'sensor.house_consumption': '500',
                           'input_number.battery_charge_rate_max': '5000',
                           'input_number.grid_connection_capacity': '20000',
                           'sensor.tibber_cached_energy_prices': price,
                           'sensor.tibber_energy_average_price_next_12_hours': average})
        return rig

    def allowed(self, rig):
        return rig.truth(rig.render(SENSORS['Should Charge Battery During Car Charging']['state']))

    def test_cheap_positive_price_is_compared_in_matching_currency_units(self):
        self.assertTrue(self.allowed(self.rig(price='0.10', average='20')))

    def test_expensive_price_and_capacity_limit_still_block_optimization(self):
        self.assertFalse(self.allowed(self.rig(price='0.30', average='20')))
        rig = self.rig()
        rig.states['sensor.house_consumption'] = '2500'  # 18.5 kW exceeds 90%.
        self.assertFalse(self.allowed(rig))

    def test_breached_reserve_can_recover_while_car_charges_despite_price(self):
        rig = self.rig(soc='900', price='0.40', average='20')
        self.assertTrue(self.allowed(rig))
        rig.states.update({'binary_sensor.car_charging_stable': 'on',
                           'select.wattpilot_charging_mode': 'Default',
                           'binary_sensor.should_start_charging': 'on',
                           'binary_sensor.should_charge_battery_during_car_charging': 'on',
                           'input_boolean.battery_charging_active': 'off'})
        self.assertEqual(rig.render(SENSORS['Battery Control Mode']['state']),
                         'car_and_battery_charging')

    def test_reserve_recovery_without_prices_still_respects_capacity(self):
        rig = self.rig(soc='900', price='unavailable', average='unavailable')
        rig.states['binary_sensor.tibber_cached_price_data_valid'] = 'off'
        self.assertTrue(self.allowed(rig))
        rig.states['sensor.house_consumption'] = '2500'
        self.assertFalse(self.allowed(rig))
        self.assertFalse(self.allowed(self.rig(soc='1000', price='0.40')))

    def test_reserve_recovery_continues_to_reserve_after_crossing_start_threshold(self):
        rig = self.rig(soc='1100', price='0.40')
        rig.states['input_boolean.battery_charging_active'] = 'on'
        self.assertTrue(self.allowed(rig))
        rig.states['sensor.reading_energy_battery_soc_scaled'] = '1500'
        self.assertFalse(self.allowed(rig))

    def test_reserve_recovery_car_mode_reaches_target_then_keeps_car_protection(self):
        rig = self.rig(soc='900', price='0.40')
        rig.states.update({'binary_sensor.car_charging_stable': 'on',
                           'sensor.wattpilot_carconnected': 'charging',
                           'select.wattpilot_charging_mode': 'Default',
                           'input_boolean.battery_no_discharging_active': 'on',
                           'sensor.computed_target_soc': '15',
                           'input_number.battery_target_soc': '15'})
        for raw in ['900', '1100', '1400', '1500']:
            with self.subTest(raw=raw):
                rig.states['sensor.reading_energy_battery_soc_scaled'] = raw
                rig.states['binary_sensor.should_charge_battery_during_car_charging'] = (
                    'on' if self.allowed(rig) else 'off')
                rig.states['binary_sensor.should_start_charging'] = (
                    'on' if rig.truth(rig.render(SENSORS['Should Start Charging']['state'])) else 'off')
                rig.coordinate()
                if int(raw) < 1500:
                    self.assertLess(rig.registers[40365], 0)
                    self.assertEqual(rig.states('input_boolean.battery_charging_active'), 'on')
                else:
                    self.assertGreaterEqual(rig.registers[40365], 0)
                    self.assertEqual(rig.states('input_boolean.battery_charging_active'), 'off')
                self.assertEqual(rig.states('select.wattpilot_charging_mode'), 'Default')
                self.assertEqual(rig.states('input_boolean.battery_no_discharging_active'), 'on')

    def test_stale_numeric_house_estimate_cannot_hide_upstream_power_loss(self):
        for entity in ['sensor.reading_energy_main_meter',
                       'sensor.reading_energy_inverter_ac_output']:
            with self.subTest(entity=entity):
                rig = self.rig(soc='900')
                rig.states[entity] = 'unavailable'
                self.assertFalse(self.allowed(rig))

    def test_signed_grid_and_inverter_power_are_valid_capacity_inputs(self):
        rig = self.rig()
        rig.states.update({'sensor.reading_energy_main_meter': '-2000',
                           'sensor.reading_energy_inverter_ac_output': '-500'})
        self.assertTrue(self.allowed(rig))

    def test_unknown_or_invalid_load_never_invents_capacity_headroom(self):
        for entity in ['sensor.wattpilot_charging_power', 'sensor.house_consumption',
                       'input_number.battery_charge_rate_max',
                       'input_number.grid_connection_capacity']:
            for raw in ['unavailable', 'unknown', 'nan', 'inf', '-1']:
                with self.subTest(entity=entity, raw=raw):
                    rig = self.rig(soc='900', price='-0.10')
                    rig.states[entity] = raw
                    self.assertFalse(self.allowed(rig))

    def test_invalid_prices_do_not_authorize_nonemergency_battery_charging(self):
        rig = self.rig(price='-0.10')
        rig.states['binary_sensor.tibber_cached_price_data_valid'] = 'off'
        self.assertFalse(self.allowed(rig))
        for price, average in [('0.10', 'inf'), ('-inf', '20'), ('nan', '20')]:
            with self.subTest(price=price, average=average):
                self.assertFalse(self.allowed(self.rig(price=price, average=average)))


class DelayedBatteryPermissionTests(unittest.TestCase):
    def test_queued_charge_cannot_restart_after_master_off(self):
        rig = Rig(active=False)
        rig.states['input_boolean.battery_automation_on'] = 'off'
        rig.run(SCRIPTS['charge_battery_to_target']['sequence'])
        self.assertEqual(rig.calls, [])

    def test_manual_charge_remains_allowed_when_automatic_control_is_off(self):
        rig = Rig(active=False, manual=True)
        rig.states['input_boolean.battery_automation_on'] = 'off'
        rig.run(SCRIPTS['charge_battery_to_target']['sequence'])
        self.assertEqual(rig.states('input_boolean.battery_charging_active'), 'on')

    def test_queued_hold_cannot_undo_safety_or_master_cleanup(self):
        for changes in [{'binary_sensor.grid_control_ready': 'off'},
                        {'input_boolean.battery_automation_on': 'off'},
                        {'binary_sensor.inverter_data_valid': 'off'},
                        {'sensor.reading_energy_battery_soc_scaled': 'unavailable'},
                        {'sensor.reading_energy_battery_soc_scaled': 'inf'}]:
            with self.subTest(changes=changes):
                rig = Rig(active=False)
                rig.states.update(changes)
                rig.coordinate()
                self.assertEqual(rig.states('switch.storctl_mod'), 'off')
                rig.calls.clear()
                rig.run(SCRIPTS['hold_battery_soc']['sequence'])
                self.assertEqual(rig.calls, [])
                self.assertEqual(rig.registers, {40365: 10000, 40366: 10000})

    def test_valid_reserve_hold_still_runs(self):
        rig = Rig(active=False)
        rig.run(SCRIPTS['hold_battery_soc']['sequence'])
        self.assertEqual(rig.registers, {40365: 100, 40366: 10000})
        self.assertEqual(rig.states('switch.storctl_mod'), 'on')


class ControlTransitionTests(unittest.TestCase):
    def test_disable_automation_releases_forced_charge_without_car(self):
        rig = Rig(active=True)
        rig.states['input_boolean.battery_automation_on'] = 'off'
        rig.coordinate()
        self.assertEqual(rig.registers, {40365: 10000, 40366: 10000})
        self.assertEqual(rig.states('switch.storctl_mod'), 'off')
        self.assertEqual(rig.states('input_boolean.battery_charging_active'), 'off')

    def test_disable_automation_releases_forced_charge_while_car_charges(self):
        rig = Rig(active=True, car=True)
        rig.states['input_boolean.battery_automation_on'] = 'off'
        rig.coordinate()
        self.assertEqual(rig.states('input_boolean.battery_charging_active'), 'off')
        self.assertGreaterEqual(rig.registers[40365], 0,
                                'The inverter must no longer request forced charging')
        self.assertEqual(rig.states('switch.storctl_mod'), 'off')
        self.assertEqual(rig.states('input_boolean.battery_no_discharging_active'), 'off')

    def test_car_only_transition_removes_forced_charge_floor(self):
        rig = Rig(active=True, car=True)
        rig.states['binary_sensor.should_charge_battery_during_car_charging'] = 'off'
        rig.coordinate()
        self.assertEqual(rig.registers, {40365: 1000, 40366: 10000})
        self.assertEqual(rig.states('input_boolean.battery_charging_active'), 'off')
        self.assertEqual(rig.states('input_boolean.battery_no_discharging_active'), 'on')

    def test_taper_returns_to_full_power_if_user_raises_target(self):
        rig = Rig(manual=True, soc=78, target=80)
        rig.coordinate()
        self.assertEqual(rig.registers, {40365: -5000, 40366: 5000})
        rig.states['input_number.manual_charge_target_soc'] = '100'
        rig.coordinate()
        self.assertEqual(rig.registers, {40365: -8000, 40366: 10000})
        self.assertEqual(rig.states('input_number.battery_target_soc'), '100.0')

    def test_lowered_manual_target_releases_existing_forced_charge(self):
        rig = Rig(manual=True, soc=50, target=80)
        rig.coordinate()
        rig.states['input_number.manual_charge_target_soc'] = '40'
        rig.coordinate()
        self.assertEqual(rig.registers, {40365: 10000, 40366: 10000})
        self.assertEqual(rig.states('input_boolean.manual_battery_charge'), 'off')

    def test_grid_recovery_does_not_resume_cancelled_manual_request(self):
        rig = Rig(manual=True)
        rig.states['binary_sensor.grid_control_ready'] = 'off'
        rig.coordinate()
        rig.states['binary_sensor.grid_control_ready'] = 'on'
        rig.states['input_boolean.battery_automation_on'] = 'off'
        rig.coordinate()
        self.assertEqual(rig.registers, {40365: 10000, 40366: 10000})
        self.assertEqual(rig.states('input_boolean.manual_battery_charge'), 'off')
        self.assertEqual(rig.states('input_boolean.battery_charging_active'), 'off')

    def test_missing_raw_soc_cannot_start_charge_with_stale_validity_flag(self):
        rig = Rig(manual=True, active=False)
        rig.registers = {40365: 10000, 40366: 10000}
        # HA updates dependent templates asynchronously. Model the interval
        # after raw telemetry drops but before inverter_data_valid turns off.
        rig.states['sensor.reading_energy_battery_soc_scaled'] = 'unavailable'
        rig.run(SCRIPTS['charge_battery_to_target']['sequence'])
        self.assertEqual(rig.registers, {40365: 10000, 40366: 10000})
        self.assertEqual(rig.states('input_boolean.battery_charging_active'), 'off')

    def test_invalid_raw_soc_or_target_never_writes_registers(self):
        for soc in ('unavailable', 'unknown', '0', '-1', '10001', '65535', 'nan', 'inf'):
            with self.subTest(soc=soc):
                rig = Rig(manual=True, active=False)
                rig.states['sensor.reading_energy_battery_soc_scaled'] = soc
                rig.run(SCRIPTS['charge_battery_to_target']['sequence'])
                self.assertEqual(rig.calls, [])
        for target in ('unavailable', '0', '-1', '101', 'nan', 'inf'):
            with self.subTest(target=target):
                rig = Rig(manual=True, active=False)
                rig.states['input_number.battery_target_soc'] = target
                rig.run(SCRIPTS['charge_battery_to_target']['sequence'])
                self.assertEqual(rig.calls, [])


class RunningChargeTelemetryTests(unittest.TestCase):
    """Exercise telemetry loss after hardware charging has already started."""

    def running_charge(self, *, manual):
        rig = Rig(manual=manual, active=False, soc=50, target=80, computed=80)
        rig.registers = {40365: 10000, 40366: 10000}
        rig.states['binary_sensor.should_start_charging'] = 'on'
        rig.coordinate()
        # Verify the setup went through production actions, not just test flags.
        self.assertEqual(rig.registers, {40365: -8000, 40366: 10000})
        self.assertEqual(rig.states('switch.storctl_mod'), 'on')
        self.assertEqual(rig.states('input_boolean.battery_charging_active'), 'on')
        rig.states['binary_sensor.should_start_charging'] = 'off'
        return rig

    def test_valid_soc_keeps_existing_charge_running(self):
        for manual in (False, True):
            with self.subTest(manual=manual):
                rig = self.running_charge(manual=manual)
                rig.coordinate()
                self.assertEqual(rig.registers[40365], -8000)
                self.assertEqual(rig.states('input_boolean.battery_charging_active'), 'on')

    def test_target_completion_stops_existing_charge_without_price_data(self):
        for manual in (False, True):
            with self.subTest(manual=manual):
                rig = self.running_charge(manual=manual)
                rig.states['binary_sensor.tibber_cached_price_data_valid'] = 'off'
                rig.states['sensor.reading_energy_battery_soc_scaled'] = '8000'
                rig.coordinate()
                self.assertEqual(rig.states('switch.storctl_mod'), 'off')
                self.assertEqual(rig.registers, {40365: 10000, 40366: 10000})

    def test_raw_soc_loss_stops_existing_charge_before_validity_flag_updates(self):
        for manual in (False, True):
            for raw in ('unavailable', 'unknown', 'nan', 'inf', '-inf', '0', '-1', '10001'):
                with self.subTest(manual=manual, raw=raw):
                    rig = self.running_charge(manual=manual)
                    rig.states['sensor.reading_energy_battery_soc_scaled'] = raw
                    # Raw and derived HA entities do not update atomically.
                    self.assertEqual(rig.states('binary_sensor.inverter_data_valid'), 'on')
                    rig.coordinate()
                    self.assertEqual(rig.registers, {40365: 10000, 40366: 10000},
                                     'Rejecting another start must also release the existing forced-charge request')
                    self.assertEqual(rig.states('switch.storctl_mod'), 'off')
                    self.assertEqual(rig.states('input_boolean.battery_charging_active'), 'off')

    def test_invalidity_flag_eventually_releases_existing_charge(self):
        for manual in (False, True):
            with self.subTest(manual=manual):
                rig = self.running_charge(manual=manual)
                rig.states['sensor.reading_energy_battery_soc_scaled'] = 'unavailable'
                rig.states['binary_sensor.inverter_data_valid'] = 'off'
                rig.coordinate()
                self.assertEqual(rig.registers, {40365: 10000, 40366: 10000})
                self.assertEqual(rig.states('switch.storctl_mod'), 'off')


    def test_raw_soc_loss_releases_charge_even_with_car_protection(self):
        rig = self.running_charge(manual=True)
        rig.states.update({'binary_sensor.car_charging_stable': 'on',
                           'select.wattpilot_charging_mode': 'Default',
                           'sensor.reading_energy_battery_soc_scaled': 'unavailable'})
        rig.coordinate()
        self.assertEqual(rig.registers, {40365: 10000, 40366: 10000})
        self.assertEqual(rig.states('switch.storctl_mod'), 'off')
        self.assertEqual(rig.states('input_boolean.battery_no_discharging_active'), 'off')

    def test_queued_discharge_limit_cannot_undo_raw_data_cleanup(self):
        for raw, validity in [('unavailable', 'on'), ('nan', 'on'),
                              ('0', 'on'), ('5000', 'off')]:
            with self.subTest(raw=raw, validity=validity):
                rig = self.running_charge(manual=True)
                rig.states.update({'binary_sensor.car_charging_stable': 'on',
                                   'sensor.reading_energy_battery_soc_scaled': raw,
                                   'binary_sensor.inverter_data_valid': validity})
                rig.coordinate()
                self.assertEqual(rig.states('switch.storctl_mod'), 'off')
                # A script dispatched before the telemetry loss may run later.
                rig.run(SCRIPTS['set_dynamic_discharge_limit']['sequence'])
                self.assertEqual(rig.registers, {40365: 10000, 40366: 10000})
                self.assertEqual(rig.states('switch.storctl_mod'), 'off')

    def test_raw_soc_loss_has_an_independent_edge_trigger(self):
        trigger = next(t for t in COORDINATOR['trigger'] if t.get('id') == 'raw_soc_invalid')
        rig = Rig()
        for raw, invalid in [('5000', False), ('10000', False),
                             ('unavailable', True), ('nan', True), ('10001', True)]:
            with self.subTest(raw=raw):
                rig.states['sensor.reading_energy_battery_soc_scaled'] = raw
                self.assertEqual(rig.truth(rig.render(trigger['value_template'])), invalid)

class ManualTargetValidityTests(unittest.TestCase):
    def test_invalid_target_cancels_new_manual_request(self):
        for target in ('unavailable', 'unknown', 'nan', 'inf', '-inf', '0', '-1', '101'):
            with self.subTest(target=target):
                rig = Rig(manual=True, active=False)
                rig.registers = {40365: 10000, 40366: 10000}
                rig.states['input_number.manual_charge_target_soc'] = target
                rig.coordinate()
                self.assertEqual(rig.registers, {40365: 10000, 40366: 10000})
                self.assertEqual(rig.states('input_boolean.manual_battery_charge'), 'off')
                self.assertEqual(rig.states('switch.storctl_mod'), 'off')

    def test_invalid_target_releases_existing_manual_charge(self):
        for target in ('unavailable', 'unknown', 'nan', 'inf', '-inf', '0', '-1', '101'):
            with self.subTest(target=target):
                rig = Rig(manual=True, active=False)
                rig.coordinate()
                self.assertLess(rig.registers[40365], 0)
                rig.states['input_number.manual_charge_target_soc'] = target
                rig.coordinate()
                self.assertEqual(rig.registers, {40365: 10000, 40366: 10000})
                self.assertEqual(rig.states('input_boolean.manual_battery_charge'), 'off')

    def test_valid_manual_target_boundaries_still_work(self):
        for target, soc in [(1, 0.5), (100, 95)]:
            with self.subTest(target=target):
                rig = Rig(manual=True, active=False, soc=soc, target=target)
                rig.coordinate()
                self.assertLess(rig.registers[40365], 0)
                self.assertEqual(rig.states('input_boolean.manual_battery_charge'), 'on')


class ReserveRecoveryTests(unittest.TestCase):
    def request(self, soc, *, grid='on', automation='on', prices='off'):
        rig = Rig(soc=soc, active=False, computed=15)
        rig.states.update({'binary_sensor.grid_control_ready': grid,
                           'input_boolean.battery_automation_on': automation,
                           'binary_sensor.tibber_cached_price_data_valid': prices})
        return rig.truth(rig.render(SENSORS['Should Start Charging']['state']))

    def test_breached_reserve_recovers_even_without_prices(self):
        self.assertTrue(self.request(9))

    def test_reserve_recovery_cannot_bypass_master_or_grid_interlock(self):
        for grid, automation in [('off', 'on'), ('unavailable', 'on'),
                                 ('on', 'off')]:
            with self.subTest(grid=grid, automation=automation):
                self.assertFalse(self.request(9, grid=grid, automation=automation))

    def test_reserve_boundary_does_not_start_speculative_charging(self):
        for soc in (10, 15, 50):
            with self.subTest(soc=soc):
                self.assertFalse(self.request(soc, prices='on'))


class DischargeFallbackTests(unittest.TestCase):
    def limit(self, *, grid, ac, wallbox, smoothed='unavailable', balcony=0):
        rig = TemplateRig()
        rig.states.update({'binary_sensor.car_charging_stable': 'on',
                           'sensor.house_consumption_smoothed': smoothed,
                           'sensor.battery_surplus_discharge_power': '0',
                           'sensor.reading_max_allowed_discharge_power': '10000',
                           'sensor.reading_energy_main_meter': str(grid),
                           'sensor.reading_energy_inverter_ac_output': str(ac),
                           'sensor.balkonkraftwerk_power': str(balcony),
                           'sensor.wattpilot_charging_power': str(wallbox)})
        return float(rig.render(SENSORS['Discharge Limit Percentage']['state']))

    def test_import_fallback_subtracts_car_load(self):
        # Total load 4 kW; 3 kW car leaves 1 kW house (+15% margin).
        self.assertEqual(self.limit(grid=3000, ac=1000, wallbox=3000), 11.5)

    def test_smoothed_reading_takes_precedence_over_noisy_power_snapshot(self):
        self.assertEqual(self.limit(grid=9000, ac=1000, wallbox=3000,
                                    smoothed='1000'), 11.5)

    def test_limit_is_clamped_for_zero_and_extreme_house_load(self):
        for house, expected in [('0', 1), ('20000', 100)]:
            with self.subTest(house=house):
                self.assertEqual(self.limit(grid=0, ac=0, wallbox=0,
                                            smoothed=house), expected)

    def test_export_fallback_counts_only_actual_house_demand(self):
        # 6 kW inverter = 2 kW export + 3 kW car + 1 kW house.
        self.assertEqual(self.limit(grid=-2000, ac=6000, wallbox=3000), 11.5)

    def test_fallback_includes_balcony_ac_generation(self):
        self.assertEqual(self.limit(grid=-2200, ac=6000, wallbox=3000,
                                    balcony=200), 11.5)


class DischargeCommandBoundaryTests(unittest.TestCase):
    def test_delayed_watchdog_cannot_reenable_control_after_master_off(self):
        rig = Rig(car=True)
        rig.states['input_boolean.battery_automation_on'] = 'off'
        rig.coordinate()
        self.assertEqual(rig.states('switch.storctl_mod'), 'off')
        # Model a watchdog dispatched before the coordinator's cleanup.
        rig.run(SCRIPTS['set_dynamic_discharge_limit']['sequence'])
        self.assertEqual(rig.registers, {40365: 10000, 40366: 10000})
        self.assertEqual(rig.states('switch.storctl_mod'), 'off')

    def test_invalid_discharge_percentage_uses_safe_fallback(self):
        for value in ('-80', '0', '101', '1000', 'nan', 'inf', '-inf',
                      'unavailable', 'unknown', 'garbage'):
            with self.subTest(value=value):
                rig = Rig(car=True, active=False)
                rig.registers = {40365: 10000, 40366: 10000}
                rig.states['sensor.discharge_limit_percentage'] = value
                rig.run(SCRIPTS['set_dynamic_discharge_limit']['sequence'])
                self.assertEqual(rig.registers, {40365: 1000, 40366: 10000})

    def test_valid_discharge_percentage_boundaries_are_preserved(self):
        for value, expected in [('1', 100), ('11.5', 1150), ('100', 10000)]:
            with self.subTest(value=value):
                rig = Rig(car=True, active=False)
                rig.states['sensor.discharge_limit_percentage'] = value
                rig.run(SCRIPTS['set_dynamic_discharge_limit']['sequence'])
                self.assertEqual(rig.registers[40365], expected)


if __name__ == '__main__':
    unittest.main()
