# Changelog

All notable changes to Babbly are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Babbly is pre-1.0 and, until now, untagged. The versions below are established by
this changelog; each groups a set of merged pull requests by its milestone, and
the dates are the merge dates of that work. Safety- and authority-relevant
changes are called out under **Security** because they are central to Babbly's
design (presentation surfaces never gain execution authority).

## How to maintain this file

- Add every user-visible change under `[Unreleased]`, in the right group
  (`Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`), with the
  issue/PR number.
- When cutting a release, rename `[Unreleased]` to the new version + date and
  start a fresh, empty `[Unreleased]`.
- Prefer operator-facing wording over implementation detail.

## [Unreleased]

_Remaining roadmap work is hardware-/field-gated and tracked in the open issues:
Raspberry Pi 5 field benchmarks (#14), the forearm smartphone EUD field test
(#20), and the measured human-factors runs (#21). Parent epic: #13._

## [0.3.0] - 2026-08-14

Attention-adaptive operator interaction: attention modes, the first EUD
surfaces, the controlled write path, and the EUD session contract.

### Added

- **Operator attention state** `NORMAL` / `HEADS_UP` / `CRITICAL` with an
  operator-controlled, auditable presentation policy, and `attention.set` /
  `attention.status` canonical intents. The same `SituationSnapshot` renders at
  decreasing density (progressive disclosure). (#16)
- **Compact TUI and responsive Web Situation surface** — the first Babbly EUD
  prototype — built from a shared presentation view-model (`babbly.situation-view.v1`)
  and runnable with `python -m babbly.web`. (#17)
- **Separable energy VAD stage** (`EnergyVad`) so idle operation does not require
  continuous full ASR inference; VAD, wake/KWS, and full ASR are distinct
  responsibilities. (#14)
- **Controlled request/approval contract** `babbly.action-request.v1`
  (`ActionRequest`, `ControlledRequestManager`) — the only supported path for
  write-capable requests — with an approve/deny/cancel/timeout state machine,
  injectable clock, and full audit trail. (#18)
- **Azazel-Edge action executor** and wiring of a confirmed, allowlisted
  `operation.run` to controlled dispatch, completing the "M.I.O, isolate the
  target" flow. Disabled by default. (#18)
- **EUD-to-Core session contract** `babbly.eud-session.v1`
  (`CoreSessionEndpoint`, `ReferenceEudClient`): connect, versioned situation
  envelope with freshness, non-executing intent submission, pending-confirmation
  resync, reconnect, per-`client_msg_id` idempotency, stale detection, optional
  token auth, and message-size bounds. (#19)
- **Human-factors benchmark**: protocol, scenario fixtures, and a deterministic
  evaluator (`tools/evaluate_human_factors.py`) for completion rate/time, intent
  accuracy, false-execution and clarification rates, time-to-important-info,
  eyes-on-device and hands-on-device time, mode-switch continuity, and workload,
  with reductions vs the laptop baseline. (#21)

### Changed

- The Web EUD is now served **over the session contract** instead of touching the
  runtime directly: `/api/situation` returns a session envelope with
  `revision`/`generated_at`, intent submissions are idempotent, a dropped session
  reconnects transparently, and a failed poll keeps the last-known situation with
  a `stale` badge. (#19)
- Synced `docs/IMPLEMENTATION_STATUS.md` and `docs/NEXT.md` with the delivered
  canonical operator-intent contract and later milestones. (#23)

### Fixed

- Apple Silicon Mac setup now installs from the documented flow: relaxed the
  unavailable `vosk==0.3.45` pin to an installable build and documented the
  Python 3.11 / CMake prerequisites for the `pyopenjtalk` build. (#25)
- Ignore the local `.venv/` and `results/` produced by the Mac-first workflow. (#23)

### Security

- Attention state, agent profile, and EUD session all change presentation only;
  execution authority, confirmation policy, DRY_RUN, and the `SituationSnapshot`
  are identical across every mode and surface, with regression tests. (#16, #17, #19)
- Write requests are a separate typed contract from the read-only Situation
  Model; the `ActionExecutor` interface cannot be satisfied by a read-only
  situation adapter, human approval is always required, the external executor
  retains final authority (it may reject an approved request), and no contract
  carries a shell string. The write path is disabled by default. (#18)
- The EUD session never exposes write intents or shell execution, fails closed on
  unknown sessions, and never replays an unapproved action on reconnect. (#19)

## [0.2.0] - 2026-08-13

Foundations for the shift from a voice-controlled tool to a presentation-neutral,
offline operator-assistance framework.

### Added

- Pluggable **offline ASR** backends and a Japanese normalization/intent/policy
  foundation with a deterministic confidence boundary. (#7)
- **Situation Model** (`SituationSnapshot`, `Observation`, `Recommendation`) with
  a `SituationEngine`, the `situation.report` / `recommendation.explain` intents,
  and a **read-only** Azazel-Edge integration over a bounded, cached, GET-only
  `/api/state` transport. (#8)
- Offline **wake-word / KWS foundation** behind a replaceable interface (ASR
  compatibility gate plus an optional locally-provisioned sherpa-onnx backend),
  with a benchmark corpus and a FAR/FRR/latency evaluator. (#9)
- Raspberry Pi **runtime benchmark capture** tooling. (#10)
- **Agent/environment profiles** (`generic`, `kali`, `azazel-edge`) that select
  identity, wake phrase, persona, vocabulary, and read-only source — including
  **M.I.O** (「ミオ」) for Azazel-Edge — without changing execution authority. (#12)
- **Canonical operator-intent contract** `babbly.operator-intent.v1`
  (`OperatorIntent`, `OperatorContext`, `OperatorIntentRuntime`) so Voice, TUI,
  Web, and EUD surfaces converge on one representation. (#15, #22)

### Changed

- Adopted the **MacBook Pro M5 Pro** as the reference development host and a
  Mac-first workflow, with Raspberry Pi as a deployment/validation target. (#11)

### Security

- The Azazel-Edge integration is read-only and advisory; Edge remains the
  authority for its own actions. Profiles change identity/presentation only, not
  authorization, confirmation, or DRY_RUN. (#8, #12)

## [0.1.0] - 2024-12-03

Initial Babbly: an offline, voice-controlled assistant for authorized
penetration testing.

### Added

- Japanese and English offline voice interaction (wake phrase, command speech,
  TTS), network scanning and target registration, registered
  operation/SOP execution with Metasploit integration, and a `DRY_RUN` mode that
  suppresses operational actions.

[Unreleased]: https://github.com/01rabbit/Babbly/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/01rabbit/Babbly/releases/tag/v0.3.0
[0.2.0]: https://github.com/01rabbit/Babbly/releases/tag/v0.2.0
[0.1.0]: https://github.com/01rabbit/Babbly/releases/tag/v0.1.0
