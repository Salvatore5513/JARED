from __future__ import annotations

from devices.registry.models import Room, DeviceTemplate
from devices.registry.store import RegistryStore


def main() -> None:
    db_path = "data/jared.db"
    store = RegistryStore(db_path)

    # 1) Rooms (reuse by name; create if missing)
    garage = store.get_room_by_name("Garage")
    if garage is None:
        garage = Room(room_id="garage", name="Garage")
    store.upsert_room(garage)

    bench = store.get_room_by_name("Bench")
    if bench is None:
        bench = Room(room_id="bench", name="Bench")
    store.upsert_room(bench)

    # 2) Template (use a STABLE template_id so upsert works)
    tpl = store.get_template_by_name("mqtt_light_basic")
    if tpl is None:
        tpl = DeviceTemplate(
            template_id="tpl.mqtt_light_basic",
            name="mqtt_light_basic",
            driver_kind="mqtt",
            capabilities={
                "power": True,
                "level": False,
                "verify": False,
            },
        )
        store.upsert_template(tpl)

    # 3) Devices (use STABLE device_id, and keep names unique)
    store.upsert_device(
        device_id="dev.garage.lights",
        name="Garage Lights",
        room_id=garage.room_id,
        template_id=tpl.template_id,
        driver_config={
            "broker_host": "127.0.0.1",
            "broker_port": 1883,
            "topic_cmd": "jared/garage/lights/set",
            "payload_on": "ON",
            "payload_off": "OFF",
        },
        enabled=True,
    )

    store.upsert_device(
        device_id="dev.bench.lights",
        name="Bench Lights",
        room_id=bench.room_id,
        template_id=tpl.template_id,
        driver_config={
            "broker_host": "127.0.0.1",
            "broker_port": 1883,
            "topic_cmd": "jared/bench/lights/set",
            "payload_on": "ON",
            "payload_off": "OFF",
        },
        enabled=True,
    )

    print("Seed complete.")
    print("Rooms:", garage, bench)
    print("Template:", tpl)
    print("Devices seeded: Garage Lights, Bench Lights")


if __name__ == "__main__":
    main()