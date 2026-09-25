"""
refresh_and_publish.py -- standalone daily refresher for the 372-A
whole-market dashboard. No LLM agent involved: this pulls straight from
BigQuery via the `bq` CLI, using the corrected query logic validated during
this project's original build-out (see README.md for the full audit trail
of why each formula looks the way it does).

Unlike the original build process, this computes every rate metric
(DTC, RESPONSE, SELF PERF, FTF) as a single direct pooled aggregate across
all matching work orders market-wide, rather than a weighted average of
per-tech numbers -- simpler, less error-prone, and mathematically at least
as correct.

USAGE:
    python refresh_and_publish.py            # pull + rebuild + git commit
    python refresh_and_publish.py --push     # also `git push` if a remote exists
    python refresh_and_publish.py --no-git   # pull + rebuild only, skip git entirely

IMPORTANT -- this is NOT safe to run as a fully unattended scheduled task
yet. `bq`/`gcloud` here are authenticated with Joseph's personal OAuth
session, which periodically expires and requires an interactive browser
login (`gcloud auth login`) to refresh -- something a background Scheduled
Task cannot do. If the token has expired, this script will fail loudly
(a clear RuntimeError) rather than silently publishing stale or broken
data. To make this truly unattended, provision a service account with
read access to re-ods-explorer and point `bq`/`gcloud` at its key file
instead -- ask in #mint-support or your GCP access channel.
"""
import argparse
import json
import shutil
import subprocess
import sys
from datetime import date, timedelta

BQ_CMD = shutil.which('bq') or 'bq'  # resolves to bq.cmd on Windows; subprocess needs the real path
sys.stdout.reconfigure(line_buffering=True)  # keep our prints in order relative to subprocess output

STORES = (1334, 1381, 1646, 2112, 2482, 2766, 2767, 5428, 5332, 5349, 3846, 5257)
STORE_LIST = ", ".join(str(s) for s in STORES)
WO_TABLE = "`re-ods-explorer.us_re_fm_prod.fsai_workorders`"

QUERY_TEMPLATE = """
SELECT
  COUNT(*) AS wos,
  COUNTIF(COALESCE(third_party_assigned,'') = 'No') AS wos_1p,
  COUNTIF(COALESCE(third_party_assigned,'') = 'Yes') AS wos_3p,
  COUNTIF(STARTS_WITH(COALESCE(priority_name,''),'P1-') OR STARTS_WITH(COALESCE(priority_name,''),'P2-')) AS hp_wos,
  ROUND(AVG(CASE WHEN status_name='COMPLETED' THEN DATETIME_DIFF(completion_date, call_date, MINUTE)/1440.0 END), 2) AS dtc,
  ROUND(AVG(CASE WHEN status_name='COMPLETED' AND (STARTS_WITH(COALESCE(priority_name,''),'P1-') OR STARTS_WITH(COALESCE(priority_name,''),'P2-')) THEN DATETIME_DIFF(completion_date, call_date, MINUTE)/1440.0 END), 2) AS dtc_hp,
  ROUND(100 * SAFE_DIVIDE(COUNTIF(sla_response_compliance_reassigned='Under SLA Response'), COUNT(*)), 2) AS response,
  ROUND(100 * SAFE_DIVIDE(COUNTIF(COALESCE(third_party_assigned,'')='No'), COUNT(*)), 2) AS self_perf,
  ROUND(100 * SAFE_DIVIDE(COUNTIF(first_time_fix_compliance='Yes First Time Fix'), COUNT(*)), 2) AS ftf,
  COUNTIF(sla_response_compliance_reassigned='Under SLA Response') AS sla_under,
  COUNTIF(sla_response_compliance_reassigned='Over SLA Response') AS sla_over,
  COUNTIF(sla_response_compliance_reassigned='Missing Time') AS sla_missing,
  COUNTIF(recall_tracking_nbr IS NOT NULL) AS recalls,
  COUNT(DISTINCT SAFE_CAST(store_nbr AS INT64)) AS stores_sum,
  COUNT(DISTINCT trade_aligned_tech_name) AS n_techs
FROM {table}
WHERE SAFE_CAST(store_nbr AS INT64) IN ({stores})
  AND trade_group IN ('GM','HVAC/R')
  AND trade_aligned_tech_name IS NOT NULL AND trade_aligned_tech_name != ''
  AND call_date >= DATETIME('{start}')
  AND call_date < DATETIME('{end}')
"""

INT_FIELDS = ('wos', 'wos_1p', 'wos_3p', 'hp_wos', 'sla_under', 'sla_over',
              'sla_missing', 'recalls', 'stores_sum', 'n_techs')
FLOAT_FIELDS = ('dtc', 'dtc_hp', 'response', 'self_perf', 'ftf')


