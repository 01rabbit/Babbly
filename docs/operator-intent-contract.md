# Canonical Operator Intent Contract

Version: `babbly.operator-intent.v1`

Babbly Core treats Voice, TUI, Web and wearable EUDs as presentation/input surfaces. They must not become separate command systems. Equivalent operator actions converge on one canonical operator-intent representation before they reach task logic, confirmation state, or registered executors.

## Contract fields

`OperatorIntent` carries:

- `intent_id` and intent `version`
- normalized `parameters`
- `target_ref` and `context_ref`
- `source_modality`: `voice`, `tui`, `web`, `eud`, or `test`
- optional recognition `confidence`
- clarification/confirmation state
- `confirmation_id`
- `correlation_id`
- `audit_id`

It intentionally does **not** carry arbitrary shell strings, adapter credentials, authority grants, profile-defined privileges, or threat/attention-derived privileges.

## Agent profile relationship

Agent identity is presentation configuration, not command authority.

For example:

- Generic Babbly may use the spoken name `バブリー`.
- The Azazel-Edge profile uses `M.I.O` / `ミオ`.
- Persona tone, verbosity, wake phrases and vocabulary may differ.

Both resolve an equivalent operator action such as `situation.report` to the same canonical intent. Agent name/persona does not alter authorization, confirmation requirements, target binding, or external-system authority.

This keeps the profile model compatible with `NORMAL / HEADS_UP / CRITICAL`: Agent Profile and OperatorAttentionState may both change presentation, but neither changes the canonical task truth or execution policy.

## Context and modality switching

`OperatorContext` retains:

- current target
- current task/context
- pending confirmation identifier
- pending canonical intent
- last correlation identifier

A request may therefore begin by voice and be confirmed or denied by Web/EUD without losing target, task, confirmation, correlation, or audit identity.

Example:

```text
Voice: "recon-alpha を target A に実行"
  -> operation.run
  -> confirmation_required
  -> confirmation_id = ...

EUD: operator taps Approve
  -> same pending intent
  -> source_modality becomes eud
  -> same correlation_id / audit_id / target / context
```

## Current runtime scope

`OperatorIntentRuntime` currently provides the common path for:

- `situation.report`
- `recommendation.explain`
- registered local `operation.run` confirmation state and DRY_RUN representation

Registered operation execution remains owned by the existing registered SOP boundary. Arbitrary shell execution is not introduced by this contract.

Write-capable requests to external systems are intentionally deferred to issue #18 and must remain separate from the read-only `SituationSnapshot` / Recommendation model.

## Safety invariants

- modality does not change execution policy;
- Agent Profile does not grant authority;
- OperatorAttentionState does not grant authority;
- switching modality preserves task and confirmation context;
- no arbitrary shell string is a canonical intent;
- ASR/KWS/LLM components do not receive execution authority;
- external systems retain their own decision authority.

## Acceptance coverage

Automated tests verify:

- Voice and Web invoke `situation.report` through the same core runtime and receive equivalent snapshot data;
- a registered operation has the same semantic representation from Voice and EUD under `DRY_RUN`;
- a pending Voice confirmation can be resolved from Web while preserving target, context, confirmation, correlation and audit identifiers.
