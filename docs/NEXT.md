# Immediate next targets

The Situation Model and first read-only situation intents are already implemented. The next work should move Babbly toward the attention-adaptive operator interaction defined in [`OPERATOR_INTERACTION_CONCEPT.md`](OPERATOR_INTERACTION_CONCEPT.md).

1. Implement and benchmark a low-cost wake-word / KWS path so full ASR does not need to run continuously while idle.
2. Record Raspberry Pi 5 live ASR/KWS measurements and keep the existing false-execution and intent-accuracy gates.
3. Define a canonical operator-intent contract that can be invoked identically from voice and future visual surfaces while preserving target, task, confirmation, and audit context.
4. Implement compact TUI/Web Situation rendering from the existing SituationSnapshot model; make the web surface responsive enough to serve as the first smartphone/EUD prototype.
5. Add an operator-controlled `OperatorAttentionState` with NORMAL / HEADS_UP / CRITICAL presentation policy. Mode changes must alter information density and interaction style, never execution authority.
6. Design the controlled request/approval path for write-capable integrations separately from the read-only Situation Model.
7. Define the EUD-to-Core state/intent/session contract only after the canonical intent and controlled-request boundaries are stable.
8. Add human-factors benchmark scenarios that measure eyes-on-device time, hands-on-device time, mode-switch continuity, workload, and task correctness in addition to ASR metrics.
