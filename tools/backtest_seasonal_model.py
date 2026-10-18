"""Rolling-origin overnight demand validation; private inputs, aggregate output.

Each forecast sees only records strictly before that night's 22:00. October
observations may inform later October nights, as they would in production.
This is demand validation, not a PV replay or financial savings simulation.
"""
import argparse
from collections import defaultdict
from datetime import datetime, time, timedelta
import json
from pathlib import Path
from statistics import mean

from seasonal_model import Demand, ZONE, UTC, instant, iter_log_records, number


def backtest(records, start='2026-07-01'):
    nights = defaultdict(dict)
    for r in records:
        try:
            t = instant(r['ts'])
            local = t.astimezone(ZONE)
            if r.get('trigger') != 'periodic' or local.hour not in (22, 23, 0, 1, 2, 3, 4) or local.minute % 15:
                continue
            i, car = r['inverter'], r['car']
            vals = [number(i.get('grid_w'), None, -100000, 100000),
                    number(i.get('ac_w'), None, -100000, 100000),
                    number(car.get('wallbox_w'), None, 0, 50)]
            if None in vals or not 0 < vals[0] + vals[1] - vals[2] <= 15000:
                continue
            night = (local - timedelta(days=local.hour < 5)).date()
            if night.isoformat() < start:
                continue
            nights[night][int(t.timestamp()) // 900] = vals[0] + vals[1] - vals[2]
        except (TypeError, ValueError, KeyError):
            continue
    groups = defaultdict(list)
    for day, slots in sorted(nights.items()):
        begin = datetime.combine(day, time(22), ZONE).astimezone(UTC)
        end = datetime.combine(day + timedelta(days=1), time(5), ZONE).astimezone(UTC)
        expected = set(range(int(begin.timestamp()) // 900, int(end.timestamp()) // 900))
        if set(slots) != expected:
            continue
        demand = Demand(begin, dict(night_rate=320, day_rate=1280), records)
        actual = sum(slots.values()) / 4
        groups[f'{day:%Y-%m}'].append((320 * (end - begin).total_seconds() / 3600 - actual,
                                     demand.energy(begin, end) - actual,
                                     demand.energy(begin, end, True) - actual))
    return {month: {'nights': len(rows), **{
        name: {'mae_wh': round(mean(abs(r[index]) for r in rows), 2),
               'bias_wh': round(mean(r[index] for r in rows), 2),
               'underforecast_over_700_wh': sum(r[index] < -700 for r in rows)}
        for index, name in enumerate(('flat_320_w', 'adaptive_mean', 'adaptive_risk'))}}
        for month, rows in groups.items()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('logs', nargs='+', type=Path)
    parser.add_argument('--start', default='2026-07-01')
    args = parser.parse_args()
    print(json.dumps(backtest(list(iter_log_records(args.logs)), args.start), indent=2))
