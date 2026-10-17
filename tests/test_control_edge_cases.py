"""Behavioral checks of production YAML at control and telemetry boundaries.

Regression coverage for the corrected defects documented in BUG_REVIEW.md.
No test connects to Home Assistant or writes physical inverter registers.
"""
import unittest

from test_battery_control import Rig, SCRIPTS, COORDINATOR
from test_operational_fixes import SENSORS, TemplateRig


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


if __name__ == '__main__':
    unittest.main()
