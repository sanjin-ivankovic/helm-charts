#!/usr/bin/env python3
"""Unit tests for detect_changes.py.

Tests the chart change detection logic including:
- Git diff parsing
- Tag detection
- Chart validation
- MR vs main branch logic
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest  # type: ignore

# Import the module under test
import detect_changes


class TestChartDetector:
    """Tests for ChartDetector class."""

    def test_is_valid_chart_with_valid_chart(self, tmp_path: Path) -> None:
        """Test that a valid chart is recognized."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()

        chart_dir = charts_dir / "my-chart"
        chart_dir.mkdir()

        chart_yaml = chart_dir / "Chart.yaml"
        chart_yaml.write_text("name: my-chart\nversion: 1.0.0\n")

        detector = detect_changes.ChartDetector(charts_dir=str(charts_dir))
        assert detector.is_valid_chart("my-chart") is True

    def test_is_valid_chart_with_missing_chart_yaml(self, tmp_path: Path) -> None:
        """Test that a directory without Chart.yaml is not valid."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()

        chart_dir = charts_dir / "my-chart"
        chart_dir.mkdir()

        detector = detect_changes.ChartDetector(charts_dir=str(charts_dir))
        assert detector.is_valid_chart("my-chart") is False

    def test_is_valid_chart_with_dotfile(self, tmp_path: Path) -> None:
        """Test that dotfiles are excluded."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()

        detector = detect_changes.ChartDetector(charts_dir=str(charts_dir))
        assert detector.is_valid_chart(".gitignore") is False

    def test_get_all_charts(self, tmp_path: Path) -> None:
        """Test getting all charts in directory."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()

        # Create valid charts
        for name in ["chart-a", "chart-b", "chart-c"]:
            chart_dir = charts_dir / name
            chart_dir.mkdir()
            (chart_dir / "Chart.yaml").write_text(f"name: {name}\nversion: 1.0.0\n")

        # Create invalid directory (no Chart.yaml)
        invalid_dir = charts_dir / "not-a-chart"
        invalid_dir.mkdir()

        detector = detect_changes.ChartDetector(charts_dir=str(charts_dir))
        charts = detector.get_all_charts()

        assert len(charts) == 3
        assert "chart-a" in charts
        assert "chart-b" in charts
        assert "chart-c" in charts
        assert "not-a-chart" not in charts

    def test_extract_chart_names(self, tmp_path: Path) -> None:
        """Test extracting chart names from file paths."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()

        # Create a chart
        chart_dir = charts_dir / "my-chart"
        chart_dir.mkdir()
        (chart_dir / "Chart.yaml").write_text("name: my-chart\nversion: 1.0.0\n")

        detector = detect_changes.ChartDetector(charts_dir=str(charts_dir))

        # Use absolute paths since charts_dir is absolute
        files: set[str] = {
            str(charts_dir / "my-chart" / "Chart.yaml"),
            str(charts_dir / "my-chart" / "values.yaml"),
            str(charts_dir / "my-chart" / "templates" / "deployment.yaml"),
            "README.md",  # Not in charts dir
        }

        chart_names = detector.extract_chart_names(files)

        assert len(chart_names) == 1
        assert "my-chart" in chart_names

    @patch.dict(os.environ, {"CI_COMMIT_TAG": "v1.0.0"})
    def test_detect_changes_with_tag(self, tmp_path: Path) -> None:
        """Test that tag detection returns all charts."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()

        # Create charts
        for name in ["chart-a", "chart-b"]:
            chart_dir = charts_dir / name
            chart_dir.mkdir()
            (chart_dir / "Chart.yaml").write_text(f"name: {name}\nversion: 1.0.0\n")

        detector = detect_changes.ChartDetector(charts_dir=str(charts_dir))
        charts = detector.detect_changes()

        assert len(charts) == 2
        assert "chart-a" in charts
        assert "chart-b" in charts

    @patch.dict(os.environ, {"RELEASE_ALL": "true"})
    def test_detect_changes_with_release_all(self, tmp_path: Path) -> None:
        """Test that RELEASE_ALL returns all charts."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()

        # Create charts
        for name in ["chart-a", "chart-b"]:
            chart_dir = charts_dir / name
            chart_dir.mkdir()
            (chart_dir / "Chart.yaml").write_text(f"name: {name}\nversion: 1.0.0\n")

        detector = detect_changes.ChartDetector(charts_dir=str(charts_dir))
        charts = detector.detect_changes()

        assert len(charts) == 2


def test_main_with_text_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test main function with text output."""
    charts_dir = tmp_path / "charts"
    charts_dir.mkdir()

    # Create a chart
    chart_dir = charts_dir / "test-chart"
    chart_dir.mkdir()
    (chart_dir / "Chart.yaml").write_text("name: test-chart\nversion: 1.0.0\n")

    # Mock environment and git commands
    with patch.dict(os.environ, {"RELEASE_ALL": "true"}):
        with patch("sys.argv", ["detect_changes.py", "--charts-dir", str(charts_dir)]):
            with pytest.raises(SystemExit) as exc_info:
                detect_changes.main()

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            assert "test-chart" in captured.out


def test_main_with_json_output(tmp_path: Path) -> None:
    """Test main function with JSON output."""
    charts_dir = tmp_path / "charts"
    charts_dir.mkdir()

    # Create a chart
    chart_dir = charts_dir / "test-chart"
    chart_dir.mkdir()
    (chart_dir / "Chart.yaml").write_text("name: test-chart\nversion: 1.0.0\n")

    output_file = tmp_path / "output.json"

    # Mock environment
    with patch.dict(os.environ, {"RELEASE_ALL": "true"}):
        with patch(
            "sys.argv",
            [
                "detect_changes.py",
                "--charts-dir",
                str(charts_dir),
                "--format",
                "json",
                "--output",
                str(output_file),
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                detect_changes.main()

            assert exc_info.value.code == 0
            assert output_file.exists()

            data: dict[str, list[str]] = json.loads(output_file.read_text())
            assert "charts" in data
            assert "test-chart" in data["charts"]
