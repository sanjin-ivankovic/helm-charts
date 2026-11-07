#!/usr/bin/env python3
"""Unit tests for check_chart_standard.py: rules, exceptions and the CLI."""

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest  # type: ignore
import yaml

import check_chart_standard as std  # type: ignore

LABELS = {label: "x" for label in std.LABELS}
CONTAINER = {
    "name": "app",
    "image": "repo/app:1.0@sha256:abc",
    "resources": {"requests": {"cpu": "1m"}, "limits": {"cpu": "2m"}},
    "securityContext": {"allowPrivilegeEscalation": False, "readOnlyRootFilesystem": True,
                        "capabilities": {"drop": ["ALL"]}},
    "readinessProbe": {"httpGet": {"path": "/"}},
    "livenessProbe": {"httpGet": {"path": "/"}},
}
POD = {
    "priorityClassName": std.SENTINEL["priorityClassName"],
    "nodeSelector": dict(std.SENTINEL["nodeSelector"]),
    "tolerations": list(std.SENTINEL["tolerations"]),
    "affinity": dict(std.SENTINEL["affinity"]),
    "securityContext": {"runAsNonRoot": True, "seccompProfile": {"type": "RuntimeDefault"}},
    "containers": [CONTAINER],
}
CHART = {"apiVersion": "v2", "name": "app", "description": "d", "type": "application",
         "version": "1.0.0", "appVersion": "1", "kubeVersion": ">=1.19.0", "home": "h",
         "sources": ["s"], "maintainers": [{"name": "m"}], "keywords": ["k"]}
VALUES = "## @param image.tag t\nimage:\n  tag: x\n## @param worker.priorityClassName p\nworker:\n  priorityClassName: ''\n"


def deployment(pod=None, kind="Deployment"):
    spec = {"template": {"spec": copy.deepcopy(pod or POD)}}
    if kind == "CronJob":
        spec = {"jobTemplate": {"spec": spec}}
    return {"kind": kind, "metadata": {"name": "app", "labels": dict(LABELS)}, "spec": spec}


def rules(violations):
    return sorted(rule for rule, _ in violations)


class TestRules:
    def test_compliant_workload_passes_every_rule(self):
        docs = [deployment(), {"kind": "Service", "metadata": {"name": "s", "labels": LABELS}}]
        assert std.check_labels(docs) == []
        assert std.check_placement(docs) == []
        assert std.check_pod_security(docs) == []
        assert std.check_containers(docs) == []
        assert std.check_no_ingress(docs) == []

    def test_missing_labels(self):
        doc = {"kind": "Service", "metadata": {"name": "s", "labels": {"helm.sh/chart": "x"}}}
        (violation,) = std.check_labels([doc])
        assert violation[0] == "labels" and "app.kubernetes.io/name" in violation[1]

    def test_placement_reports_each_ignored_key(self):
        pod = dict(POD, priorityClassName=None, tolerations=[])
        (violation,) = std.check_placement([deployment(pod)])
        assert violation == ("placement", "Deployment/app ignores priorityClassName, tolerations")

    def test_pod_security(self):
        pod = dict(POD, securityContext={})
        assert rules(std.check_pod_security([deployment(pod)])) == ["pod-non-root", "pod-seccomp"]

    def test_container_rules(self):
        bare = {"name": "app", "image": "repo/app:1.0"}
        pod = dict(POD, containers=[bare])
        assert rules(std.check_containers([deployment(pod)])) == [
            "drop-all-caps", "image-digest", "no-privilege-escalation", "probes",
            "read-only-rootfs", "resources"]

    def test_init_containers_are_checked_but_need_no_probes(self):
        init = {k: v for k, v in CONTAINER.items() if not k.endswith("Probe")}
        init["securityContext"] = {}
        pod = dict(POD, initContainers=[dict(init, name="init")])
        assert rules(std.check_containers([deployment(pod)])) == [
            "drop-all-caps", "no-privilege-escalation", "read-only-rootfs"]

    def test_cronjob_pod_is_found_and_needs_no_probes(self):
        ctr = {k: v for k, v in CONTAINER.items() if not k.endswith("Probe")}
        doc = deployment(dict(POD, containers=[ctr]), kind="CronJob")
        assert std.pod_spec(doc)["containers"][0]["name"] == "app"
        assert std.check_containers([doc]) == []

    def test_non_workloads_are_skipped(self):
        doc = {"kind": "ConfigMap", "metadata": {"labels": LABELS}}
        assert std.pod_spec(doc) is None
        assert std.check_placement([doc]) == std.check_pod_security([doc]) == std.check_containers([doc]) == []

    def test_ingress_in_default_render(self):
        assert rules(std.check_no_ingress([{"kind": "Ingress", "metadata": {"name": "i"}}])) == [
            "no-ingress-by-default"]

    def test_chart_metadata(self):
        assert std.check_chart_metadata(CHART) == []
        broken = dict(CHART, apiVersion="v1", home="")
        assert [d for _, d in std.check_chart_metadata(broken)] == [
            "Chart.yaml lacks home", "apiVersion v1, not v2"]

    def test_values_documented(self):
        assert std.check_values_documented(VALUES) == []
        assert std.check_values_documented(VALUES + "extra: 1\n") == [
            ("values-documented", "no @param for extra")]
        assert std.check_values_documented("") == []


