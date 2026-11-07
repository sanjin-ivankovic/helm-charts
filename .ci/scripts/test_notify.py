"""Tests for notify.py.

NotificationSender has two responsibilities:
  1. Print human-readable summaries to stdout (validated, published)
  2. Publish an ntfy notification when NTFY_URL + NTFY_TOKEN are set
     and charts > 0

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
        for v in ("CI_REGISTRY_IMAGE", "NTFY_URL", "NTFY_TOKEN", "NTFY_TOPIC", "CI_PIPELINE_URL",
                  "CI_COMMIT_SHORT_SHA", "CI_COMMIT_REF_NAME",
                  "CI_COMMIT_SHA", "CI_COMMIT_REF"):
            monkeypatch.delenv(v, raising=False)
        s = notify.NotificationSender("validated")
        assert s.notification_type == "validated"
        assert s.registry_image == "registry.example.com/example-org/helm-charts"
        assert s.commit_sha == "unknown"
        assert s.ref_name == "unknown"
        assert s.ntfy_url is None
        assert s.ntfy_token is None
        assert s.ntfy_topic == "gitlab-pipelines"
        assert s.pipeline_url == ""

    def test_picks_up_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CI_REGISTRY_IMAGE", "registry.example.com/charts")
        monkeypatch.setenv("CI_COMMIT_SHORT_SHA", "abc12345")
        monkeypatch.setenv("CI_COMMIT_REF_NAME", "main")
        monkeypatch.setenv("NTFY_URL", "https://ntfy.example.com")
        monkeypatch.setenv("NTFY_TOKEN", "tk_fake")
        monkeypatch.setenv("NTFY_TOPIC", "charts")
        s = notify.NotificationSender("published")
        assert s.registry_image == "registry.example.com/charts"
        assert s.commit_sha == "abc12345"
        assert s.ref_name == "main"
        assert s.ntfy_url == "https://ntfy.example.com"
        assert s.ntfy_token == "tk_fake"
        assert s.ntfy_topic == "charts"


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
# send_ntfy_notification — mock `requests` carefully
# --------------------------------------------------------------------------


def _fake_requests(monkeypatch: pytest.MonkeyPatch, **post_kwargs) -> MagicMock:
    """Install a stub `requests` so the lazy import picks it up."""
    fake_requests = MagicMock()

    class FakeRequestException(Exception):
        pass

    fake_requests.exceptions.RequestException = FakeRequestException
    fake_requests.post = MagicMock(**post_kwargs)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    return fake_requests


class TestSendNtfy:
    @pytest.fixture(autouse=True)
    def _configured(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("NTFY_URL", "https://ntfy.example.com/")
        monkeypatch.setenv("NTFY_TOKEN", "tk_fake")
        monkeypatch.delenv("NTFY_TOPIC", raising=False)
        monkeypatch.setenv("CI_PIPELINE_URL", "https://git.example.com/p/1")
        monkeypatch.setenv("CI_COMMIT_SHORT_SHA", "abc12345")
        monkeypatch.setenv("CI_COMMIT_REF_NAME", "main")

    @pytest.mark.parametrize("unset", ["NTFY_URL", "NTFY_TOKEN"])
    def test_unconfigured_returns_true(self, monkeypatch: pytest.MonkeyPatch,
                                       unset: str):
        monkeypatch.delenv(unset)
        fake = _fake_requests(monkeypatch)
        s = notify.NotificationSender("published")
        assert s.send_ntfy_notification(["chart-a"]) is True
        fake.post.assert_not_called()

    def test_no_charts_returns_true(self, monkeypatch: pytest.MonkeyPatch):
        fake = _fake_requests(monkeypatch)
        s = notify.NotificationSender("published")
        assert s.send_ntfy_notification([]) is True
        fake.post.assert_not_called()

    def test_posts_payload_on_success(self, monkeypatch: pytest.MonkeyPatch):
        fake = _fake_requests(monkeypatch, return_value=MagicMock())
        s = notify.NotificationSender("published")
        assert s.send_ntfy_notification(["chart-a", "chart-b"]) is True
        fake.post.assert_called_once()
        args, kwargs = fake.post.call_args
        # Trailing slash stripped: JSON publishing posts to the server root.
        assert args[0] == "https://ntfy.example.com"
        assert kwargs["headers"] == {"Authorization": "Bearer tk_fake"}
        payload = kwargs["json"]
        assert payload["topic"] == "gitlab-pipelines"
        assert payload["title"] == "Helm charts published"
        assert "chart-a, chart-b" in payload["message"]
        assert "main · abc12345" in payload["message"]
        assert payload["click"] == "https://git.example.com/p/1"
        assert payload["priority"] == 3

    def test_topic_override(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("NTFY_TOPIC", "charts")
        fake = _fake_requests(monkeypatch, return_value=MagicMock())
        notify.NotificationSender("published").send_ntfy_notification(["c"])
        assert fake.post.call_args.kwargs["json"]["topic"] == "charts"

    def test_request_failure_returns_false(self, monkeypatch: pytest.MonkeyPatch,
                                           caplog: pytest.LogCaptureFixture):
        fake = _fake_requests(monkeypatch)
        fake.post.side_effect = fake.exceptions.RequestException("403 Forbidden")
        s = notify.NotificationSender("published")
        with caplog.at_level(logging.WARNING):
            assert s.send_ntfy_notification(["chart-a"]) is False
        assert any("ntfy notification failed" in r.message
                   for r in caplog.records)

    def test_missing_requests_library_returns_false(self):
        """ntfy configured but `requests` not installed: graceful skip."""
        real_import = __builtins__["__import__"] if isinstance(
            __builtins__, dict) else __import__

        def fake_import(name, *args, **kwargs):
            if name == "requests":
                raise ImportError("requests missing")
            return real_import(name, *args, **kwargs)

        s = notify.NotificationSender("published")
        with patch("builtins.__import__", side_effect=fake_import):
            assert s.send_ntfy_notification(["chart-a"]) is False


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
        monkeypatch.delenv("NTFY_URL", raising=False)
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


def test_main_published_no_ntfy(tmp_path: Path,
                                monkeypatch: pytest.MonkeyPatch):
    """published path with ntfy unconfigured succeeds."""
    monkeypatch.delenv("NTFY_URL", raising=False)
    input_file = tmp_path / "list.txt"
    input_file.write_text("chart-a\n")
    with patch("sys.argv",
               ["notify.py", "--type", "published",
                "--input-file", str(input_file), "--verbose"]):
        with pytest.raises(SystemExit) as exc:
            notify.main()
    assert exc.value.code == 0
