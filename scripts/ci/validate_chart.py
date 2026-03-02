#!/usr/bin/env python3
"""
Validate a Helm chart: linting, dependency check, and template rendering.

This script performs comprehensive validation of a Helm chart including:
- Helm lint checks
- Dependency updates (if needed)
- Template rendering tests

Usage:
    python3 validate_chart.py CHART_NAME [--charts-dir DIR] [--verbose]

Environment Variables:
    CHARTS_DIR: Directory containing charts (default: charts)
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
    setup_logging,
)

logger = logging.getLogger(__name__)


class ChartValidator:
    """Validates Helm charts."""

    def __init__(self, charts_dir: str = "charts", verbose: bool = False):
        self.chart_helper = ChartHelper(Path(charts_dir))
        self.cmd_runner = CommandRunner(verbose=verbose)

    def validate_chart(self, chart_name: str) -> bool:
        """
        Validate a Helm chart.

        Args:
            chart_name: Name of the chart to validate

        Returns:
            True if validation passed, False otherwise
        """
        logger.info("=" * 70)
        logger.info(f"Validating chart: {chart_name}")
        logger.info("=" * 70)

        # Get and verify chart path
        try:
            chart_path = self.chart_helper.get_chart_path(chart_name)
            metadata = self.chart_helper.read_chart_metadata(chart_name)

            logger.info(f"Chart name: {metadata.name}")
            logger.info(f"Chart version: {metadata.version}")
            logger.info(f"App version: {metadata.app_version}")

            # Verify chart name matches directory
            if chart_name != metadata.name:
                logger.warning(
                    f"Chart directory name ({chart_name}) doesn't match "
                    f"Chart.yaml name ({metadata.name})"
                )
        except (ChartNotFoundError, ChartValidationError) as e:
            logger.error(str(e))
            return False

        # Step 1: Run helm lint
        if not self._run_lint(chart_path):
            return False

        # Step 2: Update dependencies if they exist
        if metadata.has_dependencies:
            if not self._update_dependencies(chart_path):
                return False
        else:
            logger.info("Step 2/3: No dependencies found - skipping dependency update")

        # Step 3: Test template rendering
        if not self._test_rendering(chart_path):
            return False

        logger.info("=" * 70)
        logger.info(f"✓ Chart validation PASSED: {chart_name}")
        logger.info("=" * 70)

        return True

    def _run_lint(self, chart_path: Path) -> bool:
        """Run helm lint on the chart."""
        logger.info("Step 1/3: Running helm lint...")

        exit_code, stdout, stderr = self.cmd_runner.run_helm(
            "lint", str(chart_path), check=False
        )

        if exit_code == 0:
            logger.info("✓ Lint passed")
            if stdout:
                logger.debug(f"Lint output:\n{stdout}")
            return True
        else:
            logger.error("✗ Lint failed")
            if stdout:
                logger.error(f"Stdout:\n{stdout}")
            if stderr:
                logger.error(f"Stderr:\n{stderr}")
            return False

    def _update_dependencies(self, chart_path: Path) -> bool:
        """Update chart dependencies."""
        logger.info("Step 2/3: Updating dependencies...")

        exit_code, stdout, stderr = self.cmd_runner.run_helm(
            "dependency", "update", str(chart_path), check=False
        )

        if exit_code == 0:
            logger.info("✓ Dependencies updated")
            if stdout:
                logger.debug(f"Dependency output:\n{stdout}")
            return True
        else:
            logger.error("✗ Dependency update failed")
            if stdout:
                logger.error(f"Stdout:\n{stdout}")
            if stderr:
                logger.error(f"Stderr:\n{stderr}")
            return False

    def _test_rendering(self, chart_path: Path) -> bool:
        """Test template rendering."""
        logger.info("Step 3/3: Testing template rendering...")

        exit_code, _stdout, stderr = self.cmd_runner.run_helm(
            "template", "test-release", str(chart_path), "--dry-run", check=False
        )

        if exit_code == 0:
            logger.info("✓ Template rendering passed")
            return True
        else:
            logger.error("✗ Template rendering failed")
            logger.error(
                f"Run 'helm template test-release {chart_path}' to see details"
            )
            if stderr:
                logger.error(f"Stderr:\n{stderr}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate a Helm chart")
    parser.add_argument("chart_name", nargs="?", help="Name of the chart to validate")
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
            logger.info("No charts to validate - input file is empty")
            sys.exit(ExitCode.SUCCESS)
        chart_names = [
            line.strip() for line in input_path.read_text().splitlines() if line.strip()
        ]
    elif args.chart_name:
        chart_names = [args.chart_name]
    else:
        parser.error("Either chart_name or --input-file must be provided")

    # Validate charts
    validator = ChartValidator(charts_dir=args.charts_dir, verbose=args.verbose)
    failed_charts: list[str] = []

    for chart_name in chart_names:
        if not validator.validate_chart(chart_name):
            failed_charts.append(chart_name)

    # Report results
    if failed_charts:
        logger.error(f"\n✗ Validation failed for {len(failed_charts)} chart(s):")
        for chart in failed_charts:
            logger.error(f"  - {chart}")
        sys.exit(ExitCode.FAILURE)

    sys.exit(ExitCode.SUCCESS)


if __name__ == "__main__":
    main()
