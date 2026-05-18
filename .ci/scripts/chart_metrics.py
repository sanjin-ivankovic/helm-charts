#!/usr/bin/env python3
"""
Collect and analyze Helm chart CI/CD metrics.

This script tracks metrics for chart validation, packaging, and publishing
to help identify performance trends and bottlenecks.

Usage:
    python3 chart_metrics.py [--output FILE] [--format markdown|json]

Environment Variables:
    CI_PROJECT_ID: GitLab project ID
    CI_JOB_TOKEN: GitLab job token for API access
    CI_SERVER_URL: GitLab server URL
"""

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar

from common import ExitCode, setup_logging

try:
    import requests  # type: ignore
except ImportError:
    print("ERROR: requests library not found. Install with: pip install requests")
    sys.exit(1)

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT = 30
DEFAULT_PER_PAGE = 100
DEFAULT_SAMPLE_SIZE = 20
DEFAULT_DAYS = 30
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0
MAX_WORKERS = 10

# Type variable for retry decorator
F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class JobMetrics:
    """Metrics for a specific job type."""

    count: int = 0
    total_duration: float = 0.0
    failures: int = 0
    avg_duration: float = 0.0
    failure_rate: float = 0.0

    def calculate_averages(self) -> None:
        """Calculate average duration and failure rate."""
        if self.count > 0:
            self.avg_duration = self.total_duration / self.count
            self.failure_rate = (self.failures / self.count) * 100.0


def _empty_status_dict() -> dict[str, int]:
    """Factory function for empty pipeline statuses dict."""
    return {}


def _empty_job_metrics() -> dict[str, JobMetrics]:
    """Factory function for empty job metrics dict."""
    return {}


@dataclass
class MetricsResult:
    """Container for collected metrics."""

    period_days: int
    total_pipelines: int
    pipeline_statuses: dict[str, int] = field(default_factory=_empty_status_dict)
    job_metrics: dict[str, JobMetrics] = field(default_factory=_empty_job_metrics)
    avg_pipeline_duration: float = 0.0


