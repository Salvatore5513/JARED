from __future__ import annotations

from typing import Optional, Dict, Any
import time
import os
import paho.mqtt.client as mqtt

from devices.drivers.base import Driver, DriverResult
from devices.registry.models import DeviceRecord
from devices.execution.action_request import ActionRequest


class MQTTDriver(Driver):
    kind = "mqtt"

    def supports(self, capability: str) -> bool:
        # MQTT is a transport; capability is validated at template level.
        return True

    def execute(self, device: DeviceRecord, action: ActionRequest) -> DriverResult:
        cfg = device.driver_config or {}

        host = cfg.get("broker_host") or os.getenv("JARED_MQTT_HOST", "127.0.0.1")
        port = int(cfg.get("broker_port") or os.getenv("JARED_MQTT_PORT", "1883"))
        topic = cfg.get("topic_cmd")

        if not topic:
            return DriverResult(ok=False, driver_code="ERR_BAD_CONFIG", details="Missing 'topic_cmd' in driver_config")

        payload = self._build_payload(cfg, action)
        if payload is None:
            return DriverResult(ok=False, driver_code="ERR_UNSUPPORTED", details="Unsupported action/slots for MQTTDriver")

        try:
            client = mqtt.Client()
            # Optional auth
            username = cfg.get("username")
            password = cfg.get("password")
            if username:
                client.username_pw_set(str(username), str(password) if password is not None else None)

            client.connect(host, port, keepalive=10)
            # publish
            info = client.publish(topic, payload=payload, qos=int(cfg.get("qos", 0)), retain=bool(cfg.get("retain", False)))
            info.wait_for_publish(timeout=5)
            client.disconnect()

            return DriverResult(
                ok=True,
                driver_code="OK",
                details=f"Published to {topic}",
                raw={"topic": topic, "payload": payload, "host": host, "port": port},
            )
        except Exception as e:
            return DriverResult(ok=False, driver_code="ERR_UNREACHABLE", details=f"MQTT error: {e}", raw={"host": host, "port": port})

    def read_state(self, device: DeviceRecord) -> Optional[Dict[str, Any]]:
        # Milestone 3: no state readback unless you add topic_state later
        return None

    @staticmethod
    def _build_payload(cfg: Dict[str, Any], action: ActionRequest) -> Optional[str]:
        slots = action.slots or {}

        # On/off
        if action.intent_name in ("device.set_power", "device.toggle"):
            # prefer explicit state
            state = slots.get("state") or slots.get("power") or slots.get("enabled")

            if isinstance(state, str):
                s = state.strip().lower()
                if s in ("on", "true", "1", "enable", "enabled"):
                    return str(cfg.get("payload_on", "ON"))
                if s in ("off", "false", "0", "disable", "disabled"):
                    return str(cfg.get("payload_off", "OFF"))

            if isinstance(state, bool):
                return str(cfg.get("payload_on", "ON")) if state else str(cfg.get("payload_off", "OFF"))

            if isinstance(state, (int, float)):
                return str(cfg.get("payload_on", "ON")) if state != 0 else str(cfg.get("payload_off", "OFF"))

            # toggle fallback: if no state provided, send "TOGGLE" if configured
            toggle_payload = cfg.get("payload_toggle")
            if toggle_payload is not None:
                return str(toggle_payload)

            return None

        # Dimming/level
        if action.intent_name == "device.set_level":
            level = slots.get("level")
            if level is None:
                return None
            return str(level)

        return None