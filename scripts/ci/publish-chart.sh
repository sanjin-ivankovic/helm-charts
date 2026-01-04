#!/bin/bash
# scripts/ci/publish-chart.sh CHART_NAME
# Publishes a Helm chart to OCI registry with idempotency

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
log_info "Publishing chart: $CHART_NAME"
log_info "======================================"

# Verify chart directory exists
if [ ! -d "$CHART_PATH" ]; then
    log_error "Chart directory not found: $CHART_PATH"
    exit 1
fi

# Get chart info
CHART_VERSION=$(get_chart_version "$CHART_PATH")
PACKAGE_FILE="$PACKAGES_DIR/$CHART_NAME-$CHART_VERSION.tgz"

log_info "Chart version: $CHART_VERSION"

# Verify package exists
if [ ! -f "$PACKAGE_FILE" ]; then
    log_error "Package file not found: $PACKAGE_FILE"
    log_error "Run package-chart.sh first to create the package"
    exit 1
fi

# Determine registry path
if [ -n "${CI_REGISTRY_IMAGE:-}" ]; then
    REGISTRY_PATH="oci://$CI_REGISTRY_IMAGE"
    log_info "Using CI_REGISTRY_IMAGE: $CI_REGISTRY_IMAGE"
else
    REGISTRY_HOST="${REGISTRY_HOST:-registry.example.com}"
    REGISTRY_OWNER="${REGISTRY_OWNER:-homelab}"
    REGISTRY_PROJECT="${REGISTRY_PROJECT:-helm-charts}"
    REGISTRY_PATH="oci://$REGISTRY_HOST/$REGISTRY_OWNER/$REGISTRY_PROJECT"
    log_info "Using configured registry: $REGISTRY_PATH"
fi

log_info "Target registry: $REGISTRY_PATH"
log_info "Full chart path: ${REGISTRY_PATH#oci://}/$CHART_NAME:$CHART_VERSION"

# IDEMPOTENCY CHECK: Verify if version already exists
log_info "Checking if chart version already exists in registry..."
if chart_version_exists "${REGISTRY_PATH#oci://}" "$CHART_NAME" "$CHART_VERSION"; then
    log_warn "======================================"
    log_warn "Chart $CHART_NAME:$CHART_VERSION already exists in registry"
    log_warn "Skipping push to prevent overwrite"
    log_warn "======================================"
    log_warn "To publish a new version:"
    log_warn "  1. Bump version in $CHART_PATH/Chart.yaml"
    log_warn "  2. Re-run package and publish steps"
    exit 0
fi

log_info "Version does not exist - proceeding with push"

# Push to registry
log_info "Pushing chart to registry..."
if helm push "$PACKAGE_FILE" "$REGISTRY_PATH" --debug 2>&1 | tee /tmp/helm-push.log; then
    log_success "======================================"
    log_success "Successfully published: $CHART_NAME:$CHART_VERSION"
    log_success "======================================"
    log_success "Pull with:"
    log_success "  helm pull $REGISTRY_PATH/$CHART_NAME --version $CHART_VERSION"
    log_success ""
    log_success "Install with:"
    log_success "  helm install my-release $REGISTRY_PATH/$CHART_NAME --version $CHART_VERSION"
else
    log_error "======================================"
    log_error "Failed to push $CHART_NAME:$CHART_VERSION"
    log_error "======================================"
    log_error "Common causes:"
    log_error "  1. Not logged in to registry"
    log_error "     → Run: echo \$PASSWORD | helm registry login ${REGISTRY_PATH#oci://} -u \$USER --password-stdin"
    log_error "  2. Insufficient permissions"
    log_error "     → Verify your registry access rights"
    log_error "  3. Registry path doesn't exist"
    log_error "     → Verify: $REGISTRY_PATH"
    log_error "  4. Network connectivity issues"
    log_error "     → Test: curl https://${REGISTRY_PATH#oci://}/v2/"
    exit 1
fi
