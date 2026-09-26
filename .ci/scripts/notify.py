#!/usr/bin/env python3
"""
Send pipeline notifications for chart validation and publishing.

This script provides formatted console output and optional Discord webhook
notifications for pipeline milestones.

Usage:
    python3 notify.py --type validated --input-file changed-charts.txt
    python3 notify.py --type published --input-file changed-charts.txt

Environment Variables:
    CI_REGISTRY_IMAGE: OCI registry image path (GitLab CI env name)
    CI_COMMIT_SHORT_SHA: Short commit SHA
    CI_COMMIT_REF_NAME: Branch or tag name
    DISCORD_WEBHOOK_URL: Discord webhook URL (optional)
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import ci_env
from common import ExitCode, setup_logging

logger = logging.getLogger(__name__)


class NotificationSender:
    """Sends pipeline notifications."""

    def __init__(self, notification_type: str):
        self.notification_type = notification_type
        self.registry_image = (
            ci_env.registry_image() or "registry.example.com/example-org/helm-charts"
        )
        self.commit_sha = ci_env.commit_short_sha()
        self.ref_name = ci_env.commit_ref_name()
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    def read_charts(self, input_file: Path) -> list[str]:
        """
        Read chart names from input file.

        Args:
            input_file: Path to file containing chart names

        Returns:
            List of chart names
        """
        if not input_file.exists():
            logger.warning(f"Input file not found: {input_file}")
            return []

        if input_file.stat().st_size == 0:
            return []

        return [
            line.strip() for line in input_file.read_text().splitlines() if line.strip()
        ]

    def print_validated_notification(self, charts: list[str]) -> None:
        """Print console notification for validated charts."""
        print()
        print("=" * 70)
        print("  ✅  CHARTS VALIDATED AND PACKAGED")
        print("=" * 70)
        print()

        if charts:
            print("📦 Packaged Charts:")
            for chart in charts:
                print(f"   ✓ {chart}")
            print()
        else:
            print("ℹ️  No charts changed in this commit")

        print()
        print(f"🔗 Commit:  {self.commit_sha}")
        print(f"🌿 Branch:  {self.ref_name}")
        print()

    def print_published_notification(self, charts: list[str]) -> None:
        """Print console notification for published charts."""
        print()
        print("=" * 70)
        print("  🎉  CHARTS PUBLISHED SUCCESSFULLY")
        print("=" * 70)
        print()

        if charts:
            print("🚀 Published Charts:")
            for chart in charts:
                print(f"   ✓ {chart}")
            print()
            print("=" * 70)
            print(f"📦 Registry:    {self.registry_image}")
            print(f"🔗 Commit:      {self.commit_sha}")
            print(f"🌿 Branch/Tag:  {self.ref_name}")
            print("=" * 70)
            print()
            print("📝 Install with:")
            print(f"   helm pull oci://{self.registry_image}/<chart-name> \\")
            print("     --version <version>")
            print()

    def send_discord_notification(self, charts: list[str]) -> bool:
        """
        Send Discord webhook notification.

        Args:
            charts: List of chart names

        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.discord_webhook_url:
            logger.debug("Discord webhook URL not configured - skipping")
            return True

        if not charts:
            logger.debug("No charts to notify about - skipping Discord notification")
            return True

        try:
            import requests  # type: ignore  # Lazy import, only if webhook configured
        except ImportError:
            logger.warning(
                "requests library not available - skipping Discord notification"
            )
            return False

        # Prepare chart list
        chart_list = ", ".join(charts)

        # Build Discord embed
        embed: dict[str, Any] = {
            "title": "🎉 Helm Charts Published",
            "description": "New chart versions published to registry",
            "color": 5763719,  # Green color
            "fields": [
                {
                    "name": "📦 Charts",
                    "value": chart_list,
                    "inline": False,
                },
                {
                    "name": "🔗 Commit",
                    "value": self.commit_sha,
                    "inline": True,
                },
                {
                    "name": "🌿 Branch/Tag",
                    "value": self.ref_name,
                    "inline": True,
                },
                {
                    "name": "📍 Registry",
                    "value": self.registry_image,
                    "inline": False,
                },
            ],
            "footer": {"text": "GitLab CI"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        payload: dict[str, Any] = {"embeds": [embed]}

        try:
            response = requests.post(
                self.discord_webhook_url,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            logger.info("✓ Discord notification sent successfully")
            return True
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️  Discord notification failed: {e}")
            return False

    def notify(self, input_file: Path) -> bool:
        """
        Send notifications.

        Args:
            input_file: Path to file containing chart names

        Returns:
            True if notifications sent successfully, False otherwise
        """
        # Read charts
        charts = self.read_charts(input_file)

        # Print console notification
        if self.notification_type == "validated":
            self.print_validated_notification(charts)
        elif self.notification_type == "published":
            self.print_published_notification(charts)

            # Send Discord notification (only for published)
            if charts:
                self.send_discord_notification(charts)
        else:
            logger.error(f"Unknown notification type: {self.notification_type}")
            return False

        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Send pipeline notifications")
    parser.add_argument(
        "--type",
        choices=["validated", "published"],
        required=True,
        help="Notification type",
    )
    parser.add_argument(
        "--input-file",
        type=str,
        required=True,
        help="File containing chart names (one per line)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    setup_logging(level=logging.DEBUG if args.verbose else logging.INFO)

    # Send notifications
    sender = NotificationSender(notification_type=args.type)
    success = sender.notify(Path(args.input_file))

    sys.exit(ExitCode.SUCCESS if success else ExitCode.FAILURE)


if __name__ == "__main__":
    main()
