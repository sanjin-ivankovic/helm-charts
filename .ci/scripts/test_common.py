"""Tests for the common.py shared utilities.

Covers:
  - ExitCode (enum sanity)
  - Custom exception classes (instantiation + inheritance)
  - ChartMetadata (.from_dict construction, .has_dependencies property)
  - CommandRunner (subprocess wrapping, check vs no-check, run_helm/run_git)
  - ChartHelper (is_valid_chart, get_chart_path, read_chart_metadata,
    get_all_charts, chart_has_dependencies) — uses tmp_path filesystem
  - setup_logging
  - create_directory
  - format_duration
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from common import (
    ChartError,
    ChartHelper,
    ChartMetadata,
    ChartNotFoundError,
    ChartValidationError,
    CommandRunner,
    ExitCode,
    create_directory,
    format_duration,
    setup_logging,
)


# --------------------------------------------------------------------------
# ExitCode + exception hierarchy
# --------------------------------------------------------------------------


class TestExitCode:
    def test_success_is_zero(self):
        assert int(ExitCode.SUCCESS) == 0

    def test_failure_is_one(self):
        assert int(ExitCode.FAILURE) == 1

    def test_distinct_values(self):
        codes = {ExitCode.SUCCESS, ExitCode.FAILURE,
                 ExitCode.VALIDATION_ERROR, ExitCode.NOT_FOUND}
        assert len(codes) == 4


class TestExceptions:
    def test_chart_not_found_is_chart_error(self):
        with pytest.raises(ChartError):
            raise ChartNotFoundError("no chart")

    def test_chart_validation_is_chart_error(self):
        with pytest.raises(ChartError):
            raise ChartValidationError("bad chart")

    def test_chart_error_message_preserved(self):
        try:
            raise ChartNotFoundError("foo bar")
        except ChartNotFoundError as e:
            assert "foo bar" in str(e)


# --------------------------------------------------------------------------
# ChartMetadata dataclass
# --------------------------------------------------------------------------


class TestChartMetadata:
    def test_from_dict_minimal(self):
        m = ChartMetadata.from_dict({"name": "foo", "version": "1.0.0",
                                     "appVersion": "1.2.3"})
        assert m.name == "foo"
        assert m.version == "1.0.0"
        assert m.app_version == "1.2.3"
        assert m.api_version == "v2"  # default
        assert m.kube_version is None
        assert m.description is None
        assert m.dependencies == []

    def test_from_dict_full(self):
        m = ChartMetadata.from_dict({
            "name": "bar",
            "version": "2.0.0",
            "appVersion": "3.4.5",
            "apiVersion": "v2",
            "kubeVersion": ">=1.20.0",
            "description": "a chart",
            "dependencies": [{"name": "redis", "version": "7.0.0"}],
        })
        assert m.name == "bar"
        assert m.kube_version == ">=1.20.0"
        assert m.description == "a chart"
        assert len(m.dependencies) == 1
        assert m.dependencies[0]["name"] == "redis"

    def test_from_dict_handles_missing_fields(self):
        # Empty dict → all defaults, no exception.
        m = ChartMetadata.from_dict({})
        assert m.name == ""
        assert m.version == ""
        assert m.app_version == ""

    def test_has_dependencies_true(self):
        m = ChartMetadata.from_dict({"name": "x", "version": "1",
                                     "appVersion": "1",
                                     "dependencies": [{"name": "redis"}]})
        assert m.has_dependencies is True

    def test_has_dependencies_false(self):
        m = ChartMetadata.from_dict({"name": "x", "version": "1",
                                     "appVersion": "1"})
        assert m.has_dependencies is False

    def test_frozen_dataclass(self):
        m = ChartMetadata.from_dict({"name": "x", "version": "1",
                                     "appVersion": "1"})
        with pytest.raises(Exception):  # FrozenInstanceError
            m.name = "y"  # type: ignore[misc]


# --------------------------------------------------------------------------
# CommandRunner
# --------------------------------------------------------------------------


class TestCommandRunner:
    def test_run_success(self):
        runner = CommandRunner()
        code, out, err = runner.run(["echo", "hello"])
        assert code == 0
        assert "hello" in out
        assert err == ""

    def test_run_failure_with_check_raises(self):
        runner = CommandRunner()
        with pytest.raises(subprocess.CalledProcessError):
            # `false` is a builtin command that exits non-zero
            # We disable capture so the error path raises.
            runner.run(["false"], check=True, capture=False)

    def test_run_failure_with_capture_returns_code(self):
        runner = CommandRunner()
        # With capture=True, CalledProcessError is caught and returned.
        code, out, err = runner.run(["false"], check=True, capture=True)
        assert code != 0

    def test_run_no_check_returns_code(self):
        runner = CommandRunner()
        code, _out, _err = runner.run(["false"], check=False)
        assert code != 0

    def test_run_helm(self):
        # Mock subprocess at the run() level to avoid needing helm.
        runner = CommandRunner()
        with patch.object(runner, "run") as mock_run:
            mock_run.return_value = (0, "v4.0.0", "")
            runner.run_helm("version", "--short")
            mock_run.assert_called_once_with(
                ["helm", "version", "--short"], check=True
            )

    def test_run_git(self):
        runner = CommandRunner()
        with patch.object(runner, "run") as mock_run:
            mock_run.return_value = (0, "abc123", "")
            runner.run_git("rev-parse", "HEAD")
            mock_run.assert_called_once_with(
                ["git", "rev-parse", "HEAD"], check=True
            )

    def test_cwd_passed_to_subprocess(self, tmp_path: Path):
        # Verify cwd kwarg gets forwarded.
        runner = CommandRunner(cwd=tmp_path)
        code, out, _err = runner.run(["pwd"])
        assert code == 0
        # macOS prepends /private/ to /var/ paths, so do an endswith check
        assert str(tmp_path) in out or out.strip().endswith(tmp_path.name)

    def test_verbose_logs(self, caplog: pytest.LogCaptureFixture):
        runner = CommandRunner(verbose=True)
        with caplog.at_level(logging.DEBUG):
            runner.run(["true"])
        assert any("Running:" in r.message for r in caplog.records)


# --------------------------------------------------------------------------
# ChartHelper — filesystem-based
# --------------------------------------------------------------------------


def _make_chart(parent: Path, name: str, **chart_yaml_fields) -> Path:
    """Build a minimal valid chart under parent/<name>/."""
    chart_dir = parent / name
    chart_dir.mkdir(parents=True)
    chart_yaml = {
        "apiVersion": "v2",
        "name": name,
        "version": "1.0.0",
        "appVersion": "1.0.0",
        **chart_yaml_fields,
    }
    import yaml as _yaml
    (chart_dir / "Chart.yaml").write_text(_yaml.dump(chart_yaml))
    return chart_dir


class TestChartHelperIsValid:
    def test_returns_true_for_valid_chart(self, tmp_path: Path):
        _make_chart(tmp_path, "myapp")
        helper = ChartHelper(tmp_path)
        assert helper.is_valid_chart("myapp") is True

    def test_returns_false_for_empty_name(self, tmp_path: Path):
        helper = ChartHelper(tmp_path)
        assert helper.is_valid_chart("") is False

    def test_returns_false_for_dotfile(self, tmp_path: Path):
        helper = ChartHelper(tmp_path)
        assert helper.is_valid_chart(".hidden") is False

    def test_returns_false_for_missing_dir(self, tmp_path: Path):
        helper = ChartHelper(tmp_path)
        assert helper.is_valid_chart("nope") is False

    def test_returns_false_for_dir_without_chart_yaml(self, tmp_path: Path):
        (tmp_path / "empty").mkdir()
        helper = ChartHelper(tmp_path)
        assert helper.is_valid_chart("empty") is False


class TestChartHelperGetPath:
    def test_returns_path_for_valid_chart(self, tmp_path: Path):
        _make_chart(tmp_path, "myapp")
        helper = ChartHelper(tmp_path)
        assert helper.get_chart_path("myapp") == tmp_path / "myapp"

    def test_raises_when_dir_missing(self, tmp_path: Path):
        helper = ChartHelper(tmp_path)
        with pytest.raises(ChartNotFoundError, match="Chart directory"):
            helper.get_chart_path("nope")

    def test_raises_when_chart_yaml_missing(self, tmp_path: Path):
        (tmp_path / "broken").mkdir()
        helper = ChartHelper(tmp_path)
        with pytest.raises(ChartNotFoundError, match="Chart.yaml not found"):
            helper.get_chart_path("broken")


class TestChartHelperReadMetadata:
    def test_reads_minimal_chart(self, tmp_path: Path):
        _make_chart(tmp_path, "myapp")
        helper = ChartHelper(tmp_path)
        m = helper.read_chart_metadata("myapp")
        assert m.name == "myapp"
        assert m.version == "1.0.0"

    def test_reads_chart_with_dependencies(self, tmp_path: Path):
        _make_chart(tmp_path, "withdeps",
                    dependencies=[{"name": "redis", "version": "7.0.0"}])
        helper = ChartHelper(tmp_path)
        m = helper.read_chart_metadata("withdeps")
        assert m.has_dependencies
        assert m.dependencies[0]["name"] == "redis"

    def test_raises_on_invalid_yaml(self, tmp_path: Path):
        chart_dir = tmp_path / "broken"
        chart_dir.mkdir()
        # Write a yaml scalar (not a mapping) → fails format check
        (chart_dir / "Chart.yaml").write_text("just a string")
        helper = ChartHelper(tmp_path)
        with pytest.raises(ChartValidationError, match="Invalid Chart.yaml"):
            helper.read_chart_metadata("broken")

    def test_raises_on_yaml_parse_error(self, tmp_path: Path):
        chart_dir = tmp_path / "broken"
        chart_dir.mkdir()
        # Unclosed brace = YAML parse error
        (chart_dir / "Chart.yaml").write_text("name: {")
        helper = ChartHelper(tmp_path)
        with pytest.raises(ChartValidationError, match="Failed to parse"):
            helper.read_chart_metadata("broken")

    def test_raises_when_missing(self, tmp_path: Path):
        helper = ChartHelper(tmp_path)
        with pytest.raises(ChartNotFoundError):
            helper.read_chart_metadata("ghost")


class TestChartHelperGetAllCharts:
    def test_empty_dir(self, tmp_path: Path):
        helper = ChartHelper(tmp_path)
        assert helper.get_all_charts() == []

    def test_returns_sorted(self, tmp_path: Path):
        _make_chart(tmp_path, "zebra")
        _make_chart(tmp_path, "apple")
        _make_chart(tmp_path, "mango")
        helper = ChartHelper(tmp_path)
        assert helper.get_all_charts() == ["apple", "mango", "zebra"]

    def test_skips_dotfiles_and_invalid(self, tmp_path: Path):
        _make_chart(tmp_path, "ok")
        (tmp_path / ".git").mkdir()        # dotfile
        (tmp_path / "broken").mkdir()      # no Chart.yaml
        helper = ChartHelper(tmp_path)
        assert helper.get_all_charts() == ["ok"]

    def test_missing_charts_dir_returns_empty(self, tmp_path: Path):
        helper = ChartHelper(tmp_path / "does-not-exist")
        assert helper.get_all_charts() == []


class TestChartHelperHasDependencies:
    def test_true_when_chart_has_deps(self, tmp_path: Path):
        _make_chart(tmp_path, "yes",
                    dependencies=[{"name": "redis", "version": "1"}])
        helper = ChartHelper(tmp_path)
        assert helper.chart_has_dependencies("yes") is True

    def test_false_when_chart_has_no_deps(self, tmp_path: Path):
        _make_chart(tmp_path, "no")
        helper = ChartHelper(tmp_path)
        assert helper.chart_has_dependencies("no") is False

    def test_returns_false_on_missing_chart(self, tmp_path: Path):
        # Documented behavior: log + return False on error, don't raise.
        helper = ChartHelper(tmp_path)
        assert helper.chart_has_dependencies("ghost") is False


# --------------------------------------------------------------------------
# Standalone utilities
# --------------------------------------------------------------------------


class TestSetupLogging:
    def test_returns_logger(self):
        logger = setup_logging()
        assert isinstance(logger, logging.Logger)

    def test_accepts_custom_level(self):
        logger = setup_logging(level=logging.DEBUG)
        # logging.basicConfig(force=True) — root level is now DEBUG
        assert logging.getLogger().level == logging.DEBUG

    def test_accepts_custom_format(self):
        # Doesn't blow up with a non-default format string
        setup_logging(format_string="%(message)s")


class TestCreateDirectory:
    def test_creates_simple_dir(self, tmp_path: Path):
        target = tmp_path / "new"
        create_directory(target)
        assert target.is_dir()

    def test_creates_nested(self, tmp_path: Path):
        target = tmp_path / "a" / "b" / "c"
        create_directory(target)
        assert target.is_dir()

    def test_existing_dir_ok_by_default(self, tmp_path: Path):
        target = tmp_path / "x"
        target.mkdir()
        # Should not raise
        create_directory(target)

    def test_existing_dir_raises_when_disallowed(self, tmp_path: Path):
        target = tmp_path / "x"
        target.mkdir()
        with pytest.raises(FileExistsError):
            create_directory(target, exist_ok=False)


class TestFormatDuration:
    def test_under_a_minute(self):
        assert format_duration(0.5) == "0.50s"
        assert format_duration(12.34) == "12.34s"
        assert format_duration(59.99) == "59.99s"

    def test_one_minute(self):
        assert format_duration(60.0) == "1m 0.00s"

    def test_multiple_minutes(self):
        assert format_duration(125.5) == "2m 5.50s"

    def test_large_value(self):
        # 1 hour = 3600s = 60m
        assert format_duration(3600.0) == "60m 0.00s"
