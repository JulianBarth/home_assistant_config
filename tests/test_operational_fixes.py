"""Regression scenarios for forecast dates, power balances, accounting and logging."""
import ast
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import gzip
import json
import math
from pathlib import Path
import subprocess
import sys
import shlex
import tempfile
from types import SimpleNamespace
import unittest
from zoneinfo import ZoneInfo

from test_battery_control import Rig, ROOT, SENSORS, TEMPLATES

sys.path.insert(0, str(ROOT / 'tools'))
from seasonal_model import build_model

ZONE = ZoneInfo('Europe/Berlin')

def number(value):
    try:
        return math.isfinite(float(value))
    except (ValueError, TypeError):
        return False

def date(value):
    return value if isinstance(value, datetime) else datetime.fromisoformat(value)

def timestamp(value, default=None):
    try:
        return date(value).timestamp()
    except (ValueError, TypeError):
        return default

class TemplateRig(Rig):
    def __init__(self, when='2026-10-16T00:00:00+02:00'):
        super().__init__()
        self.when = date(when)
        self.attrs = {}
        self.env.globals.update(now=lambda: self.when, timedelta=timedelta,
                                as_datetime=date, as_timestamp=timestamp,
                                is_number=number,
                                state_attr=lambda e, a: self.attrs.get((e, a)))
        self.env.filters['as_local'] = lambda d: d.astimezone(ZONE)

    def tracker(self, previous, trigger):
        self.env.globals.update(this=SimpleNamespace(attributes={'data': previous}),
                                trigger=SimpleNamespace(id=trigger))
        return ast.literal_eval(self.render(SENSORS['Battery Charge Cycle Tracker']['attributes']['data']))


def attach_year_model(rig, records=()):
    """Render the actual production input command, then run its pure model."""
    import yaml
    text = (ROOT / 'configuration.yaml').read_text().split('command_line:\n', 1)[1].split('\n# Archive', 1)[0]
    command = yaml.safe_load(text)[0]['sensor']['command']
    rig.env.filters.update(to_json=lambda value: json.dumps(value, default=str),
                           base64_encode=lambda value: base64.b64encode(value.encode()).decode())
    argv = shlex.split(rig.render(command))
    assert argv[:5] == ['python3', '/config/tools/seasonal_model.py', '--history-root', '/config', '--payload']
    assert len(argv) == 6
    result = build_model(json.loads(base64.b64decode(argv[5], validate=True)), records)
    rig.states['sensor.reutlingen_energy_model'] = result['generated_at']
    for key, value in result.items():
        rig.attrs[('sensor.reutlingen_energy_model', key)] = value
    return result


class DiagnosticReloadTests(unittest.TestCase):
    def test_missing_diagnostic_lists_do_not_throw_or_claim_all_clear(self):
        rig = TemplateRig()
        for attribute in ['diagnosis', 'recommendations']:
            with self.subTest(attribute=attribute):
                text = rig.render(SENSORS['Sankey Debug Info']['attributes'][attribute])
                self.assertIn('unavailable', text.lower())
                self.assertNotIn('All entities are available', text)

    def test_available_empty_diagnostic_lists_report_healthy(self):
        rig = TemplateRig()
        for name in ['unavailable_entities', 'invalid_entities']:
            rig.attrs[('sensor.sankey_entity_check', name)] = []
        self.assertIn('All entities are available', rig.render(
            SENSORS['Sankey Debug Info']['attributes']['diagnosis']))

    def test_partially_initialized_diagnostic_lists_are_not_all_clear(self):
        rig = TemplateRig()
        rig.attrs[('sensor.sankey_entity_check', 'unavailable_entities')] = []
        for attribute in ['diagnosis', 'recommendations']:
            with self.subTest(attribute=attribute):
                self.assertIn('unavailable', rig.render(
                    SENSORS['Sankey Debug Info']['attributes'][attribute]).lower())

    def test_invalid_only_diagnostic_does_not_recommend_all_clear(self):
        rig = TemplateRig()
        rig.attrs[('sensor.sankey_entity_check', 'unavailable_entities')] = []
        rig.attrs[('sensor.sankey_entity_check', 'invalid_entities')] = ['sensor.total_solar_power']
        text = rig.render(SENSORS['Sankey Debug Info']['attributes']['recommendations'])
        self.assertIn('invalid', text.lower())
        self.assertNotIn('No issues detected', text)

    def test_real_unavailable_entities_keep_their_diagnosis_and_recommendation(self):
        rig = TemplateRig()
        rig.attrs[('sensor.sankey_entity_check', 'unavailable_entities')] = ['sensor.total_solar_power']
        rig.attrs[('sensor.sankey_entity_check', 'invalid_entities')] = []
        self.assertIn('1 entities are unavailable', rig.render(
            SENSORS['Sankey Debug Info']['attributes']['diagnosis']))
        self.assertIn('Check Fronius Modbus connection', rig.render(
            SENSORS['Sankey Debug Info']['attributes']['recommendations']))

