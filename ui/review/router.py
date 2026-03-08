from __future__ import annotations

from typing import Any


class ReviewRouter:
    def __init__(self, bus) -> None:
        self.bus = bus
        self._requests_by_id: dict[str, dict[str, Any]] = {}

        self.bus.subscribe("action.requested", self._on_action_requested)
        self.bus.subscribe("ui.review.approve_request", self._on_approve_request)
        self.bus.subscribe("ui.review.deny_request", self._on_deny_request)

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

    def _on_approve_request(self, evt) -> None:
        request_id = str(evt.data.get("request_id", "")).strip()
        if not request_id:
            return

        original = self._requests_by_id.get(request_id)
        if not original:
            return

        request = original.get("request", {})
        target = original.get("target", {})

        # notify system the review decision happened
        self.bus.publish(
            "action.review.resolved",
            request_id=request_id,
            decision="approved",
        )

        # re-run the original command
        self.bus.publish(
            "action.requested",
            request=request,
            target=target,
            source="review_override",
        )

    def _on_deny_request(self, evt) -> None:
        request_id = str(evt.data.get("request_id", "")).strip()
        if not request_id:
            return

        original = self._requests_by_id.get(request_id, {})
        self.bus.publish(
            "action.review.resolved",
            request_id=request_id,
            decision="denied",
            request=original.get("request", {}),
            target=original.get("target", {}),
        )