"""CI environment variable helpers.

These small accessors read the GitLab CI `CI_*` env vars (e.g.
`CI_COMMIT_SHORT_SHA`, `CI_REGISTRY_IMAGE`) that the pipeline sets, with
sensible fallbacks for local runs.
"""

from __future__ import annotations

import os


def commit_branch() -> str:
    """Branch name the build is on."""
    return os.getenv("CI_COMMIT_BRANCH", "")


def commit_ref_name() -> str:
    """Human-readable commit ref name (branch or tag)."""
    return os.getenv("CI_COMMIT_REF_NAME") or "unknown"


def commit_sha() -> str:
    """Full commit SHA."""
    return os.getenv("CI_COMMIT_SHA") or ""


def commit_short_sha() -> str:
    """Short (8-char) commit SHA; derive from the full SHA when missing."""
    short = os.getenv("CI_COMMIT_SHORT_SHA")
    if short:
        return short
    full = commit_sha()
    return full[:8] if full else "unknown"


def commit_before_sha() -> str:
    """Previous commit SHA (used for `git diff <before>..HEAD`)."""
    return os.getenv("CI_COMMIT_BEFORE_SHA") or ""


def commit_tag() -> str:
    """Tag name if the build was triggered by a tag, else empty."""
    return os.getenv("CI_COMMIT_TAG", "")


def merge_request_target_branch() -> str:
    """Target branch of an MR (defaults to 'main')."""
    return os.getenv("CI_MERGE_REQUEST_TARGET_BRANCH_NAME") or "main"


def registry_image() -> str | None:
    """Container/OCI registry path for this repo's artifacts.

    GitLab CI provides this verbatim. Returning None lets the caller compute a
    default from the registry host/owner/project when it is unset.
    """
    return os.getenv("CI_REGISTRY_IMAGE")
