# Babbly 2.x Roadmap

## North-star objective

Babbly should evolve into an **offline operator-assistance system that preserves situational awareness**.

The operator must be able to use a visual surface when attention is available and move to eyes-free / hands-free interaction when attention must remain on the surrounding environment, without changing the underlying task state or weakening execution safeguards.

Visual, voice, TUI, web, and future wearable EUD surfaces must converge on the same canonical intents, Situation Model, policy boundary, and registered operations.

See [`OPERATOR_INTERACTION_CONCEPT.md`](OPERATOR_INTERACTION_CONCEPT.md).

## Phase A — Offline speech foundation

- pluggable ASR backend
- Japanese normalization
- deterministic intent routing
- confidence policy
- explicit clarification
- dry-run validation
- Pi 5 benchmark harness

Purpose: make reliable eyes-free input possible without cloud dependency or arbitrary shell authority.

## Phase B — Situation awareness foundation

- generic Observation / Recommendation / SituationSnapshot model
- optional adapter framework
- read-only Azazel adapter
- adapter failure isolation

Purpose: define one operator-facing truth model that every presentation surface can render.

## Phase C — Operator experience

- `situation.report` intent
- concise spoken situation reports
- explanation of highest-priority recommendation
- configurable verbosity and alert interruption policy
- canonical intent contract shared by voice and visual surfaces
- OperatorAttentionState design: NORMAL / HEADS_UP / CRITICAL
- presentation policy that compresses information without changing SituationSnapshot truth

Purpose: reduce interaction cost while preserving task continuity and human authority.

## Phase D — Field runtime

- low-power wake-word/KWS backend
- streaming ARM ASR evaluation
- local persistence and replay
- TUI and compact web Situation surface
- responsive smartphone layout suitable for an initial forearm-EUD prototype
- connection, current target, current operation, findings, recommendation, and confirmation-state visibility

Purpose: make the current Babbly Core usable as a field operator interface before committing to a native wearable client.

## Phase E — Controlled requests

- separate request/approval contract for write-capable integrations
- explicit human confirmation
- risk-aware confirmation policy shared across voice and visual interaction
- external authority preserved (for example, Azazel-Edge remains authoritative for Azazel actions)
- complete audit trail
- preserve pending confirmation and request context across modality changes

Purpose: allow controlled operator requests without turning Babbly into an autonomous execution authority.

## Phase F — Wearable / heads-up EUD integration

- define EUD-to-Core session, SituationSnapshot, intent, confirmation, and connectivity contract
- implement operator-controlled NORMAL / HEADS_UP / CRITICAL switching
- guarantee modality continuity between visual and voice interaction
- build a forearm-smartphone EUD using the stable interaction contract
- keep execution-heavy security tools behind controlled executors/adapters rather than embedding them in the EUD
- validate degraded/disconnected behavior and reconnection semantics
- field-test visual, hybrid, and eyes-free workflows using authorized test tasks

Purpose: implement the final Babbly concept as a wearable human-machine interface for maintaining situational awareness while cyber tasks continue.

## Phase G — Human-factors validation

Evaluate Babbly against conventional laptop/CLI operation and visual-only EUD operation.

Recommended measures:

- task completion rate and time
- intent accuracy
- false-execution rate
- clarification rate
- time to important information
- eyes-on-device time
- hands-on-device time
- mode-switch continuity errors
- operator workload

The project should not claim situational-awareness benefit solely from ASR accuracy. The final concept is successful only if operator attention captured by the computing device is measurably reduced without unacceptable loss of correctness or control.
