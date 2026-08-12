# Raspberry Pi 5 Offline ASR Benchmark

Use the same recorded Japanese utterances for every backend. Do not compare live microphone sessions because speaker timing, background noise, and wording drift make the result difficult to reproduce.

## Corpus

`ja_command_corpus.json` defines the expected text and task-level intent. Record one WAV file per `id` using the same microphone, distance, gain, room, and speaker.

Recommended first pass:

- 16 kHz, mono, PCM WAV
- quiet-room set
- moderate-noise set
- at least three repetitions per command after the initial prototype

Keep recordings out of the public repository unless the speaker has explicitly approved publication.

## Backend result format

Store one JSON object per corpus id:

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

## Metrics

The first benchmark intentionally emphasizes operational behavior over transcription cosmetics:

- normalized transcript exact rate
- task-level intent accuracy
- false-execution rate
- mean recognition latency

For the Pi 5 hardware study, also record externally:

- peak RSS / memory
- average and peak CPU utilization
- device temperature
- model load time
- idle power if available

The preferred backend is not automatically the one with the lowest character error rate. Babbly should prioritize high intent accuracy, zero or near-zero false execution, acceptable clarification rate, and field-usable latency.

## Safety

Run Babbly with `DRY_RUN: true` during all speech-recognition tuning. This exercises wake phrase, normalization, intent routing, confidence policy, and confirmation dialogue without executing registered operational commands.
