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


# --------------------------------------------------------------------------
# Additional tests filling coverage gaps (git diff, comparison ranges,
# fetch_base_ref, main with empty result)
# --------------------------------------------------------------------------


class TestGetChangedFiles:
    """get_changed_files() wraps `git diff --name-only` with caching."""

    def _detector(self, tmp_path: Path) -> "detect_changes.ChartDetector":
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        return detect_changes.ChartDetector(charts_dir=str(charts_dir))

    def test_returns_parsed_files(self, tmp_path: Path):
        d = self._detector(tmp_path)
        with patch.object(d.cmd_runner, "run_git") as mock:
            mock.return_value = (0, "a/Chart.yaml\nb/values.yaml\n", "")
            files = d.get_changed_files("HEAD~1..HEAD")
        assert files == {"a/Chart.yaml", "b/values.yaml"}

    def test_returns_empty_set_on_no_output(self, tmp_path: Path):
        d = self._detector(tmp_path)
        with patch.object(d.cmd_runner, "run_git", return_value=(0, "", "")):
            assert d.get_changed_files("HEAD~1..HEAD") == set()

    def test_returns_empty_on_git_failure(self, tmp_path: Path):
        d = self._detector(tmp_path)
        with patch.object(d.cmd_runner, "run_git",
                          return_value=(1, "", "fatal: bad object")):
            assert d.get_changed_files("HEAD~1..HEAD") == set()

    def test_caches_repeated_calls(self, tmp_path: Path):
        d = self._detector(tmp_path)
        with patch.object(d.cmd_runner, "run_git") as mock:
            mock.return_value = (0, "x.yml\n", "")
            d.get_changed_files("HEAD~1..HEAD")
            d.get_changed_files("HEAD~1..HEAD")  # cached
            assert mock.call_count == 1

    def test_swallows_exception(self, tmp_path: Path):
        d = self._detector(tmp_path)
        with patch.object(d.cmd_runner, "run_git",
                          side_effect=RuntimeError("boom")):
            assert d.get_changed_files("HEAD~1..HEAD") == set()


