# Contributing to ForgeFlow

Thanks for your interest in ForgeFlow. This document describes how to contribute code, docs, and ideas.

## Quick start for contributors

```bash
git clone https://github.com/JoelJohnsonThomas/ForgeFlow.git
cd ForgeFlow
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
docker compose up -d postgres
alembic upgrade head
pytest tests/unit -v
```

## Where to contribute

Open a [GitHub issue](https://github.com/JoelJohnsonThomas/ForgeFlow/issues) before starting non-trivial work. See [ROADMAP.md](ROADMAP.md) for planned features — issues tagged `help wanted` and `good first issue` are open for community pickup.

## Pull request process

1. **Fork & branch** off `main`. Use a descriptive branch name (`feat/slack-notifications`, `fix/budget-guard-rounding`).
2. **Write tests** for any new behavior. Unit tests live in `tests/unit/`, integration tests in `tests/integration/`. New features without tests will not be merged.
3. **Lint & type-check locally** before opening a PR:
   ```bash
   ruff check forgeflow/ dashboard/ tests/
   mypy forgeflow/ --ignore-missing-imports --no-strict-optional
   ```
4. **Sign off your commits** with the Developer Certificate of Origin: `git commit -s -m "..."`. By signing off, you certify the contents of the [DCO](https://developercertificate.org/).
5. **Keep PRs focused**. Smaller PRs review faster. Refactors should be separate from feature work.
6. **Open the PR** with the template filled in. Link the issue it closes (`Closes #42`).
7. **Wait for CI**. All three jobs (lint, test, build) must pass before review.

## Code style

- **Python 3.11+** features only. We use `from __future__ import annotations` at the top of every module.
- **Ruff** rules: see `[tool.ruff.lint]` in `pyproject.toml`. Don't suppress rules; fix them.
- **Mypy**: type annotations are required on public functions. `Any` is allowed but discouraged.
- **No emojis in code or commit messages.** README is allowed.
- **Docstrings**: one-line for module/class. Multi-line only when non-obvious behavior needs explaining.
- **No dead code, no commented-out blocks.** Delete it; git remembers.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` new user-facing feature
- `fix:` bug fix
- `docs:` documentation only
- `refactor:` code change that neither fixes a bug nor adds a feature
- `test:` test-only changes
- `ci:` CI/build only
- `chore:` everything else

Example:
```
feat(connectors): add real Slack approval notifications

Closes #17
```

## Reporting bugs

Use the **Bug Report** issue template. Include:
- Minimal reproduction (lead data, env vars, command)
- Expected vs. actual behavior
- Stack trace if any
- ForgeFlow version (`pip show forgeflow`) and Python version

## Reporting security issues

Do not open public issues for security vulnerabilities. Email the maintainer privately. We will acknowledge within 72 hours.

## Code of Conduct

This project follows the [Contributor Covenant 2.1](CODE_OF_CONDUCT.md). By participating, you agree to abide by its terms.

## License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).
