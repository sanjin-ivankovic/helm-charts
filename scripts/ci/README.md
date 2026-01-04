# Helm Chart Release Scripts

Professional Helm chart release automation with modular design and idempotent
publishing.

## Overview

This directory contains scripts for managing the complete Helm chart release
lifecycle:

```text
scripts/
├── lib/
│   └── common.sh              # Shared utilities and logging
├── detect-changes.sh          # Git-based change detection
├── validate-chart.sh          # Chart linting and validation
├── package-chart.sh           # Chart packaging with dependencies
├── publish-chart.sh           # Idempotent registry publishing
└── release.sh                 # Main orchestrator script
```

## Key Features

- ✅ **Modular Architecture**: Single-responsibility scripts with shared library
- ✅ **Idempotent Publishing**: Won't re-push existing chart versions
- ✅ **Change Detection**: Only processes modified charts
- ✅ **Comprehensive Validation**: Linting, dependency updates, template
  rendering
- ✅ **Error Handling**: Strict mode with proper error reporting
- ✅ **Structured Logging**: Timestamps and log levels

## Usage

### Individual Scripts

```bash
# Detect changed charts (git-based)
./scripts/detect-changes.sh

# Validate a chart
./scripts/validate-chart.sh my-chart

# Package a chart
./scripts/package-chart.sh my-chart

# Publish a chart (requires registry login)
./scripts/publish-chart.sh my-chart

# Full release workflow
./scripts/release.sh all              # All charts
./scripts/release.sh my-chart         # Single chart
```

### Environment Variables

```bash
CHARTS_DIR="charts"                              # Charts directory
PACKAGES_DIR=".packages"                         # Package output directory
REGISTRY_HOST="registry.example.com"              # Registry host
REGISTRY_OWNER="homelab"                         # Registry namespace
REGISTRY_PROJECT="helm-charts"                   # Registry project
RELEASE_ALL="true"                               # Force release all charts
```

### Registry Login

Before publishing, login to the registry:

```bash
# Local development
echo $PASSWORD | helm registry login registry.example.com -u $USER --password-stdin

# GitLab CI (automatic)
# Uses CI_REGISTRY_PASSWORD, CI_REGISTRY_USER, CI_REGISTRY
```

## GitLab CI Pipeline

The scripts integrate with a 5-stage GitLab CI pipeline:

1. **detect** - Identifies changed charts
2. **validate** - Lints and validates changed charts
3. **package** - Creates .tgz packages with dependency caching
4. **publish** - Pushes to registry (manual approval for main branch)
5. **notify** - Reports publish results

### Pipeline Behavior

- **Merge Requests**: Validates and packages (no publish)
- **Main Branch**: Requires manual approval to publish
- **Tags**: Automatically publishes all changed charts

## Script Details

### common.sh

Shared library providing:

- Logging functions: `log_info`, `log_success`, `log_warn`, `log_error`
- Chart utilities: `get_chart_version`, `get_chart_name`,
  `chart_has_dependencies`
- Idempotency check: `chart_version_exists`
- Requirement verification: `verify_requirements`

### detect-changes.sh

Detects which charts have changed using git diff.

**Outputs**: One chart name per line to stdout

**Behavior**:

- Tags or `RELEASE_ALL=true`: Returns all charts
- Otherwise: Returns only charts with modified files

### validate-chart.sh

Validates a chart before packaging.

**Steps**:

1. Run `helm lint`
2. Update dependencies if present
3. Test template rendering with `helm template`

**Exit Codes**:

- 0: Validation passed
- 1: Validation failed

### package-chart.sh

Packages a chart with dependency resolution.

**Steps**:

1. Build dependencies with `helm dependency build`
2. Package chart with `helm package`
3. Verify package file exists

**Output**: Creates `.tgz` file in `$PACKAGES_DIR`

### publish-chart.sh

Publishes a chart to OCI registry with idempotency.

**Steps**:

1. Verify package file exists
2. Determine registry path (CI or local)
3. **Check if version already exists** (idempotency)
4. Push to registry if new version

**Exit Codes**:

- 0: Successfully published OR version already exists (skip)
- 1: Publish failed

**Key Feature**: Won't overwrite existing versions - prompts to bump version
instead.

### release.sh

Main orchestrator that runs the complete workflow.

**Steps** (per chart):

1. Validate
2. Package
3. Publish

**Reporting**:

- Tracks success, skipped, and failed charts
- Displays summary at end
- Returns non-zero if any failures

## Error Handling

All scripts use `set -euo pipefail` for strict error handling:

- `set -e`: Exit on error
- `set -u`: Exit on undefined variable
- `set -o pipefail`: Exit on pipe failures

Each script also includes an EXIT trap for cleanup.

## Shellcheck Compliance

All scripts pass shellcheck validation. The only warnings are SC1091 (info
level) for not following sourced files, which is expected and suppressed with
`# shellcheck source=` directives.

## Key Improvements

| Feature              | Old           | New                        |
| -------------------- | ------------- | -------------------------- |
| **Idempotency**      | ❌            | ✅ Checks before push      |
| **Validation**       | ❌            | ✅ Lint + deps + templates |
| **Change Detection** | ❌            | ✅ Git-based               |
| **Modularity**       | ❌ Monolithic | ✅ 5 focused scripts       |
| **Error Handling**   | Basic         | Strict mode + traps        |
| **Logging**          | Colors only   | Structured + timestamps    |

## Troubleshooting

### "common.sh not found"

Ensure you're running scripts from the repository root or that `SCRIPT_DIR` is
correctly resolved.

### "Chart version already exists"

This is expected behavior (idempotency). To publish:

1. Bump version in `Chart.yaml`
2. Re-run package and publish

### "helm: command not found"

Install Helm 3.8+ from <https://helm.sh/docs/intro/install/>

### Registry authentication failures

Ensure you're logged in:

```bash
helm registry login <host> -u <user>
```

## Development

### Adding New Features

1. Update `lib/common.sh` for shared utilities
2. Create focused scripts for new functionality
3. Update `release.sh` to orchestrate new steps
4. Add corresponding pipeline stages in `.gitlab-ci.yml`

### Testing

```bash
# Test individual scripts
./scripts/validate-chart.sh test-chart
./scripts/package-chart.sh test-chart

# Dry run (no publish)
CHARTS_DIR=charts PACKAGES_DIR=.packages \
  ./scripts/validate-chart.sh my-chart && \
  ./scripts/package-chart.sh my-chart

# Test full workflow locally
./scripts/release.sh all
```

## License

Part of the helm-charts repository. See repository root for license information.
