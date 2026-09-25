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

### Preferred: `refresh_and_publish.py` (one command, no LLM agent needed)
```
python refresh_and_publish.py            # pull BigQuery + rebuild + git commit
python refresh_and_publish.py --push     # also push, if a git remote is set up
python refresh_and_publish.py --no-git   # pull + rebuild only, skip git
```
This queries BigQuery directly via the `bq` CLI (5 queries: the last 3
calendar months + rolling 30D/60D windows), using the same corrected
formulas validated during this project's build-out. It computes every rate
metric as one direct pooled aggregate across matching work orders
market-wide, rather than the old two-step "per-tech then weighted-average"
approach -- simpler, and it no longer depends on `../372a-dashboard/data.json`
at all.

**This is NOT yet safe as a fully unattended scheduled task.** `bq`/`gcloud`
are authenticated with a personal OAuth session that periodically expires
and needs an interactive browser login (`gcloud auth login`) to refresh --
something a background Windows Scheduled Task can't do on its own. If the
token's expired, the script fails loudly with a clear error instead of
silently publishing stale data. For true unattended automation, provision a
service account with read access to `re-ods-explorer` and point `bq`/`gcloud`
at its key file instead.

### Fallback: the old manual multi-step process (via `372a-dashboard`)
Still works if you want per-tech source data updated too (this dashboard's
previous refresh path):
1. Refresh `../372a-dashboard/data.json` first (see that folder's README).
2. Re-pull the last 3 calendar months via BigQuery, grouped by
   `DATE_TRUNC(call_date, MONTH)`, and re-run
   `python add_monthly_periods.py` from `../372a-dashboard` to merge them in.
3. Run `python build_market_data.py` here to regenerate this folder's
   `data.json` from the tech-level source.
4. Run `python rebake.py` to re-embed the JSON into `index.html`.

## Version control / GitHub
This folder is its own local git repo (separate from the rest of the
workspace, so unrelated files -- other CSVs, PPTX decks with real names,
etc. -- never get dragged in). `audio/` is gitignored -- the background
music is copyrighted and has no business in a public repo, even though it's
fine for local use.

No remote is configured yet. To push to GitHub, decide first: personal
public github.com (do one more pass checking `data.json`/`index.html` for
anything you don't want public before the first push), or a Walmart
enterprise GitHub instance if one exists for this kind of internal-tool
repo. Then:
```
git remote add origin <your-repo-url>
git push -u origin master
```
After that, `python refresh_and_publish.py --push` will push automatically
on every future run.

Built with Code Puppy.

