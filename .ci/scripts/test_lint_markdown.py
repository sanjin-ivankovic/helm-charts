"""Tests for lint_markdown.py."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

import lint_markdown


class TestCheckMarkdownlintAvailable:
    def test_present(self):
        # `shutil` is lazy-imported INSIDE check_markdownlint_available,
        # so we patch shutil.which at the module level.
        with patch("shutil.which", return_value="/usr/bin/markdownlint-cli2"):
            linter = lint_markdown.MarkdownLinter()
            assert linter.check_markdownlint_available() is True

    def test_missing(self):
        with patch("shutil.which", return_value=None):
            linter = lint_markdown.MarkdownLinter()
            assert linter.check_markdownlint_available() is False


class TestBuildCommand:
    def test_includes_config_and_glob(self):
        cmd = lint_markdown.MarkdownLinter()._build_command()
        assert cmd[0] == "markdownlint-cli2"
        assert "--config" in cmd
        assert any(".markdownlint-cli2.jsonc" in c for c in cmd)
        assert "**/*.md" in cmd


class TestRunMarkdownlint:
    def test_returns_0_when_not_installed(self,
                                          capsys: pytest.CaptureFixture[str]):
        """markdownlint is optional — missing → 0 with a soft warning."""
        linter = lint_markdown.MarkdownLinter()
        with patch.object(linter, "check_markdownlint_available",
                          return_value=False):
            assert linter.run_markdownlint() == 0
        assert "not installed" in capsys.readouterr().out

    def test_success(self):
        linter = lint_markdown.MarkdownLinter(verbose=True)
        with patch.object(linter, "check_markdownlint_available",
                          return_value=True):
            with patch("lint_markdown.subprocess.run") as mock:
                mock.return_value = MagicMock(stdout="", stderr="", returncode=0)
                assert linter.run_markdownlint() == 0

    def test_failure_default_is_warning_only(self):
        """Default fail_on_error=False: even on failure, return 0."""
        linter = lint_markdown.MarkdownLinter()
        with patch.object(linter, "check_markdownlint_available",
                          return_value=True):
            with patch("lint_markdown.subprocess.run") as mock:
                mock.return_value = MagicMock(stdout="errs", stderr="",
                                              returncode=1)
                assert linter.run_markdownlint() == 0

    def test_failure_with_fail_on_error_propagates(self):
        linter = lint_markdown.MarkdownLinter(fail_on_error=True)
        with patch.object(linter, "check_markdownlint_available",
                          return_value=True):
            with patch("lint_markdown.subprocess.run") as mock:
                mock.return_value = MagicMock(stdout="errs", stderr="",
                                              returncode=1)
                assert linter.run_markdownlint() == 1

    def test_timeout_warning_only(self):
        linter = lint_markdown.MarkdownLinter()
        with patch.object(linter, "check_markdownlint_available",
                          return_value=True):
            with patch("lint_markdown.subprocess.run",
                       side_effect=subprocess.TimeoutExpired(
                           cmd="markdownlint", timeout=120)):
                assert linter.run_markdownlint() == 0

    def test_timeout_with_fail_on_error_propagates(self):
        linter = lint_markdown.MarkdownLinter(fail_on_error=True)
        with patch.object(linter, "check_markdownlint_available",
                          return_value=True):
            with patch("lint_markdown.subprocess.run",
                       side_effect=subprocess.TimeoutExpired(
                           cmd="markdownlint", timeout=120)):
                assert linter.run_markdownlint() == 1

    def test_unexpected_exception_warning_only(self):
        linter = lint_markdown.MarkdownLinter()
        with patch.object(linter, "check_markdownlint_available",
                          return_value=True):
            with patch("lint_markdown.subprocess.run",
                       side_effect=RuntimeError("boom")):
                assert linter.run_markdownlint() == 0

    def test_unexpected_exception_with_fail_on_error(self):
        linter = lint_markdown.MarkdownLinter(fail_on_error=True)
        with patch.object(linter, "check_markdownlint_available",
                          return_value=True):
            with patch("lint_markdown.subprocess.run",
                       side_effect=RuntimeError("boom")):
                assert linter.run_markdownlint() == 1


class TestLog:
    def test_silent(self, capsys: pytest.CaptureFixture[str]):
        lint_markdown.MarkdownLinter().log("hi")
        assert capsys.readouterr().out == ""

    def test_verbose(self, capsys: pytest.CaptureFixture[str]):
        lint_markdown.MarkdownLinter(verbose=True).log("hi")
        assert "hi" in capsys.readouterr().out


class TestMain:
    def test_main_default(self):
        with patch("lint_markdown.MarkdownLinter.run_markdownlint",
                   return_value=0):
            with patch("sys.argv", ["lint_markdown.py"]):
                assert lint_markdown.main() == 0

    def test_main_fail_on_error_flag(self):
        with patch("lint_markdown.MarkdownLinter") as mock_cls:
            mock_cls.return_value.run_markdownlint = MagicMock(return_value=0)
            with patch("sys.argv",
                       ["lint_markdown.py", "--fail-on-error", "--verbose"]):
                lint_markdown.main()
        # Verify the flag propagated.
        mock_cls.assert_called_once_with(verbose=True, fail_on_error=True)