class TestExtractChartNamesEdges:
    def test_file_outside_charts_dir(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        d = detect_changes.ChartDetector(charts_dir=str(charts_dir))
        # README is at repo root, not in charts/.
        assert d.extract_chart_names({"README.md"}) == set()

    def test_path_with_no_chart_subdir(self, tmp_path: Path):
        # File path "charts/" by itself has no chart subdir.
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        d = detect_changes.ChartDetector(charts_dir=str(charts_dir))
        # `charts/` with nothing after the trailing slash → empty parts
        # after relative_to — silently skipped.
        result = d.extract_chart_names({f"{charts_dir}/"})
        assert result == set()

    def test_unknown_chart_name_ignored(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        d = detect_changes.ChartDetector(charts_dir=str(charts_dir))
        # File path under charts/ but the chart doesn't actually exist
        # (no Chart.yaml) — extract_chart_names filters it out.
        result = d.extract_chart_names({f"{charts_dir}/phantom/values.yaml"})
        assert result == set()


class TestGetComparisonRange:
    def _detector(self, tmp_path: Path) -> "detect_changes.ChartDetector":
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        return detect_changes.ChartDetector(charts_dir=str(charts_dir))

    @patch.dict(os.environ, {"CI_COMMIT_TAG": "v1.2.3"})
    def test_tag_returns_none(self, tmp_path: Path):
        d = self._detector(tmp_path)
        assert d.get_comparison_range() is None

    @patch.dict(os.environ, {"RELEASE_ALL": "1"}, clear=True)
    def test_release_all_returns_none(self, tmp_path: Path):
        d = self._detector(tmp_path)
        assert d.get_comparison_range() is None

    @patch.dict(os.environ, {"CI_COMMIT_BRANCH": "main",
                             "CI_COMMIT_BEFORE_SHA": "deadbeef"}, clear=True)
    def test_main_branch_with_before_sha(self, tmp_path: Path):
        d = self._detector(tmp_path)
        assert d.get_comparison_range() == "deadbeef..HEAD"

    @patch.dict(os.environ, {"CI_COMMIT_BRANCH": "main"}, clear=True)
    def test_main_branch_without_before_sha_falls_back(self, tmp_path: Path):
        d = self._detector(tmp_path)
        assert d.get_comparison_range() == "HEAD~1..HEAD"

    @patch.dict(os.environ, {"CI_COMMIT_BRANCH": "main",
                             "CI_COMMIT_BEFORE_SHA": "0" * 40},
                clear=True)
    def test_main_branch_with_zero_before_sha_falls_back(self, tmp_path: Path):
        # The all-zero SHA is GitLab's signal for first-push-to-branch.
        d = self._detector(tmp_path)
        assert d.get_comparison_range() == "HEAD~1..HEAD"

    @patch.dict(os.environ,
                {"CI_COMMIT_BRANCH": "feat/x",
                 "CI_MERGE_REQUEST_TARGET_BRANCH_NAME": "main"},
                clear=True)
    def test_feature_branch_with_resolvable_base_ref(self, tmp_path: Path):
        d = self._detector(tmp_path)
        with patch.object(d.cmd_runner, "run_git", return_value=(0, "", "")):
            assert d.get_comparison_range() == "origin/main...HEAD"

    @patch.dict(os.environ,
                {"CI_COMMIT_BRANCH": "feat/x",
                 "CI_MERGE_REQUEST_TARGET_BRANCH_NAME": "main"},
                clear=True)
    def test_feature_branch_falls_back_when_rev_parse_fails(self, tmp_path: Path):
        d = self._detector(tmp_path)
        # rev-parse raises → fallback to HEAD~1..HEAD.
        with patch.object(d.cmd_runner, "run_git",
                          side_effect=RuntimeError("no such ref")):
            assert d.get_comparison_range() == "HEAD~1..HEAD"


class TestFetchBaseRef:
    @patch.dict(os.environ, {}, clear=True)
    def test_skips_outside_ci(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        d = detect_changes.ChartDetector(charts_dir=str(charts_dir))
        with patch.object(d.cmd_runner, "run_git") as mock:
            d.fetch_base_ref()
            mock.assert_not_called()

    @patch.dict(os.environ, {"CI": "true"}, clear=True)
    def test_calls_git_fetch_in_ci(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        d = detect_changes.ChartDetector(charts_dir=str(charts_dir))
        with patch.object(d.cmd_runner, "run_git", return_value=(0, "", "")) as mock:
            d.fetch_base_ref()
            mock.assert_called_once()
            assert "fetch" in mock.call_args[0]

    @patch.dict(os.environ, {"CI": "true"}, clear=True)
    def test_swallows_fetch_failure(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        d = detect_changes.ChartDetector(charts_dir=str(charts_dir))
        with patch.object(d.cmd_runner, "run_git",
                          side_effect=RuntimeError("network down")):
            # Should not raise — failure is logged + ignored.
            d.fetch_base_ref()


class TestDetectChangesFullFlow:
    @patch.dict(os.environ, {"CI_COMMIT_BRANCH": "main",
                             "CI_COMMIT_BEFORE_SHA": "0123abc"}, clear=True)
    def test_no_files_changed_returns_empty(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        d = detect_changes.ChartDetector(charts_dir=str(charts_dir))
        with patch.object(d.cmd_runner, "run_git", return_value=(0, "", "")):
            assert d.detect_changes() == []

    @patch.dict(os.environ, {"CI_COMMIT_BRANCH": "main",
                             "CI_COMMIT_BEFORE_SHA": "0123abc"}, clear=True)
    def test_files_but_no_charts(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        d = detect_changes.ChartDetector(charts_dir=str(charts_dir))
        # Only non-chart files changed.
        with patch.object(d.cmd_runner, "run_git",
                          return_value=(0, "README.md\n.gitignore\n", "")):
            assert d.detect_changes() == []

    @patch.dict(os.environ, {"CI_COMMIT_BRANCH": "main",
                             "CI_COMMIT_BEFORE_SHA": "0123abc"}, clear=True)
    def test_returns_sorted_chart_names(self, tmp_path: Path):
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        # Create two charts with valid Chart.yaml.
        for name in ("zebra", "apple"):
            chart_dir = charts_dir / name
            chart_dir.mkdir()
            (chart_dir / "Chart.yaml").write_text(f"name: {name}\nversion: 1\n")
        d = detect_changes.ChartDetector(charts_dir=str(charts_dir))
        stdout = f"{charts_dir}/zebra/values.yaml\n{charts_dir}/apple/Chart.yaml\n"
        with patch.object(d.cmd_runner, "run_git", return_value=(0, stdout, "")):
            assert d.detect_changes() == ["apple", "zebra"]


def test_main_with_no_changes(tmp_path: Path,
                              capsys: pytest.CaptureFixture[str]) -> None:
    """main() with empty result prints '(none)' and exits 0."""
    charts_dir = tmp_path / "charts"
    charts_dir.mkdir()
    with patch.dict(os.environ,
                    {"CI_COMMIT_BRANCH": "main",
                     "CI_COMMIT_BEFORE_SHA": "abc1234"}, clear=True):
        with patch("sys.argv",
                   ["detect_changes.py", "--charts-dir", str(charts_dir)]):
            # Mock git → no changed files.
            with patch("detect_changes.CommandRunner.run_git",
                       return_value=(0, "", "")):
                with pytest.raises(SystemExit) as exc:
                    detect_changes.main()
        assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "(none)" in captured.out


def test_main_verbose_logging(tmp_path: Path,
                              capsys: pytest.CaptureFixture[str]) -> None:
    """--verbose flag wires DEBUG-level logging."""
    charts_dir = tmp_path / "charts"
    charts_dir.mkdir()
    with patch.dict(os.environ, {"RELEASE_ALL": "true"}):
        with patch("sys.argv",
                   ["detect_changes.py", "--charts-dir", str(charts_dir),
                    "--verbose"]):
            with pytest.raises(SystemExit):
                detect_changes.main()
