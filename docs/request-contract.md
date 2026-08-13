# Controlled request / approval contract

Version: `babbly.action-request.v1`. Implemented in `babbly/core/request.py`
(issue #18).

This is the **only** supported path by which Babbly submits a write-capable or
state-changing request to an external executor. It is separate from the
read-only `SituationSnapshot` / Recommendation model and preserves explicit
human authority and an audit trail.

## Why it is separate from the Situation Model

The Situation Model and Recommendations are read-only/advisory. A recommendation
is never replayed as a command, and a read-only situation adapter can never
satisfy the write contract: the executor interface uses a distinct method
(`ActionExecutor.execute_action`), so a situation source that only exposes
`collect()` is not an executor.

`ActionRequest` carries an action **identifier** and normalized parameters — no
shell string, no credentials, no authority grant.

## State machine

```text
                submit
                  v
          PENDING_APPROVAL ──approve──> APPROVED ──dispatch──> COMPLETED
             │  │  │                       │                     
             │  │  └──deny──> DENIED        └──dispatch(fail /    ──> FAILED
             │  │                                 executor reject)
             │  └──cancel──> CANCELLED      (cancel before dispatch also allowed)
             └──timeout──> TIMED_OUT
```

- `PENDING_APPROVAL` → `APPROVED` | `DENIED` | `CANCELLED` | `TIMED_OUT`
- `APPROVED` → `COMPLETED` | `FAILED` | `CANCELLED` (before dispatch)
- `DENIED`, `CANCELLED`, `TIMED_OUT`, `COMPLETED`, `FAILED` are terminal.

Approval is always an explicit, separate human step. `RiskClass`
(low/medium/high) is advisory metadata for surfaces; it never removes the
approval requirement.

## Human authority and external authority

- A request only dispatches after a human `approve`.
- The external executor keeps **final** authority: it may reject an already
  human-approved request (`ExecutionResult(ok=False, rejected_by_executor=True)`
  → `FAILED`). Approval by Babbly is necessary but not sufficient.
- Under `dry_run`, an approved request completes without calling the executor,
  for field tuning.

## Modality switching

Requests are keyed by `request_id` and carry a stable `correlation_id` and
`audit_id`. A request submitted from voice can be approved or denied from the
web/EUD surface without losing correlation; every transition records the acting
`modality`. Confirmation policy is identical across surfaces.

## Timeouts

Each request may carry an approval window (`default_timeout_seconds`). Once the
deadline passes, `poll_timeouts()` (and any approve/deny attempt) moves a still
`PENDING_APPROVAL` request to `TIMED_OUT`. The clock is injectable, so timeout
behaviour is deterministic under test.

## Audit record

Every transition appends an `AuditEntry` with `seq`, `request_id`, `event`,
`from_state`, `to_state`, `modality`, `at`, and optional `detail`. The audit log
therefore contains the request, the approval decision, the result, and modality
metadata for the full lifecycle.

## Relationship to the canonical intent runtime

`OperatorIntentRuntime` today stops registered `operation.run` at
`confirmation_required` and represents DRY_RUN; it does not itself perform
external writes. Wiring a confirmed operation into a `ControlledRequestManager`
request (and an Azazel-Edge `ActionExecutor`) is the integration point for the
future "M.I.O, isolate the target" flow, which must still end at Azazel-Edge's
deterministic decision authority.

## Safety invariants

- `SituationSnapshot` / Recommendation stay read-only/advisory.
- no observed `current_action` is replayed as a Babbly command.
- external systems retain final authority for their own actions.
- visual and voice surfaces apply identical confirmation policy.
- no arbitrary shell string is a request contract.
