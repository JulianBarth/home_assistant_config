"""Offline regression tests of the actual YAML templates and action sequences.

Run with: python -m unittest discover -s tests -v (requires PyYAML and Jinja2).
This small action interpreter is not a replacement for HA config/live validation.
"""
from pathlib import Path
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import yaml
from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = yaml.safe_load((ROOT / 'scripts.yaml').read_text())
AUTOMATIONS = yaml.safe_load((ROOT / 'automations.yaml').read_text())
TEMPLATES = yaml.safe_load((ROOT / 'templates.yaml').read_text())
COORDINATOR = next(a for a in AUTOMATIONS if a['alias'] == 'Unified Battery Control Coordinator')
SENSORS = {s['name']: s for block in TEMPLATES for key in ('sensor', 'binary_sensor') for s in block.get(key, [])}


class StateMap(dict):
    def __call__(self, entity):
        return self.get(entity.lower(), 'unknown')

    def __getattr__(self, domain):
        return SimpleNamespace(**{
            k.split('.', 1)[1]: SimpleNamespace(state=v, last_changed=datetime.now(timezone.utc) - timedelta(hours=1))
            for k, v in self.items() if k.startswith(domain + '.')
        })


class Rig:
    def __init__(self, *, manual=False, soc=50, target=80, computed=80, active=True, car=False):
        self.states = StateMap({
            'sensor.reading_energy_battery_soc_scaled': str(soc * 100),
            'input_number.manual_charge_target_soc': str(target),
            'input_number.battery_target_soc': str(target),
            'sensor.computed_target_soc': str(computed),
            'input_number.soc_target_default': '15',
            'input_number.battery_hold_threshold': '3',
            'input_boolean.manual_battery_charge': 'on' if manual else 'off',
            'input_boolean.battery_charging_active': 'on' if active else 'off',
            'input_boolean.battery_no_discharging_active': 'off',
            'input_boolean.battery_automation_on': 'on',
            'binary_sensor.inverter_data_valid': 'on',
            'binary_sensor.grid_available': 'on',
            'binary_sensor.tibber_cached_price_data_valid': 'on',
            'binary_sensor.car_charging_stable': 'on' if car else 'off',
            'binary_sensor.should_charge_battery_during_car_charging': 'on',
            'binary_sensor.should_start_charging': 'off',
            'binary_sensor.should_prevent_discharge': 'off',
            'sensor.discharge_limit_percentage': '10',
            'select.wattpilot_charging_mode': 'Default' if car else 'Eco',
            'switch.storctl_mod': 'on',
        })
        self.env = Environment(undefined=StrictUndefined)
        self.env.globals.update(states=self.states, is_state=lambda e, v: self.states(e) == v,
                                now=lambda: datetime.now(timezone.utc))
        self.registers = {40365: -8000, 40366: 10000}
        self.calls = []

    def render(self, value):
        return self.env.from_string(value).render().strip() if isinstance(value, str) else value

    def truth(self, value):
        return str(value).lower() in ('true', 'on', '1')

    def condition(self, condition):
        if isinstance(condition, list):
            return all(self.condition(c) for c in condition)
        kind = condition['condition']
        if kind == 'state':
            return self.states(condition['entity_id']) == condition['state']
        if kind == 'template':
            return self.truth(self.render(condition['value_template']))
        raise AssertionError(f'Unsupported condition: {condition}')

    def run(self, steps):
        for step in steps:
            if 'condition' in step:
                if not self.condition(step):
                    return
            elif 'choose' in step:
                branch = next((b['sequence'] for b in step['choose'] if self.condition(b['conditions'])), step.get('default', []))
                self.run(branch)
            else:
                service = self.render(step.get('service', step.get('action')))
                self.calls.append(service)
                if service.startswith('script.'):
                    # Async dispatch would invalidate the write-order guarantees.
                    assert service != 'script.turn_on', 'Battery control must await its hardware writes'
                    self.run(SCRIPTS[service.split('.')[1]]['sequence'])
                elif service == 'modbus.write_register':
                    data = step['data']
                    value = int(float(self.render(data['value'])))
                    self.registers[data['address']] = value - 65536 if value > 32767 else value
                    assert -self.registers[40366] <= self.registers[40365], f'Inverted power window: {self.registers}'
                elif service == 'input_number.set_value':
                    self.states[step['target']['entity_id']] = str(self.render(step['data']['value']))
                elif service.startswith(('switch.', 'input_boolean.')):
                    entities = step['target']['entity_id']
                    for entity in entities if isinstance(entities, list) else [entities]:
                        self.states[entity.lower()] = 'on' if service.endswith('turn_on') else 'off'
                else:
                    raise AssertionError(f'Unexpected action: {service}')

    def update_decisions(self):
        for name, entity in [('Should Stop Charging', 'binary_sensor.should_stop_charging'),
                             ('Should Hold Battery SOC', 'binary_sensor.should_hold_battery_soc'),
                             ('Battery Control Mode', 'sensor.battery_control_mode')]:
            value = self.render(SENSORS[name]['state'])
            self.states[entity] = ('on' if self.truth(value) else 'off') if entity.startswith('binary_sensor.') else value

    def coordinate(self):
        self.update_decisions()
        self.run(COORDINATOR['action'])