def retry_with_backoff(max_retries: int = MAX_RETRIES) -> Callable[[F], F]:
    """
    Decorator to retry function calls with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = INITIAL_RETRY_DELAY
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except requests.HTTPError as e:
                    last_exception = e
                    # Don't retry on client errors (4xx) except rate limiting
                    if e.response and 400 <= e.response.status_code < 500:
                        if e.response.status_code == 429:  # Rate limited
                            retry_after = int(
                                e.response.headers.get("Retry-After", delay)
                            )
                            logger.warning(
                                f"Rate limited, waiting {retry_after}s before retry"
                            )
                            time.sleep(retry_after)
                            continue
                        raise  # Don't retry other 4xx errors

                    if attempt < max_retries:
                        logger.warning(
                            f"Request failed (attempt {attempt + 1}/{max_retries + 1}), "
                            f"retrying in {delay}s: {e}"
                        )
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
                except requests.RequestException as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Request failed (attempt {attempt + 1}/{max_retries + 1}), "
                            f"retrying in {delay}s: {e}"
                        )
                        time.sleep(delay)
                        delay *= 2

            # All retries exhausted
            logger.error(f"All {max_retries + 1} attempts failed: {last_exception}")
            raise last_exception  # type: ignore

        return wrapper  # type: ignore

    return decorator


class ChartMetricsCollector:
    """Collects and analyzes chart CI/CD metrics."""

    def __init__(
        self,
        project_id: str,
        token: str,
        gitlab_url: str = "https://gitlab.com",
        verbose: bool = False,
    ):
        self.project_id = project_id
        self.gitlab_url = gitlab_url.rstrip("/")
        self.api_base = f"{self.gitlab_url}/api/v4"
        self.verbose = verbose

        # Setup session with authentication
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )

    def fetch_recent_pipelines(self, days: int = 30) -> list[dict[str, Any]]:
        """
        Fetch recent pipelines.

        Args:
            days: Number of days to look back

        Returns:
            List of pipeline dictionaries
        """
        since = (datetime.now() - timedelta(days=days)).isoformat()
        url = f"{self.api_base}/projects/{self.project_id}/pipelines"

        params: dict[str, str | int] = {
            "updated_after": since,
            "per_page": 100,
            "order_by": "updated_at",
            "sort": "desc",
        }

        logger.info(f"Fetching pipelines from last {days} days...")

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            pipelines = response.json()
            logger.info(f"Found {len(pipelines)} pipelines")
            return pipelines
        except requests.RequestException as e:
            logger.error(f"Failed to fetch pipelines: {e}")
            return []

    def fetch_pipeline_jobs(self, pipeline_id: int) -> list[dict[str, Any]]:
        """
        Fetch jobs for a specific pipeline.

        Args:
            pipeline_id: Pipeline ID

        Returns:
            List of job dictionaries
        """
        url = f"{self.api_base}/projects/{self.project_id}/pipelines/{pipeline_id}/jobs"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.debug(f"Failed to fetch jobs for pipeline {pipeline_id}: {e}")
            return []

    def analyze_metrics(self, days: int = 30) -> dict[str, Any]:
        """
        Analyze chart CI/CD metrics.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary of metrics
        """
        pipelines = self.fetch_recent_pipelines(days)

        if not pipelines:
            logger.warning("No pipelines found")
            return {}

        metrics: dict[str, Any] = {
            "period_days": days,
            "total_pipelines": len(pipelines),
            "pipeline_statuses": {},
            "job_metrics": {
                "detect:changes": {"count": 0, "total_duration": 0.0, "failures": 0},
                "validate:charts": {"count": 0, "total_duration": 0.0, "failures": 0},
                "package:charts": {"count": 0, "total_duration": 0.0, "failures": 0},
                "publish:charts": {"count": 0, "total_duration": 0.0, "failures": 0},
            },
            "avg_pipeline_duration": 0.0,
        }

        # Analyze pipeline statuses
        for pipeline in pipelines:
            status = pipeline.get("status", "unknown")
            metrics["pipeline_statuses"][status] = (
                metrics["pipeline_statuses"].get(status, 0) + 1
            )

        # Analyze job metrics (sample from recent pipelines)
        total_duration = 0
        pipeline_count = 0

        for pipeline in pipelines[:20]:  # Sample last 20 pipelines
            pipeline_id = pipeline.get("id")
            if not pipeline_id:
                continue

            jobs = self.fetch_pipeline_jobs(pipeline_id)

            for job in jobs:
                job_name = job.get("name", "")
                job_status = job.get("status", "")
                job_duration = job.get("duration", 0)

                if job_name in metrics["job_metrics"]:
                    metrics["job_metrics"][job_name]["count"] += 1
                    if job_duration:
                        metrics["job_metrics"][job_name]["total_duration"] += float(
                            job_duration
                        )
                    if job_status == "failed":
                        metrics["job_metrics"][job_name]["failures"] += 1

            # Track pipeline duration
            if pipeline.get("duration"):
                total_duration += pipeline["duration"]
                pipeline_count += 1

        # Calculate averages
        if pipeline_count > 0:
            metrics["avg_pipeline_duration"] = float(total_duration) / pipeline_count

        for job_name, job_data in metrics["job_metrics"].items():
            if job_data["count"] > 0:
                job_data["avg_duration"] = (
                    float(job_data["total_duration"]) / job_data["count"]
                )
                job_data["failure_rate"] = (
                    float(job_data["failures"]) / job_data["count"]
                ) * 100.0
            else:
                job_data["avg_duration"] = 0.0
                job_data["failure_rate"] = 0.0

        return metrics

    def format_markdown(self, metrics: dict[str, Any]) -> str:
        """
        Format metrics as markdown.

        Args:
            metrics: Metrics dictionary

        Returns:
            Markdown formatted string
        """
        if not metrics:
            return "# Chart CI/CD Metrics\n\nNo data available.\n"

        md = ["# Chart CI/CD Metrics\n"]
        md.append(f"**Analysis Period**: Last {metrics['period_days']} days\n")
        md.append(f"**Total Pipelines**: {metrics['total_pipelines']}\n")

        # Pipeline statuses
        md.append("\n## Pipeline Status Distribution\n")
        for status, count in sorted(metrics["pipeline_statuses"].items()):
            percentage = (count / metrics["total_pipelines"]) * 100
            md.append(f"- **{status}**: {count} ({percentage:.1f}%)")

        # Average pipeline duration
        avg_duration_min = metrics["avg_pipeline_duration"] / 60
        md.append(f"\n**Average Pipeline Duration**: {avg_duration_min:.1f} minutes\n")

        # Job metrics
        md.append("\n## Job Performance\n")
        md.append("| Job | Runs | Avg Duration | Failure Rate |")
        md.append("|-----|------|--------------|--------------|")

        for job_name, job_data in metrics["job_metrics"].items():
            if job_data["count"] > 0:
                avg_dur = job_data["avg_duration"]
                failure_rate = job_data["failure_rate"]
                md.append(
                    f"| `{job_name}` | {job_data['count']} | {avg_dur:.1f}s | {failure_rate:.1f}% |"
                )

        return "\n".join(md)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Collect and analyze chart CI/CD metrics"
    )
    parser.add_argument(
        "--project-id",
        type=str,
        default=os.getenv("CI_PROJECT_ID"),
        help="GitLab project ID",
    )
    parser.add_argument(
        "--token", type=str, default=os.getenv("CI_JOB_TOKEN"), help="GitLab API token"
    )
    parser.add_argument(
        "--gitlab-url",
        type=str,
        default=os.getenv("CI_SERVER_URL", "https://gitlab.com"),
        help="GitLab server URL",
    )
    parser.add_argument(
        "--days", type=int, default=30, help="Number of days to analyze (default: 30)"
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument("--output", type=str, help="Output file (default: stdout)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    setup_logging(level=logging.DEBUG if args.verbose else logging.INFO)

    # Validate required arguments
    if not args.project_id:
        logger.error("Project ID is required (--project-id or CI_PROJECT_ID)")
        sys.exit(ExitCode.VALIDATION_ERROR)

    if not args.token:
        logger.error("API token is required (--token or CI_JOB_TOKEN)")
        sys.exit(ExitCode.VALIDATION_ERROR)

    # Collect metrics
    collector = ChartMetricsCollector(
        project_id=args.project_id,
        token=args.token,
        gitlab_url=args.gitlab_url,
        verbose=args.verbose,
    )

    metrics = collector.analyze_metrics(days=args.days)

    # Format output
    if args.format == "json":
        output = json.dumps(metrics, indent=2)
    else:
        output = collector.format_markdown(metrics)

    # Write output
    if args.output:
        Path(args.output).write_text(output)
        logger.info(f"Metrics written to: {args.output}")
    else:
        print(output)

    sys.exit(ExitCode.SUCCESS)


if __name__ == "__main__":
    main()
