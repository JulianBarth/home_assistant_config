"""Dashboard navigation, read-only flags and template safety checks."""
from pathlib import Path
import unittest
import yaml
from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = yaml.safe_load((ROOT / 'ui-lovelace.yaml').read_text())

def walk(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)

class DashboardTests(unittest.TestCase):
    def test_four_main_views_and_reachable_subviews(self):
        views = DASHBOARD['views']
        self.assertEqual([v['title'] for v in views if not v.get('subview')],
                         ['Overview', 'Energy', 'Charging', 'Settings'])
        routes = {'/energy-overview/' + v['path'] for v in views}
        links = {x['navigation_path'] for x in walk(DASHBOARD) if x.get('action') == 'navigate'}
        self.assertTrue(links <= routes)
        for view in views:
            if view.get('subview'):
                self.assertIn('/energy-overview/' + view['path'], links)
                self.assertIn(view['back_path'], routes)

    def test_operational_flags_cannot_be_toggled_from_rows(self):
        flags = {'battery_charging_active','battery_no_discharging_active',
                 'car_boost_active','car_cheap_grid_active','car_boost_suppressed',
                 'car_boost_notified','grid_outage_active'}
        for card in walk(DASHBOARD):
            if card.get('type') != 'entities':
                continue
            self.assertFalse(card.get('show_header_toggle', True))
            for row in card['entities']:
                if not isinstance(row, dict):
                    continue
                if row.get('entity','').removeprefix('input_boolean.') in flags:
                    self.assertEqual(row['type'], 'simple-entity')
                    for key in ['tap_action','hold_action','double_tap_action']:
                        self.assertEqual(row[key]['action'], 'none')
                if row.get('entity','').startswith('script.'):
                    self.assertTrue(row['confirmation']['text'])

    def test_overview_templates_do_not_render_unknown_as_zero(self):
        overview = DASHBOARD['views'][0]
        env = Environment(undefined=StrictUndefined)
        states = {'sensor.grid_connection_status':'uncertain'}
        env.globals.update(states=lambda id: states.get(id,'unavailable'),
                           is_state=lambda id,value: states.get(id,'unavailable') == value,
                           state_attr=lambda *_: None,
                           is_number=lambda value: str(value).replace('.','',1).isdigit())
        cards = [x for x in walk(overview) if x.get('type') == 'markdown' and 'title' in x]
        car = next(x for x in cards if x['title'] == 'Car charging')
        rendered = env.from_string(car['content']).render()
        self.assertIn('Connection status unavailable', rendered)
        states['input_boolean.car_cheap_grid_active']='on'
        rendered = env.from_string(car['content']).render()
        self.assertIn('Price unavailable', rendered)
        self.assertIn('Power unavailable', rendered)
        self.assertNotIn('0.0 ct/kWh', rendered)

    def test_theme_and_resource_are_available(self):
        theme = yaml.safe_load((ROOT / 'themes/energy-calm.yaml').read_text())
        for view in DASHBOARD['views']:
            self.assertIn(view['theme'], theme)
        config = (ROOT / 'configuration.yaml').read_text()
        self.assertIn('/local/energy-flow-card.js?v=20261016-2', config)

    def test_all_dashboard_templates_parse(self):
        env = Environment()
        for card in walk(DASHBOARD):
            if isinstance(card.get('content'), str):
                env.parse(card['content'])

    def test_numeric_charts_keep_percentiles_and_modes_separate(self):
        for card in walk(DASHBOARD):
            if card.get('type') != 'custom:apexcharts-card':
                continue
            ids = [series['entity'] for series in card['series']]
            self.assertFalse(any(id.startswith(('input_boolean.', 'binary_sensor.')) for id in ids))
            self.assertNotIn('sensor.tibber_energy_price_percentile_next_12_hours', ids)
            axis_ids = {axis['id'] for axis in card.get('yaxis', []) if 'id' in axis}
            for series in card['series']:
                if 'yaxis_id' in series:
                    self.assertIn(series['yaxis_id'], axis_ids)
