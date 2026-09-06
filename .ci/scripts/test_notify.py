"""Tests for notify.py.

NotificationSender has two responsibilities:
  1. Print human-readable summaries to stdout (validated, published)
  2. POST a Discord embed when DISCORD_WEBHOOK_URL is set + charts > 0

We use capsys to capture stdout and patch the `requests` import to
avoid touching the network.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import notify


# --------------------------------------------------------------------------
# Construction / env wiring
# --------------------------------------------------------------------------


class TestNotificationSenderInit:
    def test_defaults_when_env_empty(self, monkeypatch: pytest.MonkeyPatch):
        for v in ("CI_REGISTRY_IMAGE", "DISCORD_WEBHOOK_URL",
                  "CI_COMMIT_SHORT_SHA", "CI_COMMIT_REF_NAME",
                  "CI_COMMIT_SHA", "CI_COMMIT_REF"):
            monkeypatch.delenv(v, raising=False)
        s = notify.NotificationSender("validated")
        assert s.notification_type == "validated"
        assert s.registry_image == "registry.example.com/example-org/helm-charts"
        assert s.commit_sha == "unknown"
        assert s.ref_name == "unknown"
        assert s.discord_webhook_url is None

    def test_picks_up_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CI_REGISTRY_IMAGE", "registry.example.com/charts")
        monkeypatch.setenv("CI_COMMIT_SHORT_SHA", "abc12345")
        monkeypatch.setenv("CI_COMMIT_REF_NAME", "main")
        monkeypatch.setenv("DISCORD_WEBHOOK_URL",
                           "https://discord.com/api/webhooks/fake")
        s = notify.NotificationSender("published")
        assert s.registry_image == "registry.example.com/charts"
        assert s.commit_sha == "abc12345"
        assert s.ref_name == "main"
        assert s.discord_webhook_url == "https://discord.com/api/webhooks/fake"


# --------------------------------------------------------------------------
# read_charts
# --------------------------------------------------------------------------


class TestReadCharts:
    def test_missing_file_returns_empty(self, tmp_path: Path):
        s = notify.NotificationSender("validated")
        assert s.read_charts(tmp_path / "nope.txt") == []

    def test_empty_file_returns_empty(self, tmp_path: Path):
        input_file = tmp_path / "empty.txt"
        input_file.write_text("")
        s = notify.NotificationSender("validated")
        assert s.read_charts(input_file) == []

    def test_parses_one_per_line(self, tmp_path: Path):
        input_file = tmp_path / "list.txt"
        input_file.write_text("alpha\nbeta\ngamma\n")
        s = notify.NotificationSender("validated")
        assert s.read_charts(input_file) == ["alpha", "beta", "gamma"]

    def test_strips_whitespace_and_blanks(self, tmp_path: Path):
        input_file = tmp_path / "msgy.txt"
        input_file.write_text("  alpha  \n\n  beta\n\n\n")
        s = notify.NotificationSender("validated")
        assert s.read_charts(input_file) == ["alpha", "beta"]


# --------------------------------------------------------------------------
# Console printing
# --------------------------------------------------------------------------


class TestPrintValidated:
    def test_with_charts(self, capsys: pytest.CaptureFixture[str]):
        s = notify.NotificationSender("validated")
        s.print_validated_notification(["chart-a", "chart-b"])
        out = capsys.readouterr().out
        assert "CHARTS VALIDATED" in out
        assert "chart-a" in out
        assert "chart-b" in out

    def test_without_charts(self, capsys: pytest.CaptureFixture[str]):
        s = notify.NotificationSender("validated")
        s.print_validated_notification([])
        out = capsys.readouterr().out
        assert "No charts changed" in out


class TestPrintPublished:
    def test_with_charts(self, capsys: pytest.CaptureFixture[str]):
        s = notify.NotificationSender("published")
        s.print_published_notification(["chart-a"])
        out = capsys.readouterr().out
        assert "PUBLISHED SUCCESSFULLY" in out
        assert "chart-a" in out
        assert "helm pull" in out

    def test_without_charts_prints_header_only(
        self, capsys: pytest.CaptureFixture[str]
    ):
        s = notify.NotificationSender("published")
        s.print_published_notification([])
        out = capsys.readouterr().out
        assert "PUBLISHED SUCCESSFULLY" in out
        # The detailed registry/install block only prints when charts are present
        assert "helm pull" not in out


# --------------------------------------------------------------------------
# send_discord_notification — mock `requests` carefully
# --------------------------------------------------------------------------


class TestSendDiscord:
    def test_no_webhook_returns_true(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
        s = notify.NotificationSender("published")
        # No-op short-circuit returns True.
        assert s.send_discord_notification(["chart-a"]) is True

    def test_no_charts_returns_true(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://example.com/hook")
        s = notify.NotificationSender("published")
        assert s.send_discord_notification([]) is True

    def test_posts_payload_on_success(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://example.com/hook")
        s = notify.NotificationSender("published")
        # Mock `requests` module via sys.modules so the lazy import
        # inside send_discord_notification picks up our stub.
        fake_requests = MagicMock()
        fake_response = MagicMock()
        fake_response.raise_for_status = MagicMock()
        fake_requests.post = MagicMock(return_value=fake_response)
        fake_requests.exceptions = MagicMock()
        # Make the lazy import find our stub.
        monkeypatch.setitem(sys.modules, "requests", fake_requests)
        # And ensure the RequestException reference resolves inside
        # the except: clause.
        fake_requests.exceptions.RequestException = Exception

        ok = s.send_discord_notification(["chart-a", "chart-b"])
        assert ok is True
        fake_requests.post.assert_called_once()
        # Verify the embed payload structure.
        url, kwargs = fake_requests.post.call_args
        assert url[0] == "https://example.com/hook"
        embed = kwargs["json"]["embeds"][0]
        assert embed["title"] == "🎉 Helm Charts Published"
        assert "chart-a" in embed["fields"][0]["value"]
        assert "chart-b" in embed["fields"][0]["value"]

    def test_request_failure_returns_false(self, monkeypatch: pytest.MonkeyPatch,
                                           caplog: pytest.LogCaptureFixture):
        monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://example.com/hook")
        s = notify.NotificationSender("published")
        fake_requests = MagicMock()
        fake_requests.exceptions = MagicMock()
        # Make the network-error class match.
        class FakeRequestException(Exception):
            pass
        fake_requests.exceptions.RequestException = FakeRequestException
        fake_requests.post = MagicMock(
            side_effect=FakeRequestException("connection refused")
        )
        monkeypatch.setitem(sys.modules, "requests", fake_requests)

        with caplog.at_level(logging.WARNING):
            ok = s.send_discord_notification(["chart-a"])
        assert ok is False
        assert any("Discord notification failed" in r.message
                   for r in caplog.records)

    def test_missing_requests_library_returns_false(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        """If the user runs notify.py with DISCORD_WEBHOOK_URL set but
        without `requests` installed, we want a graceful skip."""
        monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://example.com/hook")
        s = notify.NotificationSender("published")
        # Force `import requests` inside the function to fail.
        # The simplest way: make sys.modules['requests'] None — but
        # Python raises ModuleNotFoundError for that. Use a wrapper.
        real_import = __builtins__["__import__"] if isinstance(
            __builtins__, dict) else __import__

        def fake_import(name, *args, **kwargs):
            if name == "requests":
                raise ImportError("requests missing")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            ok = s.send_discord_notification(["chart-a"])
        assert ok is False


# --------------------------------------------------------------------------
# notify() coordinator + main()
# --------------------------------------------------------------------------


class TestNotifyCoordinator:
    def test_validated_routes_to_print(self, tmp_path: Path,
                                       capsys: pytest.CaptureFixture[str]):
        s = notify.NotificationSender("validated")
        input_file = tmp_path / "list.txt"
        input_file.write_text("chart-a\n")
        assert s.notify(input_file) is True
        assert "CHARTS VALIDATED" in capsys.readouterr().out

    def test_published_routes_to_print(self, tmp_path: Path,
                                       capsys: pytest.CaptureFixture[str],
                                       monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
        s = notify.NotificationSender("published")
        input_file = tmp_path / "list.txt"
        input_file.write_text("chart-a\n")
        assert s.notify(input_file) is True
        assert "PUBLISHED SUCCESSFULLY" in capsys.readouterr().out

    def test_unknown_type_returns_false(self, tmp_path: Path,
                                        caplog: pytest.LogCaptureFixture):
        s = notify.NotificationSender("bogus")
        input_file = tmp_path / "list.txt"
        input_file.write_text("chart-a\n")
        with caplog.at_level(logging.ERROR):
            assert s.notify(input_file) is False
        assert any("Unknown notification type" in r.message
                   for r in caplog.records)


def test_main_validated_success(tmp_path: Path):
    input_file = tmp_path / "list.txt"
    input_file.write_text("chart-a\n")
    with patch("sys.argv",
               ["notify.py", "--type", "validated",
                "--input-file", str(input_file)]):
        with pytest.raises(SystemExit) as exc:
            notify.main()
    assert exc.value.code == 0


def test_main_published_no_discord(tmp_path: Path,
                                   monkeypatch: pytest.MonkeyPatch):
    """published path with no Discord URL succeeds."""
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    input_file = tmp_path / "list.txt"
    input_file.write_text("chart-a\n")
    with patch("sys.argv",
               ["notify.py", "--type", "published",
                "--input-file", str(input_file), "--verbose"]):
        with pytest.raises(SystemExit) as exc:
            notify.main()
    assert exc.value.code == 0
