"""Year-round behavior, physical time, forecast trust and real YAML wiring."""
import ast
from datetime import date, datetime, time, timedelta
import json
import math
import sys
from types import SimpleNamespace
import unittest

from test_battery_control import ROOT, SENSORS, AUTOMATIONS
from test_operational_fixes import TemplateRig, attach_year_model

sys.path.insert(0, str(ROOT / 'tools'))
from seasonal_model import Demand, PV, ZONE, UTC, build_model, instant, solar_day


def forecast(when, peak=8, ratio=.6):
    rows = []
    today = when.astimezone(ZONE).date()
    start = datetime.combine(today, time(), ZONE).astimezone(UTC)
    end = datetime.combine(today + timedelta(days=2), time(), ZONE).astimezone(UTC)
    while start < end:
        sun = solar_day(start.astimezone(ZONE).date())
        position = (start - sun['sunrise']).total_seconds() / (sun['sunset'] - sun['sunrise']).total_seconds()
        power = peak * max(0, math.sin(math.pi * max(0, min(1, position))))
        rows.append({'period_start': start.isoformat(), 'pv_estimate': power,
                     'pv_estimate10': power * ratio})
        start += timedelta(minutes=30)
    return rows


def settings(when='2026-10-18T00:00:00+02:00', peak=8):
    when = instant(when)
    return dict(when=when.isoformat(), night_rate=320, day_rate=1280,
                weekday_wake=5.5, weekend_wake=7.5, sleep_hour=22,
                capacity_wh=10000, reserve_soc=15, soc=90, car_floor_soc=40,
                safety_margin_wh=700, solar_confidence_pct=70,
                forecast_updated_at=when.isoformat(), forecast=forecast(when, peak))


class CalendarTests(unittest.TestCase):
    def test_reutlingen_solstices_and_local_time(self):
        summer, winter = solar_day(date(2026, 6, 21)), solar_day(date(2026, 12, 21))
        self.assertTrue(15.8 < summer['daylight_hours'] < 16.4)
        self.assertTrue(8.0 < winter['daylight_hours'] < 8.5)
        self.assertEqual(summer['noon'].astimezone(ZONE).utcoffset(), timedelta(hours=2))
        self.assertEqual(winter['noon'].astimezone(ZONE).utcoffset(), timedelta(hours=1))
        # Reutlingen's solar noon is neither 13:00 year-round nor civil noon.
        self.assertNotEqual(summer['noon'].astimezone(ZONE).hour, winter['noon'].astimezone(ZONE).hour)

    def test_full_calendar_including_leap_day_is_finite_and_ordered(self):
        day = date(2028, 1, 1)
        for offset in range(366):
            sun = solar_day(day + timedelta(days=offset))
            self.assertLess(sun['sunrise'], sun['noon'])
            self.assertLess(sun['noon'], sun['sunset'])
            self.assertTrue(8 < sun['daylight_hours'] < 17)

    def test_dst_nights_integrate_elapsed_hours_and_do_not_double_count(self):
        model = Demand(instant('2026-03-28T00:00:00+01:00'), {'night_rate': 320})
        for start, end, hours in [('2026-03-28T22:00:00+01:00', '2026-03-29T05:00:00+02:00', 6),
                                  ('2026-10-24T22:00:00+02:00', '2026-10-25T05:00:00+01:00', 8)]:
            self.assertEqual(model.energy(instant(start), instant(end)), hours * 320)


