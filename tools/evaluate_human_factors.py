#!/usr/bin/env python3
"""Evaluate human-factors benchmark records for situational-awareness preservation.

Babbly's concept is judged by whether it reduces operator attention captured by
the computing device while preserving correctness and control (issue #21), not
by ASR accuracy alone. This tool turns raw per-task session records into
per-condition summary statistics and a comparison against the laptop/CLI
baseline. The human runs produce the records; this evaluator is deterministic.
"""

import argparse
import json
from pathlib import Path
from statistics import mean, median


CONDITIONS = ("laptop_cli", "visual_eud", "hybrid_voice", "eyes_free")
BASELINE = "laptop_cli"
MIN_SAMPLES = 3

_REQUIRED_NUMERIC = (
    "completion_time_s",
    "eyes_on_device_s",
    "hands_on_device_s",
)
_REQUIRED_INT = (
    "intent_attempts",
    "intent_correct",
    "false_executions",
    "clarifications",
)
_OPTIONAL_NUMERIC = ("time_to_important_info_s", "workload")
_OPTIONAL_INT = ("mode_switches", "mode_switch_continuity_errors")


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    return data


def _bool(value, field, rid):
    if type(value) is not bool:
        raise ValueError(f"{rid}: {field} must be a JSON boolean")
    return value


def _int(value, field, rid):
    if type(value) is not int or type(value) is bool or value < 0:
        raise ValueError(f"{rid}: {field} must be a non-negative integer")
    return value


def _num(value, field, rid):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{rid}: {field} must be a non-negative number")
    return float(value)


def _avg(records, field):
    values = [r[field] for r in records if r.get(field) is not None]
    return mean(values) if values else None


def _rate(records, numerator, denominator):
    denom = sum(r[denominator] for r in records)
    if denom == 0:
        return None
    return sum(r[numerator] for r in records) / denom


def _validate(records):
    seen = set()
    clean = []
    for raw in records:
        rid = str(raw.get("id") or "").strip()
        if not rid:
            raise ValueError("record is missing id")
        if rid in seen:
            raise ValueError(f"duplicate record id: {rid}")
        seen.add(rid)

        condition = raw.get("condition")
        if condition not in CONDITIONS:
            raise ValueError(f"{rid}: condition must be one of {CONDITIONS}")

        record = {"id": rid, "condition": condition, "task_id": str(raw.get("task_id") or "")}
        record["completed"] = _bool(raw.get("completed"), "completed", rid)
        for field in _REQUIRED_NUMERIC:
            record[field] = _num(raw.get(field), field, rid)
        for field in _REQUIRED_INT:
            record[field] = _int(raw.get(field), field, rid)
        if record["intent_correct"] > record["intent_attempts"]:
            raise ValueError(f"{rid}: intent_correct cannot exceed intent_attempts")
        for field in _OPTIONAL_NUMERIC:
            record[field] = None if raw.get(field) is None else _num(raw.get(field), field, rid)
        for field in _OPTIONAL_INT:
            record[field] = None if raw.get(field) is None else _int(raw.get(field), field, rid)
        clean.append(record)
    return clean


def _summarize_condition(records):
    completed = [r for r in records if r["completed"]]
    switches = sum(r["mode_switches"] or 0 for r in records)
    switch_errors = sum(r["mode_switch_continuity_errors"] or 0 for r in records)
    return {
        "n": len(records),
        "task_completion_rate": len(completed) / len(records) if records else None,
        "mean_completion_time_s": mean([r["completion_time_s"] for r in completed]) if completed else None,
        "median_completion_time_s": median([r["completion_time_s"] for r in completed]) if completed else None,
        "intent_accuracy": _rate(records, "intent_correct", "intent_attempts"),
        "false_execution_rate": _rate(records, "false_executions", "intent_attempts"),
        "total_false_executions": sum(r["false_executions"] for r in records),
        "clarification_rate": _rate(records, "clarifications", "intent_attempts"),
        "mean_time_to_important_info_s": _avg(records, "time_to_important_info_s"),
        "mean_eyes_on_device_s": _avg(records, "eyes_on_device_s"),
        "mean_hands_on_device_s": _avg(records, "hands_on_device_s"),
        "mode_switch_continuity_error_rate": (switch_errors / switches) if switches else None,
        "mean_workload": _avg(records, "workload"),
    }


