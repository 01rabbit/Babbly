from babbly.benchmark import macos_runtime


def test_process_tree_metrics_aggregates_descendants(monkeypatch):
    rows = [
        (100, 1, 10.0, 1000),
        (101, 100, 20.0, 2000),
        (102, 101, 5.0, 500),
        (200, 1, 99.0, 9000),
    ]
    monkeypatch.setattr(macos_runtime, "_run_ps", lambda: rows)

    cpu, rss = macos_runtime.read_process_tree_metrics(100)

    assert cpu == 35.0
    assert rss == 3500 * 1024


def test_summary_leaves_temperature_unknown():
    samples = [
        macos_runtime.MacRuntimeSample(0.0, 10.0, 1024),
        macos_runtime.MacRuntimeSample(0.5, 30.0, 4096),
    ]

    summary = macos_runtime.summarize(samples)

    assert summary["process_cpu_percent_mean"] == 20.0
    assert summary["process_cpu_percent_peak"] == 30.0
    assert summary["rss_bytes_peak"] == 4096
    assert summary["temperature_c_mean"] is None
    assert summary["temperature_c_peak"] is None
