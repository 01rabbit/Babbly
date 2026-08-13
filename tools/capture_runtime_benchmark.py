#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

from babbly.benchmark.runtime import profile_command, write_json_atomic


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Profile a Babbly/ASR/KWS command and emit Pi-friendly runtime metrics as JSON"
    )
    parser.add_argument("--output", required=True, help="Destination JSON path")
    parser.add_argument("--label", default="benchmark", help="Human-readable benchmark label")
    parser.add_argument("--backend-type", choices=("asr", "wake", "other"), default="other")
    parser.add_argument("--backend", help="Backend name, for example vosk, faster-whisper, sherpa-onnx")
    parser.add_argument("--model", help="Model name/path label")
    parser.add_argument(
        "--duration",
        type=float,
        help="Optional fixed profiling window. The child process is stopped when the window expires.",
    )
    parser.add_argument("--sample-interval", type=float, default=0.5)
    parser.add_argument("--stop-grace", type=float, default=3.0)
    parser.add_argument(
        "--evaluation-json",
        help="Optional JSON object from evaluate_asr_results.py/evaluate_wake_results.py to embed",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command after --")
    args = parser.parse_args()

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("a command is required after --")

    try:
        payload = profile_command(
            command,
            duration_sec=args.duration,
            sample_interval_sec=args.sample_interval,
            stop_grace_sec=args.stop_grace,
            label=args.label,
            backend_type=args.backend_type,
            backend=args.backend,
            model=args.model,
            evaluation_json=args.evaluation_json,
        )
        write_json_atomic(args.output, payload)
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"benchmark capture failed: {exc}", file=sys.stderr)
        return 2

    summary = payload["summary"]
    print(f"wrote: {args.output}")
    print(f"status: {payload['status']} duration={payload['duration_sec']:.2f}s")
    if summary.get("process_cpu_percent_mean") is not None:
        print(
            "process cpu: "
            f"mean={summary['process_cpu_percent_mean']:.1f}% "
            f"peak={summary['process_cpu_percent_peak']:.1f}%"
        )
    if summary.get("rss_bytes_peak") is not None:
        print(f"peak rss: {summary['rss_bytes_peak'] / (1024 * 1024):.1f} MiB")
    if summary.get("temperature_c_peak") is not None:
        print(f"peak temperature: {summary['temperature_c_peak']:.1f} C")
    return 0 if payload["status"] in {"ok", "completed_window"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
