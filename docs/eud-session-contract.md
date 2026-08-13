# EUD-to-Core session contract

Version: `babbly.eud-session.v1`. Implemented in `babbly/core/session.py`
(issue #19).

A transport-neutral contract between a wearable/smartphone Babbly EUD and Babbly
Core. The EUD stays a presentation/input **client**; it is never a second core
implementation. `CoreSessionEndpoint.handle(message) -> message` is a pure
function, so it runs over any transport (HTTP, WebSocket, local socket) or
directly in tests. All connected surfaces share one operator runtime, so
switching between voice and the EUD preserves target, attention state, and
pending confirmation.

## Messages

Client → Core:

- `hello` `{protocol_version, auth_token?}` → `welcome` `{session_id, protocol_version, capabilities, situation}`
- `get_situation` `{session_id}` → `situation` `{situation}`
- `submit_intent` `{session_id, intent_id, parameters, client_msg_id?}` → `intent_result` `{result, situation, deduplicated}`
- `resume` `{session_id, auth_token?}` → `resumed` `{situation}`
- `ping` → `pong`

Any handler may return `error` `{code, detail}`.

## Situation envelope and freshness

Each `situation` carries `revision` (bumped on every state-changing intent),
`generated_at` (server clock), and the shared `babbly.situation-view.v1` view.
The client compares `generated_at` against its own clock (`situation_is_stale`)
so **stale data is visibly distinguishable from current state** — required when
Core becomes unreachable and the EUD shows its last-known situation.

## Intent exposure

`submit_intent` accepts only the read/presentation allowlist
(`situation.report`, `recommendation.explain`, `attention.status`,
`attention.set`). Write-capable requests are **not** exposed over the session
until the controlled request/approval path (#18) is wired in; `operation.run`
and anything else return `intent_not_allowed`. The protocol never carries a
shell string.

## Reconnect, resume, and idempotency

- `resume` re-syncs an existing session and returns the current situation,
  including any pending confirmation, so a request begun by voice can be seen and
  resolved from the EUD after a reconnect.
- `resume` on an unknown/expired session **fails closed** (`unknown_session`);
  the client must `hello` again. Reconnect never silently replays state onto an
  unknown session.
- `submit_intent` is idempotent per `client_msg_id`: a resend (e.g. after a
  flaky reconnect) returns the cached response with `deduplicated: true` and is
  **not applied a second time**, so a queued action is never replayed.

## Security

- optional `expected_token` gates `hello`/`resume`; no token is committed to
  source control (the deployment supplies it).
- messages are bounded (`max_message_bytes`, default 64 KiB) → `message_too_large`.
- the endpoint exposes no arbitrary shell execution.

## Reference client

`ReferenceEudClient` is an in-process client used by the contract tests. It can
display a SituationSnapshot view and submit a non-executing canonical intent,
and it exercises connect / state update / intent submit / confirmation / disconnect
/ reconnect / duplicate request / stale state.
