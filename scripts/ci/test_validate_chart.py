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
