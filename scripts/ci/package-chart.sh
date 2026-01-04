#!/bin/bash
# scripts/ci/package-chart.sh CHART_NAME
# Packages a Helm chart with dependency resolution

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
log_info "Packaging chart: $CHART_NAME"
log_info "======================================"

# Verify chart directory exists
if [ ! -d "$CHART_PATH" ]; then
    log_error "Chart directory not found: $CHART_PATH"
    exit 1
fi

# Ensure .helmignore respects .gitignore patterns
GITIGNORE_FILE="$CHARTS_DIR/.gitignore"
HELMIGNORE_FILE="$CHART_PATH/.helmignore"

if [ -f "$GITIGNORE_FILE" ]; then
    log_info "Syncing .gitignore patterns to .helmignore..."
    # Read .gitignore and merge with existing .helmignore (avoid duplicates)
    TEMP_HELMIGNORE=$(mktemp)

    # Preserve existing .helmignore if it exists
    if [ -f "$HELMIGNORE_FILE" ]; then
        cp "$HELMIGNORE_FILE" "$TEMP_HELMIGNORE"
    fi

    # Add patterns from .gitignore that don't already exist
    while IFS= read -r pattern || [ -n "$pattern" ]; do
        # Skip empty lines and comments
        if [ -n "$pattern" ] && ! echo "$pattern" | grep -qE '^\s*#'; then
            # Normalize pattern (remove leading/trailing whitespace)
            pattern=$(echo "$pattern" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            # Check if pattern already exists in temp file
            if ! grep -Fxq "$pattern" "$TEMP_HELMIGNORE" 2>/dev/null; then
                echo "$pattern" >> "$TEMP_HELMIGNORE"
            fi
        fi
    done < "$GITIGNORE_FILE"

    # Replace .helmignore with merged content
    mv "$TEMP_HELMIGNORE" "$HELMIGNORE_FILE"
    log_info "Updated .helmignore with .gitignore patterns"
else
    log_warn ".gitignore not found at $GITIGNORE_FILE - skipping pattern sync"
fi

# Create packages directory
mkdir -p "$PACKAGES_DIR"
log_info "Packages directory: $PACKAGES_DIR"

# Get chart info
CHART_VERSION=$(get_chart_version "$CHART_PATH")
log_info "Chart version: $CHART_VERSION"

# Build dependencies if they exist
if chart_has_dependencies "$CHART_PATH"; then
    log_info "Building dependencies..."
    if helm dependency build "$CHART_PATH"; then
        log_success "Dependencies built successfully"
    else
        log_error "Failed to build dependencies for $CHART_NAME"
        exit 1
    fi
else
    log_info "No dependencies to build"
fi

# Package the chart
log_info "Packaging chart..."
if helm package "$CHART_PATH" -d "$PACKAGES_DIR"; then
    log_success "Chart packaged successfully"
else
    log_error "Failed to package $CHART_NAME"
    exit 1
fi

# Verify package file exists
PACKAGE_FILE="$PACKAGES_DIR/$CHART_NAME-$CHART_VERSION.tgz"
if [ ! -f "$PACKAGE_FILE" ]; then
    log_error "Package file not found: $PACKAGE_FILE"
    log_error "Expected file was not created by helm package"
    exit 1
fi

# Display package info
PACKAGE_SIZE=$(du -h "$PACKAGE_FILE" | cut -f1)
log_success "======================================"
log_success "Package created: $PACKAGE_FILE"
log_success "Package size: $PACKAGE_SIZE"
log_success "======================================"
