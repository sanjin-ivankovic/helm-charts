"""Tests for package_chart.py.

ChartPackager:
  - sync_helmignore: merge .gitignore patterns into .helmignore
  - _build_dependencies: helm dependency build
  - _package_chart: helm package
  - package_chart: full flow (lookup, sync, deps?, package, verify .tgz)
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

import package_chart


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _make_chart(charts_dir: Path, name: str, version: str = "1.0.0",
                **extra: object) -> Path:
    chart_dir = charts_dir / name
    chart_dir.mkdir(parents=True)
    md = {"apiVersion": "v2", "name": name, "version": version,
          "appVersion": "1.0.0", **extra}
    (chart_dir / "Chart.yaml").write_text(yaml.dump(md))
    return chart_dir


# --------------------------------------------------------------------------
# sync_helmignore
# --------------------------------------------------------------------------


class TestSyncHelmignore:
    def test_no_gitignore_skips(self, tmp_path: Path,
                                caplog: pytest.LogCaptureFixture):
        # No .gitignore in charts dir → warn + return.
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        chart_dir = _make_chart(charts_dir, "x")
        p = package_chart.ChartPackager(charts_dir=str(charts_dir))
        with caplog.at_level(logging.WARNING):
            p.sync_helmignore(chart_dir)
        assert any(".gitignore not found" in r.message for r in caplog.records)
        assert not (chart_dir / ".helmignore").exists()

    def test_merges_into_existing_helmignore(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        (charts_dir / ".gitignore").write_text("*.log\n.cache/\n")
        chart_dir = _make_chart(charts_dir, "x")
        (chart_dir / ".helmignore").write_text("# Comment\n*.bak\n*.log\n")

        p = package_chart.ChartPackager(charts_dir=str(charts_dir))
        p.sync_helmignore(chart_dir)

        content = (chart_dir / ".helmignore").read_text()
        # Patterns merged (set-union, sorted).
        patterns = [line for line in content.splitlines() if line]
        assert "*.log" in patterns       # from both
        assert "*.bak" in patterns       # from existing helmignore
        assert ".cache/" in patterns     # from gitignore
        # Comments are dropped — that's intentional from the
        # implementation's `line.startswith('#')` filter.
        assert "# Comment" not in patterns

    def test_creates_helmignore_when_missing(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        (charts_dir / ".gitignore").write_text("*.pyc\n__pycache__/\n")
        chart_dir = _make_chart(charts_dir, "x")
        # No .helmignore yet.

        p = package_chart.ChartPackager(charts_dir=str(charts_dir))
        p.sync_helmignore(chart_dir)

        assert (chart_dir / ".helmignore").exists()
        patterns = (chart_dir / ".helmignore").read_text().splitlines()
        assert "*.pyc" in patterns
        assert "__pycache__/" in patterns

    def test_ignores_blank_and_comment_lines(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        (charts_dir / ".gitignore").write_text(
            "# header\n\n*.log\n   \n# trailer\n"
        )
        chart_dir = _make_chart(charts_dir, "x")

        p = package_chart.ChartPackager(charts_dir=str(charts_dir))
        p.sync_helmignore(chart_dir)
        patterns = [
            line for line in (chart_dir / ".helmignore").read_text().splitlines()
            if line
        ]
        assert patterns == ["*.log"]


# --------------------------------------------------------------------------
# _build_dependencies / _package_chart (private helpers)
# --------------------------------------------------------------------------


class TestBuildDependencies:
    def test_success(self, tmp_path: Path):
        p = package_chart.ChartPackager(charts_dir=str(tmp_path))
        with patch.object(p.cmd_runner, "run_helm", return_value=(0, "out", "")):
            assert p._build_dependencies(tmp_path) is True

    def test_failure_logs_both_streams(self, tmp_path: Path,
                                       caplog: pytest.LogCaptureFixture):
        p = package_chart.ChartPackager(charts_dir=str(tmp_path))
        with caplog.at_level(logging.ERROR):
            with patch.object(p.cmd_runner, "run_helm",
                              return_value=(1, "out", "err")):
                assert p._build_dependencies(tmp_path) is False
        text = "\n".join(r.message for r in caplog.records)
        assert "out" in text
        assert "err" in text


class TestPackageChartInternal:
    def test_success(self, tmp_path: Path):
        p = package_chart.ChartPackager(charts_dir=str(tmp_path))
        with patch.object(p.cmd_runner, "run_helm", return_value=(0, "ok", "")):
            assert p._package_chart(tmp_path) is True

    def test_failure(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        p = package_chart.ChartPackager(charts_dir=str(tmp_path))
        with caplog.at_level(logging.ERROR):
            with patch.object(p.cmd_runner, "run_helm",
                              return_value=(1, "out", "err")):
                assert p._package_chart(tmp_path) is False
        text = "\n".join(r.message for r in caplog.records)
        assert "out" in text
        assert "err" in text


# --------------------------------------------------------------------------
# package_chart full flow
# --------------------------------------------------------------------------


class TestPackageChartFlow:
    def test_chart_not_found(self, tmp_path: Path):
        p = package_chart.ChartPackager(
            charts_dir=str(tmp_path / "charts"),
            packages_dir=str(tmp_path / "pkgs"),
        )
        assert p.package_chart("ghost") is False

    def test_chart_without_deps_packages(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        pkgs_dir = tmp_path / "pkgs"
        _make_chart(charts_dir, "alpha", version="1.0.0")

        p = package_chart.ChartPackager(
            charts_dir=str(charts_dir), packages_dir=str(pkgs_dir)
        )

        # helm package "creates" the package — simulate by having the
        # patched run_helm side-effect actually write the tarball.
        def fake_helm(*args, **kwargs):
            pkgs_dir.mkdir(parents=True, exist_ok=True)
            (pkgs_dir / "alpha-1.0.0.tgz").write_bytes(b"\x1f\x8b")
            return (0, "ok", "")

        with patch.object(p.cmd_runner, "run_helm",
                          side_effect=fake_helm) as mock:
            assert p.package_chart("alpha") is True
        # No `dependency` step called.
        called_subcmds = [c.args[0] for c in mock.call_args_list]
        assert "dependency" not in called_subcmds

    def test_chart_with_deps_builds_first(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        pkgs_dir = tmp_path / "pkgs"
        _make_chart(charts_dir, "alpha", version="1.0.0",
                    dependencies=[{"name": "redis", "version": "1"}])

        p = package_chart.ChartPackager(
            charts_dir=str(charts_dir), packages_dir=str(pkgs_dir)
        )

        def fake_helm(*args, **kwargs):
            if args[0] == "package":
                pkgs_dir.mkdir(parents=True, exist_ok=True)
                (pkgs_dir / "alpha-1.0.0.tgz").write_bytes(b"\x1f\x8b")
            return (0, "", "")

        with patch.object(p.cmd_runner, "run_helm",
                          side_effect=fake_helm) as mock:
            assert p.package_chart("alpha") is True
        called_subcmds = [c.args[0] for c in mock.call_args_list]
        assert called_subcmds[0] == "dependency"
        assert "package" in called_subcmds

    def test_dependency_build_failure(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        pkgs_dir = tmp_path / "pkgs"
        _make_chart(charts_dir, "alpha", version="1.0.0",
                    dependencies=[{"name": "redis", "version": "1"}])
        p = package_chart.ChartPackager(
            charts_dir=str(charts_dir), packages_dir=str(pkgs_dir)
        )
        with patch.object(p.cmd_runner, "run_helm",
                          return_value=(1, "", "dep err")):
            assert p.package_chart("alpha") is False

    def test_package_failure(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        pkgs_dir = tmp_path / "pkgs"
        _make_chart(charts_dir, "alpha", version="1.0.0")
        p = package_chart.ChartPackager(
            charts_dir=str(charts_dir), packages_dir=str(pkgs_dir)
        )
        with patch.object(p.cmd_runner, "run_helm",
                          return_value=(1, "", "package err")):
            assert p.package_chart("alpha") is False

    def test_missing_tgz_after_helm_success_returns_false(self, tmp_path: Path):
        """helm package returns 0 but the .tgz file isn't there for some reason.
        The verify step should catch it."""
        charts_dir = tmp_path / "charts"
        pkgs_dir = tmp_path / "pkgs"
        _make_chart(charts_dir, "alpha", version="1.0.0")
        p = package_chart.ChartPackager(
            charts_dir=str(charts_dir), packages_dir=str(pkgs_dir)
        )
        # helm returns success but doesn't actually create the .tgz.
        with patch.object(p.cmd_runner, "run_helm", return_value=(0, "", "")):
            assert p.package_chart("alpha") is False


# --------------------------------------------------------------------------
# main()
# --------------------------------------------------------------------------


class TestMain:
    def test_neither_arg_errors(self, tmp_path: Path):
        with patch("sys.argv",
                   ["package_chart.py", "--charts-dir", str(tmp_path)]):
            with pytest.raises(SystemExit) as exc:
                package_chart.main()
        assert exc.value.code == 2

    def test_missing_input_file_exits_failure(self, tmp_path: Path):
        with patch("sys.argv",
                   ["package_chart.py", "--input-file",
                    str(tmp_path / "nope")]):
            with pytest.raises(SystemExit) as exc:
                package_chart.main()
        assert exc.value.code == 1

    def test_empty_input_file_exits_success(self, tmp_path: Path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        with patch("sys.argv",
                   ["package_chart.py", "--input-file", str(f)]):
            with pytest.raises(SystemExit) as exc:
                package_chart.main()
        assert exc.value.code == 0

    def test_single_chart_success(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        pkgs_dir = tmp_path / "pkgs"
        _make_chart(charts_dir, "alpha", version="1.0.0")

        def fake_helm(*args, **kwargs):
            pkgs_dir.mkdir(parents=True, exist_ok=True)
            (pkgs_dir / "alpha-1.0.0.tgz").write_bytes(b"\x1f\x8b")
            return (0, "", "")

        with patch("package_chart.CommandRunner.run_helm",
                   side_effect=fake_helm):
            with patch("sys.argv",
                       ["package_chart.py", "alpha",
                        "--charts-dir", str(charts_dir),
                        "--packages-dir", str(pkgs_dir),
                        "--verbose"]):
                with pytest.raises(SystemExit) as exc:
                    package_chart.main()
        assert exc.value.code == 0

    def test_input_file_with_failure(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        pkgs_dir = tmp_path / "pkgs"
        _make_chart(charts_dir, "alpha", version="1.0.0")
        f = tmp_path / "list.txt"
        f.write_text("alpha\n")

        with patch("package_chart.CommandRunner.run_helm",
                   return_value=(1, "", "err")):
            with patch("sys.argv",
                       ["package_chart.py", "--input-file", str(f),
                        "--charts-dir", str(charts_dir),
                        "--packages-dir", str(pkgs_dir)]):
                with pytest.raises(SystemExit) as exc:
                    package_chart.main()
        assert exc.value.code == 1
