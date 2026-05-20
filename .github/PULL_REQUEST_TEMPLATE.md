## Summary

<!-- One paragraph: what does this PR do, and why? Tie to a roadmap track if applicable. -->

Closes #

## Changes

<!-- Bullet list of the concrete changes. Reviewers should not have to read the diff to understand scope. -->

-
-
-

## Test plan

<!-- How did you verify this works? Include exact commands. -->

- [ ] `ruff check forgeflow/ dashboard/ tests/` passes
- [ ] `mypy forgeflow/ --ignore-missing-imports --no-strict-optional` passes
- [ ] `pytest tests/unit -v` passes
- [ ] `pytest tests/integration -v` passes (requires Docker postgres)
- [ ] Manually exercised the changed code path: <describe>

## Breaking changes

<!-- Does this require a config migration, env var change, or schema migration? -->

None / <describe>

## Screenshots (UI changes only)

<!-- Drag and drop screenshots here. Required for dashboard or README diffs. -->

## Checklist

- [ ] Commits are signed off (`git commit -s`)
- [ ] Tests added for new behavior
- [ ] Docs updated (README / ROADMAP / docstrings) if behavior visible to users
- [ ] No new ruff or mypy warnings
- [ ] No dead code, no commented-out blocks left behind
