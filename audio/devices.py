from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import sounddevice as sd


@dataclass(frozen=True)
class AudioDevice:
    index: int
    name: str
    hostapi: str
    max_input_channels: int
    max_output_channels: int
    default_samplerate: float


def _hostapi_name(hostapi_index: int) -> str:
    try:
        info = sd.query_hostapis(hostapi_index)
        return str(info.get("name", f"hostapi_{hostapi_index}"))
    except Exception:
        return f"hostapi_{hostapi_index}"


def list_devices() -> list[AudioDevice]:
    devices: list[AudioDevice] = []
    raw = sd.query_devices()  # list-like
    for i, d in enumerate(raw):
        hostapi = _hostapi_name(int(d.get("hostapi", -1)))
        devices.append(
            AudioDevice(
                index=i,
                name=str(d.get("name", "")),
                hostapi=hostapi,
                max_input_channels=int(d.get("max_input_channels", 0)),
                max_output_channels=int(d.get("max_output_channels", 0)),
                default_samplerate=float(d.get("default_samplerate", 48000.0)),
            )
        )
    return devices


def input_devices(devices: Iterable[AudioDevice] | None = None) -> list[AudioDevice]:
    devices = list(devices or list_devices())
    return [d for d in devices if d.max_input_channels > 0]


def output_devices(devices: Iterable[AudioDevice] | None = None) -> list[AudioDevice]:
    devices = list(devices or list_devices())
    return [d for d in devices if d.max_output_channels > 0]


def find_by_name_contains(
    needle: str, *, want_input: bool | None = None, want_output: bool | None = None
) -> list[AudioDevice]:
    needle_l = needle.lower().strip()
    out: list[AudioDevice] = []
    for d in list_devices():
        if needle_l in d.name.lower():
            if want_input is True and d.max_input_channels <= 0:
                continue
            if want_output is True and d.max_output_channels <= 0:
                continue
            out.append(d)
    return out


def get_default_devices() -> dict[str, Any]:
    """
    Returns indices for sounddevice defaults (may be None).
    """
    try:
        default_in, default_out = sd.default.device  # type: ignore[misc]
    except Exception:
        default_in, default_out = None, None
    return {"input_index": default_in, "output_index": default_out}