class ForecastTests(unittest.TestCase):
    def planner(self, when):
        rig = TemplateRig(when)
        rig.states.update({'sensor.solcast_pv_forecast_prognose_verbleibende_leistung_heute':'2',
                           'sensor.solcast_pv_forecast_prognose_morgen':'30',
                           'sensor.tibber_energy_price_percentile_next_12_hours':'0',
                           'binary_sensor.battery_charging_is_profitable_enhanced':'on',
                           'sensor.tibber_cached_energy_prices':'0.2'})
        rig.attrs[('sun.sun', 'next_rising')] = '2026-10-17T07:45:00+02:00'
        attach_year_model(rig)
        return rig

    def debug(self, rig):
        return ast.literal_eval(rig.render(SENSORS['Battery Optimization Data']['attributes']['calculation_data']))

    def test_upcoming_solar_changes_date_at_midnight(self):
        for when, expected in [('2026-10-16T23:00:00+02:00',30000),
                               ('2026-10-17T01:00:00+02:00',2000)]:
            rig = self.planner(when)
            self.assertEqual(self.debug(rig)['expected_solar_wh'],expected)
        # The actual target must follow today's low solar, not tomorrow's sunshine.
        rig=self.planner('2026-10-17T01:00:00+02:00')
        self.assertGreater(float(rig.render(SENSORS['Battery Optimization Data']['state'])),15)

    def test_friday_and_sunday_evening_use_next_morning_schedule(self):
        for when,wake in [('2026-10-16T23:00:00+02:00',7.5),
                           ('2026-10-18T23:00:00+02:00',5.5)]:
            self.assertEqual(self.debug(self.planner(when))['wake_hour'],wake)

    def test_cached_arrays_are_relabelled_at_midnight(self):
        rig=TemplateRig('2026-10-17T00:00:01+02:00')
        yesterday=[{'startsAt':'2026-10-16T23:45:00+02:00','total':0.9}]
        today=[{'startsAt':'2026-10-17T00:00:00+02:00','total':0.2}]
        rig.env.globals['this']=SimpleNamespace(attributes={'today':yesterday,'tomorrow':today})
        value=ast.literal_eval(rig.render(SENSORS['Tibber Cached Energy Prices']['attributes']['today']))
        self.assertEqual(value,today)
        self.assertEqual(ast.literal_eval(rig.render(SENSORS['Tibber Cached Energy Prices']['attributes']['tomorrow'])),[])

class PowerTests(unittest.TestCase):
    def test_export_does_not_count_as_house_load(self):
        rig=TemplateRig()
        rig.states.update({'sensor.reading_energy_main_meter':'-2000',
                           'sensor.reading_energy_inverter_ac_output':'3000',
                           'sensor.wattpilot_charging_power':'0'})
        self.assertEqual(float(rig.render(SENSORS['House Consumption']['state'])),1000)

    def test_balcony_is_ac_house_supply_not_battery_dc(self):
        rig=TemplateRig()
        rig.states.update({'sensor.reading_energy_main_meter':'-2200',
                           'sensor.reading_energy_inverter_ac_output':'3000',
                           'sensor.balkonkraftwerk_power':'200',
                           'sensor.total_solar_power':'4200',
                           'sensor.fronius_solar_power':'4000',
                           'sensor.charging_state':'CHARGING'})
        self.assertEqual(float(rig.render(SENSORS['House Consumption']['state'])),1000)
        self.assertEqual(float(rig.render(SENSORS['Battery Power']['state'])),1000)

    def test_grid_charge_excludes_house_ev_and_solar(self):
        rig=TemplateRig()
        for imported,ac,charged,expected in [(7200,2000,1500,0),(7200,-1000,3000,1000),(500,-1000,3000,500),(-100,-1000,3000,0)]:
            rig.states.update({'sensor.reading_energy_main_meter':str(imported),
                               'sensor.reading_energy_inverter_ac_output':str(ac),
                               'sensor.battery_charge_power':str(charged)})
            self.assertEqual(float(rig.render(SENSORS['Grid To Battery']['state'])),expected)

    def test_missing_soc_is_unavailable_and_render_does_not_throw(self):
        rig=TemplateRig()
        rig.states['sensor.reading_energy_battery_soc_scaled']='unavailable'
        self.assertFalse(rig.truth(rig.render(SENSORS['Batterie SoC']['availability'])))
        rig.render(SENSORS['Batterie SoC']['state'])

