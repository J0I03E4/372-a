"""
Aggregates the per-tech 372-A data.json (from ../372a-dashboard/data.json)
into a single whole-market rollup -- no tech names, just totals and
volume-weighted rates. Writes ./data.json in this folder.
"""
import json
import os

SRC = os.path.join(os.path.dirname(__file__), '..', '372a-dashboard', 'data.json')
DST = os.path.join(os.path.dirname(__file__), 'data.json')

with open(SRC, encoding='utf-8') as f:
    src = json.load(f)


def weighted_avg(rows, value_key, weight_key):
    """Volume-weighted mean of value_key, weighted by weight_key. Skips rows
    where the value is null (can't blindly average away missing samples)."""
    num, den = 0.0, 0.0
    for r in rows:
        v, w = r.get(value_key), r.get(weight_key, 0)
        if v is not None and w:
            num += v * w
            den += w
    return round(num / den, 2) if den else None


def agg_period(rows):
    total_wos = sum(r['wos'] for r in rows)
    total_hp = sum(r['hp_wos'] for r in rows)
    return {
        'wos': total_wos,
        'wos_1p': sum(r['wos_1p'] for r in rows),
        'wos_3p': sum(r['wos_3p'] for r in rows),
        'hp_wos': total_hp,
        'dtc': weighted_avg(rows, 'dtc', 'wos'),
        'dtc_hp': weighted_avg(rows, 'dtc_hp', 'hp_wos'),
        'response': weighted_avg(rows, 'response', 'wos'),
        'self_perf': weighted_avg(rows, 'self_perf', 'wos'),
        'ftf': weighted_avg(rows, 'ftf', 'wos'),
        'sla_under': sum(r['sla_under'] for r in rows),
        'sla_over': sum(r['sla_over'] for r in rows),
        'sla_missing': sum(r['sla_missing'] for r in rows),
        'recalls': sum(r['recalls'] for r in rows),
        'stores_sum': sum(r['stores'] for r in rows),
        'n_techs': len(rows),
    }


periods = {p: agg_period(rows) for p, rows in src['periods'].items()}

# NOTE: the old daily (day-by-day) whole-market trend used to live here, but
# the dashboard now shows a 3-month trend (reusing `periods` above) instead
# of a 30-day daily trend, so it's no longer computed or shipped in the JSON.

out = {
    'periods': periods,
    'goals': src['goals'],
    'meta': {
        'region': src['meta']['region'],
        'refresh': src['meta']['refresh'],
        'source': src['meta']['source'],
        'n_techs': src['meta']['n_techs'],
        'period_labels': src['meta'].get('period_labels', {}),
        'notes': src['meta']['notes'] + [
            'This is a whole-market rollup: all technicians in 372-A are '
            'combined into one aggregate. No individual names or per-tech '
            'breakdowns are shown -- rate metrics (DTC, RESPONSE, SELF PERF, '
            'FTF) are volume-weighted by work-order count, not simple averages.',
        ],
    },
}

with open(DST, 'w', encoding='utf-8') as f:
    json.dump(out, f)

print('wrote', DST)
print('30d totals:', json.dumps(periods['30'], indent=2))
