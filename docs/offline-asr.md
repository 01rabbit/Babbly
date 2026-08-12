# Offline Neural ASR Migration

Babbly now treats speech recognition as a replaceable backend instead of coupling Japanese command handling directly to Vosk.

## Goals

- keep the system fully usable without cloud APIs
- preserve the legacy Vosk path during migration
- allow a neural ASR backend such as faster-whisper
- stop relying on tokenizer whitespace for Japanese command routing
- normalize punctuation, spacing, Unicode width, and known ASR variants before intent resolution
- keep executable command routing deterministic and fail closed when intent is unknown

## Backend selection

Edit `babbly/ja/config_ja.yaml`.

```yaml
ASR_BACKEND: "vosk"
```

For the optional Whisper path:

```yaml
ASR_BACKEND: "faster-whisper"
WHISPER_MODEL: "small"
WHISPER_DEVICE: "cpu"
WHISPER_COMPUTE_TYPE: "int8"
```

For disconnected operation, provision the model before entering the isolated environment and set `WHISPER_MODEL` to the local model directory instead of relying on first-run download behavior.

## Processing pipeline

```text
Microphone
  -> ASR backend
  -> raw recognized text
  -> Japanese normalization
  -> deterministic intent resolver
  -> legacy target/command/SOP lookup when required
  -> explicit action
```

The normalization layer removes dependence on ASR-inserted spaces and accepts configured domain aliases. The first deterministic intents are system exit, self introduction, network scan, target display, and command-assist mode.

## Safety rule

A neural ASR or future local LLM may improve recognition or propose an intent, but it does not directly execute arbitrary shell commands. Executable operations continue through registered commands/SOPs and explicit routing logic.

## Next steps

1. benchmark Vosk vs faster-whisper on Raspberry Pi 5 with a fixed Japanese command corpus
2. record CER/WER plus task-level intent accuracy and latency
3. add wake-word/VAD separation so expensive ASR is activated only when needed
4. add domain vocabulary correction for Azazel, Kali, and other adapters
5. add confidence-aware clarification instead of executing ambiguous commands
6. evaluate sherpa-onnx/SenseVoice as an additional streaming ARM backend
