# Raspberry Pi Runtime Benchmark Capture

`tools/capture_runtime_benchmark.py` profiles a Babbly, ASR, or wake/KWS process with standard-library-only runtime instrumentation. It is designed for Raspberry Pi 5 field measurements but degrades safely on other Linux hosts.

## What it records

Each JSON result contains:

- benchmark label and backend metadata
- exact child command
- machine / architecture / Python metadata
- wall-clock duration and exit status
- mean and peak process-tree CPU utilization
- mean and peak system CPU utilization
- mean and peak process-tree RSS
- mean and peak temperature when Linux exposes a thermal sensor
- raw timestamped samples
- optional embedded ASR or Wake evaluation JSON

The process metrics include descendants, so a launcher that creates worker processes is measured as one benchmark workload.

## Fixed-window idle profile

Use a fixed window to compare the cost of an always-on wake implementation:

```bash
python tools/capture_runtime_benchmark.py \
  --output results/wake-asr-idle.json \
  --label wake-asr-idle \
  --backend-type wake \
  --backend asr \
  --duration 60 \
  -- python babbly_ja.py
```

When `--duration` expires, the profiler sends SIGINT to the child process group, waits for the configured grace interval, then escalates to SIGTERM/SIGKILL only if necessary. A deliberate fixed-window stop is reported as `status=completed_window`, not as a benchmark failure.

For sherpa-onnx, configure `WAKE_BACKEND: sherpa-onnx` and provision the local model first, then run the same command with a different label/backend.

## Command-ASR profile

A complete command that exits on its own can be profiled without `--duration`:

```bash
python tools/capture_runtime_benchmark.py \
  --output results/asr-whisper.json \
  --label asr-whisper-small \
  --backend-type asr \
  --backend faster-whisper \
  --model small \
  -- python your_backend_benchmark.py
```

## Combine quality and runtime evidence

The existing evaluators can emit machine-readable JSON:

```bash
python tools/evaluate_wake_results.py results/wake-events.json --json > results/wake-eval.json
python tools/evaluate_asr_results.py results/asr-events.json --json > results/asr-eval.json
```

Embed either result in the runtime capture:

```bash
python tools/capture_runtime_benchmark.py \
  --output results/wake-sherpa-combined.json \
  --label wake-sherpa \
  --backend-type wake \
  --backend sherpa-onnx \
  --evaluation-json results/wake-eval.json \
  --duration 60 \
  -- python babbly_ja.py
```

This keeps FAR/FRR or intent accuracy next to CPU, RSS, and temperature evidence instead of maintaining two unrelated records.

## Recommended Pi 5 matrix

Run the same hardware, microphone, room, power supply, cooling setup, sample interval, and corpus for each candidate.

| Layer | Candidate | Key quality metrics | Key runtime metrics |
|---|---|---|---|
| Wake | ASR compatibility gate | FAR, FRR, trigger latency | idle CPU/RSS/temp |
| Wake | sherpa-onnx KWS | FAR, FRR, trigger latency | idle CPU/RSS/temp |
| Command ASR | Vosk | intent accuracy, false execution, latency | CPU/RSS/temp |
| Command ASR | faster-whisper | intent accuracy, false execution, latency | CPU/RSS/temp |

Use `DRY_RUN: true` for all voice tuning and benchmark sessions that exercise operational intents.

## Interpretation

`process_cpu_percent` is process-tree CPU consumption where approximately 100% represents one fully utilized logical CPU; multi-threaded workloads may exceed 100%. `system_cpu_percent` is whole-system utilization bounded to 0–100%.

Temperature is best-effort. The profiler checks the standard Raspberry Pi thermal zone first and then common hwmon sensors. Missing temperature data remains `null` and does not invalidate other measurements.
