# Contributing

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

If you change frontend styles, also run:

```bash
npm install
npm run build:css
```

## Validation

Run the local checks before opening a PR:

```bash
ruff check .
pytest
```

## Scope

- Prefer small, reviewable pull requests.
- Keep sandbox and local-only safety behavior intact unless a change intentionally revises the spec.
- Add tests for behavior changes, especially around metadata writing, server validation, and model-selection logic.

## Pull requests

- Describe the user-visible impact.
- Note any dependency or model-cache changes.
- Update `README.md`, `SPEC.md`, or `CHANGELOG.md` when behavior or developer workflow changes.
