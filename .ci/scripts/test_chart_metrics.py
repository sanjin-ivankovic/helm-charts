"""Tests for chart_metrics.py.

ChartMetricsCollector talks to GitLab's REST API. All network calls are
mocked via requests.Session-level patches. The module imports `requests`
at top level, so we can patch chart_metrics.requests directly.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

import chart_metrics


# --------------------------------------------------------------------------
# JobMetrics dataclass
# --------------------------------------------------------------------------


class TestJobMetrics:
    def test_calculate_averages_empty(self):
        m = chart_metrics.JobMetrics()
        m.calculate_averages()
        assert m.avg_duration == 0.0
        assert m.failure_rate == 0.0

    def test_calculate_averages_with_data(self):
        m = chart_metrics.JobMetrics(count=10, total_duration=300.0,
                                     failures=2)
        m.calculate_averages()
        assert m.avg_duration == 30.0
        assert m.failure_rate == 20.0


# --------------------------------------------------------------------------
# retry_with_backoff decorator
# --------------------------------------------------------------------------


class TestRetryWithBackoff:
    def test_succeeds_immediately_does_not_retry(self):
        calls: list[int] = []

        @chart_metrics.retry_with_backoff(max_retries=3)
        def f():
            calls.append(1)
            return "ok"

        assert f() == "ok"
        assert len(calls) == 1

    def test_retries_on_request_exception(self):
        calls: list[int] = []

        @chart_metrics.retry_with_backoff(max_retries=2)
        def f():
            calls.append(1)
            if len(calls) < 3:
                raise requests.ConnectionError("transient")
            return "ok"

        # Avoid real sleep latency.
        with patch("chart_metrics.time.sleep"):
            assert f() == "ok"
        assert len(calls) == 3

    def test_does_not_retry_on_4xx_except_429(self):
        @chart_metrics.retry_with_backoff(max_retries=3)
        def f():
            response = MagicMock()
            response.status_code = 404
            err = requests.HTTPError("not found")
            err.response = response
            raise err

        with patch("chart_metrics.time.sleep"):
            with pytest.raises(requests.HTTPError):
                f()

    def test_retries_on_429_with_retry_after(self):
        calls: list[int] = []

        @chart_metrics.retry_with_backoff(max_retries=3)
        def f():
            calls.append(1)
            if len(calls) < 2:
                response = MagicMock()
                response.status_code = 429
                response.headers = {"Retry-After": "1"}
                err = requests.HTTPError("rate limited")
                err.response = response
                raise err
            return "ok"

        with patch("chart_metrics.time.sleep"):
            assert f() == "ok"

    def test_exhausts_retries_then_raises(self):
        @chart_metrics.retry_with_backoff(max_retries=1)
        def f():
            raise requests.ConnectionError("permanent")

        with patch("chart_metrics.time.sleep"):
            with pytest.raises(requests.ConnectionError):
                f()


# --------------------------------------------------------------------------
# ChartMetricsCollector — API methods
# --------------------------------------------------------------------------


class TestFetchRecentPipelines:
    def test_returns_list_on_success(self):
        c = chart_metrics.ChartMetricsCollector(project_id="42", token="x",
                                                gitlab_url="https://glab")
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=[{"id": 1}, {"id": 2}])
        with patch.object(c.session, "get", return_value=resp):
            pipelines = c.fetch_recent_pipelines(days=7)
        assert len(pipelines) == 2
        assert pipelines[0]["id"] == 1

    def test_returns_empty_on_error(self):
        c = chart_metrics.ChartMetricsCollector(project_id="42", token="x")
        with patch.object(c.session, "get",
                          side_effect=requests.ConnectionError("offline")):
            assert c.fetch_recent_pipelines() == []

    def test_strips_trailing_slash_from_url(self):
        c = chart_metrics.ChartMetricsCollector(
            project_id="42", token="x", gitlab_url="https://glab/"
        )
        assert c.gitlab_url == "https://glab"
        assert c.api_base == "https://glab/api/v4"


class TestFetchPipelineJobs:
    def test_returns_jobs(self):
        c = chart_metrics.ChartMetricsCollector(project_id="42", token="x")
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=[{"id": 1, "name": "validate"}])
        with patch.object(c.session, "get", return_value=resp):
            jobs = c.fetch_pipeline_jobs(99)
        assert jobs[0]["name"] == "validate"

    def test_returns_empty_on_error(self):
        c = chart_metrics.ChartMetricsCollector(project_id="42", token="x")
        with patch.object(c.session, "get",
                          side_effect=requests.ConnectionError("offline")):
            assert c.fetch_pipeline_jobs(99) == []


# --------------------------------------------------------------------------
# analyze_metrics
# --------------------------------------------------------------------------


class TestAnalyzeMetrics:
    def test_no_pipelines_returns_empty(self):
        c = chart_metrics.ChartMetricsCollector(project_id="42", token="x")
        with patch.object(c, "fetch_recent_pipelines", return_value=[]):
            assert c.analyze_metrics() == {}

    def test_counts_statuses_and_jobs(self):
        c = chart_metrics.ChartMetricsCollector(project_id="42", token="x")
        pipelines = [
            {"id": 1, "status": "success", "duration": 100},
            {"id": 2, "status": "success", "duration": 200},
            {"id": 3, "status": "failed", "duration": None},
        ]
        jobs_by_pid = {
            1: [
                {"name": "detect:changes", "status": "success", "duration": 5},
                {"name": "validate:charts", "status": "success", "duration": 20},
            ],
            2: [
                {"name": "validate:charts", "status": "failed", "duration": 10},
                {"name": "publish:charts", "status": "success", "duration": 30},
            ],
            3: [
                {"name": "package:charts", "status": "success", "duration": 15},
            ],
        }
        with patch.object(c, "fetch_recent_pipelines", return_value=pipelines):
            with patch.object(c, "fetch_pipeline_jobs",
                              side_effect=lambda pid: jobs_by_pid[pid]):
                m = c.analyze_metrics(days=30)

        assert m["total_pipelines"] == 3
        # 2 success + 1 failed.
        assert m["pipeline_statuses"] == {"success": 2, "failed": 1}
        # validate ran twice across pipelines: once OK, once failed.
        validate = m["job_metrics"]["validate:charts"]
        assert validate["count"] == 2
        assert validate["failures"] == 1
        assert validate["failure_rate"] == 50.0
        # avg pipeline duration = (100 + 200) / 2 = 150.0 (3rd pipeline
        # has null duration and is skipped).
        assert m["avg_pipeline_duration"] == 150.0

    def test_skips_pipelines_without_id(self):
        c = chart_metrics.ChartMetricsCollector(project_id="42", token="x")
        pipelines = [{"status": "success"}]  # no id
        with patch.object(c, "fetch_recent_pipelines", return_value=pipelines):
            m = c.analyze_metrics()
        # No job metrics counted; pipeline status still tallied.
        assert m["total_pipelines"] == 1
        assert m["pipeline_statuses"] == {"success": 1}


# --------------------------------------------------------------------------
# format_markdown
# --------------------------------------------------------------------------


class TestFormatMarkdown:
    def test_empty_metrics_returns_no_data_message(self):
        c = chart_metrics.ChartMetricsCollector(project_id="42", token="x")
        out = c.format_markdown({})
        assert "No data available" in out

    def test_renders_full_report(self):
        c = chart_metrics.ChartMetricsCollector(project_id="42", token="x")
        metrics = {
            "period_days": 7,
            "total_pipelines": 2,
            "pipeline_statuses": {"success": 1, "failed": 1},
            "avg_pipeline_duration": 120.0,
            "job_metrics": {
                "validate:charts": {
                    "count": 2,
                    "total_duration": 40.0,
                    "failures": 1,
                    "avg_duration": 20.0,
                    "failure_rate": 50.0,
                },
                "publish:charts": {
                    "count": 0,
                    "total_duration": 0.0,
                    "failures": 0,
                    "avg_duration": 0.0,
                    "failure_rate": 0.0,
                },
            },
        }
        out = c.format_markdown(metrics)
        assert "Chart CI/CD Metrics" in out
        assert "Last 7 days" in out
        assert "**success**: 1" in out
        # Average pipeline duration: 120s = 2.0 minutes.
        assert "2.0 minutes" in out
        # `publish:charts` has count=0 → not rendered as a row.
        assert "publish:charts" not in out
        # `validate:charts` IS rendered.
        assert "validate:charts" in out


# --------------------------------------------------------------------------
# main()
# --------------------------------------------------------------------------


class TestMain:
    def test_missing_project_id_exits_2(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("CI_PROJECT_ID", raising=False)
        monkeypatch.delenv("CI_JOB_TOKEN", raising=False)
        with patch("sys.argv", ["chart_metrics.py", "--token", "x"]):
            with pytest.raises(SystemExit) as exc:
                chart_metrics.main()
        assert exc.value.code == 2  # VALIDATION_ERROR

    def test_missing_token_exits_2(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("CI_PROJECT_ID", raising=False)
        monkeypatch.delenv("CI_JOB_TOKEN", raising=False)
        with patch("sys.argv",
                   ["chart_metrics.py", "--project-id", "42"]):
            with pytest.raises(SystemExit) as exc:
                chart_metrics.main()
        assert exc.value.code == 2

    def test_main_with_markdown_output_to_stdout(
        self, capsys: pytest.CaptureFixture[str]
    ):
        with patch("chart_metrics.ChartMetricsCollector") as mock_cls:
            inst = mock_cls.return_value
            inst.analyze_metrics.return_value = {"period_days": 7,
                                                 "total_pipelines": 0,
                                                 "pipeline_statuses": {},
                                                 "job_metrics": {},
                                                 "avg_pipeline_duration": 0.0}
            inst.format_markdown.return_value = "# Test\n"
            with patch("sys.argv",
                       ["chart_metrics.py", "--project-id", "42",
                        "--token", "x"]):
                with pytest.raises(SystemExit) as exc:
                    chart_metrics.main()
        assert exc.value.code == 0
        assert "# Test" in capsys.readouterr().out

    def test_main_with_json_output_to_file(self, tmp_path: Path):
        out_file = tmp_path / "metrics.json"
        sample_metrics = {"total_pipelines": 1}
        with patch("chart_metrics.ChartMetricsCollector") as mock_cls:
            mock_cls.return_value.analyze_metrics.return_value = sample_metrics
            with patch("sys.argv",
                       ["chart_metrics.py", "--project-id", "42",
                        "--token", "x", "--format", "json",
                        "--output", str(out_file), "--verbose"]):
                with pytest.raises(SystemExit) as exc:
                    chart_metrics.main()
        assert exc.value.code == 0
        assert out_file.exists()
        # Verify the file contains parseable JSON.
        parsed = json.loads(out_file.read_text())
        assert parsed == sample_metrics
