from __future__ import annotations

from typing import Any

from core.observability.logger import get_logger


class ReviewRouter:
    def __init__(self, bus, executor) -> None:
        self.bus = bus
        self.executor = executor
        self.log = get_logger("JARED")
        self._requests_by_id: dict[str, dict[str, Any]] = {}

        self.bus.subscribe("action.requested", self._on_action_requested)
        self.bus.subscribe("ui.review.approve_request", self._on_approve_request)
        self.bus.subscribe("ui.review.deny_request", self._on_deny_request)
        self.bus.subscribe("ui.review.retry_request", self._on_retry_request)

    def _on_action_requested(self, evt) -> None:
        request = evt.data.get("request", {}) or {}
        target = evt.data.get("target", {}) or {}

        if not isinstance(request, dict):
            return

        request_id = str(request.get("request_id", "")).strip()
        if not request_id:
            return

        self._requests_by_id[request_id] = {
            "request": request,
            "target": target if isinstance(target, dict) else {},
        }

    def _publish_resolution(self, *, request_id: str, decision: str) -> dict[str, Any]:
        original = self._requests_by_id.get(request_id, {})
        request = original.get("request", {})
        target = original.get("target", {})

        self.bus.publish(
            "action.review.resolved",
            request_id=request_id,
            decision=decision,
            request=request,
            target=target,
        )

        return original

    def _execute_stored_request(self, request_id: str) -> bool:
        original = self._requests_by_id.get(request_id)
        if not original:
            self.log.warning(f"[review] missing stored request for request_id={request_id}")
            return False

        request = original.get("request", {})
        target = original.get("target", {})

        if not isinstance(request, dict) or not request:
            self.log.warning(f"[review] invalid stored request for request_id={request_id}")
            return False

        if not isinstance(target, dict):
            self.log.warning(f"[review] invalid stored target for request_id={request_id}")
            return False

        self.executor.execute(
            request_payload=request,
            target_payload=target,
        )
        return True

    def _on_approve_request(self, evt) -> None:
        request_id = str(evt.data.get("request_id", "")).strip()
        if not request_id:
            return

        original = self._requests_by_id.get(request_id)
        if not original:
            return

        self._publish_resolution(request_id=request_id, decision="approved")
        executed = self._execute_stored_request(request_id)
        if executed:
            self._requests_by_id.pop(request_id, None)

    def _on_deny_request(self, evt) -> None:
        request_id = str(evt.data.get("request_id", "")).strip()
        if not request_id:
            return

        self._publish_resolution(request_id=request_id, decision="denied")
        self._requests_by_id.pop(request_id, None)

    def _on_retry_request(self, evt) -> None:
        request_id = str(evt.data.get("request_id", "")).strip()
        if not request_id:
            return

        original = self._requests_by_id.get(request_id)
        if not original:
            return

        self._publish_resolution(request_id=request_id, decision="retried")
        self._execute_stored_request(request_id)