# Babbly Operator Interaction Concept

## North-star objective

Babbly is evolving into an **offline operator-assistance system that preserves situational awareness**.

The operator must be able to use a visual surface when attention is available, then move to eyes-free / hands-free interaction when operational workload or the surrounding situation requires attention elsewhere, without changing the underlying task model.

Babbly is therefore not defined as "a voice-controlled shell". Voice, TUI, web, and future wearable interfaces are presentation and input surfaces over the same Situation Model, Intent system, policy boundary, and registered operations.

## Core principle

> Preserve operator attention by allowing seamless movement between visual and voice interaction while keeping intent semantics, execution policy, and task state consistent.

The desired interaction model is:

```text
                         Operator
                            |
             +--------------+--------------+
             |                             |
       Visual surface                  Voice surface
       tap / select                    speech / TTS
             |                             |
             +--------------+--------------+
                            |
                      Canonical Intent
                            |
                       Safety Policy
                            |
               +------------+------------+
               |                         |
        Situation Model          Registered request / SOP
               |                         |
               +------------+------------+
                            |
                      Adapter boundary
                            |
                 Kali / Azazel / others
```

A visual action and its spoken equivalent must resolve to the same canonical intent whenever they mean the same thing. Switching modality must not discard the current target, task state, SituationSnapshot, pending confirmation, or audit context.

## Attention modes

Babbly should support an operator-attention state that is separate from system threat severity.

### NORMAL

Visual-first operation. The operator can inspect details, navigate findings, and select actions on the EUD, TUI, or web surface. Voice remains available as an alternative input.

### HEADS_UP

Reduced visual interaction. Information density is compressed and voice becomes the preferred interaction path. The visual surface should expose only the current target, operation state, important findings, recommendation, and confirmation state.

### CRITICAL

Eyes-free / hands-free operation is assumed. Babbly should minimize speech length, preserve access to status and control intents, and restrict execution to known registered operations under the normal policy and confirmation rules.

The initial implementation must make attention-mode changes **operator-controlled**. Babbly must not infer battlefield danger, tactical urgency, or operator safety and autonomously switch modes based on speculative AI judgment.

## Presentation policy

The Situation Model remains the source of operator-facing state. Attention mode changes presentation, not truth.

The same SituationSnapshot may be rendered differently:

```text
NORMAL
- detailed observations
- recommendation reason
- adapter health
- action affordances

HEADS_UP
- current target
- current operation
- top findings
- highest-priority recommendation

CRITICAL
- concise spoken state
- concise spoken recommendation
- confirmation / stop / repeat / status controls
```

This is progressive disclosure: Babbly should expose enough information for the operator's current attention budget while retaining detail for later inspection.

## Wearable EUD boundary

A forearm-mounted smartphone or other wearable device is a **Babbly EUD**, not Babbly Core.

The EUD should provide:

- compact visual SituationSnapshot rendering
- voice capture and TTS
- attention-mode control
- canonical intent submission
- confirmation UI
- connection / target / execution-state visibility

Execution-heavy security tooling remains behind a controlled executor or external-system adapter. This keeps Android/device constraints out of Babbly Core and allows the same core to support a laptop, Raspberry Pi, smartphone, headset, or future smart-glass surface.

The first EUD prototype should be implemented as a compact web surface backed by the same models used by voice/TUI. A native Android client can follow only after the interaction contract is stable.

## Safety and authority invariants

The existing Babbly safety model remains mandatory across every modality:

- neural ASR or a future local LLM may interpret or propose intent, but must not receive arbitrary shell authority
- executable behavior must pass through registered commands, SOPs, or explicit request contracts
- unknown or low-confidence intent fails closed
- confirmation requirements are policy-driven and identical across voice and visual surfaces
- Situation Model recommendations remain advisory unless a separate approved request path exists
- external authority remains external; for example, an Azazel adapter must not bypass Azazel-Edge decision authority
- switching attention mode must never weaken execution policy

## Development sequence

The current Babbly 2.x work should continue rather than being replaced by a separate wearable project.

1. Complete offline speech and wake/KWS foundations.
2. Stabilize Situation Model and adapter contracts.
3. Unify voice and visual actions behind canonical intents.
4. Implement compact TUI/web Situation rendering as the first EUD surface.
5. Add OperatorAttentionState and presentation policy for NORMAL / HEADS_UP / CRITICAL.
6. Complete controlled request/approval contracts for write-capable integrations.
7. Define the EUD-to-Core session/intent/state contract.
8. Build and field-test the forearm smartphone EUD.
9. Validate the concept with human-factors measurements.

## Evaluation target

Babbly should be evaluated not only by speech-recognition accuracy but by whether it reduces operator attention captured by the computing device while preserving task correctness.

Recommended measures include:

- task completion rate and completion time
- intent accuracy
- false-execution rate
- clarification rate
- time to important information
- eyes-on-device time
- hands-on-device time
- mode-switch continuity errors
- operator workload

Comparisons should include conventional laptop/CLI operation, visual EUD operation, hybrid visual/voice operation, and eyes-free operation using equivalent authorized test tasks.

## Non-goals

This concept does not make Babbly an autonomous tactical decision-maker. Babbly does not determine battlefield threat, replace surrounding-area security procedures, or independently select offensive actions. Its role is to reduce unnecessary interaction cost with the computing system while preserving human authority and situational awareness.
