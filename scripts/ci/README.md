# CI Scripts

This directory contains scripts for the Helm charts CI/CD pipeline.

## Python Scripts (Active - Used by CI)

These scripts are used by the GitLab CI pipeline:

- **`detect_changes.py`** - Detects which charts have changed via git diff
- **`validate_chart.py`** - Validates a chart (lint, dependencies, template
  rendering)
- **`package_chart.py`** - Packages a chart into a .tgz file
- **`publish_chart.py`** - Publishes a chart to the OCI registry
- **`chart_metrics.py`** - Collects and analyzes chart CI/CD metrics

## Testing

- **`test_detect_changes.py`** - Unit tests for detect_changes.py
- **`test_validate_chart.py`** - Unit tests for validate_chart.py
- **`pytest.ini`** - Pytest configuration
- **`requirements.txt`** - Python dependencies

Run tests with:

```bash
cd scripts/ci
pytest -v --cov=.
```

## Bash Scripts (Legacy - For Local Use Only)

These bash scripts are **no longer used by the CI pipeline** but are kept for
local testing and manual releases:

- **`release.sh`** - Orchestrates the full release process (validate → package
  → publish)
- **`detect-changes.sh`** - Legacy version of detect_changes.py
- **`validate-chart.sh`** - Legacy version of validate_chart.py
- **`package-chart.sh`** - Legacy version of package_chart.py
- **`publish-chart.sh`** - Legacy version of publish_chart.py
- **`lib/common.sh`** - Shared utilities for bash scripts

### Using release.sh Locally

```bash
# Release all charts
./scripts/ci/release.sh all

# Release a specific chart
./scripts/ci/release.sh my-chart
```

## Migration Notes

The CI pipeline was migrated from bash to Python for:

- Better testability (unit tests with pytest)
- Type safety (type hints throughout)
- Better error handling
- Structured logging
- Easier maintenance

The bash scripts remain for backward compatibility and local testing workflows.
