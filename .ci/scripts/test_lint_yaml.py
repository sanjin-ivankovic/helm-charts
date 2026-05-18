"""Tests for lint_yaml.py."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

import lint_yaml


# --------------------------------------------------------------------------
# check_yamllint_available
# --------------------------------------------------------------------------


class TestCheckYamllintAvailable:
    def test_returns_true_when_present(self):
        with patch("lint_yaml.shutil.which", return_value="/usr/bin/yamllint"):
            assert lint_yaml.YAMLLinter().check_yamllint_available() is True

    def test_returns_false_when_missing(self):
        with patch("lint_yaml.shutil.which", return_value=None):
            assert lint_yaml.YAMLLinter().check_yamllint_available() is False


# --------------------------------------------------------------------------
# _build_command
# --------------------------------------------------------------------------


class TestBuildCommand:
    def test_standard_format(self):
        cmd = lint_yaml.YAMLLinter()._build_command("standard")
        assert cmd[0] == "yamllint"
        # No --format flag for standard
        assert "--format" not in cmd

    def test_parsable_format(self):
        cmd = lint_yaml.YAMLLinter()._build_command("parsable")
        assert "--format" in cmd
        assert "parsable" in cmd

    def test_gitlab_format_uses_parsable(self):
        # gitlab is converted client-side, so it uses parsable upstream.
        cmd = lint_yaml.YAMLLinter()._build_command("gitlab")
        assert "parsable" in cmd


# --------------------------------------------------------------------------
# _convert_to_gitlab_format
# --------------------------------------------------------------------------


class TestConvertToGitlabFormat:
    def test_empty_output(self):
        linter = lint_yaml.YAMLLinter()
        assert linter._convert_to_gitlab_format("") == "[]"

    def test_parses_one_issue(self):
        sample = "myfile.yaml:10:5: [error] line too long (line-length)"
        linter = lint_yaml.YAMLLinter()
        import json as _json
        issues = _json.loads(linter._convert_to_gitlab_format(sample))
        assert len(issues) == 1
        assert issues[0]["check_name"] == "yamllint/line-length"
        assert issues[0]["severity"] == "major"  # error → major
        assert issues[0]["location"]["lines"]["begin"] == 10
        assert issues[0]["location"]["path"] == "myfile.yaml"

    def test_warning_severity_is_minor(self):
        sample = "myfile.yaml:1:1: [warning] missing document start (document-start)"
        import json as _json
        issues = _json.loads(
            lint_yaml.YAMLLinter()._convert_to_gitlab_format(sample)
        )
        assert issues[0]["severity"] == "minor"

    def test_ignores_non_matching_lines(self):
        sample = "garbage\nmyfile.yaml:1:1: [warning] x (y)\n\nmore garbage"
        import json as _json
        issues = _json.loads(
            lint_yaml.YAMLLinter()._convert_to_gitlab_format(sample)
        )
        assert len(issues) == 1


# --------------------------------------------------------------------------
# run_yamllint
# --------------------------------------------------------------------------


class TestRunYamllint:
    def test_missing_yamllint_returns_1(self):
        linter = lint_yaml.YAMLLinter()
        with patch.object(linter, "check_yamllint_available", return_value=False):
            assert linter.run_yamllint() == 1

    def test_success(self):
        linter = lint_yaml.YAMLLinter(verbose=True)
        with patch.object(linter, "check_yamllint_available", return_value=True):
            with patch("lint_yaml.subprocess.run") as mock:
                # First call: version check; second: actual lint.
                mock.side_effect = [
                    MagicMock(stdout="yamllint 1.0\n", stderr="", returncode=0),
                    MagicMock(stdout="", stderr="", returncode=0),
                ]
                assert linter.run_yamllint() == 0

    def test_failure(self):
        linter = lint_yaml.YAMLLinter()
        with patch.object(linter, "check_yamllint_available", return_value=True):
            with patch("lint_yaml.subprocess.run") as mock:
                mock.side_effect = [
                    MagicMock(stdout="yamllint 1.0\n", stderr="", returncode=0),
                    MagicMock(stdout="some errors", stderr="", returncode=1),
                ]
                assert linter.run_yamllint() == 1

    def test_gitlab_format_prints_json(self, capsys: pytest.CaptureFixture[str]):
        linter = lint_yaml.YAMLLinter()
        with patch.object(linter, "check_yamllint_available", return_value=True):
            with patch("lint_yaml.subprocess.run") as mock:
                mock.side_effect = [
                    MagicMock(stdout="yamllint 1.0\n", stderr="", returncode=0),
                    MagicMock(stdout="x.yaml:1:1: [error] bad (rule)",
                              stderr="", returncode=1),
                ]
                rc = linter.run_yamllint(output_format="gitlab")
        assert rc == 1
        out = capsys.readouterr().out
        # JSON output starts with '[' (array of issues).
        assert "[" in out
        assert "yamllint/rule" in out

    def test_version_check_failure_does_not_abort(self,
                                                  capsys: pytest.CaptureFixture[str]):
        """If yamllint --version times out, scan should still proceed."""
        linter = lint_yaml.YAMLLinter()
        with patch.object(linter, "check_yamllint_available", return_value=True):
            with patch("lint_yaml.subprocess.run") as mock:
                mock.side_effect = [
                    subprocess.TimeoutExpired(cmd="yamllint --version",
                                              timeout=5),
                    MagicMock(stdout="", stderr="", returncode=0),
                ]
                rc = linter.run_yamllint()
        assert rc == 0

    def test_main_timeout(self):
        linter = lint_yaml.YAMLLinter()
        with patch.object(linter, "check_yamllint_available", return_value=True):
            with patch("lint_yaml.subprocess.run") as mock:
                mock.side_effect = [
                    MagicMock(stdout="yamllint 1.0\n", returncode=0),
                    subprocess.TimeoutExpired(cmd="yamllint",
                                              timeout=120),
                ]
                assert linter.run_yamllint() == 1

    def test_unexpected_exception(self):
        linter = lint_yaml.YAMLLinter()
        with patch.object(linter, "check_yamllint_available", return_value=True):
            with patch("lint_yaml.subprocess.run") as mock:
                mock.side_effect = [
                    MagicMock(stdout="", returncode=0),
                    RuntimeError("boom"),
                ]
                assert linter.run_yamllint() == 1


# --------------------------------------------------------------------------
# log / main
# --------------------------------------------------------------------------


class TestLog:
    def test_silent_default(self, capsys: pytest.CaptureFixture[str]):
        lint_yaml.YAMLLinter().log("hi")
        assert capsys.readouterr().out == ""

    def test_prints_when_verbose(self, capsys: pytest.CaptureFixture[str]):
        lint_yaml.YAMLLinter(verbose=True).log("hi")
        assert "hi" in capsys.readouterr().out


class TestMain:
    def test_main_runs_run_yamllint(self):
        with patch("lint_yaml.YAMLLinter.run_yamllint",
                   return_value=0) as mock:
            with patch("sys.argv", ["lint_yaml.py"]):
                assert lint_yaml.main() == 0
        mock.assert_called_once_with(output_format="standard")

    def test_main_threads_format(self):
        with patch("lint_yaml.YAMLLinter.run_yamllint",
                   return_value=0) as mock:
            with patch("sys.argv",
                       ["lint_yaml.py", "--format", "gitlab"]):
                lint_yaml.main()
        mock.assert_called_once_with(output_format="gitlab")
