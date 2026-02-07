# ============================================================================
# Helm Charts Makefile
# ============================================================================
#
# Manage Helm charts: lint, test, package, and publish to OCI registry
#
# Usage:
#   make help              - Show this help
#   make lint CHART=searxng - Lint single chart
#   make test CHART=searxng - Test single chart templates
#   make validate CHART=searxng - Lint + test single chart
#   make package CHART=searxng - Package single chart
#   make push CHART=searxng - Push single chart to registry
#   make release CHART=searxng - Full workflow: validate, package, push
#   make lint-all          - Lint all charts
#   make test-all          - Test all charts
#   make validate-all      - Lint + test all charts
#
# Version Management:
#   make version-bump CHART=searxng TYPE=patch  - Bump version (patch/minor/major)
#   make version-show CHART=searxng             - Show current version
#
# ============================================================================

.PHONY: help
.DEFAULT_GOAL := help

# ============================================================================
# Configuration
# ============================================================================

CHARTS_DIR := charts
PACKAGES_DIR := .packages
# Registry Configuration
# Use GitLab CI variables if available, otherwise fallback to defaults
REGISTRY_HOST ?= registry.example.com
REGISTRY_OWNER ?= homelab
REGISTRY_PROJECT ?= helm-charts

ifdef CI_REGISTRY
  REGISTRY_HOST := $(CI_REGISTRY)
endif

# GitLab Container Registry path: oci://<host>/<owner>/<project>
# Charts are pushed as: oci://<host>/<owner>/<project>/<chart-name>
ifdef CI_REGISTRY_IMAGE
  REGISTRY_PATH := oci://$(CI_REGISTRY_IMAGE)
else
  REGISTRY_PATH := oci://$(REGISTRY_HOST)/$(REGISTRY_OWNER)/$(REGISTRY_PROJECT)
endif

# Chart selection (use CHART= variable or detect from git)
CHART ?=
CHARTS := $(shell find $(CHARTS_DIR) -maxdepth 1 -mindepth 1 -type d -exec basename {} \;)

# Version bump type (patch, minor, major)
TYPE ?= patch

