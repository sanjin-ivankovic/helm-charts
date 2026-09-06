#!/usr/bin/env python3
"""
Unit tests for validate_chart.py

Tests the chart validation logic including:
- Helm lint execution
- Dependency checking
- Template rendering
- Error handling
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest  # type: ignore
import yaml

# Import the module under test
import validate_chart  # type: ignore
from common import ChartMetadata  # type: ignore


class TestChartValidator:
    """Tests for ChartValidator class."""

    def test_validate_chart_success(self, tmp_path):
        """Test successful chart validation."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()

        chart_dir = charts_dir / "my-chart"
        chart_dir.mkdir()

        metadata = {
            "name": "my-chart",
            "version": "1.0.0",
            "appVersion": "1.0.0",
        }

        chart_yaml = chart_dir / "Chart.yaml"
        chart_yaml.write_text(yaml.dump(metadata))

        validator = validate_chart.ChartValidator(charts_dir=str(charts_dir))

        # Mock the helm commands to return success
        with patch.object(validator.cmd_runner, "run_helm") as mock_helm:
            mock_helm.return_value = (0, "Success", "")

            result = validator.validate_chart("my-chart")

            assert result is True
            # Should call helm lint and helm template (2 calls, no dependencies)
            assert mock_helm.call_count == 2

    def test_validate_chart_with_dependencies(self, tmp_path):
        """Test chart validation with dependencies."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()

        chart_dir = charts_dir / "my-chart"
        chart_dir.mkdir()

        metadata = {
            "name": "my-chart",
            "version": "1.0.0",
            "appVersion": "1.0.0",
            "dependencies": [{"name": "postgresql", "version": "12.0.0"}],
        }

        chart_yaml = chart_dir / "Chart.yaml"
        chart_yaml.write_text(yaml.dump(metadata))

        validator = validate_chart.ChartValidator(charts_dir=str(charts_dir))

        # Mock the helm commands to return success
        with patch.object(validator.cmd_runner, "run_helm") as mock_helm:
            mock_helm.return_value = (0, "Success", "")

            result = validator.validate_chart("my-chart")

            assert result is True
            # Should call helm lint, helm dependency update, and helm template (3 calls)
            assert mock_helm.call_count == 3

    def test_validate_chart_lint_failure(self, tmp_path):
        """Test chart validation with lint failure."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()

        chart_dir = charts_dir / "my-chart"
        chart_dir.mkdir()

        metadata = {
            "name": "my-chart",
            "version": "1.0.0",
            "appVersion": "1.0.0",
        }

        chart_yaml = chart_dir / "Chart.yaml"
        chart_yaml.write_text(yaml.dump(metadata))

        validator = validate_chart.ChartValidator(charts_dir=str(charts_dir))

        # Mock failed helm lint
        with patch.object(validator.cmd_runner, "run_helm") as mock_helm:
            mock_helm.return_value = (1, "", "Lint error")

            result = validator.validate_chart("my-chart")

            assert result is False
            # Should only call helm lint before failing
            assert mock_helm.call_count == 1

    def test_validate_chart_template_failure(self, tmp_path):
        """Test chart validation with template rendering failure."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()

        chart_dir = charts_dir / "my-chart"
        chart_dir.mkdir()

        metadata = {
            "name": "my-chart",
            "version": "1.0.0",
            "appVersion": "1.0.0",
        }

        chart_yaml = chart_dir / "Chart.yaml"
        chart_yaml.write_text(yaml.dump(metadata))

        validator = validate_chart.ChartValidator(charts_dir=str(charts_dir))

        # Mock helm commands: lint succeeds, template fails
        with patch.object(validator.cmd_runner, "run_helm") as mock_helm:
            mock_helm.side_effect = [
                (0, "Lint passed", ""),  # helm lint
                (1, "", "Template error"),  # helm template
            ]

            result = validator.validate_chart("my-chart")

            assert result is False
            # Should call helm lint and helm template
            assert mock_helm.call_count == 2

    def test_validate_chart_not_found(self, tmp_path):
        """Test validation with non-existent chart."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()

        validator = validate_chart.ChartValidator(charts_dir=str(charts_dir))
        result = validator.validate_chart("non-existent-chart")

        assert result is False

    def test_validate_chart_name_mismatch(self, tmp_path):
        """Test warning when directory name doesn't match Chart.yaml name."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()

        chart_dir = charts_dir / "my-chart"
        chart_dir.mkdir()

        # Directory is "my-chart" but Chart.yaml says "different-name"
        metadata = {
            "name": "different-name",
            "version": "1.0.0",
            "appVersion": "1.0.0",
        }

        chart_yaml = chart_dir / "Chart.yaml"
        chart_yaml.write_text(yaml.dump(metadata))

        validator = validate_chart.ChartValidator(charts_dir=str(charts_dir))

        # Mock the helm commands to return success
        with patch.object(validator.cmd_runner, "run_helm") as mock_helm:
            mock_helm.return_value = (0, "Success", "")

            # Should still validate but log warning
            result = validator.validate_chart("my-chart")

            assert result is True


def test_main_success(tmp_path):
    """Test main function with successful validation."""
    charts_dir = tmp_path / "charts"
    charts_dir.mkdir()

    chart_dir = charts_dir / "test-chart"
    chart_dir.mkdir()

    metadata = {
        "name": "test-chart",
        "version": "1.0.0",
        "appVersion": "1.0.0",
    }
    (chart_dir / "Chart.yaml").write_text(yaml.dump(metadata))

    with patch("validate_chart.CommandRunner.run_helm") as mock_helm:
        mock_helm.return_value = (0, "Success", "")

        with patch(
            "sys.argv",
            ["validate_chart.py", "test-chart", "--charts-dir", str(charts_dir)],
        ):
            with pytest.raises(SystemExit) as exc_info:
                validate_chart.main()

            assert exc_info.value.code == 0


def test_main_failure(tmp_path):
    """Test main function with validation failure."""
    charts_dir = tmp_path / "charts"
    charts_dir.mkdir()

    chart_dir = charts_dir / "test-chart"
    chart_dir.mkdir()

    metadata = {
        "name": "test-chart",
        "version": "1.0.0",
        "appVersion": "1.0.0",
    }
    (chart_dir / "Chart.yaml").write_text(yaml.dump(metadata))

    with patch("validate_chart.CommandRunner.run_helm") as mock_helm:
        mock_helm.return_value = (1, "", "Error")

        with patch(
            "sys.argv",
            ["validate_chart.py", "test-chart", "--charts-dir", str(charts_dir)],
        ):
            with pytest.raises(SystemExit) as exc_info:
                validate_chart.main()

            assert exc_info.value.code == 1


# --------------------------------------------------------------------------
# Additional tests filling coverage gaps
# --------------------------------------------------------------------------


def _create_chart(charts_dir: Path, name: str, **extra) -> Path:
    """Helper: create a minimal valid chart on disk."""
    chart_dir = charts_dir / name
    chart_dir.mkdir(parents=True)
    chart_yaml = {
        "apiVersion": "v2",
        "name": name,
        "version": "1.0.0",
        "appVersion": "1.0.0",
        **extra,
    }
    (chart_dir / "Chart.yaml").write_text(yaml.dump(chart_yaml))
    return chart_dir


class TestValidateChartInternalSteps:
    """Tests for the private _run_lint, _update_dependencies, _test_rendering
    methods. The class also has public validate_chart() but we want
    targeted coverage on the failure branches."""

    def test_lint_failure_logs_stderr(self, tmp_path: Path,
                                      caplog: pytest.LogCaptureFixture):
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        _create_chart(charts_dir, "broken")

        v = validate_chart.ChartValidator(charts_dir=str(charts_dir))
        with patch.object(v.cmd_runner, "run_helm",
                          return_value=(1, "lint stdout", "lint stderr")):
            ok = v._run_lint(charts_dir / "broken")
        assert ok is False
        # Lint failure path logs both stdout and stderr.
        joined = "\n".join(r.message for r in caplog.records)
        assert "lint stdout" in joined
        assert "lint stderr" in joined

    def test_dependency_update_failure_logs_stderr(self, tmp_path: Path,
                                                   caplog: pytest.LogCaptureFixture):
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        _create_chart(charts_dir, "deps",
                      dependencies=[{"name": "redis", "version": "1"}])

        v = validate_chart.ChartValidator(charts_dir=str(charts_dir))
        with patch.object(v.cmd_runner, "run_helm",
                          return_value=(1, "dep out", "dep err")):
            ok = v._update_dependencies(charts_dir / "deps")
        assert ok is False
        joined = "\n".join(r.message for r in caplog.records)
        assert "dep out" in joined
        assert "dep err" in joined

    def test_dependency_update_success_logs_to_debug(self, tmp_path: Path,
                                                    caplog: pytest.LogCaptureFixture):
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        _create_chart(charts_dir, "ok",
                      dependencies=[{"name": "redis", "version": "1"}])
        v = validate_chart.ChartValidator(charts_dir=str(charts_dir))
        import logging as _log
        with caplog.at_level(_log.DEBUG):
            with patch.object(v.cmd_runner, "run_helm",
                              return_value=(0, "dep ok", "")):
                ok = v._update_dependencies(charts_dir / "ok")
        assert ok is True

    def test_rendering_failure_logs_stderr(self, tmp_path: Path,
                                           caplog: pytest.LogCaptureFixture):
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        _create_chart(charts_dir, "broken")

        v = validate_chart.ChartValidator(charts_dir=str(charts_dir))
        with patch.object(v.cmd_runner, "run_helm",
                          return_value=(1, "", "template error")):
            ok = v._test_rendering(charts_dir / "broken")
        assert ok is False
        assert any("template error" in r.message for r in caplog.records)

    def test_validate_chart_returns_false_when_deps_fail(self, tmp_path: Path):
        """Whole-flow test: lint OK → deps fail → return False (line 82)."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        _create_chart(charts_dir, "x",
                      dependencies=[{"name": "redis", "version": "1"}])

        v = validate_chart.ChartValidator(charts_dir=str(charts_dir))
        # First helm call (lint) OK, second (dependency update) fails.
        with patch.object(v.cmd_runner, "run_helm",
                          side_effect=[(0, "", ""), (1, "", "deps err")]):
            assert v.validate_chart("x") is False


