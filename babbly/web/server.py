"""Compact responsive Web/TUI Situation surface (issue #17).

This is the first Babbly EUD prototype: a smartphone-friendly web view over the
existing `SituationSnapshot`, driven entirely through the canonical operator
intent runtime. It is a presentation/input surface, not a second command
system:

- reads go through the canonical `situation.report` intent;
- the only write it accepts is a presentation change (`attention.set`) plus the
  read intents, all on the same `OperatorIntentRuntime` used by voice;
- it never executes registered operations or arbitrary shell strings. The
  controlled write/approval path is deferred to #18.

It depends only on `babbly.core` and the Python standard library, so it runs
without the offline voice/ASR stack.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple

from babbly.core.operator_intent import OperatorIntent, SourceModality
from babbly.core.operator_runtime import OperatorIntentRuntime
from babbly.core.situation import SituationSnapshot
from babbly.core.surface import build_situation_view


# Surfaces may request reads and presentation changes only. Operation execution
# and any external write remain outside this prototype (see #18).
ALLOWED_WEB_INTENTS = {
    "situation.report",
    "recommendation.explain",
    "attention.status",
    "attention.set",
}


class SituationWebApp:
    """Framework-neutral request handling for the Situation surface.

    The dispatch logic is a pure function of (method, path, body) so it can be
    tested without opening a socket. ``make_server`` wires it to the standard
    library HTTP server.
    """

    def __init__(self, runtime: Optional[OperatorIntentRuntime] = None) -> None:
        self.runtime = runtime or OperatorIntentRuntime()

    # -- view model -----------------------------------------------------------

    def current_view(self) -> Dict[str, Any]:
        """Collect the situation through the canonical read intent and render it."""
        result = self.runtime.submit(
            OperatorIntent(intent_id="situation.report", source_modality=SourceModality.WEB)
        )
        snapshot = SituationSnapshot.from_dict(result.payload.get("snapshot", {}))
        return build_situation_view(
            snapshot,
            self.runtime.attention.state,
            pending_confirmation=self._pending_confirmation(),
        )

    def _pending_confirmation(self) -> Optional[Dict[str, Any]]:
        pending = self.runtime.context.pending_intent
        if pending is None:
            return None
        return {
            "operation": pending.parameters.get("operation"),
            "confirmation_id": self.runtime.context.pending_confirmation_id,
            "target_ref": pending.target_ref,
        }

    # -- dispatch -------------------------------------------------------------

    def handle(self, method: str, path: str, body: bytes = b"") -> Tuple[int, str, bytes]:
        route = path.split("?", 1)[0].rstrip("/") or "/"

        if method == "GET" and route == "/":
            return 200, "text/html; charset=utf-8", INDEX_HTML.encode("utf-8")

        if method == "GET" and route == "/api/situation":
            return self._json(200, self.current_view())

        if method == "POST" and route == "/api/intent":
            return self._handle_intent(body)

        return self._json(404, {"error": "not_found", "path": route})

    def _handle_intent(self, body: bytes) -> Tuple[int, str, bytes]:
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
            if not isinstance(payload, dict):
                raise ValueError("intent body must be an object")
        except (ValueError, UnicodeDecodeError) as exc:
            return self._json(400, {"error": "invalid_json", "detail": str(exc)})

        intent_id = payload.get("intent_id")
        if intent_id not in ALLOWED_WEB_INTENTS:
            # Fail closed: the web surface cannot invoke anything outside the
            # read/presentation allowlist.
            return self._json(
                400,
                {"error": "intent_not_allowed", "intent_id": intent_id, "allowed": sorted(ALLOWED_WEB_INTENTS)},
            )

        parameters = payload.get("parameters")
        intent = OperatorIntent(
            intent_id=intent_id,
            source_modality=SourceModality.WEB,
            parameters=parameters if isinstance(parameters, dict) else {},
            target_ref=payload.get("target_ref"),
            context_ref=payload.get("context_ref"),
        )
        result = self.runtime.submit(intent)
        status = 200 if result.status in {"ok", "confirmation_required"} else 400
        return self._json(status, {"result": result.to_dict(), "view": self.current_view()})

    @staticmethod
    def _json(status: int, data: Dict[str, Any]) -> Tuple[int, str, bytes]:
        return status, "application/json; charset=utf-8", json.dumps(data, ensure_ascii=False).encode("utf-8")


def make_server(app: SituationWebApp, host: str = "127.0.0.1", port: int = 8787) -> ThreadingHTTPServer:
    """Bind a threading HTTP server that delegates to ``app.handle``."""

    class _Handler(BaseHTTPRequestHandler):
        def _dispatch(self, method: str) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            status, content_type, payload = app.handle(method, self.path, body)
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802 - stdlib naming
            self._dispatch("GET")

        def do_POST(self) -> None:  # noqa: N802 - stdlib naming
            self._dispatch("POST")

        def log_message(self, *_args) -> None:  # silence default stderr logging
            return

    return ThreadingHTTPServer((host, port), _Handler)


def serve(host: str = "127.0.0.1", port: int = 8787, runtime: Optional[OperatorIntentRuntime] = None) -> None:
    """Run the Situation surface until interrupted (local prototype; binds loopback)."""
    app = SituationWebApp(runtime)
    server = make_server(app, host, port)
    print(f"Babbly Situation surface on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


INDEX_HTML = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Babbly Situation</title>
<style>
  :root { color-scheme: light dark; --gap: 12px; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, sans-serif; line-height: 1.5;
         padding: env(safe-area-inset-top) 14px calc(env(safe-area-inset-bottom) + 14px); }
  h1 { font-size: 1.05rem; margin: 14px 0 8px; }
  .status { font-size: 1.6rem; font-weight: 700; margin: 4px 0 2px; overflow-wrap: anywhere; }
  .muted { opacity: .7; font-size: .85rem; }
  .card { border: 1px solid rgba(128,128,128,.35); border-radius: 12px;
          padding: 12px; margin: var(--gap) 0; }
  .obs { display: flex; gap: 8px; padding: 6px 0; border-top: 1px solid rgba(128,128,128,.2); overflow-wrap: anywhere; }
  .obs:first-child { border-top: 0; }
  .sev { font-size: .7rem; padding: 2px 8px; border-radius: 999px; align-self: center;
         white-space: nowrap; background: rgba(128,128,128,.25); }
  .sev.warning, .sev.critical { background: #c0392b; color: #fff; }
  .sev.caution { background: #e67e22; color: #fff; }
  .modes { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
  button { font: inherit; padding: 14px 8px; border-radius: 12px; border: 1px solid rgba(128,128,128,.4);
           background: rgba(128,128,128,.12); min-height: 52px; cursor: pointer; }
  button.active { background: #2d6cdf; color: #fff; border-color: #2d6cdf; }
  .degraded { color: #c0392b; font-weight: 600; }
  .err { color: #c0392b; }
</style>
</head>
<body>
  <h1>Babbly Situation <span id="conn" class="muted"></span></h1>
  <div class="card">
    <div class="muted" id="mode">—</div>
    <div class="status" id="status">…</div>
    <div class="muted" id="systems"></div>
    <div class="degraded" id="degraded" hidden>⚠ 一部アダプタが取得エラー</div>
  </div>
  <div class="card">
    <div class="muted">観測</div>
    <div id="observations"></div>
  </div>
  <div class="card" id="recCard" hidden>
    <div class="muted">推奨</div>
    <div id="recommendation"></div>
  </div>
  <div class="card" id="pendingCard" hidden>
    <div class="muted">確認待ち</div>
    <div id="pending"></div>
  </div>
  <div class="modes">
    <button data-mode="normal">NORMAL</button>
    <button data-mode="heads_up">HEADS-UP</button>
    <button data-mode="critical">CRITICAL</button>
  </div>
<script>
const $ = (id) => document.getElementById(id);
function render(v) {
  $("conn").textContent = "";
  $("mode").textContent = "モード: " + v.attention_state.toUpperCase();
  $("status").textContent = v.status_label;
  const s = v.systems_summary;
  $("systems").textContent = s.total ? ("系統 正常 " + s.online + "/" + s.total) : "";
  $("degraded").hidden = !v.degraded;
  const obs = $("observations"); obs.innerHTML = "";
  if (!v.observations.length) { obs.innerHTML = '<div class="muted">なし</div>'; }
  for (const o of v.observations) {
    const row = document.createElement("div"); row.className = "obs";
    const sev = document.createElement("span"); sev.className = "sev " + o.severity; sev.textContent = o.severity;
    const txt = document.createElement("span"); txt.textContent = o.summary;
    row.append(sev, txt); obs.append(row);
  }
  const rc = $("recCard");
  if (v.recommendation) {
    rc.hidden = false;
    let t = v.recommendation.action;
    if (v.recommendation.reason) t += " — " + v.recommendation.reason;
    if (v.recommendation.advisory_only) t += "（助言）";
    $("recommendation").textContent = t;
  } else { rc.hidden = true; }
  const pc = $("pendingCard");
  if (v.pending_confirmation) {
    pc.hidden = false;
    $("pending").textContent = (v.pending_confirmation.operation || "?") + " → 承認/却下";
  } else { pc.hidden = true; }
  for (const b of document.querySelectorAll("button[data-mode]"))
    b.classList.toggle("active", b.dataset.mode === v.attention_state);
}
async function refresh() {
  try { const r = await fetch("/api/situation"); render(await r.json()); }
  catch (e) { $("conn").innerHTML = '<span class="err">接続エラー</span>'; }
}
async function setMode(mode) {
  try {
    const r = await fetch("/api/intent", { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intent_id: "attention.set", parameters: { state: mode } }) });
    const data = await r.json(); if (data.view) render(data.view);
  } catch (e) { $("conn").innerHTML = '<span class="err">接続エラー</span>'; }
}
for (const b of document.querySelectorAll("button[data-mode]"))
  b.addEventListener("click", () => setMode(b.dataset.mode));
refresh(); setInterval(refresh, 3000);
</script>
</body>
</html>
"""
