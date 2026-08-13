from __future__ import annotations

import json
import math
import os
import platform
import signal
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable, Mapping, Optional, Sequence


@dataclass(frozen=True)
class RuntimeSample:
    elapsed_sec: float
    process_cpu_percent: Optional[float]
    system_cpu_percent: Optional[float]
    rss_bytes: Optional[int]
    temperature_c: Optional[float]


def _read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _parse_proc_stat_line(text: str) -> tuple[int, int, int]:
    """Return (ppid, utime_ticks, stime_ticks) from /proc/<pid>/stat."""
    end = text.rfind(")")
    if end < 0:
        raise ValueError("invalid proc stat")
    fields = text[end + 2 :].split()
    if len(fields) < 13:
        raise ValueError("short proc stat")
    return int(fields[1]), int(fields[11]), int(fields[12])


def process_tree_pids(root_pid: int, proc_root: Path = Path("/proc")) -> set[int]:
    parent_by_pid: dict[int, int] = {}
    try:
        entries = list(proc_root.iterdir())
    except OSError:
        return {root_pid}

    for entry in entries:
        if not entry.name.isdigit():
            continue
        text = _read_text(entry / "stat")
        if not text:
            continue
        try:
            ppid, _, _ = _parse_proc_stat_line(text)
        except (TypeError, ValueError):
            continue
        parent_by_pid[int(entry.name)] = ppid

    selected = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, ppid in parent_by_pid.items():
            if pid not in selected and ppid in selected:
                selected.add(pid)
                changed = True
    return selected


def read_process_ticks(root_pid: int, proc_root: Path = Path("/proc")) -> Optional[int]:
    total = 0
    found = False
    for pid in process_tree_pids(root_pid, proc_root):
        text = _read_text(proc_root / str(pid) / "stat")
        if not text:
            continue
        try:
            _, utime, stime = _parse_proc_stat_line(text)
        except (TypeError, ValueError):
            continue
        total += utime + stime
        found = True
    return total if found else None


def read_process_rss_bytes(root_pid: int, proc_root: Path = Path("/proc")) -> Optional[int]:
    total_kib = 0
    found = False
    for pid in process_tree_pids(root_pid, proc_root):
        text = _read_text(proc_root / str(pid) / "status")
        if not text:
            continue
        for line in text.splitlines():
            if not line.startswith("VmRSS:"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    total_kib += int(parts[1])
                    found = True
                except ValueError:
                    pass
            break
    return total_kib * 1024 if found else None


def read_system_cpu(proc_stat: Path = Path("/proc/stat")) -> Optional[tuple[int, int]]:
    text = _read_text(proc_stat)
    if not text:
        return None
    first = text.splitlines()[0].split()
    if not first or first[0] != "cpu":
        return None
    try:
        values = [int(value) for value in first[1:]]
    except ValueError:
        return None
    if len(values) < 4:
        return None
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    total = sum(values)
    return idle, total


def _temperature_value(path: Path) -> Optional[float]:
    text = _read_text(path)
    if not text:
        return None
    try:
        value = float(text.strip())
    except ValueError:
        return None
    if abs(value) > 1000:
        value /= 1000.0
    if -20.0 <= value <= 150.0:
        return value
    return None


def read_temperature_c(sys_root: Path = Path("/sys")) -> Optional[float]:
    candidates = [sys_root / "class/thermal/thermal_zone0/temp"]
    hwmon = sys_root / "class/hwmon"
    try:
        for directory in hwmon.glob("hwmon*"):
            candidates.extend(sorted(directory.glob("temp*_input")))
    except OSError:
        pass
    for path in candidates:
        value = _temperature_value(path)
        if value is not None:
            return value
    return None


def _safe_mean(values: Iterable[Optional[float]]) -> Optional[float]:
    present = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    return mean(present) if present else None


def _safe_max(values: Iterable[Optional[float]]) -> Optional[float]:
    present = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    return max(present) if present else None


def summarize_samples(samples: Sequence[RuntimeSample]) -> dict[str, object]:
    return {
        "sample_count": len(samples),
        "process_cpu_percent_mean": _safe_mean(sample.process_cpu_percent for sample in samples),
        "process_cpu_percent_peak": _safe_max(sample.process_cpu_percent for sample in samples),
        "system_cpu_percent_mean": _safe_mean(sample.system_cpu_percent for sample in samples),
        "system_cpu_percent_peak": _safe_max(sample.system_cpu_percent for sample in samples),
        "rss_bytes_mean": _safe_mean(
            float(sample.rss_bytes) if sample.rss_bytes is not None else None for sample in samples
        ),
        "rss_bytes_peak": (
            int(value)
            if (value := _safe_max(
                float(sample.rss_bytes) if sample.rss_bytes is not None else None for sample in samples
            ))
            is not None
            else None
        ),
        "temperature_c_mean": _safe_mean(sample.temperature_c for sample in samples),
        "temperature_c_peak": _safe_max(sample.temperature_c for sample in samples),
    }


def machine_info() -> dict[str, object]:
    model = None
    for path in (Path("/proc/device-tree/model"), Path("/sys/firmware/devicetree/base/model")):
        text = _read_text(path)
        if text:
            model = text.replace("\x00", "").strip()
            break
    if not model:
        cpuinfo = _read_text(Path("/proc/cpuinfo")) or ""
        for line in cpuinfo.splitlines():
            if line.lower().startswith("model name") or line.lower().startswith("model\t"):
                model = line.split(":", 1)[-1].strip()
                break
    return {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "model": model,
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
    }


class RuntimeSampler:
    def __init__(self, pid: int) -> None:
        self.pid = int(pid)
        self.clock_ticks = int(os.sysconf("SC_CLK_TCK"))
        self.started = time.monotonic()
        self._previous_time: Optional[float] = None
        self._previous_ticks: Optional[int] = None
        self._previous_system: Optional[tuple[int, int]] = None

    def sample(self) -> RuntimeSample:
        now = time.monotonic()
        ticks = read_process_ticks(self.pid)
        system = read_system_cpu()
        process_cpu = None
        system_cpu = None

        if self._previous_time is not None and ticks is not None and self._previous_ticks is not None:
            elapsed = now - self._previous_time
            if elapsed > 0:
                process_cpu = max(0.0, (ticks - self._previous_ticks) / self.clock_ticks / elapsed * 100.0)

        if system is not None and self._previous_system is not None:
            idle_delta = system[0] - self._previous_system[0]
            total_delta = system[1] - self._previous_system[1]
            if total_delta > 0:
                system_cpu = max(0.0, min(100.0, (total_delta - idle_delta) / total_delta * 100.0))

        self._previous_time = now
        self._previous_ticks = ticks
        self._previous_system = system

        return RuntimeSample(
            elapsed_sec=now - self.started,
            process_cpu_percent=process_cpu,
            system_cpu_percent=system_cpu,
            rss_bytes=read_process_rss_bytes(self.pid),
            temperature_c=read_temperature_c(),
        )


def _terminate_process_group(process: subprocess.Popen, grace_sec: float = 3.0) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGINT)
    except (OSError, ProcessLookupError):
        return
    try:
        process.wait(timeout=max(0.1, grace_sec))
        return
    except subprocess.TimeoutExpired:
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


