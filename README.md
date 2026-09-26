
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
etc. -- never get dragged in). Background music is `audio/chiptune-loop.wav`,
a fully original 8-bit-style loop synthesized from scratch by
`generate_chiptune.py` (square waves + math, zero samples, zero licensed
material) -- safe for a public repo. `.gitignore` blocks everything else
under `audio/` by default (`audio/*` + a `!audio/chiptune-loop.wav`
exception), in case a copyrighted track ever ends up dropped in that folder
for local testing again.

**Live at:** `https://github.com/J0I03E4/372-a` (public repo) and served via
GitHub Pages at `https://j0i03e4.github.io/372-a/` once Pages is enabled in
repo Settings -> Pages -> Source: `main` branch, `/ (root)`.

 **This repo is PUBLIC.** It contains real Walmart store numbers and
internal SLA/recall/DTC metrics. That was a deliberate, informed choice --
if that ever changes, either make the repo private (needs a paid GitHub
plan for Pages to still work) or pull the site down entirely.

`python refresh_and_publish.py --push` pushes automatically on every run
since `origin` is already configured.

## Hourly auto-refresh (Windows Scheduled Task)
A task named **`372A-Hourly-Refresh`** (`run_refresh.bat` -> the project's
own `.venv` -> `refresh_and_publish.py --push`) is **ENABLED** and running.
Joseph already has full read access to `re-ods-explorer` under his own
identity (confirmed live -- no service account was ever needed for
*access*), so this works today.

**The one real caveat:** `bq`/`gcloud` run under Joseph's personal OAuth
session, which periodically expires and needs an interactive browser login
(`gcloud auth login`) to refresh -- something a background Scheduled Task
can't do by itself. When that happens, the hourly run fails loudly (the
script refuses to publish stale/broken data) until someone notices and
re-logs in manually. This could go days between hiccups; treat a stale
`meta.refresh` date on the live site as the signal to run `gcloud auth
login` again.

**To eliminate that caveat entirely**, get a service account with read
access to `re-ods-explorer` (ask in #mint-support or your GCP access
channel), then:
```
gcloud auth activate-service-account --key-file=path\to\key.json
```
No code changes needed -- `bq`/`gcloud` will just use whichever credential
is currently active, service account or personal.

### Drafted ask for #mint-support / GCP access channel
> Hi team -- I already have personal read access to
> `re-ods-explorer.us_re_fm_prod.fsai_workorders`, but I'd like a service
> account with the same read-only access so an hourly automated dashboard
> refresh doesn't depend on my personal OAuth session (which periodically
> expires and needs an interactive browser re-login that a background task
> can't do). A key file I can point `gcloud auth activate-service-account`
> at would be perfect. Thanks!

Built with Code Puppy.
