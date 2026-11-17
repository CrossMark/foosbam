# Repository guidance

Foosbam is a Flask application. Read [README.md](README.md) for setup and architecture, and [CONTRIBUTING.md](CONTRIBUTING.md) for contribution and migration practices.

## Changes

- Keep changes focused and follow existing patterns in the relevant blueprint, model, template, or core module.
- Add or update tests for behavior changes. Tests use `unittest`; the CI workflow enforces 100% branch coverage for application code.
- For model or schema changes, create and review a new Alembic migration. Do not rewrite migrations that may have been applied to shared databases.
- Treat `app.sqlite` as persistent local data. Do not delete, reset, or modify it as part of routine development or testing.
- Keep credentials and other secrets out of source control.

## Verification

Run the relevant tests while iterating. Before finishing, run the full suite and the same coverage gate used in CI:

```powershell
python -m coverage run --branch --source=foosbam,config,app -m unittest discover -s tests
python -m coverage report --fail-under=100
```

Report any tests or checks that could not be run.

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues. See `docs/agents/issue-tracker.md`.

### Triage labels

Triage states use the canonical five-role vocabulary. See `docs/agents/triage-labels.md`.

### Domain docs

Domain docs use a single-context layout. See `docs/agents/domain.md`.
