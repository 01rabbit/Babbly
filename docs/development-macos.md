# MacBook-first development workflow

Babbly development is MacBook-first. Raspberry Pi is a deployment and hardware-validation target, not the primary edit/test host.

## Reference development host

- macOS on Apple Silicon (MacBook Air M2 reference)
- Python 3
- project virtual environment: `.venv`
- repository-local launcher: `./run_babbly.sh`

## Development sequence

1. Implement on the MacBook.
2. Run compile/unit/core tests on the MacBook.
3. Exercise normalization, intent, policy, Situation Model, adapters, dry-run behavior, and benchmark tooling locally.
4. Commit and push to GitHub; CI runs on both macOS and Linux.
5. Pull the verified revision to the Raspberry Pi target.
6. Validate Pi-specific audio devices, KWS/ASR latency, thermal behavior, and resource limits on the Pi.

The Mac and Pi audio devices are different. A successful Mac test is not evidence that microphone selection, gain, speaker output, or real-time audio timing is correct on the Pi.

## Initial setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install pipenv
pipenv requirements > /tmp/babbly-requirements.txt
python -m pip install -r /tmp/babbly-requirements.txt
python -m pip install "pytest>=8,<10"
```

Run tests:

```bash
./run_babbly.sh test
```

Run Japanese Babbly:

```bash
./run_babbly.sh ja
```

During voice/intent development, set `DRY_RUN: true` in `babbly/ja/config_ja.yaml` so operational actions remain suppressed.

## Mac runtime benchmark

The primary development-host profiler is platform-aware:

```bash
python tools/capture_dev_benchmark.py \
  --output results/mac-vosk.json \
  --label mac-vosk \
  --backend-type asr \
  --backend vosk \
  --duration 30 \
  -- python babbly_ja.py
```

On macOS it uses `ps` to aggregate CPU and RSS for the Babbly process tree. It does not invent a temperature value: macOS temperature remains `null` unless a future explicitly supported sensor provider is added.

## Raspberry Pi promotion gate

Move a change to Pi validation only after the Mac/CI layer passes. Pi validation is responsible for:

- physical microphone/speaker behavior
- ALSA/Pulse/PipeWire/device-specific integration where applicable
- wake-word false accept/reject behavior on the actual microphone
- ASR real-time latency
- CPU/RSS under the deployment image
- temperature and throttling
- long-running stability

This keeps ordinary development fast on the Mac while preserving hardware truth on the deployment target.
