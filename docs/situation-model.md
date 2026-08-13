# Babbly Situation Model

Babbly is evolving from a voice-triggered command launcher into a reusable offline operator-assistance layer. The Situation Model is the boundary that keeps Babbly generic while allowing systems such as Azazel to provide context.

## Responsibility

Babbly owns:

- operator-facing observations
- cross-adapter situation aggregation
- advisory recommendations
- presentation by voice, TUI, or future UI surfaces

Adapters own translation from an external system's status shape into Babbly's generic model.

Babbly does not gain external-system action authority merely because an adapter is connected.

## Core objects

`Observation` records source, category, human-readable summary, severity, optional confidence, and source data.

`Recommendation` records an advisory action, reason, priority, and optional confidence. `advisory_only` defaults to `true`.

`SituationSnapshot` aggregates observations, recommendations, and per-adapter health. Its overall status is derived from the highest observation severity.

## Adapter boundary

`BabblyAdapter` is read-only/advisory by default:

```text
External system
     |
     v
BabblyAdapter
     |
     +--> Observation[]
     +--> Recommendation[]
              |
              v
       SituationEngine
              |
              v
       SituationSnapshot
              |
        +-----+-----+
        |           |
      Voice        TUI
```

## Azazel-Edge live status integration

The first live provider is intentionally narrow:

```text
Azazel-Edge
  GET /api/state
       |
       v
 status_view (Azazel-Fabric StatusView)
       |
       v
AzazelEdgeStatusProvider
       |
       v
AzazelAdapter
       |
       v
SituationEngine
```

Babbly consumes the JSON wire contract only; it does not require the `azazel-fabric` Python package. The shared `status_view` is preferred whenever present. Native Edge state fields are used only as a compatibility fallback for an installation where the additive view is unavailable.

The provider is GET-only and uses the canonical `X-AZAZEL-TOKEN` header. It has a bounded timeout, a response-size limit, no automatic retry loop, and a short monotonic TTL cache. The cache also prevents one SituationEngine collection from fetching `/api/state` twice when observations and recommendations are requested separately.

Current `StatusView` mapping:

- `posture` + `headline` -> system-state observation
- `reasons` -> status-reason observations
- `health` -> health observations with normalized severity
- `current_action` -> observation of an action Edge has already selected; never an execution request
- `next_actions` -> advisory Babbly recommendations
- current Edge `operator_wording` -> advisory fallback when `next_actions` is empty
- `trace_id`, `mode`, `evidence_ids`, and other contract metadata -> observation metadata

`product_view.edge_snapshot` is not treated as a command source. The shared Fabric view remains the presentation contract.

### Configuration

The integration is disabled by default. Enable it in `babbly/ja/config_ja.yaml` or an equivalent deployment configuration:

```yaml
AZAZEL_EDGE_ENABLED: true
AZAZEL_EDGE_URL: "http://127.0.0.1:8084"
AZAZEL_EDGE_TOKEN_ENV: "AZAZEL_EDGE_TOKEN"
AZAZEL_EDGE_TOKEN_FILE: ""
AZAZEL_EDGE_TIMEOUT_SEC: 2.0
AZAZEL_EDGE_CACHE_TTL_SEC: 1.0
```

Prefer a token environment variable or a protected token file; do not commit a token into the YAML file.

## Authority boundary

Situation reporting and recommendation explanation are read-only. A future Azazel write path must be modeled separately as an explicit request to Azazel-Edge. Babbly must not bypass Edge's deterministic decision authority, and a `current_action` observed in StatusView must never be replayed as a Babbly action.

## Failure behavior

An HTTP/auth/JSON/adapter failure marks the Azazel adapter as `error` and does not terminate the Situation Engine. Babbly remains usable when the optional integration is absent or unavailable. Transport errors do not fall through into command/SOP execution.

## Implemented voice intents

- `situation.report`: collect the current snapshot and speak a concise situation report.
- `recommendation.explain`: speak the highest-priority advisory recommendation, if any.

Both are non-executing intents.

## Next steps

1. validate live Edge/Babbly behavior on the Raspberry Pi reference appliance
2. add low-cost wake-word/KWS and VAD separation
3. record Pi 5 Vosk vs faster-whisper benchmark measurements
4. add other read-only adapters without coupling Babbly Core to their products
5. keep all future execution requests separate from the read-only Situation Model
