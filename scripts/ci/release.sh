#!/bin/bash
# scripts/ci/release.sh [CHART_NAME|all]
# Main orchestrator for Helm chart release process
# Validates, packages, and publishes charts

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
if [ -f "$SCRIPT_DIR/lib/common.sh" ]; then
    source "$SCRIPT_DIR/lib/common.sh"
else
    echo "Error: common.sh not found at $SCRIPT_DIR/lib/common.sh" >&2
    exit 1
fi

# Verify requirements
verify_requirements || exit 1

CHARTS_DIR="${CHARTS_DIR:-charts}"

# Display usage
usage() {
    echo "Usage: $0 [CHART_NAME|all]"
    echo ""
    echo "Examples:"
    echo "  $0 all              # Release all charts"
    echo "  $0 my-chart         # Release specific chart"
    echo ""
    echo "Environment variables:"
    echo "  CHARTS_DIR          # Directory containing charts (default: charts)"
    echo "  PACKAGES_DIR        # Directory for packages (default: .packages)"
    echo "  REGISTRY_HOST       # Registry host (default: registry.example.com)"
    echo "  REGISTRY_OWNER      # Registry owner (default: homelab)"
    echo "  REGISTRY_PROJECT    # Registry project (default: helm-charts)"
    exit 1
}

# Check arguments
if [ $# -lt 1 ]; then
    usage
fi

# Determine which charts to process
if [ "$1" == "all" ]; then
    log_info "Processing ALL charts in $CHARTS_DIR"
    CHARTS=$(find "$CHARTS_DIR" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort)
    if [ -z "$CHARTS" ]; then
        log_error "No charts found in $CHARTS_DIR"
        exit 1
    fi
else
    CHARTS=$1
    if [ ! -d "$CHARTS_DIR/$CHARTS" ]; then
        log_error "Chart not found: $CHARTS_DIR/$CHARTS"
        exit 1
    fi
fi

# Count charts
CHART_COUNT=$(echo "$CHARTS" | wc -w | tr -d ' ')
log_info "Charts to process: $CHART_COUNT"

# Track results
FAILED_CHARTS=()
SKIPPED_CHARTS=()
SUCCESS_CHARTS=()

# Process each chart
for chart in $CHARTS; do
    echo ""
    log_info "╔════════════════════════════════════════╗"
    log_info "║  Processing: $chart"
    log_info "╚════════════════════════════════════════╝"
    echo ""

    # Step 1: Validate
    log_info "[$chart] Step 1/3: Validation"
    if ! "$SCRIPT_DIR/validate-chart.sh" "$chart"; then
        log_error "[$chart] Validation failed"
        FAILED_CHARTS+=("$chart (validation)")
        continue
    fi

    # Step 2: Package
    log_info "[$chart] Step 2/3: Packaging"
    if ! "$SCRIPT_DIR/package-chart.sh" "$chart"; then
        log_error "[$chart] Packaging failed"
        FAILED_CHARTS+=("$chart (packaging)")
        continue
    fi

    # Step 3: Publish
    log_info "[$chart] Step 3/3: Publishing"
    if "$SCRIPT_DIR/publish-chart.sh" "$chart"; then
        # Check if it was skipped (exit 0 but with warning about existing version)
        if grep -q "already exists in registry" /tmp/publish-*.log 2>/dev/null; then
            log_warn "[$chart] Skipped - version already exists"
            SKIPPED_CHARTS+=("$chart")
        else
            log_success "[$chart] Published successfully"
            SUCCESS_CHARTS+=("$chart")
        fi
    else
        log_error "[$chart] Publishing failed"
        FAILED_CHARTS+=("$chart (publishing)")
        continue
    fi
done

# Display summary
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                     RELEASE SUMMARY                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

log_info "Total charts processed: $CHART_COUNT"

if [ ${#SUCCESS_CHARTS[@]} -gt 0 ]; then
    log_success "Successfully published (${#SUCCESS_CHARTS[@]}):"
    for chart in "${SUCCESS_CHARTS[@]}"; do
        log_success "  ✓ $chart"
    done
fi

if [ ${#SKIPPED_CHARTS[@]} -gt 0 ]; then
    log_warn "Skipped - already exists (${#SKIPPED_CHARTS[@]}):"
    for chart in "${SKIPPED_CHARTS[@]}"; do
        log_warn "  ⊘ $chart"
    done
fi

if [ ${#FAILED_CHARTS[@]} -gt 0 ]; then
    log_error "Failed (${#FAILED_CHARTS[@]}):"
    for chart in "${FAILED_CHARTS[@]}"; do
        log_error "  ✗ $chart"
    done
    echo ""
    log_error "Release completed with errors"
    exit 1
fi

echo ""
log_success "╔════════════════════════════════════════════════════════════╗"
log_success "║            ALL CHARTS PROCESSED SUCCESSFULLY               ║"
log_success "╚════════════════════════════════════════════════════════════╝"
exit 0
