# Immediate next targets

The Situation Model, the first read-only situation intents, and the canonical
operator-intent contract (`babbly.operator-intent.v1`, issue #15 / PR #22) are
already implemented. The next work should move Babbly toward the
attention-adaptive operator interaction defined in
[`OPERATOR_INTERACTION_CONCEPT.md`](OPERATOR_INTERACTION_CONCEPT.md).

Tracking epic: #13. Canonical intent (#15) is complete and unblocks #16 and #17.

1. (#16) Add an operator-controlled `OperatorAttentionState` with
   NORMAL / HEADS_UP / CRITICAL presentation policy. Mode changes must alter
   information density and interaction style, never execution authority.
2. (#17) Implement compact TUI/Web Situation rendering from the existing
   `SituationSnapshot` model; make the web surface responsive enough to serve as
   the first smartphone/EUD prototype. Visual actions must invoke the canonical
   operator intent, not a second command implementation.
3. (#14) Implement and benchmark a low-cost wake-word / KWS path so full ASR does
   not need to run continuously while idle. Complete the software layer on the
   Mac; keep the Raspberry Pi 5 live ASR/KWS measurement as a separate hardware
   gate. Preserve the existing false-execution and intent-accuracy gates.
4. (#18) Design the controlled request/approval path for write-capable
   integrations separately from the read-only Situation Model.
5. (#19) Define the EUD-to-Core state/intent/session/reconnection contract only
   after the canonical intent and controlled-request boundaries are stable.
6. (#20) Build and field-test the responsive Web EUD on a forearm smartphone. A
   native Android client is deferred until measurement proves the Web surface is
   insufficient.
7. (#21) Add human-factors benchmark scenarios that measure eyes-on-device time,
   hands-on-device time, mode-switch continuity, workload, and task correctness
   in addition to ASR metrics.
