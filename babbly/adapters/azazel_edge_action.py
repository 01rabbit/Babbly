"""Write-capable Azazel-Edge action executor for the controlled request path.

This is the counterpart to the read-only status transport. It implements the
`ActionExecutor` contract (#18) by translating a Babbly `ActionRequest` into an
action *proposal* envelope and POSTing it to Azazel-Edge. Babbly never decides
the action itself: Azazel-Edge retains final, deterministic decision authority
and may reject an already human-approved request.

The executor is disabled by default (see `create_action_executor`) so standalone
and read-only deployments gain no write path. There is no shell string anywhere
in this contract.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Mapping, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from babbly.core.request import ActionExecutor, ActionRequest, ExecutionResult


ACTION_PROPOSAL_SCHEMA = "babbly.action-proposal.v1"

_APPROVED = {"approved", "accepted", "allow", "allowed", "ok", "success"}
_REJECTED = {"rejected", "denied", "deny", "blocked", "refused"}


class AzazelEdgeActionError(RuntimeError):
    """Raised when the Edge action surface cannot be reached or understood."""


def translate_action_request(request: ActionRequest) -> dict:
    """Translate an ActionRequest into the Edge action-proposal envelope."""
    return {
        "schema_version": ACTION_PROPOSAL_SCHEMA,
        "action": request.action,
        "parameters": dict(request.parameters),
        "target": request.target_ref,
        "context": request.context_ref,
        "risk_class": request.risk_class.value,
        "requested_by_modality": request.requested_by_modality,
        "correlation_id": request.correlation_id,
        "audit_id": request.audit_id,
    }


def interpret_edge_decision(payload: Mapping[str, Any]) -> ExecutionResult:
    """Map an Edge decision response to an ExecutionResult.

    Edge is authoritative. An unrecognized decision is treated as *not*
    approved so the request fails closed rather than being assumed successful.
    """
    decision = str(payload.get("decision") or payload.get("status") or "").strip().lower()
    detail = str(payload.get("detail") or payload.get("reason") or "")
    external_ref = payload.get("external_ref") or payload.get("id")
    external_ref = str(external_ref) if external_ref is not None else None
    if decision in _APPROVED:
        return ExecutionResult(ok=True, detail=detail, external_ref=external_ref)
    rejected = decision in _REJECTED or decision != ""
    return ExecutionResult(ok=False, detail=detail or f"edge decision: {decision or 'unknown'}",
                           external_ref=external_ref, rejected_by_executor=rejected)


class AzazelEdgeActionExecutor(ActionExecutor):
    """POST an approved ActionRequest to Azazel-Edge and interpret its decision."""

    def __init__(
        self,
        base_url: str,
        *,
        token: Optional[str] = None,
        path: str = "/api/action",
        timeout_sec: float = 3.0,
        max_response_bytes: int = 256 * 1024,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        base = str(base_url or "").strip().rstrip("/")
        parsed = urlparse(base)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("AZAZEL_EDGE_URL must be an http(s) URL")
        self.url = base + "/" + str(path or "/api/action").lstrip("/")
        self.token = str(token or "").strip()
        self.timeout_sec = max(0.1, float(timeout_sec))
        self.max_response_bytes = max(1024, int(max_response_bytes))
        self.opener = opener

    def execute_action(self, request: ActionRequest) -> ExecutionResult:
        body = json.dumps(translate_action_request(request)).encode("utf-8")
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.token:
            headers["X-AZAZEL-TOKEN"] = self.token
        http_request = Request(self.url, data=body, headers=headers, method="POST")

        response = None
        try:
            response = self.opener(http_request, timeout=self.timeout_sec)
            status = response.getcode() if hasattr(response, "getcode") else getattr(response, "status", 200)
            if status is not None and int(status) >= 400:
                return ExecutionResult(ok=False, detail=f"edge HTTP {status}", rejected_by_executor=False)
            raw = response.read(self.max_response_bytes + 1)
        except Exception as exc:  # transport failure is not an authoritative denial
            return ExecutionResult(ok=False, detail=f"edge action request failed: {exc}", rejected_by_executor=False)
        finally:
            if response is not None:
                close = getattr(response, "close", None)
                if callable(close):
                    close()

        if len(raw) > self.max_response_bytes:
            return ExecutionResult(ok=False, detail="edge action response exceeded size limit", rejected_by_executor=False)
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return ExecutionResult(ok=False, detail="edge returned invalid JSON", rejected_by_executor=False)
        if not isinstance(decoded, Mapping):
            return ExecutionResult(ok=False, detail="edge action payload is not an object", rejected_by_executor=False)
        return interpret_edge_decision(decoded)
