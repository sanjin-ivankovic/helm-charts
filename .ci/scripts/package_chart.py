#!/usr/bin/env python3
"""
Package a Helm chart with dependency resolution.

This script packages a Helm chart into a .tgz file, handling:
- Dependency building
- .helmignore synchronization with .gitignore
- Package verification

Usage:
    python3 package_chart.py CHART_NAME [--charts-dir DIR] [--packages-dir DIR]

Environment Variables:
    CHARTS_DIR: Directory containing charts (default: charts)
    PACKAGES_DIR: Directory for packaged charts (default: .packages)
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from common import (
    ChartHelper,
    ChartNotFoundError,
    ChartValidationError,
    CommandRunner,
    ExitCode,
    create_directory,
    setup_logging,
)

logger = logging.getLogger(__name__)


class ChartPackager:
    """Packages Helm charts."""

    def __init__(
        self,
        charts_dir: str = "charts",
        packages_dir: str = ".packages",
        verbose: bool = False,
    ):
        self.chart_helper = ChartHelper(Path(charts_dir))
        self.cmd_runner = CommandRunner(verbose=verbose)
        self.charts_dir = Path(charts_dir)
        self.packages_dir = Path(packages_dir)

    def sync_helmignore(self, chart_path: Path) -> None:
        """
        Sync .gitignore patterns to .helmignore.

        Args:
            chart_path: Path to chart directory
        """
        gitignore_file = self.charts_dir / ".gitignore"
        helmignore_file = chart_path / ".helmignore"

        if not gitignore_file.exists():
            logger.warning(
                f".gitignore not found at {gitignore_file} - skipping pattern sync"
            )
            return

        logger.info("Syncing .gitignore patterns to .helmignore...")

        # Read existing .helmignore patterns
        existing_patterns: set[str] = set()
        if helmignore_file.exists():
            with open(helmignore_file, "r") as f:
                existing_patterns = {
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith("#")
                }

        # Read .gitignore patterns
        with open(gitignore_file, "r") as f:
            gitignore_patterns: set[str] = {
                line.strip() for line in f if line.strip() and not line.startswith("#")
            }

        # Merge patterns
        all_patterns: set[str] = existing_patterns | gitignore_patterns

        # Write merged patterns
        with open(helmignore_file, "w") as f:
            for pattern in sorted(all_patterns):
                f.write(f"{pattern}\n")

        logger.info("Updated .helmignore with .gitignore patterns")

    def package_chart(self, chart_name: str) -> bool:
        """
        Package a Helm chart.

        Args:
            chart_name: Name of the chart to package

        Returns:
            True if packaging succeeded, False otherwise
        """
        logger.info("=" * 70)
        logger.info(f"Packaging chart: {chart_name}")
        logger.info("=" * 70)

        # Get chart metadata and verify chart
        try:
            chart_path = self.chart_helper.get_chart_path(chart_name)
            metadata = self.chart_helper.read_chart_metadata(chart_name)
            logger.info(f"Chart version: {metadata.version}")
        except (ChartNotFoundError, ChartValidationError) as e:
            logger.error(str(e))
            return False

        # Sync .helmignore
        self.sync_helmignore(chart_path)

        # Create packages directory
        create_directory(self.packages_dir)
        logger.info(f"Packages directory: {self.packages_dir}")

        # Build dependencies if they exist
        if metadata.has_dependencies:
            if not self._build_dependencies(chart_path):
                return False
        else:
            logger.info("No dependencies to build")

        # Package the chart
        if not self._package_chart(chart_path):
            return False

        # Verify package file
        package_file = self.packages_dir / f"{chart_name}-{metadata.version}.tgz"
        if not package_file.exists():
            logger.error(f"Package file not found: {package_file}")
            logger.error("Expected file was not created by helm package")
            return False

        # Display package info
        package_size_mb = package_file.stat().st_size / (1024 * 1024)

        logger.info("=" * 70)
        logger.info(f"✓ Package created: {package_file}")
        logger.info(f"✓ Package size: {package_size_mb:.2f} MB")
        logger.info("=" * 70)

        return True

    def _build_dependencies(self, chart_path: Path) -> bool:
        """Build chart dependencies."""
        logger.info("Building dependencies...")

        exit_code, stdout, stderr = self.cmd_runner.run_helm(
            "dependency", "build", str(chart_path), check=False
        )

        if exit_code == 0:
            logger.info("✓ Dependencies built successfully")
            if stdout:
                logger.debug(f"Dependency output:\n{stdout}")
            return True
        else:
            logger.error("✗ Failed to build dependencies")
            if stdout:
                logger.error(f"Stdout:\n{stdout}")
            if stderr:
                logger.error(f"Stderr:\n{stderr}")
            return False

    def _package_chart(self, chart_path: Path) -> bool:
        """Package the chart using helm."""
        logger.info("Packaging chart...")

        exit_code, stdout, stderr = self.cmd_runner.run_helm(
            "package", str(chart_path), "-d", str(self.packages_dir), check=False
        )

        if exit_code == 0:
            logger.info("✓ Chart packaged successfully")
            return True
        else:
            logger.error("✗ Failed to package chart")
            if stdout:
                logger.error(f"Stdout:\n{stdout}")
            if stderr:
                logger.error(f"Stderr:\n{stderr}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Package a Helm chart")
    parser.add_argument("chart_name", nargs="?", help="Name of the chart to package")
    parser.add_argument(
        "--input-file",
        type=str,
        help="File containing chart names (one per line)",
    )
    parser.add_argument(
        "--charts-dir",
        type=str,
        default=os.getenv("CHARTS_DIR", "charts"),
        help="Charts directory (default: charts)",
    )
    parser.add_argument(
        "--packages-dir",
        type=str,
        default=os.getenv("PACKAGES_DIR", ".packages"),
        help="Packages directory (default: .packages)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    setup_logging(level=logging.DEBUG if args.verbose else logging.INFO)

    # Determine chart names to process
    chart_names: list[str] = []
    if args.input_file:
        input_path = Path(args.input_file)
        if not input_path.exists():
            logger.error(f"Input file not found: {input_path}")
            sys.exit(ExitCode.FAILURE)
        if input_path.stat().st_size == 0:
            logger.info("No charts to package - input file is empty")
            sys.exit(ExitCode.SUCCESS)
        chart_names = [
            line.strip() for line in input_path.read_text().splitlines() if line.strip()
        ]
    elif args.chart_name:
        chart_names = [args.chart_name]
    else:
        parser.error("Either chart_name or --input-file must be provided")

    # Package charts
    packager = ChartPackager(
        charts_dir=args.charts_dir, packages_dir=args.packages_dir, verbose=args.verbose
    )
    failed_charts: list[str] = []
    packaged_count = 0

    for chart_name in chart_names:
        if packager.package_chart(chart_name):
            packaged_count += 1
        else:
            failed_charts.append(chart_name)

    # Report results
    logger.info(f"\nPackaged {packaged_count} chart(s)")
    if failed_charts:
        logger.error(f"\n✗ Packaging failed for {len(failed_charts)} chart(s):")
        for chart in failed_charts:
            logger.error(f"  - {chart}")
        sys.exit(ExitCode.FAILURE)

    sys.exit(ExitCode.SUCCESS)


if __name__ == "__main__":
    main()
