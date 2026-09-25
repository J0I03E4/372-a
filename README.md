# 372-A :: Whole Market (Retro Terminal Edition)

Sibling of `../372a-dashboard` (the per-tech Tech Arena), but rolled all the
way up: every technician in 372-A is collapsed into **one aggregate market
entity**. No individual names, no per-tech leaderboard -- just totals and
volume-weighted rates.

- Tech: vanilla HTML/CSS/JS, Chart.js (CDN). No backend, no build step.
- Data: derived from `../372a-dashboard/data.json` (the live BigQuery pull)
  via `build_market_data.py`, then baked into `index.html` via
  `embed_data.py` -- same two-step pattern as the tech-level dashboard.

## How the rollup works (`build_market_data.py`)
- **Counts** (WOs, high-priority WOs, SLA under/over/missing, recalls,
  stores) are summed straight across every tech.
- **Rates** (DTC, RESPONSE%, SELF PERF%, FTF%) are **volume-weighted**, not
  simple averages -- a tech with 130 WOs pulls the market number toward
  their rate much harder than a tech with 6 WOs. DTC's high-priority variant
  is weighted by high-priority WO count specifically.
- The 30-day **daily trend** merges every tech's daily rows by calendar
  date into one market-wide line (WOS summed, rates volume-weighted per day).

## Known data caveats (same as the tech dashboard, plus one more)
- DTC on the 1-day/3-day windows is structurally biased low -- trust the
  30-day window for DTC.
- FOOD Equipment techs aren't trackable at the individual level for 372-A
  stores, so they're not part of this rollup either.
- High-priority DTC uses P1/P2 priority tiers, not the native
  emergency-only flag.
- `stores_sum` in the window-comparison table is a naive sum of each tech's
  store count -- if two techs share a store, that store gets counted twice.
  Treat it as "store-visits capacity", not a unique-store count.

## Monthly comparison: real calendar months, labeled
The "Monthly Comparison" table and the "Metric By Month" chart use **actual
calendar months** (e.g. JULY 2026, AUGUST 2026, SEPTEMBER 2026), not rolling
30/60/90-day windows. `../372a-dashboard/data.json` doesn't natively have
calendar-month buckets, so they were pulled separately via BigQuery grouped
by `DATE_TRUNC(call_date, MONTH)` (same corrected methodology --
status_name='COMPLETED', DATETIME_DIFF-based DTC, third_party_assigned for
self-perf, categorical SLA text match) and merged in with
`../372a-dashboard/add_monthly_periods.py`. Column labels come from
`meta.period_labels` in the data, which the UI reads dynamically -- the
current month is explicitly marked **(partial)** since it isn't over yet.
The top "Window" tabs (1D/3D/7D/30D) still drive the KPI strip and are a
completely separate, unrelated rolling-window view.

## Refreshing the data
1. Refresh `../372a-dashboard/data.json` first (see that folder's README) --
   this covers the 1/3/7/30-day rolling windows.
2. Re-pull the last 3 calendar months via BigQuery, grouped by
   `DATE_TRUNC(call_date, MONTH)` (same store list, same corrected column
   semantics -- see `add_monthly_periods.py`'s docstring), and re-run
   `python add_monthly_periods.py` from `../372a-dashboard` to merge them in.
3. Run `python build_market_data.py` here to regenerate this folder's
   `data.json` from the tech-level source.
4. Run `python rebake.py` to re-embed the JSON into `index.html` (works
   whether or not the file already has data baked in).

Built with Code Puppy.
