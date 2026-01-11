#!/usr/bin/env python3
"""
ShellCheck Linting Script

Runs shellcheck on all shell scripts in the repository.

Usage:
    python3 shellcheck_runner.py [--path DIR] [--verbose]

Environment Variables:
    None
"""

import argparse
import logging
import sys
from pathlib import Path

from common import CommandRunner, format_duration, setup_logging

logger = logging.getLogger(__name__)


class ShellCheckLinter:
    """Runs shellcheck validation."""

    def __init__(self, scripts_path: str = "scripts/ci", verbose: bool = False):
        self.scripts_path = Path(scripts_path)
        self.project_root = Path(__file__).parent.parent.parent
        self.cmd_runner = CommandRunner(cwd=self.project_root, verbose=verbose)

    def find_shell_scripts(self) -> list[Path]:
        """
        Find all shell scripts to check.

        Returns:
            List of shell script paths
        """
        scripts_dir = self.project_root / self.scripts_path

        if not scripts_dir.exists():
            logger.warning(f"Scripts directory not found: {scripts_dir}")
            return []

        # Find all .sh files
        shell_files = list(scripts_dir.rglob("*.sh"))

        if not shell_files:
            logger.warning(f"No shell scripts found in {scripts_dir}")
            return []

        logger.info(f"Found {len(shell_files)} shell script(s) to check")
        return shell_files

    def run(self) -> tuple[int, float]:
        """
        Run shellcheck on all shell scripts.

        Returns:
            Tuple of (exit_code, duration)
        """
        import time

        logger.info("Running shellcheck...")

        shell_files = self.find_shell_scripts()

        if not shell_files:
            logger.info("✓ No shell scripts to check")
            return 0, 0.0

        start = time.time()
        exit_code, stdout, stderr = self.cmd_runner.run(
            ["shellcheck", "-x"] + [str(f) for f in shell_files], check=False
        )
        duration = time.time() - start

        if exit_code == 0:
            logger.info(f"✓ shellcheck passed ({format_duration(duration)})")
        else:
            logger.error(f"✗ shellcheck failed ({format_duration(duration)})")
            if stdout:
                logger.error(f"Output:\n{stdout}")
            if stderr:
                logger.error(f"Errors:\n{stderr}")

        return exit_code, duration


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run shellcheck on repository shell scripts"
    )
    parser.add_argument(
        "--path",
        type=str,
        default="scripts/ci",
        help="Path to scripts directory (default: scripts/ci)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    setup_logging(level=logging.DEBUG if args.verbose else logging.INFO)

    # Run shellcheck
    linter = ShellCheckLinter(scripts_path=args.path, verbose=args.verbose)
    exit_code, _duration = linter.run()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
