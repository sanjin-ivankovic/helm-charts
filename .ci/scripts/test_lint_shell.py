"""Tests for lint_shell.py."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import lint_shell


class TestCheckShellcheckAvailable:
    def test_present(self):
        with patch("lint_shell.shutil.which", return_value="/bin/shellcheck"):
            assert lint_shell.ShellLinter().check_shellcheck_available() is True

    def test_missing(self):
        with patch("lint_shell.shutil.which", return_value=None):
            assert lint_shell.ShellLinter().check_shellcheck_available() is False


class TestFindShellScripts:
    def test_finds_sh_files(self, tmp_path: Path):
        # Point project_root at tmp_path with a few scripts.
        (tmp_path / "a.sh").write_text("#!/bin/bash\necho a")
        (tmp_path / "b.sh").write_text("#!/bin/bash\necho b")
        # File outside skip dirs
        (tmp_path / "ignore.txt").write_text("nope")
        linter = lint_shell.ShellLinter()
        with patch.object(linter, "project_root", tmp_path):
            scripts = linter.find_shell_scripts()
        names = sorted(s.name for s in scripts)
        assert names == ["a.sh", "b.sh"]

    def test_skips_excluded_dirs(self, tmp_path: Path):
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "evil.sh").write_text("rm -rf /")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "hook.sh").write_text("echo hi")
        (tmp_path / "good.sh").write_text("echo good")
        linter = lint_shell.ShellLinter()
        with patch.object(linter, "project_root", tmp_path):
            scripts = linter.find_shell_scripts()
        names = sorted(s.name for s in scripts)
        assert names == ["good.sh"]


class TestRunShellcheck:
    def test_missing_shellcheck_returns_1(self):
        linter = lint_shell.ShellLinter()
        with patch.object(linter, "check_shellcheck_available",
                          return_value=False):
            assert linter.run_shellcheck() == 1

    def test_no_scripts_found_returns_0(self, tmp_path: Path):
        linter = lint_shell.ShellLinter()
        with patch.object(linter, "project_root", tmp_path):
            with patch.object(linter, "check_shellcheck_available",
                              return_value=True):
                with patch("lint_shell.subprocess.run") as mock:
                    # Just the version check
                    mock.return_value = MagicMock(
                        stdout="version: 0.10.0\n", stderr="", returncode=0
                    )
                    assert linter.run_shellcheck() == 0

    def test_success(self, tmp_path: Path):
        (tmp_path / "a.sh").write_text("#!/bin/sh\necho")
        linter = lint_shell.ShellLinter(verbose=True)
        with patch.object(linter, "project_root", tmp_path):
            with patch.object(linter, "check_shellcheck_available",
                              return_value=True):
                with patch("lint_shell.subprocess.run") as mock:
                    mock.side_effect = [
                        MagicMock(stdout="version: 0.10.0\n",
                                  stderr="", returncode=0),
                        MagicMock(stdout="", stderr="", returncode=0),
                    ]
                    assert linter.run_shellcheck() == 0

    def test_failure(self, tmp_path: Path):
        (tmp_path / "a.sh").write_text("#!/bin/sh\necho")
        linter = lint_shell.ShellLinter()
        with patch.object(linter, "project_root", tmp_path):
            with patch.object(linter, "check_shellcheck_available",
                              return_value=True):
                with patch("lint_shell.subprocess.run") as mock:
                    mock.side_effect = [
                        MagicMock(stdout="version: 0.10.0\n",
                                  stderr="", returncode=0),
                        MagicMock(stdout="error", stderr="", returncode=1),
                    ]
                    assert linter.run_shellcheck() == 1

    def test_version_check_failure_continues(self, tmp_path: Path):
        (tmp_path / "a.sh").write_text("#!/bin/sh")
        linter = lint_shell.ShellLinter()
        with patch.object(linter, "project_root", tmp_path):
            with patch.object(linter, "check_shellcheck_available",
                              return_value=True):
                with patch("lint_shell.subprocess.run") as mock:
                    mock.side_effect = [
                        subprocess.CalledProcessError(returncode=1,
                                                     cmd="shellcheck --version"),
                        MagicMock(stdout="", stderr="", returncode=0),
                    ]
                    assert linter.run_shellcheck() == 0

    def test_timeout(self, tmp_path: Path):
        (tmp_path / "a.sh").write_text("#!/bin/sh")
        linter = lint_shell.ShellLinter()
        with patch.object(linter, "project_root", tmp_path):
            with patch.object(linter, "check_shellcheck_available",
                              return_value=True):
                with patch("lint_shell.subprocess.run") as mock:
                    mock.side_effect = [
                        MagicMock(stdout="", returncode=0),
                        subprocess.TimeoutExpired(cmd="shellcheck", timeout=120),
                    ]
                    assert linter.run_shellcheck() == 1

    def test_unexpected_exception(self, tmp_path: Path):
        (tmp_path / "a.sh").write_text("#!/bin/sh")
        linter = lint_shell.ShellLinter()
        with patch.object(linter, "project_root", tmp_path):
            with patch.object(linter, "check_shellcheck_available",
                              return_value=True):
                with patch("lint_shell.subprocess.run") as mock:
                    mock.side_effect = [
                        MagicMock(stdout="", returncode=0),
                        RuntimeError("boom"),
                    ]
                    assert linter.run_shellcheck() == 1


class TestLog:
    def test_silent(self, capsys: pytest.CaptureFixture[str]):
        lint_shell.ShellLinter().log("hi")
        assert capsys.readouterr().out == ""

    def test_verbose(self, capsys: pytest.CaptureFixture[str]):
        lint_shell.ShellLinter(verbose=True).log("hi")
        assert "hi" in capsys.readouterr().out


class TestMain:
    def test_main_invokes_run_shellcheck(self):
        with patch("lint_shell.ShellLinter.run_shellcheck",
                   return_value=0) as mock:
            with patch("sys.argv", ["lint_shell.py"]):
                assert lint_shell.main() == 0
        mock.assert_called_once()
