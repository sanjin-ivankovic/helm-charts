"""CI-platform-agnostic environment variable helpers.

These small accessors return the right value regardless of which CI
runs the helper (GitLab CI, Gitea Actions, Woodpecker). Each one tries
the GitLab-style name first (for backward compatibility), falling
back to the Woodpecker-native names. Used by detect_changes.py,
notify.py, and publish_chart.py.

When GitLab CI is decommissioned in Phase D of the migration, the
GitLab-style fallbacks can be dropped — but they're harmless until
then and let the same helpers run on both runners.
"""

from __future__ import annotations

import os


def commit_branch() -> str:
    """Branch name the build is on. CI_COMMIT_BRANCH is the same name
    in both GitLab CI and Woodpecker, so no fallback needed."""
    return os.getenv("CI_COMMIT_BRANCH", "")


def commit_ref_name() -> str:
    """Human-readable commit ref name (branch or tag)."""
    return (
        os.getenv("CI_COMMIT_REF_NAME")  # GitLab CI
        or os.getenv("CI_COMMIT_REF")  # Woodpecker
        or "unknown"
    )


def commit_sha() -> str:
    """Full commit SHA."""
    return os.getenv("CI_COMMIT_SHA") or ""


def commit_short_sha() -> str:
    """Short (8-char) commit SHA. Woodpecker doesn't expose this
    natively; derive from the full SHA when missing."""
    short = os.getenv("CI_COMMIT_SHORT_SHA")
    if short:
        return short
    full = commit_sha()
    return full[:8] if full else "unknown"


def commit_before_sha() -> str:
    """Previous commit SHA (used for `git diff <before>..HEAD`)."""
    return (
        os.getenv("CI_COMMIT_BEFORE_SHA")  # GitLab CI
        or os.getenv("CI_PREV_COMMIT_SHA")  # Woodpecker
        or ""
    )


def commit_tag() -> str:
    """Tag name if the build was triggered by a tag, else empty.
    CI_COMMIT_TAG is the same in GitLab CI and Woodpecker."""
    return os.getenv("CI_COMMIT_TAG", "")


def merge_request_target_branch() -> str:
    """Target branch of a PR/MR (defaults to 'main')."""
    return (
        os.getenv("CI_MERGE_REQUEST_TARGET_BRANCH_NAME")  # GitLab CI
        or os.getenv("CI_COMMIT_TARGET_BRANCH")  # Woodpecker
        or "main"
    )


def registry_image() -> str | None:
    """Container/OCI registry path for this repo's artifacts.

    GitLab CI provides this verbatim. Woodpecker doesn't, but the
    workflow YAML can pass it via `environment.CI_REGISTRY_IMAGE`.
    Returning None lets the caller compute a default from
    CI_REPO_NAME/CI_REPO_OWNER if it wants.
    """
    return os.getenv("CI_REGISTRY_IMAGE")
