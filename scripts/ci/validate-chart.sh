#!/bin/bash
# scripts/ci/validate-chart.sh CHART_NAME
# Validates a Helm chart: linting, dependency check, and template rendering

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
if [ -f "$SCRIPT_DIR/lib/common.sh" ]; then
    source "$SCRIPT_DIR/lib/common.sh"
else
    echo "Error: common.sh not found at $SCRIPT_DIR/lib/common.sh" >&2
    exit 1
fi

# Check arguments
if [ $# -lt 1 ]; then
    log_error "Usage: $0 CHART_NAME"
    exit 1
fi

CHART_NAME=$1
CHART_PATH="$CHARTS_DIR/$CHART_NAME"

log_info "======================================"
log_info "Validating chart: $CHART_NAME"
log_info "======================================"

# Verify chart directory exists
if [ ! -d "$CHART_PATH" ]; then
    log_error "Chart directory not found: $CHART_PATH"
    exit 1
fi

# Verify Chart.yaml exists
if [ ! -f "$CHART_PATH/Chart.yaml" ]; then
    log_error "Chart.yaml not found in $CHART_PATH"
    exit 1
fi

# Display chart info
CHART_VERSION=$(get_chart_version "$CHART_PATH")
CHART_NAME_FROM_YAML=$(get_chart_name "$CHART_PATH")

log_info "Chart name: $CHART_NAME_FROM_YAML"
log_info "Chart version: $CHART_VERSION"

# Verify chart name matches directory
if [ "$CHART_NAME" != "$CHART_NAME_FROM_YAML" ]; then
    log_warn "Chart directory name ($CHART_NAME) doesn't match Chart.yaml name ($CHART_NAME_FROM_YAML)"
fi

# Step 1: Run helm lint
log_info "Step 1/3: Running helm lint..."
if helm lint "$CHART_PATH"; then
    log_success "Lint passed"
else
    log_error "Lint failed for $CHART_NAME"
    exit 1
fi

# Step 2: Update dependencies if they exist
if chart_has_dependencies "$CHART_PATH"; then
    log_info "Step 2/3: Updating dependencies..."
    if helm dependency update "$CHART_PATH"; then
        log_success "Dependencies updated"
    else
        log_error "Dependency update failed for $CHART_NAME"
        exit 1
    fi
else
    log_info "Step 2/3: No dependencies found - skipping dependency update"
fi

# Step 3: Test template rendering
log_info "Step 3/3: Testing template rendering..."
if helm template test-release "$CHART_PATH" --dry-run > /dev/null 2>&1; then
    log_success "Template rendering passed"
else
    log_error "Template rendering failed for $CHART_NAME"
    log_error "Run 'helm template test-release $CHART_PATH' to see details"
    exit 1
fi

log_success "======================================"
log_success "Chart validation PASSED: $CHART_NAME"
log_success "======================================"
