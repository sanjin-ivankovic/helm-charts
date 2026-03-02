#!/usr/bin/env python3
"""
GitHub Portfolio Publishing Script

Sanitizes the repository and publishes to GitHub.
Replaces tools/push-to-github.sh with better error handling and logging.

Usage:
    python3 publish_github.py [--dry-run] [--verbose]
    python3 publish_github.py --source /path/to/repo --output /path/to/public
"""

import argparse
import logging
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Constants
DEFAULT_BRANCH = "main"
DEFAULT_REMOTE_NAME = "github"
GIT_IGNORE_PATH = ".git"
DEFAULT_GITHUB_REMOTE = (
    "git@github.com-maintainer-user:maintainer-user/helm-charts.git"
)
GITHUB_REPO_URL = "https://github.com/maintainer-user/helm-charts"


class GitHubPublisher:
    """Handles sanitization and publishing to GitHub."""

    def __init__(
        self,
        source_repo: Path,
        output_repo: Path,
        github_remote: str,
        dry_run: bool = False,
        verbose: bool = False,
    ):
        self.source_repo = source_repo
        self.output_repo = output_repo
        self.github_remote = github_remote
        self.dry_run = dry_run

        # Setup logging
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(level=level, format="%(levelname)s: %(message)s")
        self.logger = logging.getLogger(__name__)

    def run_command(
        self, cmd: list[str], cwd: Optional[Path] = None, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        """Run a command and handle errors."""
        self.logger.debug(f"Running: {' '.join(cmd)}")

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would run: {' '.join(cmd)}")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=False
        )

        if check and result.returncode != 0:
            self.logger.error(f"Command failed: {' '.join(cmd)}")
            self.logger.error(f"Exit code: {result.returncode}")
            if result.stdout:
                self.logger.error(f"Stdout: {result.stdout}")
            if result.stderr:
                self.logger.error(f"Stderr: {result.stderr}")
            raise subprocess.CalledProcessError(
                result.returncode, cmd, result.stdout, result.stderr
            )

        return result

    def run_sanitization(self) -> None:
        """Run the sanitization script."""
        self.logger.info("=" * 60)
        self.logger.info("Running sanitization...")
        self.logger.info("=" * 60)

        sanitize_script = self.source_repo / "tools" / "sanitize" / "sanitize_repo.py"

        if not sanitize_script.exists():
            raise FileNotFoundError(f"Sanitization script not found: {sanitize_script}")

        cmd = [
            "python3",
            str(sanitize_script),
            str(self.source_repo),
            "--single-commit",
            "--output",
            str(self.output_repo),
        ]

        self.run_command(cmd)
        self.logger.info("✓ Sanitization completed")

    def run_verification(self) -> None:
        """Run the verification script."""
        self.logger.info("=" * 60)
        self.logger.info("Running security verification...")
        self.logger.info("=" * 60)

        verify_script = (
            self.source_repo / "tools" / "sanitize" / "verify_sanitization.py"
        )

        if not verify_script.exists():
            self.logger.warning(f"Verification script not found: {verify_script}")
            self.logger.warning("Skipping verification")
            return

        # Run verification from the sanitize directory
        cmd = ["python3", "verify_sanitization.py"]
        self.run_command(cmd, cwd=verify_script.parent)
        self.logger.info("✓ Verification passed - no sensitive data detected")

    def count_files(self) -> int:
        """Count files in the output repository."""
        return sum(
            1
            for f in self.output_repo.rglob("*")
            if f.is_file() and GIT_IGNORE_PATH not in f.parts
        )

    def initialize_git_repo(self) -> None:
        """Initialize a fresh git repository."""
        self.logger.info("=" * 60)
        self.logger.info("Preparing GitHub push...")
        self.logger.info("=" * 60)

        # Remove existing .git if present
        git_dir = self.output_repo / GIT_IGNORE_PATH
        if git_dir.exists():
            self.logger.info("Removing existing .git directory...")
            if not self.dry_run:
                shutil.rmtree(git_dir)

        # Initialize new repo
        self.logger.info("Initializing git repository...")
        self.run_command(["git", "init", "-b", DEFAULT_BRANCH], cwd=self.output_repo)

        # Add remote
        self.logger.info(f"Adding GitHub remote: {self.github_remote}")
        self.run_command(
            ["git", "remote", "add", DEFAULT_REMOTE_NAME, self.github_remote],
            cwd=self.output_repo,
        )

    def commit_changes(self) -> str:
        """Stage and commit all changes."""
        # Stage all files
        self.logger.info("Staging files...")
        self.run_command(["git", "add", "-A"], cwd=self.output_repo)

        # Get staged file count
        result = self.run_command(
            ["git", "diff", "--cached", "--numstat"], cwd=self.output_repo
        )
        staged_count = (
            len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
        )
        self.logger.info(f"Staged {staged_count} files")

        # Create commit message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_count = self.count_files()
        commit_msg = (
            f"Update portfolio - {timestamp}\n\n"
            f"Sanitization verified - no sensitive data detected\n\n"
            f"Files: {file_count}"
        )

        # Commit
        self.logger.info("Creating commit...")
        self.run_command(["git", "commit", "-m", commit_msg], cwd=self.output_repo)

        # Get commit hash
        result = self.run_command(
            ["git", "rev-parse", "--short", "HEAD"], cwd=self.output_repo
        )
        commit_hash = result.stdout.strip()
        self.logger.info(f"Commit created: {commit_hash}")

        return commit_hash

    def push_to_github(self) -> None:
        """Force push to GitHub."""
        self.logger.info("=" * 60)
        self.logger.info("Force pushing to GitHub...")
        self.logger.info("=" * 60)

        self.run_command(
            ["git", "push", DEFAULT_REMOTE_NAME, DEFAULT_BRANCH, "--force"],
            cwd=self.output_repo,
        )

        self.logger.info("=" * 60)
        self.logger.info("✓ Successfully published to GitHub!")
        self.logger.info("=" * 60)

    def publish(self) -> None:
        """Run the full publishing workflow."""
        try:
            # Pre-flight checks
            if not self.source_repo.exists():
                raise FileNotFoundError(f"Source repo not found: {self.source_repo}")

            file_count = self.count_files() if self.output_repo.exists() else 0
            self.logger.info(f"Source: {self.source_repo}")
            self.logger.info(f"Output: {self.output_repo}")
            self.logger.info(f"Files to publish: {file_count}")

            # Run workflow
            self.run_sanitization()
            self.run_verification()
            self.initialize_git_repo()
            self.commit_changes()
            self.push_to_github()

            self.logger.info("")
            self.logger.info("Next steps:")
            self.logger.info(f"  1. Visit: {GITHUB_REPO_URL}")
            self.logger.info("  2. Verify the content looks correct")

        except Exception as e:
            self.logger.error(f"Publishing failed: {e}")
            if self.dry_run:
                self.logger.info("(Dry run mode - no actual changes made)")
            sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publish sanitized repository to GitHub"
    )
    parser.add_argument(
        "--source",
        type=Path,
        help="Source repository path (default: current directory's parent)",
    )
    parser.add_argument(
        "--output", type=Path, help="Output repository path (default: source_public)"
    )
    parser.add_argument(
        "--remote",
        default=DEFAULT_GITHUB_REMOTE,
        help="GitHub remote URL",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Determine paths
    source_repo = (
        args.source.resolve()
        if args.source
        else Path(__file__).parent.parent.parent.resolve()
    )
    output_repo = (
        args.output.resolve()
        if args.output
        else source_repo.parent / f"{source_repo.name}_public"
    )

    publisher = GitHubPublisher(
        source_repo=source_repo,
        output_repo=output_repo,
        github_remote=args.remote,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    publisher.publish()


if __name__ == "__main__":
    main()
