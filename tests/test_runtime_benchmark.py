import json
from pathlib import Path

import pytest

from babbly.benchmark.runtime import (
    RuntimeSample,
    _parse_proc_stat_line,
    process_tree_pids,
    read_process_rss_bytes,
    read_process_ticks,
    summarize_samples,
    write_json_atomic,
)


def _stat(pid, ppid, utime, stime, comm="python worker"):
    # fields after comm start at proc field 3 (state). utime/stime are fields 14/15.
    tail = [
        "S",
        str(ppid),
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        str(utime),
        str(stime),
        "0",
        "0",
        "0",
    ]
    return f"{pid} ({comm}) " + " ".join(tail)


def _write_proc(proc_root: Path, pid: int, ppid: int, utime: int, stime: int, rss_kib: int):
    directory = proc_root / str(pid)
    directory.mkdir(parents=True)
    (directory / "stat").write_text(_stat(pid, ppid, utime, stime), encoding="utf-8")
    (directory / "status").write_text(f"Name:\ttest\nVmRSS:\t{rss_kib} kB\n", encoding="utf-8")


def test_parse_proc_stat_handles_spaces_in_comm():
    assert _parse_proc_stat_line(_stat(10, 3, 20, 5, "python child worker")) == (3, 20, 5)


def test_process_tree_and_metrics_include_descendants(tmp_path):
    proc = tmp_path / "proc"
    proc.mkdir()
    _write_proc(proc, 100, 1, 10, 5, 1024)
    _write_proc(proc, 101, 100, 20, 7, 2048)
    _write_proc(proc, 102, 101, 3, 2, 512)
    _write_proc(proc, 200, 1, 99, 99, 9999)

    assert process_tree_pids(100, proc) == {100, 101, 102}
    assert read_process_ticks(100, proc) == 47
    assert read_process_rss_bytes(100, proc) == (1024 + 2048 + 512) * 1024


def test_summarize_samples_ignores_missing_values():
    summary = summarize_samples(
        [
            RuntimeSample(0.0, None, None, 10, None),
            RuntimeSample(0.5, 25.0, 50.0, 30, 60.0),
            RuntimeSample(1.0, 75.0, 70.0, 20, 64.0),
        ]
    )
    assert summary["sample_count"] == 3
    assert summary["process_cpu_percent_mean"] == pytest.approx(50.0)
    assert summary["process_cpu_percent_peak"] == pytest.approx(75.0)
    assert summary["rss_bytes_peak"] == 30
    assert summary["temperature_c_peak"] == pytest.approx(64.0)


def test_write_json_atomic_creates_parent_and_valid_json(tmp_path):
    output = tmp_path / "nested" / "result.json"
    write_json_atomic(output, {"schema_version": "test", "ok": True})
    assert json.loads(output.read_text(encoding="utf-8")) == {"schema_version": "test", "ok": True}
    assert not (output.parent / "result.json.tmp").exists()
