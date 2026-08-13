from __future__ import annotations

import json
import os
import platform
import signal
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Mapping, Optional, Sequence


@dataclass(frozen=True)
class MacRuntimeSample:
    elapsed_sec: float
    process_cpu_percent: Optional[float]
    rss_bytes: Optional[int]


def _run_ps() -> list[tuple[int, int, float, int]]:
    """Return (pid, ppid, cpu_percent, rss_kib) for current processes on macOS."""
    completed = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,%cpu=,rss="],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return []
    rows: list[tuple[int, int, float, int]] = []
    for line in completed.stdout.splitlines():
        parts = line.split()
        if len(parts) != 4:
            continue
        try:
            rows.append((int(parts[0]), int(parts[1]), float(parts[2]), int(parts[3])))
        except ValueError:
            continue
    return rows


def _process_tree_rows(root_pid: int) -> list[tuple[int, int, float, int]]:
    rows = _run_ps()
    by_parent: dict[int, list[int]] = {}
    by_pid = {pid: row for pid, *rest in rows for row in [(pid, rest[0], rest[1], rest[2])]}
    for pid, ppid, _, _ in rows:
        by_parent.setdefault(ppid, []).append(pid)

    selected = {int(root_pid)}
    pending = [int(root_pid)]
    while pending:
        parent = pending.pop()
        for child in by_parent.get(parent, []):
            if child not in selected:
                selected.add(child)
                pending.append(child)
    return [by_pid[pid] for pid in selected if pid in by_pid]


def read_process_tree_metrics(root_pid: int) -> tuple[Optional[float], Optional[int]]:
    rows = _process_tree_rows(root_pid)
    if not rows:
        return None, None
    cpu = sum(row[2] for row in rows)
    rss = sum(row[3] for row in rows) * 1024
    return cpu, rss


def _sysctl(name: str) -> Optional[str]:
    completed = subprocess.run(["sysctl", "-n", name], check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def machine_info() -> dict[str, object]:
    return {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "model": _sysctl("hw.model"),
        "chip": _sysctl("machdep.cpu.brand_string"),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "development_host": "macOS",
    }


def summarize(samples: Sequence[MacRuntimeSample]) -> dict[str, object]:
    cpu = [s.process_cpu_percent for s in samples if s.process_cpu_percent is not None]
    rss = [s.rss_bytes for s in samples if s.rss_bytes is not None]
    return {
        "sample_count": len(samples),
        "process_cpu_percent_mean": mean(cpu) if cpu else None,
        "process_cpu_percent_peak": max(cpu) if cpu else None,
        "rss_bytes_mean": mean(rss) if rss else None,
        "rss_bytes_peak": max(rss) if rss else None,
        "temperature_c_mean": None,
        "temperature_c_peak": None,
        "temperature_note": "macOS temperature is intentionally not inferred without a privileged/external sensor source",
    }


def _terminate(process: subprocess.Popen, grace_sec: float) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGINT)
        process.wait(timeout=max(0.1, grace_sec))
        return
    except (OSError, ProcessLookupError, subprocess.TimeoutExpired):
        pass
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=1.0)
        return
    except (OSError, ProcessLookupError, subprocess.TimeoutExpired):
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        pass


def profile_command(
    command: Sequence[str],
    *,
    duration_sec: Optional[float] = None,
    sample_interval_sec: float = 0.5,
    stop_grace_sec: float = 3.0,
    label: str = "mac-dev-benchmark",
    backend_type: Optional[str] = None,
    backend: Optional[str] = None,
    model: Optional[str] = None,
) -> dict[str, object]:
    if platform.system() != "Darwin":
        raise RuntimeError("macOS runtime sampler requires Darwin")
    if not command:
        raise ValueError("command is required")
    if duration_sec is not None and duration_sec <= 0:
        raise ValueError("duration_sec must be positive")
    if sample_interval_sec <= 0:
        raise ValueError("sample_interval_sec must be positive")

    started_wall = time.time()
    started = time.monotonic()
    process = subprocess.Popen(list(command), start_new_session=True)
    samples: list[MacRuntimeSample] = []
    stopped_by_duration = False

    try:
        while True:
            now = time.monotonic()
            cpu, rss = read_process_tree_metrics(process.pid)
            samples.append(MacRuntimeSample(now - started, cpu, rss))
            if process.poll() is not None:
                break
            if duration_sec is not None and now - started >= duration_sec:
                stopped_by_duration = True
                _terminate(process, stop_grace_sec)
                break
            time.sleep(sample_interval_sec)
    except KeyboardInterrupt:
        _terminate(process, stop_grace_sec)
        raise

    if process.poll() is None:
        process.wait()
    elapsed = time.monotonic() - started
    return {
        "schema_version": "babbly.runtime-benchmark.v1",
        "host_role": "development",
        "label": label,
        "backend_type": backend_type,
        "backend": backend,
        "model": model,
        "command": list(command),
        "started_at_epoch": started_wall,
        "duration_sec": elapsed,
        "configured_duration_sec": duration_sec,
        "sample_interval_sec": sample_interval_sec,
        "stopped_by_duration": stopped_by_duration,
        "exit_code": process.returncode,
        "status": "completed_window" if stopped_by_duration else ("ok" if process.returncode == 0 else "error"),
        "machine": machine_info(),
        "summary": summarize(samples),
        "samples": [asdict(sample) for sample in samples],
    }


def write_json_atomic(path: str | Path, payload: Mapping[str, object]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)
