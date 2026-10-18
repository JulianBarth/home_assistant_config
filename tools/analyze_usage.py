"""Offline calibration of quiet-night loads from private HA algorithm logs.

No network, recorder changes or hardware writes. Pass .log/.gz files explicitly.
Prints aggregates only; never publishes raw household records.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import gzip
import json
import math
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

ZONE = ZoneInfo('Europe/Berlin')
HOURS = (22, 23, 0, 1, 2, 3, 4)


def read_records(paths):
    """Recover legacy adjacent JSON objects, fail visibly on corrupt input."""
    decoder = json.JSONDecoder()
    for path in paths:
        opener = gzip.open if str(path).endswith('.gz') else open
        with opener(path, 'rt') as stream:
            for line_no, line in enumerate(stream, 1):
                rest = line.strip()
                while rest:
                    try:
                        record, end = decoder.raw_decode(rest)
                    except ValueError as exc:
                        raise ValueError(f'{path}:{line_no}: invalid JSON') from exc
                    if not isinstance(record, dict):
                        raise ValueError(f'{path}:{line_no}: expected object')
                    yield record
                    rest = rest[end:].strip()


def sample(record):
    """Unclamped signed balance, only without EV or daylight ambiguity."""
    try:
        when = datetime.fromisoformat(record['ts'])
        if when.tzinfo is None:
            return None
        when = when.astimezone(ZONE)
        if record.get('trigger') != 'periodic' or when.hour not in HOURS:
            return None
        values = [record['inverter']['grid_w'], record['inverter']['ac_w'],
                  record['car']['wallbox_w']]
        if any(isinstance(v, bool) or not isinstance(v, (int, float))
               or not math.isfinite(v) for v in values):
            return None
        grid, ac, ev = values
        load = grid + ac - ev
        if not 0 <= ev <= 50 or not 0 < load <= 15000:
            return None
        return when, load
    except (KeyError, TypeError, ValueError):
        return None


def analyze(records, start='2026-07-01', cutoff='2026-10-01', baseline=320):
    buckets = defaultdict(list)
    nights = defaultdict(dict)
    seen = set()
    counts = Counter()
    for record in records:
        counts['records'] += 1
        value = sample(record)
        if value is None:
            continue
        when, load = value
        stamp = when.isoformat()[:10]
        if stamp < start or when.minute % 15:
            continue
        slot = when.replace(second=0, microsecond=0).isoformat()
        if slot in seen:
            counts['duplicate_slots'] += 1
            continue
        seen.add(slot)
        counts['accepted_night_samples'] += 1
        if stamp < cutoff:
            buckets[when.hour].append(load)
        night = (when - timedelta(days=when.hour < 5)).date().isoformat()
        nights[night][(when.hour, when.minute)] = load
    if any(len(buckets[h]) < 100 for h in HOURS):
        raise ValueError('Insufficient training coverage: need 100 samples per hour')
    profile = {h: round(mean(buckets[h])) for h in HOURS}
    report = {'counts': dict(counts), 'training_start': start, 'holdout_start': cutoff,
              'baseline_w': baseline, 'profile_w': profile,
              'training_samples_by_hour': {h: len(buckets[h]) for h in HOURS}}
    expected = {(h, m) for h in HOURS for m in (0, 15, 30, 45)}
    for split in ('training', 'holdout'):
        errors = {'flat': [], 'profile': []}
        for night, slots in sorted(nights.items()):
            next_date = (datetime.fromisoformat(night) + timedelta(days=1)).date().isoformat()
            eligible = ((start <= night and next_date < cutoff)
                        if split == 'training' else night >= cutoff)
            if not eligible or set(slots) != expected:
                continue
            errors['flat'].append(sum(baseline - v for v in slots.values()) / 4)
            errors['profile'].append(sum(profile[h] - v for (h, _), v in slots.items()) / 4)
        if not errors['flat']:
            raise ValueError(f'No complete nights in {split}')
        report[split] = {'complete_nights': len(errors['flat'])}
        for model, values in errors.items():
            report[split][model] = {'mae_wh': round(mean(map(abs, values)), 2),
                                    'bias_wh': round(mean(values), 2)}
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('logs', nargs='+', type=Path)
    parser.add_argument('--start', default='2026-07-01')
    parser.add_argument('--cutoff', default='2026-10-01')
    parser.add_argument('--baseline', type=float, default=320)
    args = parser.parse_args()
    print(json.dumps(analyze(read_records(args.logs), args.start, args.cutoff,
                             args.baseline), indent=2))
