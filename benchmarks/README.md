# Babbly Offline ASR / Wake Benchmark

Babbly uses a two-stage benchmark workflow:

1. development comparison on the reference MacBook Pro M5 Pro;
2. deployment validation on Raspberry Pi hardware.

Use the same recorded Japanese utterances for every backend. Do not compare live microphone sessions between backends because speaker timing, background noise, and wording drift make the result difficult to reproduce.

## Reference development host

Current reference development machine:

- MacBook Pro
- Apple M5 Pro
- macOS / Apple Silicon

Use this host for rapid ASR, wake, normalization, Intent, policy, and latency comparisons during development. Record machine metadata in every result so results from other Macs are not mixed into the M5 Pro baseline.

## Corpus

`ja_command_corpus.json` defines the expected text and task-level intent. Record one WAV file per `id` using the same microphone, distance, gain, room, and speaker.

Recommended first pass:

- 16 kHz, mono, PCM WAV
- quiet-room set
- moderate-noise set
- at least three repetitions per command after the initial prototype

Keep recordings out of the public repository unless the speaker has explicitly approved publication.

## Backend result format

Start from `example_results.json` and store one JSON object per corpus id:

```json
[
  {
    "id": "scan-001",
    "recognized_text": "ネットワークをスキャンして",
    "latency_ms": 842.4,
    "backend": "faster-whisper",
    "model": "small"
  }
]
```

Then run:

```bash
python tools/evaluate_asr_results.py results/faster-whisper-small.json
```

## Development-host runtime capture

On the MacBook Pro M5 Pro:

```bash
python tools/capture_dev_benchmark.py \
  --output results/mac-m5pro-whisper-small.json \
  --label mac-m5pro-whisper-small \
  --backend-type asr \
  --backend faster-whisper \
  --model small \
  --duration 30 \
  -- python babbly_ja.py
```

The macOS sampler records process-tree CPU, RSS, timing, and machine identity. Temperature is intentionally left unknown rather than inferred from an unsupported macOS source.

## Metrics

The benchmark emphasizes operational behavior over transcription cosmetics:

- normalized transcript exact rate
- task-level intent accuracy
- false-execution rate
- clarification rate where applicable
- mean recognition latency
- process-tree CPU
- process-tree RSS

## Raspberry Pi promotion benchmark

After a backend/configuration is acceptable on the M5 Pro development baseline, repeat the same corpus and task-level evaluation on the target Raspberry Pi. Pi validation additionally records:

- peak RSS / memory
- average and peak CPU utilization
- device temperature
- model load time
- idle power if available
- actual microphone/speaker behavior
- long-running stability

`tools/capture_runtime_benchmark.py` remains the Linux/Pi deployment profiler. See [`docs/pi-runtime-benchmark.md`](../docs/pi-runtime-benchmark.md).

The preferred backend is not automatically the one with the lowest character error rate. Babbly should prioritize high intent accuracy, zero or near-zero false execution, acceptable clarification rate, and field-usable latency, then verify that the selected configuration fits the target Pi resource envelope.

## Safety

Run Babbly with `DRY_RUN: true` during all speech-recognition tuning. This exercises wake phrase, normalization, intent routing, confidence policy, and confirmation dialogue without executing registered operational commands.
