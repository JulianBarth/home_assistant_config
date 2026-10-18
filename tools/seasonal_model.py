"""Year-round Reutlingen household/PV model; standard library, no hardware writes.

Inputs arrive as base64 JSON from HA. Historical logs are read-only, and only
past observations are used. Astronomy is a daylight boundary, never a PV forecast.
See YEAR_ROUND_MODEL.md for assumptions, sources and validation limitations.
"""
import argparse
import base64
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
import gzip
import json
import math
from pathlib import Path
from statistics import mean, quantiles
from zoneinfo import ZoneInfo

ZONE = ZoneInfo('Europe/Berlin')
UTC = timezone.utc
LATITUDE = 48 + 29 / 60 + 34 / 3600
LONGITUDE = 9 + 12 / 60 + 45 / 3600
VERSION = 'reutlingen-v1'
STEP = timedelta(minutes=15)


def number(value, default, low, high):
    try:
        result = float(value)
        return result if math.isfinite(result) and low <= result <= high else default
    except (TypeError, ValueError):
        return default


def instant(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError('An offset-aware timestamp is required')
    return value.astimezone(UTC)


def solar_day(day):
    """NOAA fractional-year approximation at Reutlingen city coordinates."""
    year_days = (date(day.year + 1, 1, 1) - date(day.year, 1, 1)).days
    g = 2 * math.pi / year_days * (day.timetuple().tm_yday - 1)
    eq = 229.18 * (.000075 + .001868 * math.cos(g) - .032077 * math.sin(g)
                   - .014615 * math.cos(2 * g) - .040849 * math.sin(2 * g))
    dec = (.006918 - .399912 * math.cos(g) + .070257 * math.sin(g)
           - .006758 * math.cos(2 * g) + .000907 * math.sin(2 * g)
           - .002697 * math.cos(3 * g) + .00148 * math.sin(3 * g))
    lat = math.radians(LATITUDE)
    cosine = ((math.cos(math.radians(90.833)) / (math.cos(lat) * math.cos(dec)))
              - math.tan(lat) * math.tan(dec))
    angle = math.degrees(math.acos(max(-1, min(1, cosine))))
    midnight = datetime.combine(day, time(), UTC)
    noon = midnight + timedelta(minutes=720 - 4 * LONGITUDE - eq)
    rising = noon - timedelta(minutes=4 * angle)
    setting = noon + timedelta(minutes=4 * angle)
    return {'sunrise': rising, 'noon': noon, 'sunset': setting,
            'daylight_hours': (setting - rising).total_seconds() / 3600}


def iter_log_records(paths):
    """Skip corrupt legacy lines; expose rejection counts via training coverage."""
    decoder = json.JSONDecoder()
    for path in paths:
        try:
            opener = gzip.open if str(path).endswith('.gz') else open
            with opener(path, 'rt') as stream:
                for line in stream:
                    rest = line.strip()
                    while rest:
                        try:
                            record, end = decoder.raw_decode(rest)
                        except ValueError:
                            break
                        if isinstance(record, dict):
                            yield record
                        rest = rest[end:].strip()
        except (OSError, EOFError):
            continue


def load_history_paths(root, when):
    # Read only the current log and monthly archives intersecting 42 past days.
    paths = [root / 'battery_algorithm.log']
    for offset in range(43):
        d = when.astimezone(ZONE).date() - timedelta(days=offset)
        path = root / f'battery_algorithm-{d:%Y-%m}.log.gz'
        if path not in paths and path.exists():
            paths.append(path)
    return paths


class Demand:
    def __init__(self, when, settings, records=()):
        self.when = instant(when)
        self.night = number(settings.get('night_rate'), 320, 50, 600)
        self.day = number(settings.get('day_rate'), 1280, 200, 2000)
        self.weekday_wake = number(settings.get('weekday_wake'), 5.5, 0, 12)
        self.weekend_wake = number(settings.get('weekend_wake'), 7.5, 0, 12)
        self.sleep = number(settings.get('sleep_hour'), 22, 12, 24)
        self.buckets = defaultdict(list)
        self.days = defaultdict(set)
        self.accepted = 0
        seen = set()
        for r in records:
            try:
                t = instant(r['ts'])
                local = t.astimezone(ZONE)
                if r.get('trigger') != 'periodic' or not self.when - timedelta(days=42) <= t < self.when:
                    continue
                # No future leakage and no repeated weighting of event/duplicate records.
                slot = int(t.timestamp()) // 900
                if slot in seen or local.minute % 15:
                    continue
                i, car = r['inverter'], r['car']
                if not isinstance(i, dict) or not isinstance(car, dict):
                    continue
                if 'power_valid' in i and i['power_valid'] is not True:
                    continue
                vals = [number(i.get('grid_w'), None, -100000, 100000),
                        number(i.get('ac_w'), None, -100000, 100000),
                        number(car.get('wallbox_w'), None, 0, 50)]
                if None in vals:
                    continue
                g, ac, ev = vals
                # Daytime learning needs the complete, signed balance and raw validity.
                daylight = solar_day(local.date())
                dark = t < daylight['sunrise'] or t >= daylight['sunset']
                balcony = number(i.get('balcony_w'), None, 0, 10000)
                balcony_valid = i.get('balcony_valid', i.get('power_valid', False)) is True
                if not dark and (balcony is None or not balcony_valid):
                    continue
                load = g + ac + (balcony or 0) - ev
                if not 0 < load <= 15000:
                    continue
                seen.add(slot)
                key = (local.weekday() >= 5, local.hour)
                self.buckets[key].append(load)
                self.days[key].add(local.date())
                self.accepted += 1
            except (KeyError, TypeError, ValueError):
                continue

    def wake(self, day):
        return self.weekend_wake if day.weekday() >= 5 else self.weekday_wake

    def watts(self, when, risk=False):
        local = when.astimezone(ZONE)
        hour = local.hour + local.minute / 60
        prior = self.night if hour < self.wake(local.date()) or hour >= self.sleep else self.day
        key = (local.weekday() >= 5, local.hour)
        values = self.buckets.get(key, [])
        # At least 4 distinct days; shrink estimates until 80 samples (20 h).
        if len(self.days.get(key, ())) < 4 or len(values) < 16:
            return prior
        weight = min(.9, len(values) / (len(values) + 40))
        observed = mean(values)
        if risk:
            observed = max(observed, quantiles(values, n=4, method='inclusive')[2])
        # Configured demand remains the prior; no guessed winter/heating uplift.
        return max(50, min(15000, prior * (1 - weight) + observed * weight))

    def energy(self, start, end, risk=False):
        cursor, total = instant(start), 0.0
        end = instant(end)
        while cursor < end:
            # UTC stepping accounts for real 23/25-hour days and repeated hours.
            boundary = datetime.fromtimestamp((int(cursor.timestamp()) // 900 + 1) * 900, UTC)
            stop = min(end, boundary)
            total += self.watts(cursor, risk) * (stop - cursor).total_seconds() / 3600
            cursor = stop
        return total


class PV:
    def __init__(self, when, settings):
        self.when = instant(when)
        self.slots = {}
        self.status = 'missing_or_stale'
        self.p10_slots = 0
        confidence = number(settings.get('solar_confidence_pct'), 70, 0, 100) / 100
        try:
            age = (self.when - instant(settings.get('forecast_updated_at'))).total_seconds() / 3600
            if not 0 <= age <= 18:
                return
        except (TypeError, ValueError):
            return
        conflicts = set()
        rows = settings.get('forecast')
        rows = rows if isinstance(rows, list) else []
        for r in rows[:300]:
            try:
                start = instant(r['period_start'])
                if start.minute not in (0, 30) or start.second or not self.when - timedelta(days=1) <= start <= self.when + timedelta(days=3):
                    continue
                median = number(r.get('pv_estimate'), None, 0, 100)
                if median is None:
                    continue
                low = number(r.get('pv_estimate10'), None, 0, median)
                if 'pv_estimate10' in r and low is None:
                    continue
                watts = min(low, median * confidence) * 1000 if low is not None else median * min(confidence, .7) * 1000
                if start in self.slots and self.slots[start] != watts:
                    conflicts.add(start)
                else:
                    self.slots[start] = watts
                    self.p10_slots += low is not None
            except (KeyError, TypeError, ValueError):
                continue
        for start in conflicts:
            self.slots.pop(start, None)
        if self.slots:
            self.status = 'fresh_p10' if self.p10_slots else 'fresh_discounted_p50'

    def watts(self, when):
        t = instant(when)
        slot = datetime.fromtimestamp(int(t.timestamp()) // 1800 * 1800, UTC)
        # Astronomical darkness overrides a malformed forecast with night output.
        sun = solar_day(t.astimezone(ZONE).date())
        if t < sun['sunrise'] or t >= sun['sunset']:
            return 0.0
        return self.slots.get(slot, 0.0)

    def energy(self, start, end):
        cursor, total = instant(start), 0.0
        end = instant(end)
        while cursor < end:
            stop = min(end, datetime.fromtimestamp((int(cursor.timestamp()) // 900 + 1) * 900, UTC))
            sun = solar_day(cursor.astimezone(ZONE).date())
            for boundary in (sun['sunrise'], sun['sunset']):
                if cursor < boundary < stop:
                    stop = boundary
            total += self.watts(cursor) * (stop - cursor).total_seconds() / 3600
            cursor = stop
        return total

    def recovery(self, start, demand):
        """First full hour with forecast PV covering conservative household load."""
        start = instant(start)
        cursor = datetime.fromtimestamp(math.ceil(start.timestamp() / 1800) * 1800, UTC)
        limit = start + timedelta(hours=24)
        while cursor + timedelta(hours=1) <= limit:
            sunset = solar_day(cursor.astimezone(ZONE).date())['sunset']
            if cursor + timedelta(hours=1) <= sunset and all(self.watts(cursor + STEP * i) >= demand.watts(cursor + STEP * i, True)
                   for i in range(4)):
                return cursor
            cursor += timedelta(minutes=30)
        return None


def deficit(demand, pv, start, end, risk=False, charge_efficiency=1, discharge_efficiency=1):
    """Initial storage required: maximum cumulative net demand before recovery."""
    cursor, running, peak = instant(start), 0.0, 0.0
    end = instant(end)
    while cursor < end:
        stop = min(end, datetime.fromtimestamp((int(cursor.timestamp()) // 900 + 1) * 900, UTC))
        net = demand.energy(cursor, stop, risk) - pv.energy(cursor, stop)
        running += net / discharge_efficiency if net >= 0 else net * charge_efficiency
        peak = max(peak, running)
        cursor = stop
    return peak


def safe_loan(demand, pv, start, end, initial, capacity, minimum, upper, charge_efficiency, discharge_efficiency):
    """Cap a storage-side loan using a finite-capacity forecast trajectory."""
    changes = []
    cursor, end = instant(start), instant(end)
    while cursor < end:
        stop = min(end, datetime.fromtimestamp((int(cursor.timestamp()) // 900 + 1) * 900, UTC))
        net = pv.energy(cursor, stop) - demand.energy(cursor, stop, True)
        changes.append(net * charge_efficiency if net >= 0 else net / discharge_efficiency)
        cursor = stop

    def safe(loan):
        stored = initial - loan
        if stored < minimum:
            return False
        for change in changes:
            stored = min(capacity, stored + change)
            if stored < minimum:
                return False
        return True

    if upper <= 0 or not safe(0):
        return 0
    if safe(upper):
        return upper
    low, high = 0.0, upper
    for _ in range(16):
        mid = (low + high) / 2
        if safe(mid):
            low = mid
        else:
            high = mid
    return low


def build_model(settings, records=()):
    when = instant(settings['when'])
    local = when.astimezone(ZONE)
    demand, pv = Demand(when, settings, records), PV(when, settings)
    capacity = number(settings.get('capacity_wh'), 10000, 1000, 50000)
    reserve = number(settings.get('reserve_soc'), 15, 1, 100)
    soc = number(settings.get('soc'), 0, 0, 100)
    margin = number(settings.get('safety_margin_wh'), 700, 0, 10000)
    floor = number(settings.get('car_floor_soc'), max(40, reserve), reserve, 100)
    # Engineering assumptions consistent with ~90% round-trip efficiency;
    # these are not estimates fitted from the household logs.
    charge_eff = number(settings.get('charge_efficiency'), .95, .5, 1)
    discharge_eff = number(settings.get('discharge_efficiency'), .95, .5, 1)
    today = solar_day(local.date())
    tomorrow = solar_day(local.date() + timedelta(days=1))
    recovery = pv.recovery(when, demand)
    end = recovery if recovery is not None else when + timedelta(hours=24)
    bridge_load = demand.energy(when, end)
    bridge_pv = pv.energy(when, end)
    need = min(capacity, deficit(demand, pv, when, end, False, charge_eff, discharge_eff))
    # Future sunshine never removes storage required BEFORE that sunshine arrives.
    target = min(100, reserve + need / capacity * 100)
    upcoming_day = end.astimezone(ZONE).date() if recovery else (local.date() + timedelta(days=when >= today['sunset']))
    sun = solar_day(upcoming_day)
    low_solar_threshold = number(settings.get('low_solar_threshold_wh'), 3000, 0, 100000)
    low_solar_day = recovery is None or pv.energy(sun['sunrise'], sun['sunset']) < low_solar_threshold
    solar_surplus = max(0, pv.energy(max(when, sun['sunrise']), sun['sunset'])
                        - demand.energy(max(when, sun['sunrise']), sun['sunset'], True))
    max_grid = max(target, 100 - solar_surplus * charge_eff / capacity * 100)
    remaining_today = pv.energy(when, today['sunset'])
    house_until_sunset = demand.energy(when, today['sunset'], True)
    refill_surplus = max(0, remaining_today - house_until_sunset)
    next_recovery = pv.recovery(max(when, today['sunset']), demand)
    night_start = max(when, today['sunset'])
    night_end = next_recovery or night_start + timedelta(hours=24)
    overnight = deficit(demand, pv, night_start, night_end, True, charge_eff, discharge_eff)
    # Unlearned hours use the conservative configured rates. Margin stays explicit.
    needed_sunset = reserve / 100 * capacity + overnight + margin
    bridge_risk = deficit(demand, pv, when, end, True, charge_eff, discharge_eff)
    bridge_room = soc / 100 * capacity - reserve / 100 * capacity - bridge_risk - margin
    budget = max(0, min((soc - floor) / 100 * capacity,
                        soc / 100 * capacity + refill_surplus * charge_eff - needed_sunset,
                        refill_surplus * charge_eff, bridge_room))
    budget = safe_loan(demand, pv, when, night_end, soc / 100 * capacity,
                       capacity, reserve / 100 * capacity + margin, budget,
                       charge_eff, discharge_eff) if budget > 0 else 0
    # Exposed loan and extra-discharge budgets are AC-deliverable energy;
    # SOC, capacity, required storage and margins are storage-side Wh.
    budget = math.floor(budget * discharge_eff)
    active = when < today['sunrise'] or when >= today['sunset']
    required = bridge_risk
    available = max(0, (soc - reserve) / 100 * capacity)
    recovery_ok = recovery is not None and solar_surplus * charge_eff >= capacity * .8
    surplus = max(0, available - required - margin) if active and recovery_ok else 0
    forecast_day = 'tomorrow' if when >= today['sunset'] else 'today'
    scalar = number(settings.get(f'{forecast_day}_solar_kwh'), 0, 0, 1000) * 1000
    hour = lambda t: t.astimezone(ZONE).hour + t.astimezone(ZONE).minute / 60
    battery = {
        'current_hour': hour(when), 'wake_hour': demand.wake(upcoming_day),
        'is_weekend': upcoming_day.weekday() >= 5,
        'sunrise_hour': hour(sun['sunrise']),
        'solar_start': hour(end) if recovery else 24,
        'solar_recovery_at': recovery.astimezone(ZONE).isoformat() if recovery else None,
        'solar_noon_hour': hour(sun['noon']),
        'bridge_hours': (end - when).total_seconds() / 3600,
        'bridge_type': 'forecast_recovery' if recovery else 'no_verified_recovery_24h',
        'bridge_consumption_wh': round(bridge_load),
        'expected_solar_wh': round(scalar), 'effective_solar_wh': round(bridge_pv),
        'usable_solar_wh': round(bridge_pv), 'energy_deficit_wh': round(need),
        'is_low_solar_day': low_solar_day,
        'max_grid_target': min(100, max_grid), 'calculated_target': target,
        'current_stored_wh': max(0, (soc - reserve) / 100 * capacity),
    }
    return {
        'version': VERSION, 'generated_at': when.isoformat(), 'inputs_ready': 0 < soc <= 100,
        'location': 'Reutlingen', 'latitude': LATITUDE, 'longitude': LONGITUDE,
        'timezone': 'Europe/Berlin', 'forecast_status': pv.status,
        'charge_efficiency': charge_eff, 'discharge_efficiency': discharge_eff,
        'accepted_history_samples': demand.accepted,
        'learned_hour_groups': sum(len(demand.days[k]) >= 4 and len(v) >= 16 for k, v in demand.buckets.items()),
        'calendar': {label: {k: (v.astimezone(ZONE).isoformat() if isinstance(v, datetime) else round(v, 3))
                             for k, v in data.items()}
                     for label, data in [('today', today), ('tomorrow', tomorrow)]},
        'battery': battery,
        'surplus': {'active_window': active, 'hours_to_solar': (end - when).total_seconds() / 3600,
                    'required_until_solar_wh': round(required), 'safety_margin_wh': margin,
                    'available_above_reserve_wh': available, 'surplus_wh': math.floor(surplus * discharge_eff),
                    'discharge_efficiency': discharge_eff,
                    'expected_solar_wh': round(scalar), 'usable_solar_wh': round(solar_surplus),
                    'solar_recovery_ok': recovery_ok, 'bridge_type': battery['bridge_type']},
        'car': {'remaining_solar_wh': round(remaining_today), 'usable_solar_wh': round(remaining_today),
                'house_until_sunset_wh': round(house_until_sunset), 'solar_surplus_wh': round(refill_surplus),
                'overnight_need_wh': round(overnight), 'needed_at_sunset_wh': round(needed_sunset),
                'constraint_bridge_wh': round(bridge_room),
                'floor_soc': floor, 'soc': soc, 'budget_wh': round(budget),
                'decision_reason': 'Conservative forecast and overnight reserve' if budget else 'Insufficient verified solar or reserve'},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload', help='Base64-encoded HA input JSON')
    parser.add_argument('--history-root', type=Path)
    parser.add_argument('--calendar-year', type=int)
    args = parser.parse_args()
    if args.calendar_year:
        print(json.dumps([{str(day): {k: v.astimezone(ZONE).isoformat() if isinstance(v, datetime) else v
                                     for k, v in solar_day(day).items()}}
                          for month in range(1, 13)
                          for day in [date(args.calendar_year, month, 21)]], indent=2))
        return
    settings = json.loads(base64.b64decode(args.payload, validate=True))
    history = iter_log_records(load_history_paths(args.history_root, instant(settings['when']))) if args.history_root else ()
    print(json.dumps(build_model(settings, history), allow_nan=False, separators=(',', ':')))


if __name__ == '__main__':
    main()
