import uuid

from devices.registry.models import Room, DeviceTemplate
from devices.registry.store import RegistryStore


def main() -> None:
    db_path = "data/jared.db"  # use the same db path you plan to use for audit_log too
    store = RegistryStore(db_path)

    # 1) Room
    garage = Room(room_id=str(uuid.uuid4()), name="Garage")
    store.upsert_room(garage)

    # 2) Template (MQTT light)
    tpl = DeviceTemplate(
        template_id=str(uuid.uuid4()),
        name="mqtt_light_basic",
        driver_kind="mqtt",
        capabilities={
            "power": True,          # supports on/off
            "level": False,         # no dimming for now
            "verify": False,        # driver may not support readback yet
        },
    )
    store.upsert_template(tpl)

    # 3) Device (Garage Lights)
    store.upsert_device(
        device_id=str(uuid.uuid4()),
        name="Lights",
        room_id=garage.room_id,
        template_id=tpl.template_id,
        driver_config={
            # We’ll implement the MQTT driver later to use these keys.
            "broker_host": "127.0.0.1",
            "broker_port": 1883,
            "topic_cmd": "jared/garage/lights/set",
            "payload_on": "ON",
            "payload_off": "OFF",
        },
        enabled=True,
    )

    print("Seed complete.")
    print("Room:", garage)
    print("Template:", tpl)
    print("Try resolving: room='Garage', device='Lights'")


if __name__ == "__main__":
    main()