# Colors for output
COLOR_RESET := \033[0m
COLOR_BOLD := \033[1m
COLOR_GREEN := \033[32m
COLOR_YELLOW := \033[33m
COLOR_RED := \033[31m
COLOR_BLUE := \033[34m

# ============================================================================
# Helper Functions
# ============================================================================

define print_header
	@echo ""
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)═══════════════════════════════════════════════════════════$(COLOR_RESET)"
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)  $(1)$(COLOR_RESET)"
	@echo "$(COLOR_BOLD)$(COLOR_BLUE)═══════════════════════════════════════════════════════════$(COLOR_RESET)"
	@echo ""
endef

define print_success
	@echo "$(COLOR_GREEN)✓$(COLOR_RESET) $(1)"
endef

define print_error
	@echo "$(COLOR_RED)✗$(COLOR_RESET) $(1)"
endef

define print_warning
	@echo "$(COLOR_YELLOW)⚠$(COLOR_RESET) $(1)"
endef

define print_info
	@echo "$(COLOR_BLUE)ℹ$(COLOR_RESET) $(1)"
endef

define check_chart_exists
	@if [ ! -d "$(CHARTS_DIR)/$(1)" ]; then \
		echo "$(COLOR_RED)Error: Chart '$(1)' not found in $(CHARTS_DIR)/$(COLOR_RESET)"; \
		echo "Available charts: $(CHARTS)"; \
		exit 1; \
	fi
endef

define get_chart_version
	grep "^version:" $(CHARTS_DIR)/$(1)/Chart.yaml | awk '{print $$2}' | tr -d '"'
endef

define get_chart_name
	grep "^name:" $(CHARTS_DIR)/$(1)/Chart.yaml | awk '{print $$2}' | tr -d '"'
endef

# ============================================================================
# Help Target
# ============================================================================

help: ## Show this help message
	@echo "$(COLOR_BOLD)Helm Charts Makefile$(COLOR_RESET)"
	@echo ""
	@echo "$(COLOR_BOLD)Usage:$(COLOR_RESET)"
	@echo "  make <target> [CHART=<chart-name>] [TYPE=patch|minor|major]"
	@echo ""
	@echo "$(COLOR_BOLD)Single Chart Operations:$(COLOR_RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		grep -v "all\|help" | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(COLOR_BLUE)%-20s$(COLOR_RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(COLOR_BOLD)Batch Operations:$(COLOR_RESET)"
	@grep -E '^[a-zA-Z_-]+-all:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(COLOR_BLUE)%-20s$(COLOR_RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(COLOR_BOLD)Version Management:$(COLOR_RESET)"
	@grep -E '^version-.*:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(COLOR_BLUE)%-20s$(COLOR_RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(COLOR_BOLD)Utility:$(COLOR_RESET)"
	@grep -E '^(login|list-charts|clean):.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(COLOR_BLUE)%-20s$(COLOR_RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(COLOR_BOLD)Examples:$(COLOR_RESET)"
	@echo "  make validate CHART=searxng          # Lint and test searxng chart"
	@echo "  make release CHART=gitea-runner      # Full workflow for gitea-runner"
	@echo "  make version-bump CHART=pgadmin TYPE=minor  # Bump minor version"
	@echo "  make validate-all                    # Validate all charts"
	@echo ""
	@echo "$(COLOR_BOLD)Available Charts:$(COLOR_RESET)"
	@echo "  $(CHARTS)"
	@echo ""

# ============================================================================
# Validation Targets
# ============================================================================

lint: ## Lint chart (requires CHART=name)
	$(call print_header,Linting Chart: $(CHART))
	@if [ -z "$(CHART)" ]; then \
		echo "$(COLOR_RED)Error: CHART variable required$(COLOR_RESET)"; \
		echo "Usage: make lint CHART=<chart-name>"; \
		exit 1; \
	fi
	$(call check_chart_exists,$(CHART))
	@helm lint $(CHARTS_DIR)/$(CHART) --strict
	$(call print_success,Chart $(CHART) passed linting)

test: ## Test chart templates (requires CHART=name)
	$(call print_header,Testing Chart Templates: $(CHART))
	@if [ -z "$(CHART)" ]; then \
		echo "$(COLOR_RED)Error: CHART variable required$(COLOR_RESET)"; \
		echo "Usage: make test CHART=<chart-name>"; \
		exit 1; \
	fi
	$(call check_chart_exists,$(CHART))
	@echo "Rendering templates..."
	@helm template test-release $(CHARTS_DIR)/$(CHART) > /tmp/rendered-$(CHART).yaml
	@echo "Validating YAML syntax..."
	@python3 -c "import yaml; list(yaml.safe_load_all(open('/tmp/rendered-$(CHART).yaml')))" 2>/dev/null
	@rm -f /tmp/rendered-$(CHART).yaml
	$(call print_success,Chart $(CHART) templates are valid)

validate: lint test ## Lint and test chart (requires CHART=name)
	$(call print_success,Chart $(CHART) validation complete)

lint-all: ## Lint all charts
	$(call print_header,Linting All Charts)
	@for chart in $(CHARTS); do \
		echo ""; \
		echo "$(COLOR_BOLD)Linting: $$chart$(COLOR_RESET)"; \
		helm lint $(CHARTS_DIR)/$$chart --strict || exit 1; \
	done
	$(call print_success,All charts passed linting)

test-all: ## Test all chart templates
	$(call print_header,Testing All Chart Templates)
	@for chart in $(CHARTS); do \
		echo ""; \
		echo "$(COLOR_BOLD)Testing: $$chart$(COLOR_RESET)"; \
		helm template test-release $(CHARTS_DIR)/$$chart > /tmp/rendered-$$chart.yaml || exit 1; \
		python3 -c "import yaml; list(yaml.safe_load_all(open('/tmp/rendered-$$chart.yaml')))" 2>/dev/null || exit 1; \
		rm -f /tmp/rendered-$$chart.yaml; \
	done
	$(call print_success,All chart templates are valid)

validate-all: lint-all test-all ## Lint and test all charts
	$(call print_success,All charts validation complete)

# ============================================================================
# Package & Push Targets
# ============================================================================

package: ## Package chart (requires CHART=name)
	$(call print_header,Packaging Chart: $(CHART))
	@if [ -z "$(CHART)" ]; then \
		echo "$(COLOR_RED)Error: CHART variable required$(COLOR_RESET)"; \
		echo "Usage: make package CHART=<chart-name>"; \
		exit 1; \
	fi
	$(call check_chart_exists,$(CHART))
	@mkdir -p $(PACKAGES_DIR)
	@VERSION=$$($(call get_chart_version,$(CHART))); \
	CHART_NAME=$$($(call get_chart_name,$(CHART))); \
	echo "Packaging $$CHART_NAME version $$VERSION..."; \
	helm package $(CHARTS_DIR)/$(CHART) -d $(PACKAGES_DIR)
	$(call print_success,Chart $(CHART) packaged successfully)
	@ls -lh $(PACKAGES_DIR)/*.tgz | tail -1

push: ## Push chart to OCI registry (requires CHART=name)
	$(call print_header,Pushing Chart to Registry: $(CHART))
	@if [ -z "$(CHART)" ]; then \
		echo "$(COLOR_RED)Error: CHART variable required$(COLOR_RESET)"; \
		echo "Usage: make push CHART=<chart-name>"; \
		exit 1; \
	fi
	$(call check_chart_exists,$(CHART))
	@VERSION=$$($(call get_chart_version,$(CHART))); \
	CHART_NAME=$$($(call get_chart_name,$(CHART))); \
	PACKAGE_FILE="$(PACKAGES_DIR)/$$CHART_NAME-$$VERSION.tgz"; \
	if [ ! -f "$$PACKAGE_FILE" ]; then \
		echo "$(COLOR_YELLOW)Package not found, creating it...$(COLOR_RESET)"; \
		$(MAKE) package CHART=$(CHART); \
	fi; \
	echo ""; \
	echo "$(COLOR_YELLOW)About to push: $$CHART_NAME:$$VERSION$(COLOR_RESET)"; \
	echo "Registry: $(REGISTRY_PATH)"; \
	echo ""; \
	if [ -z "$(CI)" ]; then \
		read -p "Continue? [y/N] " -n 1 -r; \
		echo; \
		if [[ ! $$REPLY =~ ^[Yy]$$ ]]; then \
			echo "$(COLOR_YELLOW)Push cancelled$(COLOR_RESET)"; \
			exit 1; \
		fi; \
	fi; \
	helm push "$$PACKAGE_FILE" $(REGISTRY_PATH) && \
	echo "" && \
	echo "$(COLOR_GREEN)✓$(COLOR_RESET) Chart $$CHART_NAME:$$VERSION pushed successfully" && \
	echo "" && \
	echo "$(COLOR_BOLD)Pull command:$(COLOR_RESET)" && \
	echo "  helm pull $(REGISTRY_PATH)/$$CHART_NAME --version $$VERSION";

release: validate package push ## Full release workflow (requires CHART=name)
	@echo "$(COLOR_GREEN)✓$(COLOR_RESET) Chart $(CHART) released successfully"

release-all: ## Release all charts
	$(call print_header,Releasing All Charts)
	@for chart in $(CHARTS); do \
		echo ""; \
		echo "$(COLOR_BOLD)Releasing: $$chart$(COLOR_RESET)"; \
		$(MAKE) release CHART=$$chart || exit 1; \
	done
	$(call print_success,All charts released successfully)

# ============================================================================
# Version Management
# ============================================================================

version-show: ## Show chart version (requires CHART=name)
	@if [ -z "$(CHART)" ]; then \
		echo "$(COLOR_RED)Error: CHART variable required$(COLOR_RESET)"; \
		echo "Usage: make version-show CHART=<chart-name>"; \
		exit 1; \
	fi
	$(call check_chart_exists,$(CHART))
	@VERSION=$$($(call get_chart_version,$(CHART))); \
	CHART_NAME=$$($(call get_chart_name,$(CHART))); \
	echo "Chart: $$CHART_NAME"; \
	echo "Version: $$VERSION"

version-bump: ## Bump chart version (requires CHART=name TYPE=patch|minor|major)
	$(call print_header,Bumping Chart Version: $(CHART))
	@if [ -z "$(CHART)" ]; then \
		echo "$(COLOR_RED)Error: CHART variable required$(COLOR_RESET)"; \
		echo "Usage: make version-bump CHART=<chart-name> TYPE=patch"; \
		exit 1; \
	fi
	$(call check_chart_exists,$(CHART))
	@CURRENT_VERSION=$$($(call get_chart_version,$(CHART))); \
	echo "Current version: $$CURRENT_VERSION"; \
	IFS='.' read -r major minor patch <<< "$$CURRENT_VERSION"; \
	case "$(TYPE)" in \
		major) NEW_VERSION="$$((major + 1)).0.0" ;; \
		minor) NEW_VERSION="$$major.$$((minor + 1)).0" ;; \
		patch) NEW_VERSION="$$major.$$minor.$$((patch + 1))" ;; \
		*) echo "$(COLOR_RED)Error: TYPE must be patch, minor, or major$(COLOR_RESET)"; exit 1 ;; \
	esac; \
	echo "New version: $$NEW_VERSION"; \
	echo ""; \
	read -p "Update Chart.yaml? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		sed -i.bak "s/^version: .*/version: $$NEW_VERSION/" $(CHARTS_DIR)/$(CHART)/Chart.yaml; \
		rm -f $(CHARTS_DIR)/$(CHART)/Chart.yaml.bak; \
		$(call print_success,Version updated to $$NEW_VERSION); \
		echo ""; \
		echo "$(COLOR_YELLOW)Next steps:$(COLOR_RESET)"; \
		echo "  1. Review changes: git diff $(CHARTS_DIR)/$(CHART)/Chart.yaml"; \
		echo "  2. Commit: git add $(CHARTS_DIR)/$(CHART)/Chart.yaml && git commit -m 'Bump $(CHART) to $$NEW_VERSION'"; \
		echo "  3. Release: make release CHART=$(CHART)"; \
	else \
		echo "$(COLOR_YELLOW)Version bump cancelled$(COLOR_RESET)"; \
	fi

# ============================================================================
# Utility Targets
# ============================================================================

login: ## Login to OCI registry
	$(call print_header,Login to OCI Registry)
	@echo "Registry: $(REGISTRY_HOST)"
	@echo "$(COLOR_YELLOW)Note: For GitLab, use a Personal Access Token (PAT) with 'api' or 'read_registry/write_registry' scopes as the password.$(COLOR_RESET)"
	@if [ -n "$(CI_REGISTRY_USER)" ] && [ -n "$(CI_REGISTRY_PASSWORD)" ]; then \
		echo "Logging in using CI credentials..."; \
		echo "$(CI_REGISTRY_PASSWORD)" | helm registry login $(REGISTRY_HOST) --username $(CI_REGISTRY_USER) --password-stdin; \
	else \
		echo "Logging in using local credentials..."; \
		helm registry login $(REGISTRY_HOST); \
	fi
	$(call print_success,Logged in to $(REGISTRY_HOST))

list-charts: ## List all available charts
	@echo "$(COLOR_BOLD)Available Charts:$(COLOR_RESET)"
	@for chart in $(CHARTS); do \
		VERSION=$$($(call get_chart_version,$$chart)); \
		CHART_NAME=$$($(call get_chart_name,$$chart)); \
		printf "  $(COLOR_BLUE)%-20s$(COLOR_RESET) %-10s %s\n" "$$chart" "$$VERSION" "$$CHART_NAME"; \
	done

clean: ## Clean packaged charts
	$(call print_header,Cleaning Packages)
	@rm -rf $(PACKAGES_DIR)
	@rm -f /tmp/rendered-*.yaml
	$(call print_success,Cleaned package directory)

# ============================================================================
# Git Integration (Optional)
# ============================================================================

changed-charts: ## List charts changed in git (compared to main)
	@git diff --name-only main...HEAD 2>/dev/null | \
		grep -E "^$(CHARTS_DIR)/[^/]+" | \
		cut -d'/' -f1-2 | \
		sort -u || echo "No charts changed"

validate-changed: ## Validate only changed charts
	@CHANGED=$$(git diff --name-only main...HEAD 2>/dev/null | \
		grep -E "^$(CHARTS_DIR)/[^/]+" | \
		cut -d'/' -f2 | \
		sort -u); \
	if [ -z "$$CHANGED" ]; then \
		echo "$(COLOR_YELLOW)No charts changed$(COLOR_RESET)"; \
		exit 0; \
	fi; \
	for chart in $$CHANGED; do \
		echo ""; \
		$(MAKE) validate CHART=$$chart || exit 1; \
	done