def _reduction(baseline, value):
    if baseline is None or value is None:
        return None
    delta = value - baseline
    pct = (delta / baseline * 100.0) if baseline else None
    return {"delta": delta, "pct_change": pct}


def evaluate(records):
    clean = _validate(records)
    by_condition = {c: [r for r in clean if r["condition"] == c] for c in CONDITIONS}
    per_condition = {c: _summarize_condition(rs) for c, rs in by_condition.items() if rs}

    comparison = {}
    base = per_condition.get(BASELINE)
    if base:
        for condition, summary in per_condition.items():
            if condition == BASELINE:
                continue
            comparison[condition] = {
                "eyes_on_device_s": _reduction(base["mean_eyes_on_device_s"], summary["mean_eyes_on_device_s"]),
                "hands_on_device_s": _reduction(base["mean_hands_on_device_s"], summary["mean_hands_on_device_s"]),
                "completion_time_s": _reduction(base["mean_completion_time_s"], summary["mean_completion_time_s"]),
            }

    limitations = []
    if BASELINE not in per_condition:
        limitations.append(f"no baseline ({BASELINE}) records; comparison omitted")
    for condition in CONDITIONS:
        summary = per_condition.get(condition)
        if summary is None:
            limitations.append(f"no records for condition {condition}")
        elif summary["n"] < MIN_SAMPLES:
            limitations.append(f"{condition}: only {summary['n']} sample(s) (< {MIN_SAMPLES}); treat as indicative")

    summary = {
        "total_records": len(clean),
        "conditions_present": sorted(per_condition),
        "per_condition": per_condition,
        "comparison_vs_baseline": comparison,
        "limitations": limitations,
    }
    return summary, per_condition


def _fmt(value, spec="{:.2f}"):
    return "n/a" if value is None else spec.format(value)


def main():
    parser = argparse.ArgumentParser(description="Evaluate human-factors benchmark records")
    parser.add_argument("results", help="JSON array of per-task session records")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()

    summary, _rows = evaluate(load_json(Path(args.results)))

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    print(f"records: {summary['total_records']}  conditions: {', '.join(summary['conditions_present'])}")
    for condition, s in summary["per_condition"].items():
        print(f"\n[{condition}] n={s['n']}")
        print(f"  completion rate: {_fmt(s['task_completion_rate'], '{:.1%}')}")
        print(f"  mean completion time s: {_fmt(s['mean_completion_time_s'])}")
        print(f"  intent accuracy: {_fmt(s['intent_accuracy'], '{:.1%}')}")
        print(f"  false-execution rate: {_fmt(s['false_execution_rate'], '{:.3f}')}")
        print(f"  clarification rate: {_fmt(s['clarification_rate'], '{:.3f}')}")
        print(f"  mean eyes-on-device s: {_fmt(s['mean_eyes_on_device_s'])}")
        print(f"  mean hands-on-device s: {_fmt(s['mean_hands_on_device_s'])}")
        print(f"  mode-switch continuity error rate: {_fmt(s['mode_switch_continuity_error_rate'], '{:.3f}')}")
        print(f"  mean workload: {_fmt(s['mean_workload'])}")
    if summary["comparison_vs_baseline"]:
        print(f"\nvs baseline ({BASELINE}):")
        for condition, cmp in summary["comparison_vs_baseline"].items():
            eyes = cmp["eyes_on_device_s"]
            print(f"  {condition}: eyes-on-device {(_fmt(eyes['pct_change'], '{:+.1f}%') if eyes else 'n/a')}")
    if summary["limitations"]:
        print("\nlimitations:")
        for item in summary["limitations"]:
            print(f"  - {item}")


if __name__ == "__main__":
    main()
