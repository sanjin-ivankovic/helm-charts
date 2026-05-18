"""Tests for scan_secrets.py.

SecretScanner wraps `gitleaks detect` with SARIF output. We mock
subprocess + shutil.which so tests don't depend on gitleaks being
installed.
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

import scan_secrets


# --------------------------------------------------------------------------
# check_gitleaks_available
# --------------------------------------------------------------------------


class TestCheckGitleaksAvailable:
    def test_returns_true_when_found(self):
        scanner = scan_secrets.SecretScanner()
        with patch("scan_secrets.shutil.which", return_value="/usr/bin/gitleaks"):
            assert scanner.check_gitleaks_available() is True

    def test_returns_false_when_missing(self):
        scanner = scan_secrets.SecretScanner()
        with patch("scan_secrets.shutil.which", return_value=None):
            assert scanner.check_gitleaks_available() is False


# --------------------------------------------------------------------------
# _build_command
# --------------------------------------------------------------------------


class TestBuildCommand:
    def test_includes_required_flags(self):
        scanner = scan_secrets.SecretScanner()
        cmd = scanner._build_command(no_git=False, report_path="r.json")
        assert cmd[0] == "gitleaks"
        assert "detect" in cmd
        assert "--source" in cmd
        assert "--config" in cmd
        assert scan_secrets.GITLEAKS_CONFIG in cmd
        assert "--report-format" in cmd
        assert "sarif" in cmd
        assert "--report-path" in cmd
        assert "r.json" in cmd
        assert "--platform" in cmd
        assert "gitlab" in cmd

    def test_no_git_flag_appended(self):
        scanner = scan_secrets.SecretScanner()
        cmd = scanner._build_command(no_git=True, report_path="x.json")
        assert "--no-git" in cmd

    def test_default_no_git_is_false(self):
        scanner = scan_secrets.SecretScanner()
        cmd = scanner._build_command(no_git=False, report_path="x.json")
        assert "--no-git" not in cmd


# --------------------------------------------------------------------------
# scan() — wraps subprocess.run
# --------------------------------------------------------------------------


class TestScan:
    def test_returns_subprocess_returncode(self,
                                          monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("SCHEDULE_TYPE", raising=False)
        scanner = scan_secrets.SecretScanner(verbose=True)
        with patch("scan_secrets.subprocess.run") as mock:
            mock.return_value = MagicMock(returncode=0)
            assert scanner.scan(report_path="r.json") == 0

    def test_returns_nonzero_when_leaks_found(self,
                                              monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("SCHEDULE_TYPE", raising=False)
        scanner = scan_secrets.SecretScanner()
        with patch("scan_secrets.subprocess.run") as mock:
            mock.return_value = MagicMock(returncode=1)
            assert scanner.scan() == 1

    def test_timeout_returns_1(self, monkeypatch: pytest.MonkeyPatch,
                               capsys: pytest.CaptureFixture[str]):
        monkeypatch.delenv("SCHEDULE_TYPE", raising=False)
        scanner = scan_secrets.SecretScanner()
        with patch("scan_secrets.subprocess.run",
                   side_effect=subprocess.TimeoutExpired(cmd="gitleaks",
                                                         timeout=300)):
            assert scanner.scan() == 1
        # Timeout prints an error to stdout.
        assert "timed out" in capsys.readouterr().out.lower()

    def test_github_sync_schedule_uses_no_git(self,
                                              monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("SCHEDULE_TYPE", "github_sync")
        scanner = scan_secrets.SecretScanner()
        with patch("scan_secrets.subprocess.run") as mock:
            mock.return_value = MagicMock(returncode=0)
            scanner.scan()
        called_cmd = mock.call_args[0][0]
        assert "--no-git" in called_cmd

    def test_default_schedule_full_scan(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("SCHEDULE_TYPE", raising=False)
        scanner = scan_secrets.SecretScanner()
        with patch("scan_secrets.subprocess.run") as mock:
            mock.return_value = MagicMock(returncode=0)
            scanner.scan()
        called_cmd = mock.call_args[0][0]
        assert "--no-git" not in called_cmd

    def test_passes_cwd_to_subprocess(self,
                                      monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("SCHEDULE_TYPE", raising=False)
        scanner = scan_secrets.SecretScanner()
        with patch("scan_secrets.subprocess.run") as mock:
            mock.return_value = MagicMock(returncode=0)
            scanner.scan()
        # subprocess.run was called with cwd=project_root.
        assert mock.call_args.kwargs["cwd"] == scanner.project_root


# --------------------------------------------------------------------------
# log()
# --------------------------------------------------------------------------


class TestLog:
    def test_silent_by_default(self, capsys: pytest.CaptureFixture[str]):
        scanner = scan_secrets.SecretScanner(verbose=False)
        scanner.log("hello")
        assert capsys.readouterr().out == ""

    def test_prints_when_verbose(self, capsys: pytest.CaptureFixture[str]):
        scanner = scan_secrets.SecretScanner(verbose=True)
        scanner.log("hello")
        assert "hello" in capsys.readouterr().out


# --------------------------------------------------------------------------
# main()
# --------------------------------------------------------------------------


class TestMain:
    def test_missing_gitleaks_returns_1(self, capsys: pytest.CaptureFixture[str]):
        with patch("scan_secrets.shutil.which", return_value=None):
            with patch("sys.argv", ["scan_secrets.py"]):
                rc = scan_secrets.main()
        assert rc == 1
        assert "not installed" in capsys.readouterr().out

    def test_main_with_gitleaks_runs_scan(self):
        with patch("scan_secrets.shutil.which", return_value="/bin/gitleaks"):
            with patch("scan_secrets.subprocess.run",
                       return_value=MagicMock(returncode=0)):
                with patch("sys.argv", ["scan_secrets.py", "--verbose"]):
                    rc = scan_secrets.main()
        assert rc == 0

    def test_main_passes_custom_report_path(self):
        with patch("scan_secrets.shutil.which", return_value="/bin/gitleaks"):
            with patch("scan_secrets.subprocess.run") as mock:
                mock.return_value = MagicMock(returncode=0)
                with patch("sys.argv",
                           ["scan_secrets.py", "--report-path",
                            "custom-report.json"]):
                    scan_secrets.main()
        called_cmd = mock.call_args[0][0]
        assert "custom-report.json" in called_cmd