class ForecastTrustTests(unittest.TestCase):
    def test_recovery_must_cover_a_full_hour_before_sunset(self):
        data = settings('2026-12-21T15:30:00+01:00', 100)
        result = build_model(data)
        recovery = result['battery']['solar_recovery_at']
        if recovery:
            t = instant(recovery)
            self.assertLessEqual(t + timedelta(hours=1), solar_day(t.astimezone(ZONE).date())['sunset'])

    def test_sunrise_and_large_daily_total_do_not_invent_usable_solar(self):
        data = settings('2026-12-21T03:00:00+01:00')
        data.update(forecast=[], today_solar_kwh=100)
        result = build_model(data)
        self.assertEqual(result['battery']['solar_start'], 24)
        self.assertIsNone(result['battery']['solar_recovery_at'])
        self.assertEqual(result['car']['budget_wh'], 0)
        self.assertEqual(result['surplus']['surplus_wh'], 0)

    def test_recovery_follows_forecast_even_when_after_09(self):
        data = settings('2026-12-21T03:00:00+01:00', peak=12)
        for row in data['forecast']:
            if instant(row['period_start']).astimezone(ZONE).hour < 10:
                row.update(pv_estimate=0, pv_estimate10=0)
        result = build_model(data)
        recovery = instant(result['battery']['solar_recovery_at']).astimezone(ZONE)
        self.assertGreaterEqual(recovery.hour, 10)
        self.assertGreater(result['battery']['bridge_hours'], 6)

    def test_cloudy_winter_does_not_lend_battery_energy(self):
        data = settings('2026-12-21T10:00:00+01:00', peak=.5)
        result = build_model(data)
        self.assertIsNone(result['battery']['solar_recovery_at'])
        self.assertEqual(result['car']['budget_wh'], 0)

    def test_stale_future_invalid_forecast_poll_times_give_no_solar_credit(self):
        for stamp in ('2026-10-16T00:00:00+02:00', '2026-10-19T00:00:00+02:00', None, 'unknown'):
            data = settings()
            data['forecast_updated_at'] = stamp
            result = build_model(data)
            self.assertEqual(result['car']['usable_solar_wh'], 0)
            self.assertEqual(result['car']['budget_wh'], 0)

    def test_p10_kilowatts_become_watt_hours_and_missing_interval_is_zero(self):
        when = instant('2026-06-21T12:00:00+02:00')
        data = settings(when)
        data['forecast'] = [{'period_start': when.isoformat(), 'pv_estimate': 10, 'pv_estimate10': 2}]
        pv = PV(when, data)
        self.assertEqual(pv.energy(when, when + timedelta(hours=1)), 1000)
        # Missing next half-hour must not be forward-filled from the previous one.
        self.assertIsNone(pv.recovery(when, Demand(when, data)))

    def test_duplicate_conflicting_slots_are_rejected_and_bad_values_do_not_propagate(self):
        data = settings('2026-06-21T12:00:00+02:00')
        row = {'period_start': data['when'], 'pv_estimate': 10, 'pv_estimate10': 2}
        data['forecast'] = [row, dict(row, pv_estimate10=3), dict(row, pv_estimate=float('nan'))]
        pv = PV(instant(data['when']), data)
        self.assertEqual(pv.energy(instant(data['when']), instant(data['when']) + timedelta(hours=1)), 0)

    def test_missing_p10_uses_discounted_p50_without_calling_it_a_quantile(self):
        data = settings('2026-06-21T12:00:00+02:00')
        data['forecast'] = [{'period_start': data['when'], 'pv_estimate': 10}]
        pv = PV(instant(data['when']), data)
        self.assertEqual(pv.status, 'fresh_discounted_p50')
        self.assertEqual(pv.energy(instant(data['when']), instant(data['when']) + timedelta(minutes=30)), 3500)