class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.rig=TemplateRig('2026-10-16T00:45:00+02:00')
        self.rig.states['sensor.grid_to_battery']='3600'
        prices=[{'startsAt':f'2026-10-16T{t}:00+02:00','total':v} for t,v in [('00:30',0.6),('00:45',0.415),('01:00',0.4321)]]
        self.rig.attrs[('sensor.tibber_cached_energy_prices','today')]=prices
        self.d=self.rig.tracker({},'start')

    def step(self,when,trig='tick'):
        self.rig.when=date(when)
        self.d=self.rig.tracker(self.d,trig)
        return self.d

    def test_tariff_boundary_prices_elapsed_slot_and_splits_crossing(self):
        self.rig.when=date('2026-10-16T00:59:55+02:00')
        self.d=self.rig.tracker({},'start')
        d=self.step('2026-10-16T01:00:05+02:00','stop')
        self.assertAlmostEqual(d['cycle_kwh'],0.01)
        self.assertAlmostEqual(d['cycle_cost_eur'],0.005*0.415+0.005*0.4321,places=7)

    def test_stop_prices_previous_power_when_new_power_is_zero(self):
        self.rig.states['sensor.grid_to_battery']='0'
        d=self.step('2026-10-16T00:46:00+02:00','stop')
        self.assertAlmostEqual(d['cycle_kwh'],0.06)
        self.assertAlmostEqual(d['cycle_cost_eur'],0.06*0.415)
        self.assertEqual(d['month_cycles'],1)

    def test_solar_charge_does_not_enter_grid_totals(self):
        self.rig.states['sensor.grid_to_battery']='0'
        self.d=self.rig.tracker({},'start')
        self.assertEqual(self.step('2026-10-16T00:46:00+02:00','stop')['month_kwh'],0)

    def test_long_gap_and_restart_are_not_extrapolated(self):
        self.assertEqual(self.step('2026-10-16T01:00:00+02:00')['month_kwh'],0)
        self.assertEqual(self.d['unmeasured_seconds'],900)
        self.assertEqual(self.step('2026-10-16T02:00:00+02:00','boot')['month_kwh'],0)
        self.assertFalse(self.d['cycle_active'])

    def test_unknown_power_does_not_bridge_to_recovery(self):
        self.rig.states['sensor.grid_to_battery']='unavailable'
        self.step('2026-10-16T00:45:10+02:00','sample')
        self.rig.states['sensor.grid_to_battery']='3600'
        self.step('2026-10-16T00:46:10+02:00','sample')
        self.assertAlmostEqual(self.d['month_kwh'],0.01)
        self.assertEqual(self.d['unmeasured_seconds'],60)

    def test_legacy_totals_are_preserved_separately(self):
        legacy={'month':'2026-10','month_kwh':17.77,'month_cost_eur':6.225,'month_saved_eur':0.761}
        d=self.rig.tracker(legacy,'tick')
        self.assertEqual(d['month_kwh'],0)
        self.assertEqual(d['legacy_totals']['kwh'],17.77)
        self.assertEqual(d['accounting_version'],2)

    def test_average_uses_date_not_array_name(self):
        self.rig.attrs[('sensor.tibber_cached_energy_prices','today')]=[{'startsAt':'2026-10-15T23:45:00+02:00','total':9}]
        self.rig.attrs[('sensor.tibber_cached_energy_prices','tomorrow')]=[{'startsAt':'2026-10-16T00:45:00+02:00','total':0.415}]
        d=self.rig.tracker({},'start')
        self.assertAlmostEqual(d['sample_day_avg'],0.415)

    def test_midnight_month_rollover_keeps_only_new_month_interval(self):
        self.rig.when=date('2026-10-31T23:59:55+01:00')
        self.rig.attrs[('sensor.tibber_cached_energy_prices','today')]=[{'startsAt':'2026-10-31T23:45:00+01:00','total':0.2}]
        self.rig.attrs[('sensor.tibber_cached_energy_prices','tomorrow')]=[{'startsAt':'2026-11-01T00:00:00+01:00','total':0.3}]
        self.d=self.rig.tracker({},'start')
        d=self.step('2026-11-01T00:00:05+01:00','stop')
        self.assertAlmostEqual(d['month_kwh'],0.005)
        self.assertAlmostEqual(d['month_cost_eur'],0.0015)
        self.assertAlmostEqual(d['cycle_kwh'],0.01)

class LoggerTests(unittest.TestCase):
    def test_parallel_records_and_rotation_remain_complete(self):
        script=ROOT/'tools/battery_log.py'
        with tempfile.TemporaryDirectory() as directory:
            log=Path(directory)/'battery_algorithm.log'
            def write(i):
                subprocess.run([sys.executable,str(script),'--path',str(log)],input=json.dumps({'i':i,'text':'a\nb; $HOME'}),text=True,check=True)
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(write,range(40)))
            self.assertEqual({json.loads(l)['i'] for l in log.read_text().splitlines()},set(range(40)))
            subprocess.run([sys.executable,str(script),'--path',str(log),'--rotate','2026-09'],check=True)
            self.assertEqual(len(gzip.open(Path(directory)/'battery_algorithm-2026-09.log.gz','rt').read().splitlines()),40)
            self.assertEqual(log.read_text(),'')
            write(41)
            self.assertEqual(json.loads(log.read_text())['i'],41)

if __name__=='__main__':
    unittest.main()
