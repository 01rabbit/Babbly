#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture Babbly development-host runtime metrics; macOS is the primary development target"
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--label", default="mac-dev-benchmark")
    parser.add_argument("--backend-type", choices=("asr", "wake", "other"), default="other")
    parser.add_argument("--backend")
    parser.add_argument("--model")
    parser.add_argument("--duration", type=float)
    parser.add_argument("--sample-interval", type=float, default=0.5)
    parser.add_argument("--stop-grace", type=float, default=3.0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("a command is required after --")

    try:
        if platform.system() == "Darwin":
            from babbly.benchmark.macos_runtime import profile_command, write_json_atomic
        elif platform.system() == "Linux":
            from babbly.benchmark.runtime import profile_command, write_json_atomic
        else:
            raise RuntimeError(f"unsupported benchmark host: {platform.system()}")

        payload = profile_command(
            command,
            duration_sec=args.duration,
            sample_interval_sec=args.sample_interval,
            stop_grace_sec=args.stop_grace,
            label=args.label,
            backend_type=args.backend_type,
            backend=args.backend,
            model=args.model,
        )
        write_json_atomic(args.output, payload)
    except KeyboardInterrupt:
        return 130
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"benchmark capture failed: {exc}", file=sys.stderr)
        return 2

    summary = payload["summary"]
    print(f"wrote: {args.output}")
    print(f"host: {platform.system()} status={payload['status']} duration={payload['duration_sec']:.2f}s")
    if summary.get("process_cpu_percent_mean") is not None:
        print(
            f"process cpu: mean={summary['process_cpu_percent_mean']:.1f}% "
            f"peak={summary['process_cpu_percent_peak']:.1f}%"
        )
    if summary.get("rss_bytes_peak") is not None:
        print(f"peak rss: {summary['rss_bytes_peak'] / (1024 * 1024):.1f} MiB")
    return 0 if payload["status"] in {"ok", "completed_window"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
