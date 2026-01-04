#!/bin/bash
# scripts/ci/detect-changes.sh
# Detects which Helm charts have changed based on git diff
# Outputs one chart name per line

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
if [ -f "$SCRIPT_DIR/lib/common.sh" ]; then
    source "$SCRIPT_DIR/lib/common.sh"
else
    echo "Error: common.sh not found at $SCRIPT_DIR/lib/common.sh" >&2
    exit 1
fi

CHARTS_DIR="${CHARTS_DIR:-charts}"
BASE_REF="${CI_MERGE_REQUEST_TARGET_BRANCH_NAME:-main}"

is_valid_chart() {
    local chart_name="$1"

    # Exclude empty names and dotfiles like ".gitignore"
    if [ -z "$chart_name" ] || [[ "$chart_name" == .* ]]; then
        return 1
    fi

    # Must be a chart directory with Chart.yaml
    if [ ! -d "$CHARTS_DIR/$chart_name" ]; then
        return 1
    fi
    if [ ! -f "$CHARTS_DIR/$chart_name/Chart.yaml" ]; then
        return 1
    fi

    return 0
}

log_info "Detecting changed charts..."

# If this is a tag or RELEASE_ALL is set, release all charts
if [ -n "${CI_COMMIT_TAG:-}" ]; then
    log_info "Tag detected: ${CI_COMMIT_TAG} - will process all charts"
    for dir in "$CHARTS_DIR"/*; do
        if [ -d "$dir" ] && [ -f "$dir/Chart.yaml" ]; then
            basename "$dir"
        fi
    done
    exit 0
fi

if [ -n "${RELEASE_ALL:-}" ]; then
    log_info "RELEASE_ALL is set - will process all charts"
    for dir in "$CHARTS_DIR"/*; do
        if [ -d "$dir" ] && [ -f "$dir/Chart.yaml" ]; then
            basename "$dir"
        fi
    done
    exit 0
fi

# Otherwise, detect changes via git diff
# Determine comparison strategy
if [ "${CI_COMMIT_BRANCH:-}" = "main" ] || [ "${CI_COMMIT_BRANCH:-}" = "master" ]; then
    # On main/master branch, compare current commit with previous (or push range)
    if [ -n "${CI_COMMIT_BEFORE_SHA:-}" ] && [ "${CI_COMMIT_BEFORE_SHA}" != "0000000000000000000000000000000000000000" ]; then
        log_info "Main branch detected - comparing range ${CI_COMMIT_BEFORE_SHA}..HEAD"
        CHANGED_CHARTS=$(git diff --name-only "${CI_COMMIT_BEFORE_SHA}..HEAD" \
            | grep "^$CHARTS_DIR/" \
            | cut -d/ -f2 \
            | sort -u)
    else
        log_info "Main branch detected (single commit or unknown base) - comparing HEAD~1 with HEAD"
        CHANGED_CHARTS=$(git diff --name-only HEAD~1 HEAD \
            | grep "^$CHARTS_DIR/" \
            | cut -d/ -f2 \
            | sort -u)
    fi
else
    # On feature branches or MRs, fetch base ref and compare
    if [ -n "${CI:-}" ]; then
        log_info "CI environment detected, fetching base ref..."
        git fetch origin "$BASE_REF" --depth=50 || true
    fi

    # Get changed files and extract chart names
    if git rev-parse "origin/$BASE_REF" &>/dev/null; then
        log_info "Comparing against base ref: origin/$BASE_REF"
        CHANGED_CHARTS=$(git diff --name-only "origin/$BASE_REF"...HEAD \
            | grep "^$CHARTS_DIR/" \
            | cut -d/ -f2 \
            | sort -u)
    else
        log_warn "Could not find origin/$BASE_REF, comparing with HEAD~1"
        CHANGED_CHARTS=$(git diff --name-only HEAD~1 HEAD \
            | grep "^$CHARTS_DIR/" \
            | cut -d/ -f2 \
            | sort -u)
    fi
fi

# Filter out non-chart entries (e.g., charts/.gitignore)
FILTERED_CHARTS=""
while IFS= read -r candidate || [ -n "$candidate" ]; do
    if is_valid_chart "$candidate"; then
        FILTERED_CHARTS+="$candidate"$'\n'
    else
        log_info "Ignoring non-chart change under $CHARTS_DIR/: $candidate"
    fi
done <<< "${CHANGED_CHARTS:-}"

CHANGED_CHARTS=$(echo -n "$FILTERED_CHARTS" | sed '/^$/d' | sort -u)

if [ -z "$CHANGED_CHARTS" ]; then
    log_warn "No charts changed in this commit"
    exit 0
fi

log_success "Found changed charts:"
for chart in $CHANGED_CHARTS; do
    log_success "  - $chart"
done

echo "$CHANGED_CHARTS"
