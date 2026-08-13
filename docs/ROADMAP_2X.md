# Babbly 2.x Roadmap

## Phase A — Offline speech foundation

- pluggable ASR backend
- Japanese normalization
- deterministic intent routing
- confidence policy
- explicit clarification
- dry-run validation
- Pi 5 benchmark harness

## Phase B — Situation awareness foundation

- generic Observation / Recommendation / SituationSnapshot model
- optional adapter framework
- read-only Azazel adapter
- adapter failure isolation

## Phase C — Operator experience

- `situation.report` intent
- concise spoken situation reports
- explanation of highest-priority recommendation
- configurable verbosity and alert interruption policy

## Phase D — Field runtime

- low-power wake-word/KWS backend
- streaming ARM ASR evaluation
- local persistence and replay
- TUI and compact web surface

## Phase E — Controlled requests

- separate request/approval contract for write-capable integrations
- explicit human confirmation
- external authority preserved (for example, Azazel-Edge remains authoritative for Azazel actions)
- complete audit trail
