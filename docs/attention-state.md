# Operator attention state

`OperatorAttentionState` is an operator-controlled presentation budget. It is
defined in [`OPERATOR_INTERACTION_CONCEPT.md`](OPERATOR_INTERACTION_CONCEPT.md)
and implemented in `babbly/core/attention.py`.

It is deliberately **separate from threat/system severity**. It expresses how
much visual and manual attention the operator can currently spend on the device,
not how dangerous the situation is.

## States

| State       | Assumed operator attention        | Presentation                                             |
| ----------- | --------------------------------- | -------------------------------------------------------- |
| `NORMAL`    | visual-first, attention available | adapter health, up to 3 observations, recommendation reason, action affordances |
| `HEADS_UP`  | reduced visual, voice preferred   | current target/findings, up to 2 observations, no health/reason |
| `CRITICAL`  | eyes-free / hands-free            | concise spoken state, top observation only, essential controls |

The same `SituationSnapshot` is rendered at different densities by
`render_situation_for_attention()` and `render_recommendation_for_attention()`.
This is progressive disclosure: the snapshot itself never changes.

## Operator control only

Transitions happen only through `AttentionController.request_state()`, driven by
an explicit operator action from a surface. There is **no autonomous or inferred
transition** — Babbly does not switch modes from speculative tactical or
battlefield judgment. Every accepted change is appended to an auditable history
(`sequence`, `from_state`, `to_state`, `source_modality`, `reason`).

## Canonical intent path

Attention changes travel through the same canonical operator-intent runtime as
every other surface action, so Voice, TUI, Web and EUD request them identically:

- `attention.set` — parameters `{"state": "normal" | "heads_up" | "critical"}`;
  applied without confirmation; unknown state fails closed
  (`attention.invalid_state`).
- `attention.status` — read-only report of the current state and policy.

## Authority invariants

Attention state changes presentation only. It must never:

- change execution authority or which operations are permitted;
- weaken or add confirmation requirements;
- alter a pending confirmation, target, context, correlation, or audit identity;
- modify the underlying `SituationSnapshot`.

`OperatorIntentRuntime` enforces operation confirmation and DRY_RUN behaviour
identically in every attention mode; `tests/test_operator_attention.py` asserts
this invariance across all three states, alongside coverage of every state
transition and the density differences between renderings.