def _load_evaluation(path: Optional[str]) -> Optional[Mapping[str, object]]:
    if not path:
        return None
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError("evaluation JSON must be an object")
    return payload


def profile_command(
    command: Sequence[str],
    *,
    duration_sec: Optional[float] = None,
    sample_interval_sec: float = 0.5,
    stop_grace_sec: float = 3.0,
    label: str = "benchmark",
    backend_type: Optional[str] = None,
    backend: Optional[str] = None,
    model: Optional[str] = None,
    evaluation_json: Optional[str] = None,
) -> dict[str, object]:
    if not command:
        raise ValueError("command is required")
    if duration_sec is not None and duration_sec <= 0:
        raise ValueError("duration_sec must be positive")
    if sample_interval_sec <= 0:
        raise ValueError("sample_interval_sec must be positive")

    started_wall = time.time()
    started_monotonic = time.monotonic()
    process = subprocess.Popen(list(command), start_new_session=True)
    sampler = RuntimeSampler(process.pid)
    samples: list[RuntimeSample] = []
    stopped_by_duration = False

    try:
        while True:
            samples.append(sampler.sample())
            if process.poll() is not None:
                break
            elapsed = time.monotonic() - started_monotonic
            if duration_sec is not None and elapsed >= duration_sec:
                stopped_by_duration = True
                _terminate_process_group(process, stop_grace_sec)
                break
            time.sleep(sample_interval_sec)
    except KeyboardInterrupt:
        _terminate_process_group(process, stop_grace_sec)
        raise

    if process.poll() is None:
        process.wait()
    ended_monotonic = time.monotonic()

    result: dict[str, object] = {
        "schema_version": "babbly.runtime-benchmark.v1",
        "label": label,
        "backend_type": backend_type,
        "backend": backend,
        "model": model,
        "command": list(command),
        "started_at_epoch": started_wall,
        "duration_sec": ended_monotonic - started_monotonic,
        "configured_duration_sec": duration_sec,
        "sample_interval_sec": sample_interval_sec,
        "stopped_by_duration": stopped_by_duration,
        "exit_code": process.returncode,
        "status": "completed_window" if stopped_by_duration else ("ok" if process.returncode == 0 else "error"),
        "machine": machine_info(),
        "summary": summarize_samples(samples),
        "samples": [asdict(sample) for sample in samples],
    }
    evaluation = _load_evaluation(evaluation_json)
    if evaluation is not None:
        result["evaluation"] = dict(evaluation)
    return result


def write_json_atomic(path: str | Path, payload: Mapping[str, object]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)
