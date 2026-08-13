# Offline Wake Word / KWS Foundation

Babbly separates wake detection from command speech recognition so the full ASR backend does not need to run continuously while idle.

## Pipeline

```text
microphone
  -> VAD (energy)                         # is there speech at all?
  -> WakeDetector
       -> ASR compatibility gate (default)
       -> sherpa-onnx KWS (optional)
  -> wake event only
  -> command ASR
  -> normalization / intent / policy
  -> registered action or read-only query
```

VAD, wake/KWS, and full ASR are kept as separate responsibilities so idle
operation does not require continuous full ASR inference. Wake detection has
deliberately low authority. A trigger may only open the command-listening
window. It cannot create an intent, select a target, or execute an action.

## VAD stage

`babbly/wake/vad.py` provides `EnergyVad`, a low-cost, model-free energy voice
activity detector. It decides *whether there is speech*, never *what was said*,
so it can gate expensive full-ASR inference while idle without any model asset,
and it has no action authority.

`EnergyVad` is a small hysteresis state machine over per-frame RMS:
`start_frames` consecutive loud frames open an utterance and `hangover_frames`
consecutive quiet frames close it (a brief dip inside speech does not end the
utterance). It emits `SPEECH_START` / `SPEECH` / `SPEECH_END` / `SILENCE`
events. The faster-whisper backend uses it to bound utterance capture, so a
silent window is never transcribed. Its decision logic is covered by
deterministic unit tests independent of any microphone or model.

## Backends

### `asr` (default)

Preserves the previous behavior by listening with the configured ASR backend until `WAKEUP_PHRASE` is recognized. This is the compatibility path and requires no new dependency.

### `sherpa-onnx`

Uses `sherpa_onnx.KeywordSpotter` with a locally provisioned streaming KWS model and keyword file. Babbly never downloads a model at runtime.

Required deployment settings:

```yaml
WAKE_BACKEND: "sherpa-onnx"
KWS_TOKENS: "/opt/babbly/models/kws/tokens.txt"
KWS_ENCODER: "/opt/babbly/models/kws/encoder.int8.onnx"
KWS_DECODER: "/opt/babbly/models/kws/decoder.onnx"
KWS_JOINER: "/opt/babbly/models/kws/joiner.int8.onnx"
KWS_KEYWORDS_FILE: "/opt/babbly/models/kws/keywords.txt"
KWS_SAMPLE_RATE: 16000
KWS_CHUNK_MS: 100
KWS_NUM_THREADS: 2
KWS_PROVIDER: "cpu"
```

Install `sherpa-onnx` in the deployment environment only when this backend is selected.

## Japanese warning

As of the implementation date, sherpa-onnx's documented public KWS pretrained model list is Chinese/English-focused. Do not assume those artifacts can reliably detect the Japanese legacy wake phrase `プログラム`. The backend therefore requires an explicit compatible model/keyword file rather than silently selecting or downloading a model.

For the Pi 5 study, evaluate two tracks:

1. keep the legacy Japanese wake phrase and use the ASR compatibility gate;
2. define a short Babbly-specific wake phrase that can be represented by the selected KWS model, then measure false accepts, false rejects, latency, CPU, RAM, and temperature.

## Reproducible wake benchmark

`benchmarks/wake_corpus.json` defines positive wake samples, ordinary negative speech, command-like speech without a wake word, and a confusable phrase. Record several repetitions of each class under the same microphone/gain/distance conditions used for the ASR benchmark.

Store backend output using the shape in `benchmarks/example_wake_results.json`:

```json
{
  "id": "wake-positive-001",
  "actual_trigger": true,
  "latency_ms": 180.2,
  "backend": "sherpa-onnx-kws",
  "model": "local-model"
}
```

Evaluate it with:

```bash
python tools/evaluate_wake_results.py results/wake-sherpa.json
```

or machine-readable output:

```bash
python tools/evaluate_wake_results.py results/wake-sherpa.json --json
```

The evaluator reports:

- true positive / true negative
- false positive / false negative
- false accept rate (FAR)
- false reject rate (FRR)
- accuracy
- mean true-positive trigger latency
- P95 true-positive trigger latency
- missing corpus entries

For field selection, FAR and FRR are more important than raw recognition text. Record idle CPU, peak CPU, RSS/RAM, temperature and power separately for each backend because these depend on the Pi deployment rather than the JSON decision result.

## Failure behavior

- unknown wake backend: startup configuration error
- missing sherpa model files: startup configuration error
- missing optional Python dependency: startup configuration error
- no trigger: remain at the wake gate
- trigger: open command ASR only; no action authority is granted

## Next measurements

On Raspberry Pi 5, measure idle CPU/RAM and trigger latency for the compatibility gate vs KWS, then combine those results with the existing Vosk/faster-whisper command-ASR benchmark.