class AdaptiveDemandTests(unittest.TestCase):
    def test_dark_hours_do_not_need_an_online_balcony_inverter(self):
        rows = self.records()
        for r in rows:
            r['inverter'].update(power_valid=True, balcony_w=0, balcony_valid=False)
        demand = Demand(settings()['when'], settings(), rows)
        self.assertGreater(demand.accepted, 0)
        # The logger must distinguish unavailable balcony telemetry from an
        # invalid grid/inverter/wallbox power balance.
        rig = TemplateRig()
        rig.states.update({'sensor.inverter_power': 'unavailable',
                           'sensor.reading_energy_main_meter': '200',
                           'sensor.reading_energy_inverter_ac_output': '0',
                           'sensor.wattpilot_charging_power': '0'})
        rig.env.globals['trigger'] = SimpleNamespace(id='periodic')
        logger = next(a for a in AUTOMATIONS if a.get('description') == 'Logs full algorithm state as JSON for offline analysis')
        record = json.loads(rig.render(logger['action'][0]['data']['message']))
        self.assertTrue(record['inverter']['power_valid'])
        self.assertFalse(record['inverter']['balcony_valid'])

    def test_malformed_measurement_objects_are_ignored(self):
        valid = self.records()
        malformed = [dict(valid[0], inverter=[]), dict(valid[0], car=42)]
        self.assertEqual(Demand(settings()['when'], settings(), malformed).accepted, 0)

    def records(self, start='2026-09-14T01:00:00+02:00', watts=200):
        t = instant(start)
        return [dict(ts=(t + timedelta(days=d, minutes=m)).isoformat(), trigger='periodic',
                     inverter=dict(grid_w=watts, ac_w=0), car=dict(wallbox_w=0))
                for d in range(28) for m in (0, 15, 30, 45)]

    def test_winter_without_recent_data_uses_configured_rates(self):
        data = settings('2027-01-21T01:00:00+01:00')
        d = Demand(data['when'], data, self.records())
        self.assertEqual(d.accepted, 0)
        self.assertEqual(d.watts(instant(data['when'])), 320)
        self.assertEqual(d.watts(instant('2027-01-21T12:00:00+01:00')), 1280)

    def test_recent_weekday_and_weekend_hours_shrink_toward_local_observations(self):
        data = settings()
        d = Demand(data['when'], data, self.records())
        probe = instant('2026-10-18T01:00:00+02:00')
        self.assertTrue(200 < d.watts(probe) < 320)
        self.assertGreaterEqual(d.watts(probe, True), d.watts(probe))

    def test_future_duplicate_ev_and_old_daylight_balance_are_not_training_data(self):
        data = settings()
        valid = self.records()
        before = Demand(data['when'], data, valid)
        injected = valid + valid + self.records(start='2026-10-19T01:00:00+02:00', watts=9000)
        injected += [dict(r, car=dict(wallbox_w=11000)) for r in valid]
        injected += self.records(start='2026-09-14T12:00:00+02:00', watts=9000)
        after = Demand(data['when'], data, injected)
        self.assertEqual(before.accepted, after.accepted)
        self.assertEqual(before.watts(instant(data['when'])), after.watts(instant(data['when'])))

    def test_daylight_learning_requires_balcony_and_raw_power_validity(self):
        data = settings()
        rows = self.records(start='2026-09-14T12:00:00+02:00', watts=200)
        self.assertEqual(Demand(data['when'], data, rows).accepted, 0)
        for r in rows:
            r['inverter'].update(balcony_w=0, balcony_valid=False, power_valid=True)
        self.assertEqual(Demand(data['when'], data, rows).accepted, 0)
        for r in rows:
            r['inverter'].update(balcony_w=100, balcony_valid=True, power_valid=True)
        d = Demand(data['when'], data, rows)
        self.assertGreater(d.accepted, 0)
        self.assertTrue(300 < d.watts(instant('2026-10-18T12:00:00+02:00')) < 1280)


