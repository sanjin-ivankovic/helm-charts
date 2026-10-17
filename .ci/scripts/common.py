#!/usr/bin/env python3
"""
Shared utilities for CI scripts.

This module provides common functionality used across multiple CI scripts
to reduce code duplication and improve maintainability.
"""

import logging
import subprocess
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any

import yaml


class ExitCode(IntEnum):
    """Standard exit codes for CI scripts."""

    SUCCESS = 0
    FAILURE = 1
    VALIDATION_ERROR = 2
    NOT_FOUND = 3


class ChartError(Exception):
    """Base exception for chart-related errors."""

    pass


class ChartNotFoundError(ChartError):
    """Raised when a chart directory or Chart.yaml is not found."""

    pass


class ChartValidationError(ChartError):
    """Raised when chart validation fails."""

    pass


def _empty_dependencies() -> list[dict[str, Any]]:
    """Factory function for empty dependencies list."""
    return []


@dataclass(frozen=True)
class ChartMetadata:
    """Parsed Chart.yaml metadata."""

    name: str
    version: str
    app_version: str
    api_version: str = "v2"
    kube_version: str | None = None
    description: str | None = None
    dependencies: list[dict[str, Any]] = field(default_factory=_empty_dependencies)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChartMetadata":
        """Create ChartMetadata from parsed YAML dict."""
        return cls(
            name=str(data.get("name", "")),
            version=str(data.get("version", "")),
            app_version=str(data.get("appVersion", "")),
            api_version=str(data.get("apiVersion", "v2")),
            kube_version=(
                str(data.get("kubeVersion")) if data.get("kubeVersion") else None
            ),
            description=(
                str(data.get("description")) if data.get("description") else None
            ),
            dependencies=list(data.get("dependencies") or []),
        )

    @property
    def has_dependencies(self) -> bool:
        """Check if chart has dependencies."""
        return bool(self.dependencies)


class CommandRunner:
    """Executes external commands with consistent error handling."""

    def __init__(self, cwd: Path | None = None, verbose: bool = False):
        self.cwd = cwd
        self.verbose = verbose
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(
        self, args: list[str], check: bool = True, capture: bool = True
    ) -> tuple[int, str, str]:
        """
        Run a command and return exit code, stdout, stderr.

        Args:
            args: Command and arguments to execute
            check: If True, raise exception on non-zero exit
            capture: If True, capture stdout/stderr

        Returns:
            Tuple of (exit_code, stdout, stderr)

        Raises:
            subprocess.CalledProcessError: If check=True and command fails
        """
        if self.verbose:
            self.logger.debug(f"Running: {' '.join(args)}")

        try:
            result = subprocess.run(
                args,
                cwd=self.cwd,
                capture_output=capture,
                text=True,
                check=check,
            )
            return (result.returncode, result.stdout, result.stderr)
        except subprocess.CalledProcessError as e:
            if capture:
                return (e.returncode, e.stdout or "", e.stderr or "")
            raise

    def run_helm(
        self, subcommand: str, *args: str, check: bool = True
    ) -> tuple[int, str, str]:
        """
        Run a helm command.

        Args:
            subcommand: Helm subcommand (e.g., 'lint', 'package')
            args: Additional arguments
            check: If True, raise exception on non-zero exit

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        return self.run(["helm", subcommand, *args], check=check)

    def run_git(self, *args: str, check: bool = True) -> tuple[int, str, str]:
        """
        Run a git command.

        Args:
            args: Git arguments
            check: If True, raise exception on non-zero exit

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        return self.run(["git", *args], check=check)


class ChartHelper:
    """Helper methods for working with Helm charts."""

    def __init__(self, charts_dir: Path):
        self.charts_dir = Path(charts_dir)
        self.logger = logging.getLogger(self.__class__.__name__)

    def is_valid_chart(self, chart_name: str) -> bool:
        """
        Check if a chart name represents a valid Helm chart.

        Args:
            chart_name: Name of the chart directory

        Returns:
            True if valid chart, False otherwise
        """
        # Exclude empty names and dotfiles
        if not chart_name or chart_name.startswith("."):
            return False

        chart_path = self.charts_dir / chart_name

        # Must be a directory with Chart.yaml
        if not chart_path.is_dir():
            return False

        if not (chart_path / "Chart.yaml").exists():
            return False

        return True

    def get_chart_path(self, chart_name: str) -> Path:
        """
        Get path to a chart directory.

        Args:
            chart_name: Name of the chart

        Returns:
            Path to chart directory

        Raises:
            ChartNotFoundError: If chart doesn't exist
        """
        chart_path = self.charts_dir / chart_name

        if not chart_path.is_dir():
            raise ChartNotFoundError(f"Chart directory not found: {chart_path}")

        if not (chart_path / "Chart.yaml").exists():
            raise ChartNotFoundError(f"Chart.yaml not found in {chart_path}")

        return chart_path

    def read_chart_metadata(self, chart_name: str) -> ChartMetadata:
        """
        Read and parse Chart.yaml metadata.

        Args:
            chart_name: Name of the chart

        Returns:
            ChartMetadata object

        Raises:
            ChartNotFoundError: If Chart.yaml doesn't exist
            ChartValidationError: If Chart.yaml is invalid
        """
        chart_path = self.get_chart_path(chart_name)
        chart_yaml = chart_path / "Chart.yaml"

        try:
            with open(chart_yaml) as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                raise ChartValidationError(f"Invalid Chart.yaml format in {chart_path}")

            return ChartMetadata.from_dict(data)  # type: ignore[arg-type]

        except yaml.YAMLError as e:
            raise ChartValidationError(f"Failed to parse Chart.yaml: {e}") from e
        except OSError as e:
            raise ChartNotFoundError(f"Failed to read Chart.yaml: {e}") from e

    def get_all_charts(self) -> list[str]:
        """
        Get all valid charts in the charts directory.

        Returns:
            Sorted list of chart names
        """
        if not self.charts_dir.exists():
            self.logger.warning(f"Charts directory not found: {self.charts_dir}")
            return []

        charts: list[str] = []
        for item in self.charts_dir.iterdir():
            if self.is_valid_chart(item.name):
                charts.append(item.name)

        return sorted(charts)

    def chart_has_dependencies(self, chart_name: str) -> bool:
        """
        Check if chart has dependencies defined.

        Args:
            chart_name: Name of the chart

        Returns:
            True if chart has dependencies

        Raises:
            ChartNotFoundError: If chart doesn't exist
        """
        try:
            metadata = self.read_chart_metadata(chart_name)
            return metadata.has_dependencies
        except (ChartNotFoundError, ChartValidationError) as e:
            self.logger.warning(f"Failed to check dependencies: {e}")
            return False


def setup_logging(
    level: int = logging.INFO, format_string: str | None = None
) -> logging.Logger:
    """
    Configure logging with consistent format.

    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string (default: "%(levelname)s: %(message)s")

    Returns:
        Root logger instance
    """
    if format_string is None:
        format_string = "%(levelname)s: %(message)s"

    logging.basicConfig(level=level, format=format_string, force=True)
    return logging.getLogger()


def create_directory(path: Path, exist_ok: bool = True) -> None:
    """
    Create directory with parents.

    Args:
        path: Directory path to create
        exist_ok: If True, don't raise error if directory exists
    """
    path.mkdir(parents=True, exist_ok=exist_ok)


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "1.23s", "1m 23s")
    """
    if seconds < 60:
        return f"{seconds:.2f}s"

    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}m {remaining_seconds:.2f}s"
