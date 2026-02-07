#!/usr/bin/env python3
"""
Markdownlint Linting Script

Runs markdownlint on all Markdown files in the repository.

Usage:
    python3 markdownlint_runner.py [--pattern GLOB] [--verbose]

Environment Variables:
    None
"""

import argparse
import logging
import sys
from pathlib import Path

from common import CommandRunner, format_duration, setup_logging

logger = logging.getLogger(__name__)


class MarkdownLinter:
    """Runs markdownlint validation."""

    def __init__(self, pattern: str = "**/*.md", verbose: bool = False):
        self.pattern = pattern
        self.project_root = Path(__file__).parent.parent.parent
        self.cmd_runner = CommandRunner(cwd=self.project_root, verbose=verbose)

    def check_installed(self) -> bool:
        """
        Check if markdownlint-cli2 is installed.

        Returns:
            True if installed, False otherwise
        """
        exit_code, _stdout, _stderr = self.cmd_runner.run(
            ["which", "markdownlint-cli2"], check=False, capture=True
        )
        return exit_code == 0

    def run(self) -> tuple[int, float]:
        """
        Run markdownlint on all Markdown files.

        Returns:
            Tuple of (exit_code, duration)
        """
        import time

        logger.info("Running markdownlint-cli2...")

        # Check if markdownlint is installed
        if not self.check_installed():
            logger.warning("markdownlint-cli2 not installed (optional) - skipping")
            return 0, 0.0

        start = time.time()
        # markdownlint-cli2 automatically picks up .markdownlint-cli2.jsonc
        exit_code, stdout, stderr = self.cmd_runner.run(
            ["markdownlint-cli2", self.pattern],
            check=False,
        )
        duration = time.time() - start

        if exit_code == 0:
            logger.info(f"✓ markdownlint-cli2 passed ({format_duration(duration)})")
        else:
            logger.error(f"✗ markdownlint-cli2 failed ({format_duration(duration)})")
            if stdout:
                logger.error(f"Output:\n{stdout}")
            if stderr:
                logger.error(f"Errors:\n{stderr}")

        return exit_code, duration


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run markdownlint on repository Markdown files"
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="**/*.md",
        help="Glob pattern for Markdown files (default: **/*.md)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    setup_logging(level=logging.DEBUG if args.verbose else logging.INFO)

    # Run markdownlint
    linter = MarkdownLinter(pattern=args.pattern, verbose=args.verbose)
    exit_code, _duration = linter.run()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
