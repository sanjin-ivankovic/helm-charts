#!/usr/bin/env python3
"""
Publish a Helm chart to OCI registry with idempotency.

This script publishes a packaged Helm chart to an OCI registry, handling:
- Idempotency checks (skip if version exists)
- Registry authentication
- Retry logic
- Detailed error reporting

Usage:
    python3 publish_chart.py CHART_NAME [--charts-dir DIR] [--packages-dir DIR]

Environment Variables:
    CHARTS_DIR: Directory containing charts (default: charts)
    PACKAGES_DIR: Directory with packaged charts (default: .packages)
    CI_REGISTRY_IMAGE: GitLab registry image path
    REGISTRY_HOST: Registry hostname (default: registry.example.com)
    REGISTRY_OWNER: Registry owner (default: homelab)
    REGISTRY_PROJECT: Registry project (default: helm-charts)
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


class ChartPublisher:
    """Publishes Helm charts to OCI registries."""

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

    def chart_version_exists(
        self, registry_path: str, chart_name: str, version: str
    ) -> bool:
        """
        Check if a chart version already exists in the registry.

        Args:
            registry_path: Registry path (without oci:// prefix)
            chart_name: Chart name
            version: Chart version

        Returns:
            True if version exists, False otherwise
        """
        logger.info(f"Checking if {chart_name}:{version} exists in registry...")

        exit_code, _stdout, _stderr = self.cmd_runner.run_helm(
            "show",
            "chart",
            f"oci://{registry_path}/{chart_name}",
            "--version",
            version,
            check=False,
        )

        return exit_code == 0

    def get_registry_path(self) -> str:
        """
        Determine the OCI registry path.

        Returns:
            Registry path with oci:// prefix
        """
        if ci_registry := os.getenv("CI_REGISTRY_IMAGE"):
            logger.info(f"Using CI_REGISTRY_IMAGE: {ci_registry}")
            return f"oci://{ci_registry}"

        # Fallback to configured registry
        host = os.getenv("REGISTRY_HOST", "registry.example.com")
        owner = os.getenv("REGISTRY_OWNER", "homelab")
        project = os.getenv("REGISTRY_PROJECT", "helm-charts")
        registry_path = f"oci://{host}/{owner}/{project}"

        logger.info(f"Using configured registry: {registry_path}")
        return registry_path

    def publish_chart(self, chart_name: str) -> bool:
        """
        Publish a Helm chart to OCI registry.

        Args:
            chart_name: Name of the chart to publish

        Returns:
            True if publishing succeeded, False otherwise
        """
        logger.info("=" * 70)
        logger.info(f"Publishing chart: {chart_name}")
        logger.info("=" * 70)

        # Get chart metadata
        try:
            chart_path = self.chart_helper.get_chart_path(chart_name)
            metadata = self.chart_helper.read_chart_metadata(chart_name)
            logger.info(f"Chart version: {metadata.version}")
        except (ChartNotFoundError, ChartValidationError) as e:
            logger.error(str(e))
            return False

        # Verify package exists
        package_file = self.packages_dir / f"{chart_name}-{metadata.version}.tgz"
        if not package_file.exists():
            logger.error(f"Package file not found: {package_file}")
            logger.error("Run package_chart.py first to create the package")
            return False

        # Get registry path
        registry_path = self.get_registry_path()
        registry_path_clean = registry_path.replace("oci://", "")

        logger.info(f"Target registry: {registry_path}")
        logger.info(
            f"Full chart path: {registry_path_clean}/{chart_name}:{metadata.version}"
        )

        # Idempotency check
        if self.chart_version_exists(registry_path_clean, chart_name, metadata.version):
            logger.warning("=" * 70)
            logger.warning(
                f"Chart {chart_name}:{metadata.version} already exists in registry"
            )
            logger.warning("Skipping push to prevent overwrite")
            logger.warning("=" * 70)
            logger.warning("To publish a new version:")
            logger.warning(f"  1. Bump version in {chart_path}/Chart.yaml")
            logger.warning("  2. Re-run package and publish steps")
            return True  # Not an error - idempotent behavior

        logger.info("Version does not exist - proceeding with push")

        # Push to registry
        return self._push_to_registry(
            package_file,
            registry_path,
            chart_name,
            metadata.version,
            registry_path_clean,
        )

    def _push_to_registry(
        self,
        package_file: Path,
        registry_path: str,
        chart_name: str,
        version: str,
        registry_path_clean: str,
    ) -> bool:
        """Push chart package to registry."""
        logger.info("Pushing chart to registry...")

        exit_code, _stdout, stderr = self.cmd_runner.run_helm(
            "push", str(package_file), registry_path, "--debug", check=False
        )

        if exit_code == 0:
            logger.info("=" * 70)
            logger.info(f"✓ Successfully published: {chart_name}:{version}")
            logger.info("=" * 70)
            logger.info("Pull with:")
            logger.info(f"  helm pull {registry_path}/{chart_name} --version {version}")
            logger.info("")
            logger.info("Install with:")
            logger.info(
                f"  helm install my-release {registry_path}/{chart_name} --version {version}"
            )
            return True
        else:
            logger.error("=" * 70)
            logger.error(f"✗ Failed to push {chart_name}:{version}")
            logger.error("=" * 70)
            logger.error("Common causes:")
            logger.error("  1. Not logged in to registry")
            logger.error(
                f"     → Run: echo $PASSWORD | helm registry login {registry_path_clean} -u $USER --password-stdin"
            )
            logger.error("  2. Insufficient permissions")
            logger.error("     → Verify your registry access rights")
            logger.error("  3. Registry path doesn't exist")
            logger.error(f"     → Verify: {registry_path}")
            logger.error("  4. Network connectivity issues")
            logger.error(f"     → Test: curl https://{registry_path_clean}/v2/")

            if stderr:
                logger.error(f"\nError details:\n{stderr}")

            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Publish a Helm chart to OCI registry")
    parser.add_argument("chart_name", nargs="?", help="Name of the chart to publish")
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
            logger.info("No charts to publish - input file is empty")
            sys.exit(ExitCode.SUCCESS)
        chart_names = [
            line.strip() for line in input_path.read_text().splitlines() if line.strip()
        ]
    elif args.chart_name:
        chart_names = [args.chart_name]
    else:
        parser.error("Either chart_name or --input-file must be provided")

    # Publish charts
    publisher = ChartPublisher(
        charts_dir=args.charts_dir, packages_dir=args.packages_dir, verbose=args.verbose
    )
    failed_charts: list[str] = []
    published_count = 0

    for chart_name in chart_names:
        if publisher.publish_chart(chart_name):
            published_count += 1
        else:
            failed_charts.append(chart_name)

    # Report results
    logger.info(f"\nPublished {published_count} chart(s)")
    if failed_charts:
        logger.error(f"\n✗ Publishing failed for {len(failed_charts)} chart(s):")
        for chart in failed_charts:
            logger.error(f"  - {chart}")
        sys.exit(ExitCode.FAILURE)

    sys.exit(ExitCode.SUCCESS)


if __name__ == "__main__":
    main()