class AnnualControlTests(unittest.TestCase):
    def test_raw_soc_loss_cannot_leave_positive_car_budget(self):
        rig = TemplateRig('2026-06-21T10:00:00+02:00')
        rig.states.update({'sensor.batterie_soc': '90', 'sensor.reading_energy_battery_soc_scaled': '9000',
                           'input_number.day_consumption_rate_wh': '200',
                           'sensor.solcast_pv_forecast_zeitpunkt_letzter_api_abruf': rig.when.isoformat()})
        rig.attrs[('sensor.solcast_pv_forecast_prognose_heute', 'detailedForecast')] = forecast(rig.when, 20)
        attach_year_model(rig)
        self.assertGreater(float(rig.render(SENSORS['Car Boost Energy Budget']['state'])), 0)
        for raw in ('unknown', 'nan', 'inf', '0', '11000'):
            with self.subTest(raw=raw):
                rig.states['sensor.reading_energy_battery_soc_scaled'] = raw
                self.assertEqual(float(rig.render(SENSORS['Car Boost Energy Budget']['state'])), 0)

    def test_car_boost_start_rejects_stale_derived_soc(self):
        rig = TemplateRig('2026-06-21T10:00:00+02:00')
        attach_year_model(rig)
        rig.states.update({'input_boolean.car_smart_charging_on': 'on',
                           'input_boolean.battery_charging_active': 'off',
                           'binary_sensor.wattpilot_33175380_stecker': 'on',
                           'select.wattpilot_charging_mode': 'Eco', 'sensor.batterie_soc': '90',
                           'sensor.car_boost_energy_budget': '3000',
                           'sensor.reading_energy_battery_soc_scaled': 'unknown'})
        rig.attrs[('sensor.car_boost_energy_budget', 'floor_soc')] = 40
        self.assertFalse(rig.truth(rig.render(SENSORS['Car Boost Viable']['state'])))

    def test_extra_discharge_rejects_stale_derived_soc(self):
        rig = TemplateRig()
        rig.states.update({'sensor.reutlingen_energy_model': rig.when.isoformat(),
                           'sensor.batterie_soc': '90', 'sensor.reading_energy_battery_soc_scaled': 'unknown',
                           'input_boolean.battery_charging_active': 'off'})
        rig.attrs[('sensor.reutlingen_energy_model', 'surplus')] = dict(
            active_window=True, solar_recovery_ok=True, hours_to_solar=8,
            surplus_wh=2000, required_until_solar_wh=1000, safety_margin_wh=700)
        self.assertEqual(float(rig.render(SENSORS['Battery Surplus Discharge Power']['state'])), 0)

    def test_ac_demand_includes_storage_discharge_losses(self):
        data = settings('2026-06-21T00:00:00+02:00', 16)
        data['discharge_efficiency'] = .9
        b = build_model(data)['battery']
        net_ac = b['bridge_consumption_wh'] - b['usable_solar_wh']
        self.assertGreater(net_ac, 0)
        self.assertGreaterEqual(b['energy_deficit_wh'], net_ac / .9 - 2)

    def test_early_pv_overflow_cannot_finance_late_household_demand(self):
        data = settings('2026-06-21T10:00:00+02:00', 16)
        today = instant(data['when']).astimezone(ZONE).date()
        for row in data['forecast']:
            local = instant(row['period_start']).astimezone(ZONE)
            if local.date() == today:
                value = 50 if 10 <= local.hour < 12 else 0
                row.update(pv_estimate=value, pv_estimate10=value)
        # An early pulse fills the 10 kWh battery, then spills. The long
        # afternoon and night exceed that finite capacity, despite net daily PV.
        result = build_model(data)
        self.assertGreater(result['car']['solar_surplus_wh'], 10000)
        self.assertEqual(result['car']['budget_wh'], 0)

    def test_invalid_capacity_helpers_cannot_break_the_production_target(self):
        for bad in ('0', 'nan', 'inf'):
            rig = TemplateRig()
            rig.states.update({'input_number.battery_capacity_wh': bad,
                               'sensor.tibber_energy_price_percentile_next_12_hours': '30',
                               'binary_sensor.battery_charging_is_profitable_enhanced': 'on'})
            attach_year_model(rig)
            target = float(rig.render(SENSORS['Battery Optimization Data']['state']))
            self.assertTrue(math.isfinite(target) and 15 <= target <= 100)

    def test_configured_low_solar_threshold_remains_effective(self):
        data = settings('2026-06-21T03:00:00+02:00', 12)
        self.assertFalse(build_model(dict(data, low_solar_threshold_wh=1))['battery']['is_low_solar_day'])
        self.assertTrue(build_model(dict(data, low_solar_threshold_wh=100000))['battery']['is_low_solar_day'])

    def test_all_months_obey_soc_budget_bounds_and_serialize_without_nan(self):
        for month in range(1, 13):
            for peak in (0, .5, 12):
                with self.subTest(month=month, peak=peak):
                    when = datetime(2026, month, 21, 3, tzinfo=ZONE)
                    result = build_model(settings(when, peak))
                    b, c = result['battery'], result['car']
                    self.assertTrue(15 <= b['calculated_target'] <= b['max_grid_target'] <= 100)
                    self.assertTrue(0 <= b['bridge_hours'] <= 24)
                    self.assertTrue(0 <= c['budget_wh'] <= 5000)
                    self.assertLessEqual(c['budget_wh'], c['solar_surplus_wh'])
                    json.dumps(result, allow_nan=False)

    def test_future_solar_headroom_never_removes_pre_sunrise_bridge_energy(self):
        result = build_model(settings('2026-06-21T00:00:00+02:00', 16))
        b = result['battery']
        self.assertGreater(b['energy_deficit_wh'], 0)
        self.assertGreaterEqual(b['max_grid_target'], 15 + b['energy_deficit_wh'] / 100 - .01)
        self.assertLessEqual(result['car']['budget_wh'], max(0, result['car']['constraint_bridge_wh']))

    def test_increasing_load_or_lowering_pv_cannot_increase_car_loan(self):
        base = settings('2026-06-21T10:00:00+02:00', 20)
        self.assertGreater(build_model(base)['car']['budget_wh'], 0)
        lower_pv = dict(base, forecast=forecast(instant(base['when']), 5))
        more_load = dict(base, day_rate=2000, night_rate=600)
        for other in (lower_pv, more_load):
            self.assertLessEqual(build_model(other)['car']['budget_wh'], build_model(base)['car']['budget_wh'])

    def test_real_payload_command_and_all_three_consumers_share_model(self):
        rig = TemplateRig('2026-12-21T03:00:00+01:00')
        rig.states.update({'sensor.batterie_soc': '90', 'input_number.night_consumption_rate_wh': '320',
                           'input_number.day_consumption_rate_wh': '1280',
                           'sensor.solcast_pv_forecast_zeitpunkt_letzter_api_abruf': rig.when.isoformat()})
        rows = forecast(rig.when, 12)
        rig.attrs[('sensor.solcast_pv_forecast_prognose_heute', 'detailedForecast')] = rows
        result = attach_year_model(rig)
        for sensor, key in [('Battery Optimization Data', 'battery'),
                            ('Battery Surplus Discharge Power', 'surplus'),
                            ('Car Boost Energy Budget', 'car')]:
            debug = ast.literal_eval(rig.render(SENSORS[sensor]['attributes']['calculation_data']))
            self.assertTrue(debug['model_valid'])
            shared = 'bridge_hours' if key == 'battery' else ('hours_to_solar' if key == 'surplus' else 'overnight_need_wh')
            self.assertEqual(debug[shared], result[key][shared])

    def test_missing_stale_or_future_model_disables_optional_actions(self):
        for stamp in ('unknown', '2026-10-17T23:00:00+02:00', '2026-10-18T01:00:00+02:00'):
            rig = TemplateRig('2026-10-18T00:00:00+02:00')
            rig.states['sensor.reutlingen_energy_model'] = stamp
            self.assertEqual(float(rig.render(SENSORS['Battery Optimization Data']['state'])), 15)
            self.assertEqual(float(rig.render(SENSORS['Battery Surplus Discharge Power']['state'])), 0)
            self.assertEqual(float(rig.render(SENSORS['Car Boost Energy Budget']['state'])), 0)
            debug = ast.literal_eval(rig.render(SENSORS['Battery Optimization Data']['attributes']['calculation_data']))
            self.assertEqual(debug['bridge_type'], 'model_unavailable')

    def test_new_log_keeps_raw_balcony_validity_instead_of_wrapper_zero(self):
        rig = TemplateRig()
        logger = next(a for a in AUTOMATIONS if a.get('id') == 'battery_algorithm_logging' or a.get('description') == 'Logs full algorithm state as JSON for offline analysis')
        message = logger['action'][0]['data']['message']
        rig.env.globals['trigger'] = SimpleNamespace(id='periodic')
        rig.attrs[('sensor.battery_optimization_data', 'calculation_data')] = ast.literal_eval(
            rig.render(SENSORS['Battery Optimization Data']['attributes']['calculation_data']))
        rig.states.update({'sensor.inverter_power': '123', 'sensor.reading_energy_main_meter': '200',
                           'sensor.reading_energy_inverter_ac_output': '300', 'sensor.wattpilot_charging_power': '0'})
        record = json.loads(rig.render(message))
        self.assertEqual(record['inverter']['balcony_w'], 123)
        self.assertTrue(record['inverter']['power_valid'])
        for entity in ('sensor.inverter_power', 'sensor.reading_energy_main_meter',
                       'sensor.reading_energy_inverter_ac_output', 'sensor.wattpilot_charging_power'):
            original = rig.states[entity]
            for bad in ('unknown', 'nan', 'inf'):
                rig.states[entity] = bad
                record = json.loads(rig.render(message))
                if entity == 'sensor.inverter_power':
                    self.assertTrue(record['inverter']['power_valid'])
                    self.assertFalse(record['inverter']['balcony_valid'])
                else:
                    self.assertFalse(record['inverter']['power_valid'])
            rig.states[entity] = original

    def test_boost_start_window_tracks_seasonal_daylight_and_blocks_midnight(self):
        for when, expected in [('2026-06-21T16:00:00+02:00', True),
                               ('2026-12-21T16:00:00+01:00', False),
                               ('2026-06-21T00:00:00+02:00', False)]:
            rig = TemplateRig(when)
            model = attach_year_model(rig)
            rig.states.update({'input_boolean.car_smart_charging_on': 'on',
                               'input_boolean.battery_charging_active': 'off',
                               'binary_sensor.wattpilot_33175380_stecker': 'on',
                               'select.wattpilot_charging_mode': 'Eco',
                               'sensor.batterie_soc': '90',
                               'sensor.car_boost_energy_budget': '3000'})
            rig.attrs[('sensor.car_boost_energy_budget', 'floor_soc')] = 40
            self.assertEqual(rig.truth(rig.render(SENSORS['Car Boost Viable']['state'])), expected)