class TestRendering:
    def test_sentinels_reach_workload_blocks(self):
        args = std.sentinel_args(yaml.safe_load(VALUES))
        assert std.workload_blocks(yaml.safe_load(VALUES)) == ["worker"]
        assert "priorityClassName=\"std-priority\"" in args
        assert "worker.priorityClassName=\"std-priority\"" in args
        assert len(args) == 2 * 2 * len(std.SENTINEL)

    def test_render_parses_documents(self):
        def run(cmd, **_):
            assert cmd[:3] == ["helm", "template", "std"]
            return SimpleNamespace(returncode=0, stdout="---\nkind: A\n---\n---\nkind: B\n", stderr="")
        assert [d["kind"] for d in std.render(Path("charts/app"), [], run)] == ["A", "B"]

    def test_render_failure_raises(self):
        def run(cmd, **_):
            return SimpleNamespace(returncode=1, stdout="", stderr="boom")
        with pytest.raises(RuntimeError, match="app failed: boom"):
            std.render(Path("charts/app"), [], run)

    def test_check_chart_combines_rules(self, tmp_path):
        (tmp_path / "Chart.yaml").write_text(yaml.safe_dump(CHART))
        (tmp_path / "values.yaml").write_text(VALUES)
        rendered = yaml.safe_dump_all([deployment(dict(POD, priorityClassName=None))])
        calls = []

        def run(cmd, **_):
            calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout=rendered, stderr="")
        assert rules(std.check_chart(tmp_path, run)) == ["placement"]
        assert len(calls) == 2 and calls[1][3:] == [str(tmp_path)]


class TestExceptions:
    def write(self, tmp_path, data):
        path = tmp_path / "std.yaml"
        path.write_text(yaml.safe_dump(data))
        return path

    def test_missing_file_means_no_exceptions(self, tmp_path):
        assert std.load_exceptions(tmp_path / "absent.yaml") == {}

    def test_loads_reasons(self, tmp_path):
        path = self.write(tmp_path, {"exceptions": {"app": {"probes": "accepted: no port"}}})
        assert std.load_exceptions(path) == {"app": {"probes": "accepted: no port"}}

    def test_unknown_rule_rejected(self, tmp_path):
        path = self.write(tmp_path, {"exceptions": {"app": {"nope": "x"}}})
        with pytest.raises(ValueError, match="unknown rule"):
            std.load_exceptions(path)

    def test_empty_reason_rejected(self, tmp_path):
        path = self.write(tmp_path, {"exceptions": {"app": {"probes": " "}}})
        with pytest.raises(ValueError, match="no reason"):
            std.load_exceptions(path)

    def test_evaluate(self):
        charts = {"a": [("probes", "d")], "b": [("resources", "x")], "c": []}
        exceptions = {"a": {"probes": "r"}, "c": {"labels": "r"}, "gone": {"probes": "r"}}
        assert std.evaluate(charts, exceptions) == [
            "b: resources: x",
            "c: labels: exception listed but the rule passes; remove it",
            "gone: exceptions listed for a chart that does not exist",
        ]


class TestMain:
    def test_main_reports_and_exits(self, tmp_path, monkeypatch, capsys):
        charts = tmp_path / "charts"
        for name in ("good", "bad"):
            (charts / name).mkdir(parents=True)
            (charts / name / "Chart.yaml").write_text("name: x\n")
        (charts / "notachart").mkdir()
        exceptions = tmp_path / "std.yaml"
        exceptions.write_text("exceptions:\n  bad:\n    probes: 'accepted: x'\n")
        seen = []

        def fake(chart_dir):
            seen.append(chart_dir.name)
            return [("probes", "d")] if chart_dir.name == "bad" else []
        monkeypatch.setattr(std, "check_chart", fake)
        args = ["--charts-dir", str(charts), "--exceptions", str(exceptions)]
        assert std.main(args) == 0
        assert sorted(seen) == ["bad", "good"]
        assert "2 charts, 1 listed exception(s), 0 problem(s)" in capsys.readouterr().out

        exceptions.write_text("exceptions: {}\n")
        assert std.main(args) == 1
        assert "FAIL bad: probes: d" in capsys.readouterr().out
