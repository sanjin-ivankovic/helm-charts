#!/usr/bin/env python3
"""
Detect which Helm charts have changed based on git diff.

This script analyzes git history to determine which charts in the charts/
directory have been modified and need to be validated, packaged, and published.

Usage:
    python3 detect_changes.py [--format json|text] [--output FILE]

Environment Variables:
    CHARTS_DIR: Directory containing charts (default: charts)
    CI_COMMIT_TAG: If set, processes all charts (tag release)
    RELEASE_ALL: If set, processes all charts
    CI_COMMIT_BRANCH: Current branch name
    CI_COMMIT_BEFORE_SHA: Previous commit SHA (for main branch)
    CI_MERGE_REQUEST_TARGET_BRANCH_NAME: Target branch for MR (default: main)
"""

import argparse
import json
import logging
import os
import sys
from functools import lru_cache
from pathlib import Path

from common import ChartHelper, CommandRunner, ExitCode, setup_logging

logger = logging.getLogger(__name__)


class ChartDetector:
    """Detects changed Helm charts in the repository."""

    def __init__(self, charts_dir: str = "charts"):
        self.chart_helper = ChartHelper(Path(charts_dir))
        self.cmd_runner = CommandRunner()
        self.base_ref = os.getenv("CI_MERGE_REQUEST_TARGET_BRANCH_NAME", "main")
        self._git_cache: dict[str, set[str]] = {}

    @lru_cache(maxsize=128)
    def is_valid_chart(self, chart_name: str) -> bool:
        """
        Check if a chart name represents a valid Helm chart (cached).

        Args:
            chart_name: Name of the chart directory

        Returns:
            True if valid chart, False otherwise
        """
        return self.chart_helper.is_valid_chart(chart_name)

    def get_all_charts(self) -> list[str]:
        """
        Get all valid charts in the charts directory.

        Returns:
            Sorted list of chart names
        """
        return self.chart_helper.get_all_charts()

    def get_changed_files(self, comparison: str) -> set[str]:
        """
        Get changed files from git diff (cached).

        Args:
            comparison: Git comparison string (e.g., "HEAD~1..HEAD")

        Returns:
            Set of changed file paths
        """
        if comparison in self._git_cache:
            logger.debug(f"Using cached git diff for: {comparison}")
            return self._git_cache[comparison]

        try:
            exit_code, stdout, stderr = self.cmd_runner.run_git(
                "diff", "--name-only", comparison, check=False
            )

            if exit_code != 0:
                logger.warning(f"Failed to get changed files for: {comparison}")
                if stderr:
                    logger.debug(f"Git error: {stderr}")
                return set()

            files: set[str] = (
                set(stdout.strip().split("\n")) if stdout.strip() else set()
            )
            self._git_cache[comparison] = files
            return files

        except Exception as e:
            logger.warning(f"Exception getting changed files: {e}")
            return set()

    def extract_chart_names(self, files: set[str]) -> set[str]:
        """
        Extract chart names from file paths.

        Args:
            files: Set of file paths

        Returns:
            Set of chart names
        """
        chart_names: set[str] = set()
        charts_dir_str = str(self.chart_helper.charts_dir)

        for file_path in files:
            # Check if file is in charts directory
            if not file_path.startswith(f"{charts_dir_str}/"):
                continue

            # Extract chart name by getting relative path from charts_dir
            try:
                relative_path = Path(file_path).relative_to(charts_dir_str)
                if len(relative_path.parts) < 1:
                    continue

                chart_name = relative_path.parts[0]
            except ValueError:
                # Path is not relative to charts_dir
                continue

            # Validate it's a real chart (using cached check)
            if self.is_valid_chart(chart_name):
                chart_names.add(chart_name)
            else:
                logger.debug(f"Ignoring non-chart change: {file_path}")

        return chart_names

    def fetch_base_ref(self) -> None:
        """Fetch the base reference for comparison."""
        if not os.getenv("CI"):
            logger.debug("Not in CI environment, skipping fetch")
            return

        try:
            logger.info(f"Fetching base ref: {self.base_ref}")
            self.cmd_runner.run_git(
                "fetch", "origin", self.base_ref, "--depth=50", check=True
            )
        except Exception as e:
            logger.warning(f"Failed to fetch {self.base_ref}: {e}")

    def get_comparison_range(self) -> str | None:
        """
        Determine the git comparison range based on environment.

        Returns:
            Comparison string or None if should process all charts
        """
        # Check for tag release
        if os.getenv("CI_COMMIT_TAG"):
            tag = os.getenv("CI_COMMIT_TAG")
            logger.info(f"Tag detected: {tag} - will process all charts")
            return None

        # Check for RELEASE_ALL flag
        if os.getenv("RELEASE_ALL"):
            logger.info("RELEASE_ALL is set - will process all charts")
            return None

        current_branch = os.getenv("CI_COMMIT_BRANCH", "")

        # On main/master branch
        if current_branch in ("main", "master"):
            before_sha = os.getenv("CI_COMMIT_BEFORE_SHA", "")

            if before_sha and before_sha != "0" * 40:
                logger.info(f"Main branch: comparing {before_sha}..HEAD")
                return f"{before_sha}..HEAD"
            else:
                logger.info("Main branch (single commit): comparing HEAD~1..HEAD")
                return "HEAD~1..HEAD"

        # On feature branch or MR
        self.fetch_base_ref()

        # Try to compare with base ref
        try:
            self.cmd_runner.run_git("rev-parse", f"origin/{self.base_ref}", check=True)
            logger.info(f"Comparing against base ref: origin/{self.base_ref}")
            return f"origin/{self.base_ref}...HEAD"
        except Exception:
            logger.warning(
                f"Could not find origin/{self.base_ref}, comparing with HEAD~1"
            )
            return "HEAD~1..HEAD"

    def detect_changes(self) -> list[str]:
        """
        Detect which charts have changed.

        Returns:
            Sorted list of changed chart names
        """
        comparison = self.get_comparison_range()

        # Process all charts if no comparison range
        if comparison is None:
            return self.get_all_charts()

        # Get changed files and extract chart names
        changed_files = self.get_changed_files(comparison)

        if not changed_files:
            logger.warning("No files changed in this commit")
            return []

        chart_names = self.extract_chart_names(changed_files)

        if not chart_names:
            logger.warning("No charts changed in this commit")
            return []

        logger.info("Found changed charts:")
        for chart in sorted(chart_names):
            logger.info(f"  - {chart}")

        return sorted(chart_names)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Detect changed Helm charts in the repository"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument("--output", type=str, help="Output file (default: stdout)")
    parser.add_argument(
        "--charts-dir",
        type=str,
        default=os.getenv("CHARTS_DIR", "charts"),
        help="Charts directory (default: charts)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    setup_logging(level=logging.DEBUG if args.verbose else logging.INFO)

    # Detect changes
    detector = ChartDetector(charts_dir=args.charts_dir)
    changed_charts = detector.detect_changes()

    # Format output
    if args.format == "json":
        output = json.dumps({"charts": changed_charts}, indent=2)
    else:
        output = "\n".join(changed_charts)
        if output:  # Add trailing newline if there's content
            output += "\n"

    # Write output
    if args.output:
        Path(args.output).write_text(output)
        logger.info(f"Wrote output to: {args.output}")
    else:
        print(output)

    # Print formatted summary (always to stdout)
    print("=" * 50)
    print("Changed charts detected:")
    if changed_charts:
        for chart in changed_charts:
            print(f"  - {chart}")
    else:
        print("  (none)")
    print("=" * 50)

    sys.exit(ExitCode.SUCCESS)


if __name__ == "__main__":
    main()
