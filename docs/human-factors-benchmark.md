# Human-factors benchmark

Issue #21. Babbly's concept is judged by whether it **reduces operator attention
captured by the computing device while preserving correctness, control, and task
continuity** — not by ASR accuracy alone. This document defines the protocol and
fixtures; `tools/evaluate_human_factors.py` turns recorded runs into statistics.

## Conditions

Equivalent authorized lab tasks are run under four conditions:

1. `laptop_cli` — conventional laptop/CLI operation (baseline)
2. `visual_eud` — visual-only smartphone/EUD operation
3. `hybrid_voice` — hybrid visual + voice Babbly operation
4. `eyes_free` — eyes-free Babbly operation

The baseline is `laptop_cli`; reductions are reported relative to it.

## Scenarios

`benchmarks/human_factors_scenarios.json` defines task goals that are equivalent
across conditions (a read-only status check, an operation that must reach an
explicit confirmation, and a Babbly-only mode-switch continuity task). Use the
same task goals for every condition so results are comparable.

## Measurements

Each run is one record (`benchmarks/example_human_factors_results.json` shows the
shape). Required per record:

- `completed`, `completion_time_s`
- `intent_attempts`, `intent_correct`, `false_executions`, `clarifications`
- `eyes_on_device_s`, `hands_on_device_s`

Optional: `time_to_important_info_s`, `mode_switches`,
`mode_switch_continuity_errors`, `workload` (e.g. NASA-TLX 0–100).

## Evaluation

```bash
python tools/evaluate_human_factors.py results/human-factors.json
python tools/evaluate_human_factors.py results/human-factors.json --json
```

Per condition it reports task completion rate, completion time, intent accuracy,
false-execution rate, clarification rate, time-to-important-information,
eyes-on-device and hands-on-device time, mode-switch continuity error rate, and
workload. It then compares each Babbly condition against the laptop baseline for
eyes-on-device, hands-on-device, and completion time.

## Reporting honestly

- Results must include the raw records plus the summary statistics.
- Conditions with fewer than three samples, or a missing baseline, are flagged in
  `limitations` and must be treated as indicative only.
- Failures and limitations are reported, not hidden. Final project claims about
  situational-awareness preservation must cite measured results from this
  protocol, not impressions.

## Scope note

The evaluator and fixtures are deterministic and ready now. The measured results
require human runs on the visual/hybrid/eyes-free workflows (#17 is ready; the
forearm field prototype is #20), so recorded numbers are produced during that
field work.
