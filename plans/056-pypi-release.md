# Plan 056: PyPI release — publish v1.0.0

> **Depends on**: 055 | **Priority**: P1 | **Effort**: S | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

`uv tool install haxjobs` must actually work. This plan bumps the version from `1.0.0.dev0` to `1.0.0`, tags the release, builds with `uv build`, and publishes with `uv publish`.

## Steps

1. **Final verification**: `uv run pytest -q tests/` → all pass
2. **Version bump**: `uv version 1.0.0`
3. **Build**: `uv build` → creates `dist/haxjobs-1.0.0-py3-none-any.whl` + `.tar.gz`
4. **Test install**: in a temp dir: `uv tool install ./dist/haxjobs-1.0.0-py3-none-any.whl && haxjobs --help` → shows usage
5. **Git tag**: `git tag v1.0.0 && git push origin v1.0.0`
6. **Publish**: `uv publish` (requires PyPI token in `UV_PUBLISH_TOKEN` env var or `--token`)
7. **GitHub Release**: create release from tag with changelog (list plans 040-054 as features)
8. **Push main**: `git push origin main`

## Done criteria

- [ ] Version bumped to 1.0.0 via `uv version`
- [ ] `uv build` creates wheel + sdist
- [ ] `uv tool install` from wheel works in clean environment
- [ ] Git tag v1.0.0 pushed
- [ ] PyPI page shows haxjobs 1.0.0
- [ ] GitHub Release published

## STOP conditions

- Tests fail — fix before publishing
- Package name "haxjobs" taken on PyPI — use `haxjobs-app`
- `uv publish` fails with auth — check `UV_PUBLISH_TOKEN`
