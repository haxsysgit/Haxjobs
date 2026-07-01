# Plan 054: PyPI release — publish v1.0.0

> **Depends on**: 053 (docs complete, product shippable) | **Priority**: P1 | **Effort**: S | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

`pip install haxjobs` must actually work. This plan bumps the version from `1.0.0.dev0` to `1.0.0`, tags the release, builds the package, and publishes to PyPI. This is the moment HaxJobs becomes a real product anyone can install.

## Steps

1. **Final verification**: run full test suite one last time. `python3 -m pytest -q tests/` → all pass
2. **Version bump**: change `version = "1.0.0.dev0"` to `version = "1.0.0"` in `pyproject.toml` and `src/haxjobs/__init__.py`
3. **Build package**: `python3 -m build` (requires `pip install build`). Verify `dist/haxjobs-1.0.0.tar.gz` and `dist/haxjobs-1.0.0-py3-none-any.whl` exist
4. **Test install from wheel**: in a temp venv: `pip install dist/haxjobs-1.0.0-py3-none-any.whl && haxjobs` → prints usage
5. **Git tag**: `git tag v1.0.0` and `git push origin v1.0.0`
6. **Publish to PyPI**: `python3 -m twine upload dist/*` (requires PyPI account + token)
7. **GitHub Release**: create release from tag with changelog (list all plans 040-054 as features)
8. **Push main**: `git push origin main`

## Done criteria

- [ ] Version bumped to 1.0.0
- [ ] Package builds: `.whl` and `.tar.gz` exist
- [ ] `pip install` from wheel works in clean venv
- [ ] Git tag v1.0.0 pushed
- [ ] PyPI page shows haxjobs 1.0.0
- [ ] GitHub Release published with changelog

## STOP conditions

- Tests fail on final run — fix before publishing
- PyPI package name "haxjobs" taken — check availability first, use `haxjobs-app` or similar if needed
- Twine upload fails with auth error — check PyPI token
