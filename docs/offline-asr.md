# Offline Neural ASR Migration

Babbly now treats speech recognition as a replaceable backend instead of coupling Japanese command handling directly to Vosk.

## Goals

- keep the system fully usable without cloud APIs
- preserve the legacy Vosk path during migration
- allow a neural ASR backend such as faster-whisper
- stop relying on tokenizer whitespace for Japanese command routing
- normalize punctuation, spacing, Unicode width, and known ASR variants before intent resolution
- keep executable command routing deterministic and fail closed when intent is unknown
- require clarification or rejection when recognition confidence is insufficient
- keep Kali and Azazel terminology in replaceable domain vocabulary packs

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
  -> bounded utterance capture / VAD
  -> ASR backend
  -> ASRResult(text, confidence, backend)
  -> Japanese normalization
  -> domain vocabulary correction
  -> deterministic intent resolver
  -> confidence policy
       -> execute
       -> clarify
       -> reject
  -> registered command / SOP only
```

The normalization layer removes dependence on ASR-inserted spaces. Vocabulary packs correct domain-specific variants without making the ASR engine itself responsible for product knowledge.

## Confidence policy

`INTENT_EXECUTE_THRESHOLD` and `INTENT_CLARIFY_THRESHOLD` define the deterministic execution boundary.

- high confidence: execute a known intent
- medium confidence: ask the operator to confirm
- low confidence: reject and request the command again
- unknown intent: reject

Legacy command/SOP fallback is never executed immediately after an unknown intent. Babbly asks for an explicit yes/no confirmation first.

The faster-whisper backend derives its optional utterance confidence from segment log probabilities. Vosk remains supported even when backend confidence is unavailable; in that case the deterministic intent score is used.

## Domain vocabulary

`DOMAIN_VOCABULARY` selects terminology packs:

```yaml
DOMAIN_VOCABULARY:
  - core
  - kali
  - azazel
```

The first packs normalize terms such as Nmap pronunciation variants and Azazel component/mode names. They are correction dictionaries, not action authority.

## Safety rule

A neural ASR or future local LLM may improve recognition or propose an intent, but it does not directly execute arbitrary shell commands. Executable operations continue through registered commands/SOPs and explicit routing logic.

## CI

A lightweight GitHub Actions workflow runs the deterministic NLU, confidence-policy, and vocabulary tests without installing audio/ML dependencies.

## Next steps

1. benchmark Vosk vs faster-whisper on Raspberry Pi 5 with a fixed Japanese command corpus
2. record CER/WER plus task-level intent accuracy, clarification rate, false-execution rate, latency, CPU, and RAM
3. add a low-power wake-word/KWS backend so full ASR does not run continuously while idle
4. add a structured Situation Model and adapter contract for generic tools and Azazel
5. evaluate sherpa-onnx/SenseVoice as an additional streaming ARM backend
6. add replayable recorded-audio regression fixtures after licensing/privacy-safe samples are available
