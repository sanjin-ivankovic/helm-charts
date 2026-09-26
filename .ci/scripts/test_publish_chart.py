"""Tests for publish_chart.py.

ChartPublisher orchestrates:
  - chart_version_exists() — `helm show chart` probe for idempotency
  - get_registry_path() — env-driven registry URL with fallbacks
  - publish_chart() — full happy path with idempotent skip
  - _push_to_registry() — `helm push` + error logging
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

import publish_chart


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


def _make_chart(charts_dir: Path, name: str, version: str = "1.0.0",
                **extra: object) -> Path:
    chart_dir = charts_dir / name
    chart_dir.mkdir(parents=True)
    metadata = {
        "apiVersion": "v2",
        "name": name,
        "version": version,
        "appVersion": "1.0.0",
        **extra,
    }
    (chart_dir / "Chart.yaml").write_text(yaml.dump(metadata))
    return chart_dir


def _make_package(packages_dir: Path, chart_name: str, version: str) -> Path:
    """Create a fake tarball just so the path exists."""
    packages_dir.mkdir(parents=True, exist_ok=True)
    pkg = packages_dir / f"{chart_name}-{version}.tgz"
    pkg.write_bytes(b"\x1f\x8b\x08\x00")  # gzip magic header
    return pkg


# --------------------------------------------------------------------------
# get_registry_path
# --------------------------------------------------------------------------


class TestGetRegistryPath:
    def test_uses_ci_registry_image_env(self, tmp_path: Path,
                                        monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CI_REGISTRY_IMAGE", "harbor.example.com/team/charts")
        p = publish_chart.ChartPublisher(charts_dir=str(tmp_path))
        assert p.get_registry_path() == "oci://harbor.example.com/team/charts"

    def test_falls_back_to_default(self, tmp_path: Path,
                                   monkeypatch: pytest.MonkeyPatch):
        for v in ("CI_REGISTRY_IMAGE", "REGISTRY_HOST", "REGISTRY_OWNER",
                  "REGISTRY_PROJECT"):
            monkeypatch.delenv(v, raising=False)
        p = publish_chart.ChartPublisher(charts_dir=str(tmp_path))
        assert p.get_registry_path() == "oci://registry.example.com/example-org/helm-charts"

    def test_custom_host_owner_project(self, tmp_path: Path,
                                       monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("CI_REGISTRY_IMAGE", raising=False)
        monkeypatch.setenv("REGISTRY_HOST", "registry.test")
        monkeypatch.setenv("REGISTRY_OWNER", "myorg")
        monkeypatch.setenv("REGISTRY_PROJECT", "charts")
        p = publish_chart.ChartPublisher(charts_dir=str(tmp_path))
        assert p.get_registry_path() == "oci://registry.test/myorg/charts"


# --------------------------------------------------------------------------
# chart_version_exists — wraps `helm show chart`
# --------------------------------------------------------------------------


class TestChartVersionExists:
    def test_returns_true_when_helm_succeeds(self, tmp_path: Path):
        p = publish_chart.ChartPublisher(charts_dir=str(tmp_path))
        with patch.object(p.cmd_runner, "run_helm", return_value=(0, "found", "")):
            assert p.chart_version_exists("reg.test/team/charts",
                                          "alpha", "1.0.0") is True

    def test_returns_false_when_helm_fails(self, tmp_path: Path):
        p = publish_chart.ChartPublisher(charts_dir=str(tmp_path))
        with patch.object(p.cmd_runner, "run_helm", return_value=(1, "", "not found")):
            assert p.chart_version_exists("reg.test/team/charts",
                                          "alpha", "1.0.0") is False

    def test_uses_correct_helm_args(self, tmp_path: Path):
        p = publish_chart.ChartPublisher(charts_dir=str(tmp_path))
        with patch.object(p.cmd_runner, "run_helm") as mock:
            mock.return_value = (0, "", "")
            p.chart_version_exists("reg.test/team", "myapp", "2.0.0")
        args, kwargs = mock.call_args
        # Verify the positional helm args: show chart oci://reg.test/team/myapp
        # --version 2.0.0
        assert args[0] == "show"
        assert args[1] == "chart"
        assert "oci://reg.test/team/myapp" in args
        assert "2.0.0" in args
        assert kwargs.get("check") is False


# --------------------------------------------------------------------------
# publish_chart (full flow)
# --------------------------------------------------------------------------


class TestPublishChart:
    def test_chart_not_found_returns_false(self, tmp_path: Path,
                                           caplog: pytest.LogCaptureFixture):
        # No chart exists at all.
        p = publish_chart.ChartPublisher(
            charts_dir=str(tmp_path / "charts"),
            packages_dir=str(tmp_path / "pkgs"),
        )
        with caplog.at_level(logging.ERROR):
            assert p.publish_chart("ghost") is False

    def test_missing_package_returns_false(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        _make_chart(charts_dir, "alpha", version="1.0.0")
        p = publish_chart.ChartPublisher(
            charts_dir=str(charts_dir),
            packages_dir=str(tmp_path / "pkgs"),  # empty, no .tgz
        )
        with patch.object(p.cmd_runner, "run_helm", return_value=(0, "", "")):
            assert p.publish_chart("alpha") is False

    def test_idempotent_skip_when_version_exists(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        pkgs_dir = tmp_path / "pkgs"
        _make_chart(charts_dir, "alpha", version="1.0.0")
        _make_package(pkgs_dir, "alpha", "1.0.0")
        p = publish_chart.ChartPublisher(
            charts_dir=str(charts_dir),
            packages_dir=str(pkgs_dir),
        )
        with patch.object(p.cmd_runner, "run_helm") as mock:
            # chart_version_exists() → True; never attempts push.
            mock.return_value = (0, "", "")
            assert p.publish_chart("alpha") is True
            # `helm show chart` was called once; `helm push` was NOT.
            push_calls = [c for c in mock.call_args_list
                          if c.args and c.args[0] == "push"]
            assert push_calls == []

    def test_push_when_version_missing(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        pkgs_dir = tmp_path / "pkgs"
        _make_chart(charts_dir, "alpha", version="1.0.0")
        _make_package(pkgs_dir, "alpha", "1.0.0")
        p = publish_chart.ChartPublisher(
            charts_dir=str(charts_dir),
            packages_dir=str(pkgs_dir),
        )
        # show chart → 1 (not found); push → 0 (success).
        with patch.object(p.cmd_runner, "run_helm",
                          side_effect=[(1, "", "not found"), (0, "ok", "")]) as mock:
            assert p.publish_chart("alpha") is True
        # Both show + push should have been called.
        called = [c.args[0] for c in mock.call_args_list]
        assert "show" in called
        assert "push" in called

    def test_push_failure_returns_false(self, tmp_path: Path,
                                        caplog: pytest.LogCaptureFixture):
        charts_dir = tmp_path / "charts"
        pkgs_dir = tmp_path / "pkgs"
        _make_chart(charts_dir, "alpha", version="1.0.0")
        _make_package(pkgs_dir, "alpha", "1.0.0")
        p = publish_chart.ChartPublisher(
            charts_dir=str(charts_dir),
            packages_dir=str(pkgs_dir),
        )
        with caplog.at_level(logging.ERROR):
            with patch.object(p.cmd_runner, "run_helm",
                              side_effect=[(1, "", ""), (1, "", "auth failed")]):
                assert p.publish_chart("alpha") is False
        # Error log includes the actionable hints.
        joined = "\n".join(r.message for r in caplog.records)
        assert "auth failed" in joined
        assert "helm registry login" in joined


# --------------------------------------------------------------------------
# main()
# --------------------------------------------------------------------------


class TestMain:
    def test_neither_arg_errors(self, tmp_path: Path):
        with patch("sys.argv",
                   ["publish_chart.py", "--charts-dir", str(tmp_path)]):
            with pytest.raises(SystemExit) as exc:
                publish_chart.main()
        assert exc.value.code == 2  # argparse error

    def test_missing_input_file_exits_failure(self, tmp_path: Path):
        with patch("sys.argv",
                   ["publish_chart.py", "--input-file",
                    str(tmp_path / "nope.txt")]):
            with pytest.raises(SystemExit) as exc:
                publish_chart.main()
        assert exc.value.code == 1

    def test_empty_input_file_exits_success(self, tmp_path: Path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        with patch("sys.argv", ["publish_chart.py", "--input-file", str(f)]):
            with pytest.raises(SystemExit) as exc:
                publish_chart.main()
        assert exc.value.code == 0

    def test_single_chart_success(self, tmp_path: Path,
                                  monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("CI_REGISTRY_IMAGE", raising=False)
        charts_dir = tmp_path / "charts"
        pkgs_dir = tmp_path / "pkgs"
        _make_chart(charts_dir, "alpha", version="1.0.0")
        _make_package(pkgs_dir, "alpha", "1.0.0")
        with patch("publish_chart.CommandRunner.run_helm",
                   side_effect=[(1, "", ""), (0, "", "")]):
            with patch("sys.argv",
                       ["publish_chart.py", "alpha",
                        "--charts-dir", str(charts_dir),
                        "--packages-dir", str(pkgs_dir)]):
                with pytest.raises(SystemExit) as exc:
                    publish_chart.main()
        assert exc.value.code == 0

    def test_input_file_with_failure_exits_1(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        pkgs_dir = tmp_path / "pkgs"
        _make_chart(charts_dir, "alpha", version="1.0.0")
        _make_package(pkgs_dir, "alpha", "1.0.0")
        f = tmp_path / "list.txt"
        f.write_text("alpha\n")
        # show → not exist, push → fail
        with patch("publish_chart.CommandRunner.run_helm",
                   side_effect=[(1, "", ""), (1, "", "bad creds")]):
            with patch("sys.argv",
                       ["publish_chart.py",
                        "--input-file", str(f),
                        "--charts-dir", str(charts_dir),
                        "--packages-dir", str(pkgs_dir),
                        "--verbose"]):
                with pytest.raises(SystemExit) as exc:
                    publish_chart.main()
        assert exc.value.code == 1
