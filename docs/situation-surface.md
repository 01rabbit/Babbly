# Situation surface (TUI / Web EUD prototype)

Issue #17. A compact visual surface over the existing `SituationSnapshot`,
intended as the **first Babbly EUD prototype** — a smartphone-friendly view for
brief-glance use on a forearm-mounted phone, before any native Android client is
considered.

## One presentation model, two surfaces

`babbly/core/surface.py` builds a single presentation-neutral view-model
(`babbly.situation-view.v1`) from a `SituationSnapshot`:

- `build_situation_view(snapshot, attention_state)` — status, adapter health,
  prioritized observations, top recommendation, pending confirmation, and a
  `degraded` flag, all at the density allowed by the attention state.
- `render_tui(view)` — a compact terminal panel from the same view-model.

Both the TUI and the Web page render from this one model, so the surfaces cannot
drift into separate presentations of the same situation. Density follows
[`attention-state.md`](attention-state.md): NORMAL exposes adapter health and the
recommendation reason; HEADS_UP/CRITICAL compress progressively.

## Over the EUD session contract

`babbly/web/server.py` (`SituationWebApp`) is a presentation/input surface, not a
second command system. It speaks the versioned EUD-to-Core **session contract**
(`babbly.eud-session.v1`, see [`eud-session-contract.md`](eud-session-contract.md))
rather than touching the runtime directly; the web server holds one server-side
session on the browser's behalf and re-establishes it if it is lost.

- `GET /api/situation` returns a session **envelope** (`revision`,
  `generated_at`, `view`) from the canonical `situation.report` intent, so the
  page can show freshness and flag stale data on a failed poll.
- `POST /api/intent` forwards to the session's `submit_intent`, which accepts
  only the read/presentation allowlist (`situation.report`,
  `recommendation.explain`, `attention.status`, `attention.set`). Anything else —
  including `operation.run` — is rejected (`intent_not_allowed`). Intent
  submissions carry a `client_msg_id`, so a resend is idempotent and never
  replayed. The controlled write/approval path remains #18.

The web page's mode buttons submit `attention.set`, so a visual action reaches
the same canonical intent path a voice command would, and the view immediately
re-renders at the new density. A failed poll keeps the last-known situation and
shows a `stale` badge instead of blanking the surface.

## Running it

```bash
python -m babbly.web            # http://127.0.0.1:8787
python -m babbly.web --port 9000
```

It binds loopback by default and depends only on `babbly.core` and the standard
library, so it runs without the offline voice/ASR stack. A bare runtime with no
situation adapters shows an empty ("状況不明") snapshot; wire a situation source
(e.g. the read-only Azazel-Edge adapter) to populate it.

## Safety

- The surface never executes registered operations or shell strings.
- Adapter/transport failure is represented (`degraded`, systems in `error`)
  instead of crashing the surface.
- Changing attention mode from the surface changes presentation only; execution
  authority and confirmation policy are unchanged (see `attention-state.md`).