def run_bq(sql):
    # SQL is piped via stdin (not passed as a command-line arg) and shell=True
    # is used -- bq resolves to a .cmd batch file on Windows, and CreateProcess
    # mangles multi-line/quoted arguments passed directly to batch files.
    proc = subprocess.run(
        [BQ_CMD, "query", "--use_legacy_sql=false", "--format=json"],
        input=sql, capture_output=True, text=True, timeout=180, shell=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "bq query failed -- if this mentions 'Reauthentication failed' "
            "or 'cannot prompt during non-interactive execution', run "
            "`gcloud auth login` interactively first.\n\n" + proc.stderr
        )
    rows = json.loads(proc.stdout)
    if not rows:
        raise RuntimeError("bq query returned zero rows -- refusing to publish empty/broken data")
    row = rows[0]
    for k in INT_FIELDS:
        row[k] = int(row[k]) if row.get(k) is not None else 0
    for k in FLOAT_FIELDS:
        row[k] = float(row[k]) if row.get(k) is not None else None
    return row


def month_bounds(year, month):
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def last_n_months(today, n=3):
    """(key, start, end, label) tuples for the n most recent calendar
    months, ending with the current (possibly partial) month."""
    months = []
    y, m = today.year, today.month
    for i in range(n):
        mm, yy = m - i, y
        while mm <= 0:
            mm += 12
            yy -= 1
        months.append((yy, mm))
    months.reverse()

    out = []
    for yy, mm in months:
        start, end_full = month_bounds(yy, mm)
        is_current = (yy == today.year and mm == today.month)
        end = today + timedelta(days=1) if is_current else end_full
        key = f"{yy:04d}-{mm:02d}"
        label = start.strftime('%B').upper() + f" {yy}" + (" (partial)" if is_current else "")
        out.append((key, start, end, label))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--push', action='store_true', help='git push after committing (needs a remote configured)')
    ap.add_argument('--no-git', action='store_true', help='skip git add/commit entirely')
    args = ap.parse_args()

    today = date.today()
    periods, period_labels = {}, {}

    for key, start, end, label in last_n_months(today, 3):
        print(f"Querying {label} ({start} to {end})...")
        periods[key] = run_bq(QUERY_TEMPLATE.format(
            table=WO_TABLE, stores=STORE_LIST, start=start.isoformat(), end=end.isoformat()))
        period_labels[key] = label

    for n in (30, 60):  # rolling windows needed by the 30D-trend calc in index.html
        start, end = today - timedelta(days=n), today + timedelta(days=1)
        print(f"Querying rolling {n}D window ({start} to {end})...")
        periods[str(n)] = run_bq(QUERY_TEMPLATE.format(
            table=WO_TABLE, stores=STORE_LIST, start=start.isoformat(), end=end.isoformat()))

    latest_key = list(period_labels.keys())[-1]
    out = {
        'periods': periods,
        'goals': {'dtc': 4.0, 'dtc_hp': 1.9, 'response': 85.0, 'self_perf': 72.0, 'ftf': 85.0},
        'meta': {
            'region': '372-A',
            'refresh': today.strftime('%B %d, %Y'),
            'source': 're-ods-explorer.us_re_fm_prod.fsai_workorders (live BigQuery pull, automated via refresh_and_publish.py)',
            'n_techs': periods[latest_key]['n_techs'],
            'period_labels': period_labels,
            'notes': [
                'Rate metrics (DTC, RESPONSE, SELF PERF, FTF) are computed as a single '
                'direct pooled aggregate across all matching work orders market-wide -- '
                'not a weighted average of per-tech numbers.',
                'FOOD Equipment technicians are not trackable at the individual-tech level '
                'for 372-A stores (trade_aligned_tech_name is NULL on 100% of FOOD work '
                'orders here) -- Food Equipment KPIs are omitted rather than guessed. See '
                'the sibling 372a-tableau project for the one place FOOD data exists.',
                "High-priority (HP) DTC uses P1/P2 priority tiers, not the table's native "
                'emergency-only high_priority flag -- interpret with caution on small samples.',
                'This is a whole-market rollup: all technicians in 372-A are combined into '
                'one aggregate. No individual names or per-tech breakdowns are shown.',
            ],
        },
    }

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(out, f)
    print('wrote data.json')

    subprocess.run([sys.executable, 'rebake.py'], check=True)

    if not args.no_git:
        subprocess.run(['git', 'add', 'data.json', 'index.html'], check=True)
        msg = f"Daily refresh: {today.isoformat()}"
        commit = subprocess.run(['git', 'commit', '-m', msg], capture_output=True, text=True)
        if commit.returncode == 0:
            print('committed:', msg)
        elif 'nothing to commit' in (commit.stdout + commit.stderr).lower():
            print('no changes since last refresh, nothing to commit')
        else:
            raise RuntimeError('git commit failed:\n' + commit.stderr)

        if args.push:
            remotes = subprocess.run(['git', 'remote'], capture_output=True, text=True).stdout.strip()
            if 'origin' in remotes.split():
                subprocess.run(['git', 'push', 'origin', 'HEAD'], check=True)
                print('pushed to origin')
            else:
                print('--push given but no "origin" remote configured yet -- skipping push. '
                      'Run: git remote add origin <url>')


if __name__ == '__main__':
    main()
