# MacBook-first development workflow

Babbly development is MacBook-first. Raspberry Pi is a deployment and hardware-validation target, not the primary edit/test host.

## Reference development host

- macOS on Apple Silicon
- current reference machine: MacBook Pro with M5 Pro
- Python 3
- project virtual environment: `.venv`
- repository-local launcher: `./run_babbly.sh`

The development workflow should remain compatible with Apple Silicon Macs generally, but performance baselines recorded from now on should identify the MacBook Pro M5 Pro as the reference host unless explicitly stated otherwise.

## Development sequence

1. Implement on the MacBook Pro M5 Pro.
2. Run compile/unit/core tests on the MacBook.
3. Exercise normalization, intent, policy, Agent Profiles, Situation Model, adapters, dry-run behavior, and benchmark tooling locally.
4. Commit and push to GitHub; CI runs on both macOS and Linux.
5. Pull the verified revision to the Raspberry Pi target.
6. Validate Pi-specific audio devices, KWS/ASR latency, thermal behavior, and resource limits on the Pi.

The Mac and Pi audio devices are different. A successful Mac test is not evidence that microphone selection, gain, speaker output, or real-time audio timing is correct on the Pi.

## Prerequisites

- **Python 3.11** on the reference host. CI runs 3.11, and some pinned wheels
  (e.g. `vosk`) do not publish an Apple Silicon build for 3.10. Use a 3.11
  interpreter to create the virtual environment.
- **CMake** is required to build the offline TTS dependency `pyopenjtalk` from
  source: `brew install cmake`. With CMake 4.x, export
  `CMAKE_POLICY_VERSION_MINIMUM=3.5` before installing so the vendored
  `open_jtalk`/`hts_engine` sources still configure.

## Initial setup

```bash
# Use a Python 3.11 interpreter for the virtual environment.
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install pipenv
pipenv requirements > /tmp/babbly-requirements.txt
# CMAKE_POLICY_VERSION_MINIMUM is only needed with CMake >= 4.
CMAKE_POLICY_VERSION_MINIMUM=3.5 python -m pip install -r /tmp/babbly-requirements.txt
python -m pip install "pytest>=8,<10"
```

The offline ASR model is a separate, uncommitted asset. `vosk` expects a model
directory at `MODEL_PATH` (default `babbly/ja/model`); provision it before
running the full voice loop. Tests, `--list-profiles`, and profile/DRY_RUN
startup do not require the model.

Run tests:

```bash
./run_babbly.sh test
```

List profiles:

```bash
python babbly_ja.py --list-profiles
```

Run normal Babbly:

```bash
./run_babbly.sh ja --profile generic
```

Run the Azazel-Edge M.I.O profile:

```bash
./run_babbly.sh ja --profile azazel-edge
```

For M.I.O, the expected operator-facing identity is `M.I.O`, the spoken/wake name is `ミオ`, the vocabulary is `core + azazel`, and the read-only Azazel-Edge situation source is enabled. Profile selection must not alter DRY_RUN, Intent thresholds, command/SOP registries, or action authority.

During voice/intent development, set `DRY_RUN: true` in `babbly/ja/config_ja.yaml` so operational actions remain suppressed.

## Mac runtime benchmark

The primary development-host profiler is platform-aware:

```bash
python tools/capture_dev_benchmark.py \
  --output results/mac-m5pro-vosk.json \
  --label mac-m5pro-vosk \
  --backend-type asr \
  --backend vosk \
  --duration 30 \
  -- python babbly_ja.py --profile generic
```

To benchmark M.I.O's runtime path, append `--profile azazel-edge` to the child command.

On macOS it uses `ps` to aggregate CPU and RSS for the Babbly process tree. The benchmark JSON records macOS machine information via `sysctl`, so M5 Pro measurements can be separated from other Apple Silicon results. It does not invent a temperature value: macOS temperature remains `null` unless a future explicitly supported sensor provider is added.

## Raspberry Pi promotion gate

Move a change to Pi validation only after the Mac/CI layer passes. Pi validation is responsible for:

- physical microphone/speaker behavior
- ALSA/Pulse/PipeWire/device-specific integration where applicable
- profile wake-word false accept/reject behavior on the actual microphone
- ASR real-time latency
- CPU/RSS under the deployment image
- temperature and throttling
- long-running stability

This keeps ordinary development fast on the Mac while preserving hardware truth on the deployment target.
