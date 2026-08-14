# Implementation status

Implemented on this branch:

- SituationSnapshot, Observation, Recommendation
- SituationEngine aggregation and adapter failure isolation
- BabblyAdapter read-only/advisory contract
- `situation.report` and `recommendation.explain` voice intents
- concise Japanese situation/recommendation rendering
- Azazel-Edge GET-only `/api/state` transport
- Azazel-Fabric `status_view` wire-contract translation
- canonical `X-AZAZEL-TOKEN` authentication support
- bounded timeout and response size with no automatic retries
- short TTL cache to avoid duplicate reads during one collection
- environment/token-file secret loading; no committed token
- native Edge compatibility fallback when `status_view` is absent
- Agent/environment profiles (`generic`, `kali`, `azazel-edge`) that project
  identity/wake/persona/vocabulary/read-only source but never execution authority
- canonical operator-intent contract `babbly.operator-intent.v1`
  (`OperatorIntent`, `OperatorContext`, `OperatorIntentRuntime`) shared by
  Voice/TUI/Web/EUD for `situation.report`, `recommendation.explain`, and
  registered `operation.run` confirmation/DRY_RUN state
- `OperatorAttentionState` (NORMAL/HEADS_UP/CRITICAL) presentation policy with
  operator-only, auditable transitions and `attention.set` / `attention.status`
  intents; authority is identical in every mode
- shared Situation view-model (`babbly.situation-view.v1`) with a compact TUI
  renderer and a responsive Web surface (`python -m babbly.web`) as the first
  EUD prototype; visual actions route through canonical intents only
- separated speech-entry stages: `EnergyVad` (model-free energy VAD),
  replaceable wake backends (ASR compatibility gate + optional sherpa-onnx KWS),
  and full command ASR, so idle operation does not run full ASR continuously
- offline wake benchmark corpus and FAR/FRR/latency evaluator
  (`tools/evaluate_wake_results.py`)
- live JA voice app wiring (`babbly/ja/main_program.py`): builds the runtime via
  `build_operator_runtime` so the controlled write path activates from config
  (`AZAZEL_EDGE_WRITE_ENABLED` + `AZAZEL_EDGE_WRITE_ACTIONS`, default off);
  renders situation/recommendation at the current attention density and switches
  attention mode by voice; and can serve the Web/EUD surface in a background
  thread bound to the same runtime (`WEB_SURFACE_ENABLED`, default off)
- full tests and GitHub Actions coverage

Not implemented yet:

- write/action request contract
- autonomous actions from Situation Model
- Raspberry Pi 5 live ASR/KWS field-benchmark measurements (hardware-gated;
  Mac-side software layer is complete)
- native Android EUD client

The Azazel integration is intentionally read-only. Edge remains the authority for Azazel actions.
