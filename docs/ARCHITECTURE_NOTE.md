# Architecture boundary

Babbly Core should remain usable without Azazel. Azazel is an adapter, not a core dependency.

The dependency direction is:

```text
Babbly Core <- Adapter <- External system
```

Never:

```text
Babbly Core -> Azazel-specific implementation
```

This preserves Babbly as a generic offline operator-assistance framework.

## Operator-interface boundary

Voice, TUI, web, and future wearable EUDs are input/presentation surfaces. They must not become separate execution architectures.

Equivalent operator actions should converge on a canonical intent before policy or execution:

```text
Visual input ----+
                 +--> Canonical Intent --> Policy --> Registered operation/request
Voice input -----+
```

The current target, task state, SituationSnapshot, pending confirmation, and audit context should survive a switch between visual and voice interaction.

A wearable smartphone is therefore a Babbly EUD, not Babbly Core and not the security-tool executor. Device-specific UI, microphone, speaker/TTS, and connectivity code should remain outside core domain logic.

## Situation and presentation boundary

The Situation Model is presentation-neutral. NORMAL, HEADS_UP, and CRITICAL attention modes may change information density, speech length, and preferred input modality, but must not alter the underlying SituationSnapshot or weaken safety policy.

Operator attention state is not the same as threat severity. Initial mode transitions must be operator-controlled rather than inferred from speculative tactical or battlefield judgment.

## Authority invariants

- ASR or a future local LLM may propose an intent but must not directly execute arbitrary shell commands.
- Registered commands, SOPs, or explicit request contracts remain the execution boundary.
- Unknown or low-confidence intent fails closed according to the confidence policy.
- Confirmation policy must be consistent across visual and voice surfaces.
- Read-only/advisory adapters do not gain write authority through the Situation Model.
- External systems retain their own decision authority.
- Changing presentation or attention mode must never grant additional execution capability.

See [`OPERATOR_INTERACTION_CONCEPT.md`](OPERATOR_INTERACTION_CONCEPT.md) for the full development concept.
