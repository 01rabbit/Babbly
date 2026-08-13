# Implementation status

Implemented on this branch:

- SituationSnapshot, Observation, Recommendation
- SituationEngine aggregation and adapter failure isolation
- BabblyAdapter read-only/advisory contract
- `situation.report` and `recommendation.explain` voice intents
- concise Japanese situation/recommendation rendering
- Azazel-Edge GET-only `/api/state` transport
- Azazel-Fabric `status_view` wire-contract translation
- canonical `X-AZAZEL-TOKEN` authentication support
- bounded timeout and response size with no automatic retries
- short TTL cache to avoid duplicate reads during one collection
- environment/token-file secret loading; no committed token
- native Edge compatibility fallback when `status_view` is absent
- full tests and GitHub Actions coverage

Not implemented yet:

- write/action request contract
- autonomous actions from Situation Model
- low-cost wake-word / keyword-spotting backend
- Raspberry Pi 5 live ASR/KWS benchmark measurements
- TUI/Web situation rendering

The Azazel integration is intentionally read-only. Edge remains the authority for Azazel actions.