class TestMainInputFileEdges:
    def test_missing_input_file_exits_failure(self, tmp_path: Path):
        with patch("sys.argv",
                   ["validate_chart.py", "--input-file",
                    str(tmp_path / "nope.txt"),
                    "--charts-dir", str(tmp_path)]):
            with pytest.raises(SystemExit) as exc:
                validate_chart.main()
        assert exc.value.code == 1

    def test_empty_input_file_exits_success(self, tmp_path: Path):
        input_file = tmp_path / "empty.txt"
        input_file.write_text("")
        with patch("sys.argv",
                   ["validate_chart.py", "--input-file", str(input_file),
                    "--charts-dir", str(tmp_path)]):
            with pytest.raises(SystemExit) as exc:
                validate_chart.main()
        assert exc.value.code == 0

    def test_input_file_with_charts_runs_validation(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        _create_chart(charts_dir, "alpha")
        _create_chart(charts_dir, "beta")
        input_file = tmp_path / "list.txt"
        input_file.write_text("alpha\nbeta\n")
        with patch("validate_chart.CommandRunner.run_helm",
                   return_value=(0, "", "")):
            with patch("sys.argv",
                       ["validate_chart.py",
                        "--input-file", str(input_file),
                        "--charts-dir", str(charts_dir)]):
                with pytest.raises(SystemExit) as exc:
                    validate_chart.main()
        assert exc.value.code == 0

    def test_neither_chart_name_nor_input_file_errors(self, tmp_path: Path):
        # argparse.error() raises SystemExit(2)
        with patch("sys.argv",
                   ["validate_chart.py",
                    "--charts-dir", str(tmp_path)]):
            with pytest.raises(SystemExit) as exc:
                validate_chart.main()
        # argparse exits with code 2.
        assert exc.value.code == 2
