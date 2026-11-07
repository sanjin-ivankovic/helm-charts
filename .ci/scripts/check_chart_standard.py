#!/usr/bin/env python3
"""
Check every chart against the chart standard (docs/CHARTS.md).

Each chart is rendered with sentinel placement values and its rendered
objects, Chart.yaml and values.yaml are checked rule by rule. A violation
fails unless .ci/chart-standard.yaml lists it as an exception with a reason;
an exception whose rule now passes also fails, so the list never outlives
the problem it excuses.

Usage:
    python3 check_chart_standard.py [--charts-dir DIR] [--exceptions FILE]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import yaml

RULES = {
    "labels": "every object carries the standard name/instance/managed-by/chart labels",
    "placement": "priorityClassName, nodeSelector, tolerations and affinity reach every pod",
    "pod-non-root": "pod securityContext sets runAsNonRoot: true",
    "pod-seccomp": "pod securityContext sets seccompProfile RuntimeDefault",
    "no-privilege-escalation": "every container sets allowPrivilegeEscalation: false",
    "drop-all-caps": "every container drops ALL capabilities",
    "read-only-rootfs": "every container sets readOnlyRootFilesystem: true",
    "resources": "every container sets resource requests and limits",
    "image-digest": "every image is pinned by digest",
    "probes": "every Deployment container has a readiness and a liveness probe",
    "chart-metadata": "Chart.yaml carries the required fields",
    "values-documented": "every top-level values.yaml key has an @param line",
    "no-ingress-by-default": "the default render contains no Ingress",
}

LABELS = (
    "app.kubernetes.io/name",
    "app.kubernetes.io/instance",
    "app.kubernetes.io/managed-by",
    "helm.sh/chart",
)
CHART_FIELDS = ("apiVersion", "name", "description", "type", "version", "appVersion",
                "kubeVersion", "home", "sources", "maintainers", "keywords")
POD_KINDS = ("Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob")

SENTINEL = {
    "priorityClassName": "std-priority",
    "nodeSelector": {"std-node": "std"},
    "tolerations": [{"key": "std-toleration", "operator": "Exists"}],
    "affinity": {"podAntiAffinity": {"preferredDuringSchedulingIgnoredDuringExecution": [
        {"weight": 1, "podAffinityTerm": {"topologyKey": "std-affinity"}}]}},
}

Violation = tuple[str, str]  # (rule, detail)


def pod_spec(doc: dict[str, Any]) -> dict[str, Any] | None:
    """The pod spec of a workload object, or None for other kinds."""
    kind = doc.get("kind")
    if kind not in POD_KINDS:
        return None
    spec = doc.get("spec") or {}
    if kind == "CronJob":
        spec = (spec.get("jobTemplate") or {}).get("spec") or {}
    return ((spec.get("template") or {}).get("spec")) or {}


def name_of(doc: dict[str, Any]) -> str:
    return f"{doc.get('kind')}/{(doc.get('metadata') or {}).get('name')}"


def check_labels(docs: list[dict[str, Any]]) -> list[Violation]:
    out = []
    for doc in docs:
        labels = (doc.get("metadata") or {}).get("labels") or {}
        missing = [label for label in LABELS if label not in labels]
        if missing:
            out.append(("labels", f"{name_of(doc)} lacks {', '.join(missing)}"))
    return out


def check_placement(docs: list[dict[str, Any]]) -> list[Violation]:
    out = []
    for doc in docs:
        pod = pod_spec(doc)
        if pod is None:
            continue
        got = {
            "priorityClassName": pod.get("priorityClassName") == SENTINEL["priorityClassName"],
            "nodeSelector": (pod.get("nodeSelector") or {}).get("std-node") == "std",
            "tolerations": any(t.get("key") == "std-toleration" for t in pod.get("tolerations") or []),
            "affinity": "podAntiAffinity" in (pod.get("affinity") or {}),
        }
        missing = [key for key, ok in got.items() if not ok]
        if missing:
            out.append(("placement", f"{name_of(doc)} ignores {', '.join(missing)}"))
    return out


def check_pod_security(docs: list[dict[str, Any]]) -> list[Violation]:
    out = []
    for doc in docs:
        pod = pod_spec(doc)
        if pod is None:
            continue
        psc = pod.get("securityContext") or {}
        if psc.get("runAsNonRoot") is not True:
            out.append(("pod-non-root", name_of(doc)))
        if (psc.get("seccompProfile") or {}).get("type") != "RuntimeDefault":
            out.append(("pod-seccomp", name_of(doc)))
    return out


def _containers(pod: dict[str, Any]) -> list[dict[str, Any]]:
    return list(pod.get("initContainers") or []) + list(pod.get("containers") or [])


def check_containers(docs: list[dict[str, Any]]) -> list[Violation]:
    out = []
    for doc in docs:
        pod = pod_spec(doc)
        if pod is None:
            continue
        main = {c.get("name") for c in pod.get("containers") or []}
        for ctr in _containers(pod):
            where = f"{name_of(doc)}:{ctr.get('name')}"
            csc = ctr.get("securityContext") or {}
            if csc.get("allowPrivilegeEscalation") is not False:
                out.append(("no-privilege-escalation", where))
            if "ALL" not in ((csc.get("capabilities") or {}).get("drop") or []):
                out.append(("drop-all-caps", where))
            if csc.get("readOnlyRootFilesystem") is not True:
                out.append(("read-only-rootfs", where))
            res = ctr.get("resources") or {}
            if not res.get("requests") or not res.get("limits"):
                out.append(("resources", where))
            if "@sha256:" not in str(ctr.get("image", "")):
                out.append(("image-digest", where))
            if doc.get("kind") == "Deployment" and ctr.get("name") in main:
                if not ctr.get("readinessProbe") or not ctr.get("livenessProbe"):
                    out.append(("probes", where))
    return out


def check_no_ingress(docs: list[dict[str, Any]]) -> list[Violation]:
    return [("no-ingress-by-default", name_of(d)) for d in docs if d.get("kind") == "Ingress"]


def check_chart_metadata(chart: dict[str, Any]) -> list[Violation]:
    missing = [field for field in CHART_FIELDS if not chart.get(field)]
    out = [("chart-metadata", f"Chart.yaml lacks {', '.join(missing)}")] if missing else []
    if chart.get("apiVersion") and chart.get("apiVersion") != "v2":
        out.append(("chart-metadata", f"apiVersion {chart.get('apiVersion')}, not v2"))
    return out


PARAM = re.compile(r"^##\s*@param\s+([A-Za-z0-9_.\[\]-]+)", re.M)


def check_values_documented(values_text: str) -> list[Violation]:
    values = yaml.safe_load(values_text) or {}
    documented = {p.split(".")[0].split("[")[0] for p in PARAM.findall(values_text)}
    missing = sorted(set(values) - documented)
    return [("values-documented", f"no @param for {key}") for key in missing]


def workload_blocks(values: dict[str, Any]) -> list[str]:
    """Top-level value blocks that carry their own placement keys (e.g. worker:)."""
    return sorted(k for k, v in values.items() if isinstance(v, dict) and "priorityClassName" in v)


def sentinel_args(values: dict[str, Any]) -> list[str]:
    args: list[str] = []
    for prefix in [""] + [f"{b}." for b in workload_blocks(values)]:
        for key, val in SENTINEL.items():
            args += ["--set-json", f"{prefix}{key}={json.dumps(val)}"]
    return args


def render(chart_dir: Path, args: list[str], run: Callable[..., Any] = subprocess.run) -> list[dict[str, Any]]:
    result = run(["helm", "template", "std", str(chart_dir), *args],
                 capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"helm template {chart_dir.name} failed: {result.stderr.strip()}")
    return [d for d in yaml.safe_load_all(result.stdout) if d]


def check_chart(chart_dir: Path, run: Callable[..., Any] = subprocess.run) -> list[Violation]:
    values_text = (chart_dir / "values.yaml").read_text()
    values = yaml.safe_load(values_text) or {}
    chart = yaml.safe_load((chart_dir / "Chart.yaml").read_text()) or {}
    placed = render(chart_dir, sentinel_args(values), run)
    default = render(chart_dir, [], run)
    return (check_labels(placed) + check_placement(placed) + check_pod_security(placed)
            + check_containers(placed) + check_no_ingress(default)
            + check_chart_metadata(chart) + check_values_documented(values_text))


def load_exceptions(path: Path) -> dict[str, dict[str, str]]:
    data = yaml.safe_load(path.read_text()) if path.exists() else None
    exceptions = (data or {}).get("exceptions") or {}
    for chart, rules in exceptions.items():
        for rule, reason in (rules or {}).items():
            if rule not in RULES:
                raise ValueError(f"{path}: {chart}: unknown rule {rule!r}")
            if not str(reason or "").strip():
                raise ValueError(f"{path}: {chart}: {rule} has no reason")
    return {chart: dict(rules or {}) for chart, rules in exceptions.items()}


def evaluate(charts: dict[str, list[Violation]], exceptions: dict[str, dict[str, str]]) -> list[str]:
    """Problems: violations without an exception, and exceptions that no longer apply."""
    problems = []
    for chart, violations in sorted(charts.items()):
        excused = exceptions.get(chart, {})
        failing = {rule for rule, _ in violations}
        for rule, detail in violations:
            if rule not in excused:
                problems.append(f"{chart}: {rule}: {detail}")
        for rule in sorted(set(excused) - failing):
            problems.append(f"{chart}: {rule}: exception listed but the rule passes; remove it")
    for chart in sorted(set(exceptions) - set(charts)):
        problems.append(f"{chart}: exceptions listed for a chart that does not exist")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--charts-dir", default="charts", type=Path)
    parser.add_argument("--exceptions", default=".ci/chart-standard.yaml", type=Path)
    args = parser.parse_args(argv)

    exceptions = load_exceptions(args.exceptions)
    charts = {d.name: check_chart(d) for d in sorted(args.charts_dir.iterdir())
              if (d / "Chart.yaml").exists()}
    problems = evaluate(charts, exceptions)
    for problem in problems:
        print(f"FAIL {problem}")
    excused = sum(len(v) for v in exceptions.values())
    print(f"chart standard: {len(charts)} charts, {excused} listed exception(s), "
          f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
