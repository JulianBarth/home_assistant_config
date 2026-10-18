"""Historical calibration, integration and forecast-boundary regressions."""
from datetime import datetime, timedelta
import importlib.util
from pathlib import Path
import tempfile
import unittest
from test_battery_control import ROOT

spec = importlib.util.spec_from_file_location('analyze_usage', ROOT / 'tools/analyze_usage.py')
usage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usage)


class HistoricalInputTests(unittest.TestCase):
    def record(self, **changes):
        record = {'trigger': 'periodic', 'ts': '2026-09-01T01:00:00+02:00',
                  'inverter': {'grid_w': 10, 'ac_w': 200}, 'car': {'wallbox_w': 0, 'house_w': 9999}}
        record.update(changes)
        return record

    def test_uses_signed_balance_instead_of_biased_logged_house_power(self):
        self.assertEqual(usage.sample(self.record())[1], 210)
        self.assertIsNone(usage.sample(self.record(inverter={'grid_w': -500, 'ac_w': 200})))

    def test_excludes_daylight_ev_corruption_and_event_samples(self):
        for change in ({'ts': '2026-09-01T12:00:00+02:00'}, {'car': {'wallbox_w': 11000}},
                       {'ts': '2026-09-01T01:00:00'},
                       {'trigger': 'mode_changed'}, {'inverter': {'grid_w': float('nan'), 'ac_w': 200}}):
            self.assertIsNone(usage.sample(self.record(**change)))

    def test_calibration_deduplicates_slots_and_keeps_holdout_out_of_fit(self):
        rows = []
        for day in range(33):
            start = datetime.fromisoformat('2026-07-01T22:00:00+02:00') + timedelta(days=day)
            for slot in range(28):
                when = start + timedelta(minutes=15 * slot)
                rows.append(self.record(ts=when.isoformat()))
        # A wholly separate October night has a very different actual load.
        for slot in range(28):
            when = datetime.fromisoformat('2026-10-01T22:00:00+02:00') + timedelta(minutes=15 * slot)
            rows.append(self.record(ts=when.isoformat(), inverter={'grid_w': 1000, 'ac_w': 200}))
        rows.append(rows[-1])
        result = usage.analyze(rows)
        self.assertEqual(set(result['profile_w'].values()), {210})
        self.assertEqual(result['counts']['duplicate_slots'], 1)
        self.assertEqual(result['holdout']['complete_nights'], 1)
        self.assertEqual(result['holdout']['profile']['bias_wh'], -6930)

    def test_insufficient_training_coverage_is_rejected(self):
        with self.assertRaises(ValueError):
            usage.analyze([self.record()])

    def test_recovers_legacy_concatenation_and_reports_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'log'
            path.write_text('{"a":1}{"b":2}\n')
            self.assertEqual(list(usage.read_records([path])), [{'a': 1}, {'b': 2}])
            path.write_text('{"a":1}BROKEN\n')
            with self.assertRaises(ValueError):
                list(usage.read_records([path]))
