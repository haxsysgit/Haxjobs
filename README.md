# HaxJobs

HaxJobs is Arinze's Hermes-native job application workflow.

It discovers jobs, evaluates them against Arinze's profile, generates application packs, and exposes a dashboard for reviewing jobs, skips, packs, and activity.

## Source of truth

GitHub is the source of truth for code and docs.

- Jade/local repo: `/home/hax/haxjobs`
- Archilles live repo: `/home/hermes/haxjobs`
- Remote: `https://github.com/haxsysgit/Haxjobs.git`

Normal workflow:

1. Work locally on Jade.
2. Commit and push to GitHub.
3. On Archilles, run:

```bash
haxjobs-update
```

That pulls the latest GitHub commit, preserves runtime state, installs dashboard dependencies, and restarts the dashboard/API stack.

## Runtime state not committed

These are intentionally ignored:

- `intake/`
- `packs/`
- `state/`
- `reports/`
- `outreach/`
- SQLite databases
- `.env` files
- LinkedIn cookies/browser profiles
- `node_modules/` and generated Vite bundles

## Dashboard

Dev server on Archilles:

```bash
cd /home/hermes/haxjobs/dashboard
npx vite --port 5173 --host 127.0.0.1
```

Tunnel from Jade/local:

```bash
tunnel-dash
# open http://localhost:5173
```

## Checks

Agents should read `AGENTS.md` before changing code.

From repo root:

```bash
python3 -m pytest -q
python3 -m py_compile $(find . -path './dashboard/node_modules' -prune -o -path './.git' -prune -o -path './.venv' -prune -o -name '*.py' -print)
bash -n cron/run_pipeline.sh scripts/haxjobs-update dashctl.sh build-dash.sh dev-watch.sh pack_builder.sh
cd dashboard && npm ci && npm run build
```