class BatteryControlTests(unittest.TestCase):
    def test_manual_ignores_price_target_and_master_switch(self):
        rig = Rig(manual=True, computed=15)
        rig.states['input_boolean.battery_automation_on'] = 'off'
        rig.coordinate()
        self.assertEqual(rig.registers, {40365: -8000, 40366: 10000})
        self.assertEqual(rig.states('input_boolean.manual_battery_charge'), 'on')

    def test_manual_stops_at_target_even_with_higher_computed_target(self):
        rig = Rig(manual=True, soc=80, computed=100)
        rig.coordinate()
        self.assertEqual(rig.registers, {40365: 10000, 40366: 10000})
        self.assertEqual(rig.states('switch.storctl_mod'), 'off')
        self.assertEqual(rig.states('input_boolean.manual_battery_charge'), 'off')
        self.assertEqual(rig.states('input_boolean.battery_charging_active'), 'off')

    def test_already_satisfied_manual_request_never_forces_charge(self):
        rig = Rig(manual=True, active=False, soc=90)
        rig.coordinate()
        self.assertNotIn('script.charge_battery_to_target', rig.calls)
        self.assertEqual(rig.states('input_boolean.manual_battery_charge'), 'off')

    def test_taper_for_manual_automatic_and_car_plus_battery(self):
        for manual, car, computed in [(True, False, 15), (False, False, 80), (False, True, 80)]:
            with self.subTest(manual=manual, car=car):
                rig = Rig(manual=manual, car=car, soc=78, computed=computed)
                rig.coordinate()
                self.assertEqual(rig.registers, {40365: -5000, 40366: 5000})
                self.assertEqual(rig.states('switch.storctl_mod'), 'on')
                self.assertEqual(rig.states('input_boolean.battery_charging_active'), 'on')

    def test_start_inside_taper_band_and_target_change_use_fresh_values(self):
        for manual in (True, False):
            rig = Rig(manual=manual, soc=78, target=80, active=False)
            rig.states['input_number.battery_target_soc'] = '100'
            rig.states['binary_sensor.should_start_charging'] = 'on'
            rig.coordinate()
            self.assertEqual(rig.registers, {40365: -5000, 40366: 5000})

    def test_full_target_is_not_tapered_and_stops_at_100_without_prices(self):
        for manual in (True, False):
            rig = Rig(manual=manual, soc=99, target=100, computed=100)
            rig.states['binary_sensor.tibber_cached_price_data_valid'] = 'off'
            rig.coordinate()
            self.assertEqual(rig.registers[40365], -8000)
            rig.states['sensor.reading_energy_battery_soc_scaled'] = '10000'
            rig.coordinate()
            self.assertEqual(rig.states('input_boolean.battery_charging_active'), 'off')

    def test_invalid_data_or_grid_loss_overrides_manual(self):
        for sensor in ('binary_sensor.inverter_data_valid', 'binary_sensor.grid_available'):
            rig = Rig(manual=True)
            rig.states[sensor] = 'off'
            rig.coordinate()
            self.assertEqual(rig.states('switch.storctl_mod'), 'off')
            self.assertEqual(rig.states('input_boolean.manual_battery_charge'), 'off')
            self.assertNotIn('script.charge_battery_to_target', rig.calls)

    def test_battery_completion_preserves_manual_car_charging(self):
        rig = Rig(manual=True, car=True, soc=80)
        rig.coordinate()
        self.assertEqual(rig.registers, {40365: 1000, 40366: 10000})
        self.assertEqual(rig.states('switch.storctl_mod'), 'on')
        self.assertEqual(rig.states('input_boolean.battery_no_discharging_active'), 'on')
        self.assertEqual(rig.states('select.wattpilot_charging_mode'), 'Default')
        self.assertFalse(any('wattpilot' in call for call in rig.calls))

    def test_automatic_price_target_drop_stops(self):
        rig = Rig(soc=60, target=80, computed=15)
        rig.coordinate()
        self.assertEqual(rig.states('input_boolean.battery_charging_active'), 'off')

    def test_every_register_write_preserves_valid_hardware_window(self):
        for initial in [(10000, 10000), (-8000, 10000), (-5000, 5000), (100, 100), (5000, -5000)]:
            for script in ('forced_full_recharge', 'charge_battery_reduced_rate', 'charge_battery_limit_discharge', 'stop_battery_charging'):
                with self.subTest(initial=initial, script=script):
                    rig = Rig()
                    rig.registers = dict(zip((40365, 40366), initial))
                    rig.run(SCRIPTS[script]['sequence'])


if __name__ == '__main__':
    unittest.main()
