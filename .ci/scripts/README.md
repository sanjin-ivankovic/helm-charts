# CI Scripts

This directory contains the scripts for the Helm charts CI/CD pipeline,
invoked by GitLab CI ([`.gitlab-ci.yml`](../../.gitlab-ci.yml)).

## Chart pipeline scripts

- **`detect_changes.py`** - Detects which charts have changed via git diff
- **`validate_chart.py`** - Validates a chart (lint, dependencies, template
  rendering)
- **`package_chart.py`** - Packages a chart into a `.tgz` file
- **`publish_chart.py`** - Publishes a chart to the OCI registry
- **`notify.py`** - Reports publish results (Discord webhook)
- **`ci_env.py`** / **`common.py`** - Shared CI environment + helper utilities
- **`changed_paths.sh`** - Lists changed paths for the `rules:changes` gates

The GitHub public-mirror tooling (`publish_github.py`, `sanitize_repo.py`,
`verify_sanitization.py`) is provided by the shared `ci-base` image at `/opt/ci`
and run by the `mirror-github` component; this repo keeps only its own
[`.ci/sanitize/sanitize-config.yaml`](../sanitize/sanitize-config.yaml), which
the tooling reads.

## Pre-Commit Linting

File-level linting (YAML, shell, Markdown) and secret scanning (gitleaks) are
handled by [pre-commit](https://pre-commit.com). The configuration lives in
`.pre-commit-config.yaml` at the repo root. Install it locally with
`pre-commit install`. It is a **local** hook only — CI runs the equivalent
checks as native per-tool jobs, not via pre-commit.

## Testing

Each script has a `test_*.py` unit test (pytest). Run them with:

```bash
cd .ci/scripts
pytest -v --cov=.
```

`pytest.ini` holds the pytest configuration and `requirements.txt` the Python
dependencies.
