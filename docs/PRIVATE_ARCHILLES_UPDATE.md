# Private Archilles Update Path

This is the approved private update path from Jade to Archilles.

## Source and target

```text
Source on Jade:      /home/hax/haxjobs-private-dev
Source remote:       https://github.com/haxsysgit/Haxjobs-Private.git
Target on Archilles: /home/hermes/haxjobs
```

Public release work in `/home/hax/haxjobs-public-release` must not be sent to Archilles unless Arinze explicitly asks for a specific change to be ported into the private lane.

## Normal command

From Jade:

```bash
cd /home/hax/haxjobs-private-dev
scripts/update-archilles-private
```

The script refuses to run unless:

- local origin is the private repo
- local branch is `main`
- local working tree is clean
- local HEAD is already pushed to `origin/main`
- Archilles has no tracked dirty source changes
- Archilles still has protected private/runtime items before update

## What the script does

1. Validates Jade private-dev.
2. SSHes into Archilles.
3. Changes `/home/hermes/haxjobs` origin to the private repo.
4. Fetches `origin/main`.
5. Hard-resets tracked source only to the private repo commit.
6. Verifies protected runtime/private files still exist.
7. Installs dashboard dependencies if needed.
8. Restarts the dashboard/API with `dashctl.sh restart`.
9. Calls `http://127.0.0.1:8800/api/status` and checks the JSON payload.

## Protected Archilles paths

The update path must preserve:

```text
state/
intake/
packs/
reports/
outreach/
profile/
profile/arinze_profile.local.json
cv_profile.typed.json
CV_FRAME_GOVERNANCE.md
```

## Forbidden defaults

Do not use these for private deployment:

```bash
rsync --delete
cd /home/hax/haxjobs-public-release && rsync ... archilles:/home/hermes/haxjobs
cd /home/hax/haxjobs && rsync ... archilles:/home/hermes/haxjobs
```

## Health check after update

The script performs the basic health check automatically. Manual checks:

```bash
ssh archilles 'cd /home/hermes/haxjobs && git remote -v && git rev-parse --short HEAD && git status --short --untracked-files=no'
ssh archilles 'curl -fsS http://127.0.0.1:8800/api/status'
ssh archilles 'cd /home/hermes/haxjobs && for d in state intake packs reports outreach profile; do test -e "$d" && echo "$d ok"; done'
```

## Recovery notes

If the update fails before changing source, fix the failing precondition and rerun.

If the update fails after changing source but before API health passes:

1. Do not run public-release sync.
2. Check `/tmp/pipeline-api.log` on Archilles.
3. Check `dashctl.sh status` on Archilles.
4. If source rollback is required, reset Archilles to a known private repo commit, not to the public release lane.
