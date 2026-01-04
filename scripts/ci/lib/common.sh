#!/bin/bash
# scripts/lib/common.sh
# Shared utilities for Helm chart release scripts

set -euo pipefail

# Colors for structured logging
readonly GREEN='\033[0;32m'
readonly BLUE='\033[0;34m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly NC='\033[0m'

# Configuration
CHARTS_DIR="${CHARTS_DIR:-charts}"
PACKAGES_DIR="${PACKAGES_DIR:-.packages}"

# Logging with timestamps and levels
log() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] $*" >&2
}

log_info() {
    log "${BLUE}INFO${NC}  $*"
}

log_success() {
    log "${GREEN}OK${NC}    $*"
}

log_warn() {
    log "${YELLOW}WARN${NC}  $*"
}

log_error() {
    log "${RED}ERROR${NC} $*" >&2
}

# Cleanup trap
cleanup() {
    local exit_code=$?
    # Additional cleanup logic can be added here
    exit "$exit_code"
}
trap cleanup EXIT

# Check if chart version exists in registry (idempotency check)
chart_version_exists() {
    local registry_path=$1
    local chart_name=$2
    local version=$3

    log_info "Checking if $chart_name:$version exists in registry..."

    if helm show chart "oci://${registry_path}/${chart_name}" --version "$version" &>/dev/null; then
        return 0  # exists
    else
        return 1  # does not exist
    fi
}

# Extract version from Chart.yaml
get_chart_version() {
    local chart_path=$1

    if [ ! -f "$chart_path/Chart.yaml" ]; then
        log_error "Chart.yaml not found in $chart_path"
        return 1
    fi

    # Try with yq first (preferred), fallback to grep+awk
    if command -v yq &>/dev/null; then
        yq eval '.version' "$chart_path/Chart.yaml"
    else
        grep "^version:" "$chart_path/Chart.yaml" | awk '{print $2}' | tr -d '"' | tr -d "'"
    fi
}

# Extract name from Chart.yaml
get_chart_name() {
    local chart_path=$1

    if [ ! -f "$chart_path/Chart.yaml" ]; then
        log_error "Chart.yaml not found in $chart_path"
        return 1
    fi

    # Try with yq first (preferred), fallback to grep+awk
    if command -v yq &>/dev/null; then
        yq eval '.name' "$chart_path/Chart.yaml"
    else
        grep "^name:" "$chart_path/Chart.yaml" | awk '{print $2}' | tr -d '"' | tr -d "'"
    fi
}

# Check if chart has dependencies
chart_has_dependencies() {
    local chart_path=$1

    if [ ! -f "$chart_path/Chart.yaml" ]; then
        return 1
    fi

    if command -v yq &>/dev/null; then
        if yq eval '.dependencies' "$chart_path/Chart.yaml" | grep -q 'name:'; then
            return 0
        fi
    else
        if grep -q "^dependencies:" "$chart_path/Chart.yaml"; then
            return 0
        fi
    fi

    return 1
}

# Verify required commands are available
verify_requirements() {
    local missing_commands=()

    for cmd in helm git; do
        if ! command -v "$cmd" &>/dev/null; then
            missing_commands+=("$cmd")
        fi
    done

    if [ ${#missing_commands[@]} -gt 0 ]; then
        log_error "Missing required commands: ${missing_commands[*]}"
        log_error "Please install the missing dependencies"
        return 1
    fi

    return 0
}
