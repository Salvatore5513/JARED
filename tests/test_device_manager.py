from core.event_bus import EventBus
from core.security.audit_log import AuditLog
from core.security.rate_limits import RateLimiter
from core.security.policy_engine import PolicyEngine
from core.security.auth.auth_window import AuthWindow
from devices.execution.device_manager import DeviceManager
from devices.execution.action_request import ActionRequest
from devices.registry.store import RegistryStore
from devices.registry.models import DeviceTarget
from devices.drivers.registry import DriverRegistry
from devices.drivers.mqtt.driver import MQTTDriver

drivers = DriverRegistry()
drivers.register(MQTTDriver())

bus = EventBus()

def handler(evt):
    print("EVENT:", evt.topic, evt.data)

bus.subscribe("action.*", handler)

db_path = "data/jared.db"
registry = RegistryStore(db_path)
audit = AuditLog(db_path)

print("DRIVER mqtt:", drivers.get("mqtt"))

mgr = DeviceManager(
    event_bus=bus,
    registry=registry,
    drivers=drivers,  # <-- correct (registered)
    policy=PolicyEngine(),
    auth_window=AuthWindow(),
    rate_limiter=RateLimiter(),
    audit_log=audit,
)

req = ActionRequest(
    intent_name="device.set_power",
    slots={"state": "on"},
)

outcome = mgr.handle(req, target=DeviceTarget(room_name="Garage", device_name="Lights"))
print("OUTCOME:", outcome)