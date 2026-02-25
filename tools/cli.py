from __future__ import annotations

import argparse
import sys
import time

from core.config.manager import ConfigManager
from audio.devices import list_devices, input_devices, output_devices, find_by_name_contains, get_default_devices
from audio.capture import start_level_meter, LevelReading
from audio.playback import PlaybackConfig, MusicPlayback
from audio.ducking import DuckingParams
from audio.ducking_test import DuckingTestConfig, DuckingTestRunner
from audio.calibration.wizard import run_basic_calibration



def _print_devices() -> None:
    devs = list_devices()
    print("\n=== INPUT DEVICES ===")
    for d in input_devices(devs):
        print(f"[{d.index:>3}] {d.name} | {d.hostapi} | in={d.max_input_channels} | sr={d.default_samplerate:g}")

    print("\n=== OUTPUT DEVICES ===")
    for d in output_devices(devs):
        print(f"[{d.index:>3}] {d.name} | {d.hostapi} | out={d.max_output_channels} | sr={d.default_samplerate:g}")

    defaults = get_default_devices()
    print(f"\nDefaults: input={defaults['input_index']} output={defaults['output_index']}\n")


def _bar(db: float, *, min_db: float = -60.0, max_db: float = 0.0, width: int = 40) -> str:
    db = max(min_db, min(max_db, db))
    t = (db - min_db) / (max_db - min_db)
    n = int(t * width)
    return ("#" * n).ljust(width, ".")


def cmd_audio_list(_: argparse.Namespace) -> int:
    _print_devices()
    return 0


def cmd_audio_select(args: argparse.Namespace) -> int:
    cm = ConfigManager()
    cfg = cm.load()

    def _validate(cfg: dict) -> int:
        devs = {d.index: d for d in list_devices()}

        in_idx = cfg.get("audio.input_device_index")
        out_idx = cfg.get("audio.output_device_index")

        if in_idx is not None:
            d = devs.get(int(in_idx))
            if not d or d.max_input_channels <= 0:
                print(f"ERROR: device {in_idx} is not a valid input device.")
                return 2

        if out_idx is not None:
            d = devs.get(int(out_idx))
            if not d or d.max_output_channels <= 0:
                print(f"ERROR: device {out_idx} is not a valid output device.")
                return 2

        return 0

    if args.find:
        matches = find_by_name_contains(args.find, want_input=True)
        if not matches:
            print(f"No input devices matched: {args.find!r}")
            return 2
        if len(matches) > 1 and args.pick is None:
            print("Multiple matches found. Re-run with --pick <index> from below:")
            for d in matches:
                print(f"[{d.index}] {d.name}")
            return 2

        idx = args.pick if args.pick is not None else matches[0].index
        cfg["audio.input_device_index"] = idx

        rc = _validate(cfg)
        if rc != 0:
            return rc

        cm.save(cfg)
        print(f"Saved audio.input_device_index = {idx}")
        return 0

    if args.input is not None:
        cfg["audio.input_device_index"] = args.input
    if args.output is not None:
        cfg["audio.output_device_index"] = args.output

    rc = _validate(cfg)
    if rc != 0:
        return rc

    cm.save(cfg)
    print("Saved:")
    print(f"  audio.input_device_index  = {cfg.get('audio.input_device_index')}")
    print(f"  audio.output_device_index = {cfg.get('audio.output_device_index')}")
    return 0



def cmd_audio_meter(args: argparse.Namespace) -> int:
    cm = ConfigManager()
    cfg = cm.load()
    dev_idx = cfg.get("audio.input_device_index", None)
    if args.input is not None:
        dev_idx = args.input

    samplerate = int(cfg.get("audio.samplerate", 48000))
    if args.samplerate:
        samplerate = int(args.samplerate)

    # UMA-8 usually exposes multiple channels; for now we meter mono (channel count can be >1)
    channels = int(args.channels or cfg.get("audio.input_channels", 1))

    last_print = 0.0

    def on_level(reading: LevelReading) -> None:
        nonlocal last_print
        now = time.time()
        if now - last_print < 0.05:  # 20 fps max
            return
        last_print = now

        rms_bar = _bar(reading.rms_db)
        peak_bar = _bar(reading.peak_db)
        sys.stdout.write(
            f"\rIN[{dev_idx}] RMS {reading.rms_db:7.1f} dB [{rms_bar}] "
            f"PEAK {reading.peak_db:7.1f} dB [{peak_bar}]"
        )
        sys.stdout.flush()

    try:
        stream = start_level_meter(
            device_index=dev_idx,
            samplerate=samplerate,
            channels=channels,
            blocksize=1024,
            on_level=on_level,
        )
    except Exception as e:
        print(f"Failed to open input device {dev_idx}: {e}")
        return 2

    print("\n(Press Ctrl+C to stop)\n")
    try:
        while True:
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass
        print("\nStopped.\n")

    return 0


def cmd_audio_calibrate(args: argparse.Namespace) -> int:
    cm = ConfigManager()
    cfg = cm.load()

    in_idx = cfg.get("audio.input_device_index", None)
    samplerate = int(cfg.get("audio.samplerate", 48000))

    res = run_basic_calibration(in_idx, samplerate=samplerate)

    # Save results + recommended ducking values
    cfg["audio.calibration.noise_rms_db"] = res.noise_rms_db
    cfg["audio.calibration.speech_rms_db"] = res.speech_rms_db
    cfg["audio.ducking_threshold_db"] = res.recommended_threshold_db
    cfg["audio.ducking_hysteresis_db"] = res.recommended_hysteresis_db

    cm.save(cfg)

    print("\nSaved calibration + updated ducking params:")
    print(f"  noise_rms_db             = {res.noise_rms_db:.1f}")
    print(f"  speech_rms_db            = {res.speech_rms_db:.1f}")
    print(f"  audio.ducking_threshold_db   = {res.recommended_threshold_db:.1f}")
    print(f"  audio.ducking_hysteresis_db  = {res.recommended_hysteresis_db:.1f}\n")

    return 0

def cmd_audio_music(args: argparse.Namespace) -> int:
    cm = ConfigManager()
    cfg = cm.load()

    in_idx = cfg.get("audio.input_device_index", None)
    out_idx = cfg.get("audio.output_device_index", None)
    samplerate = int(cfg.get("audio.samplerate", 48000))

    params = DuckingParams(
        strength=float(cfg.get("audio.ducking_strength", 0.40)),
        threshold_db=float(cfg.get("audio.ducking_threshold_db", -29.0)),
        hysteresis_db=float(cfg.get("audio.ducking_hysteresis_db", 5.0)),
        attack_ms=float(cfg.get("audio.ducking_attack_ms", 120.0)),
        release_ms=float(cfg.get("audio.ducking_release_ms", 2555.0)),
    )

    music_volume = float(cfg.get("audio.music_volume", 1.0))

    player = MusicPlayback(
        PlaybackConfig(
            input_device_index=in_idx,
            output_device_index=out_idx,
            samplerate=samplerate,
            out_channels=2,
            music_volume=music_volume,
        ),
        duck_params=params,
        wav_path=args.wav,
    )

    print("\nMusic playback running (WAV + ducking). Ctrl+C to stop.\n")
    try:
        player.start()
        while True:
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        player.stop()
        print("\nStopped.\n")

    return 0

def cmd_audio_set(args: argparse.Namespace) -> int:
    cm = ConfigManager()
    cfg = cm.load()

    if args.music_volume is not None:
        cfg["audio.music_volume"] = float(args.music_volume)

    if args.tts_volume is not None:
        cfg["audio.tts_volume"] = float(args.tts_volume)

    if args.duck_strength is not None:
        cfg["audio.ducking_strength"] = float(args.duck_strength)

    cm.save(cfg)
    print("Saved:")
    print(f"  audio.music_volume      = {cfg.get('audio.music_volume')}")
    print(f"  audio.tts_volume        = {cfg.get('audio.tts_volume')}")
    print(f"  audio.ducking_strength  = {cfg.get('audio.ducking_strength')}")
    return 0



def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jared")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("audio-list", help="List audio input/output devices")
    a.set_defaults(fn=cmd_audio_list)

    #Audio Select
    s = sub.add_parser("audio-select", help="Persist selected audio devices")
    s.add_argument("--input", type=int, help="Input device index")
    s.add_argument("--output", type=int, help="Output device index")
    s.add_argument("--find", type=str, help="Find input device by name contains (e.g., UMA-8)")
    s.add_argument("--pick", type=int, help="If multiple matches, pick exact device index")
    s.set_defaults(fn=cmd_audio_select)

    #Audio Meter
    m = sub.add_parser("audio-meter", help="Live mic level meter")
    m.add_argument("--input", type=int, help="Override input device index (does not save)")
    m.add_argument("--samplerate", type=int, help="Override samplerate (default 48000)")
    m.add_argument("--channels", type=int, help="Number of input channels to open (default 1)")
    m.set_defaults(fn=cmd_audio_meter)

    #Audio Calibration
    c = sub.add_parser("audio-calibrate", help="Measure noise/speech and recommend ducking thresholds")
    c.set_defaults(fn=cmd_audio_calibrate)

    #Audio Music
    mu = sub.add_parser("audio-music", help="Play a WAV file and duck on mic RMS")
    mu.add_argument("--wav", required=True, help="Path to a PCM WAV file (recommended 48000 Hz)")
    mu.set_defaults(fn=cmd_audio_music)

    #Audio Set
    s2 = sub.add_parser("audio-set", help="Set audio knobs (no UI yet)")
    s2.add_argument("--music-volume", type=float)
    s2.add_argument("--tts-volume", type=float)
    s2.add_argument("--duck-strength", type=float)
    s2.set_defaults(fn=cmd_audio_set)

    #Audio Status (Milestone 1 snapshot)
    st = sub.add_parser("audio-status", help="Show current audio config")
    st.set_defaults(fn=cmd_audio_status)




#           """TEST SECTIONS"""
    d = sub.add_parser("audio-duck-test", help="Play continuous audio and duck on mic RMS")
    d.set_defaults(fn=cmd_audio_duck_test)


    return p

def cmd_audio_status(args: argparse.Namespace) -> int:
    cm = ConfigManager()
    cfg = cm.load()

    keys = [
        "audio.input_device_index",
        "audio.output_device_index",
        "audio.samplerate",
        "audio.music_volume",
        "audio.tts_volume",
        "audio.ducking_strength",
        "audio.ducking_threshold_db",
        "audio.ducking_hysteresis_db",
        "audio.ducking_attack_ms",
        "audio.ducking_release_ms",
        "audio.calibration.noise_rms_db",
        "audio.calibration.speech_rms_db",
    ]

    print("\n=== AUDIO STATUS ===")
    for k in keys:
        if k in cfg:
            print(f"{k:32} = {cfg[k]}")
    print()
    return 0



#           """TESTS SECTION"""

def cmd_audio_duck_test(args: argparse.Namespace) -> int:
    cm = ConfigManager()
    cfg = cm.load()

    in_idx = cfg.get("audio.input_device_index", None)
    out_idx = cfg.get("audio.output_device_index", None)
    samplerate = int(cfg.get("audio.samplerate", 48000))

    params = DuckingParams(
        strength=float(cfg.get("audio.ducking_strength", 0.60)),
        threshold_db=float(cfg.get("audio.ducking_threshold_db", -35.0)),
        hysteresis_db=float(cfg.get("audio.ducking_hysteresis_db", 6.0)),
        attack_ms=float(cfg.get("audio.ducking_attack_ms", 120.0)),
        release_ms=float(cfg.get("audio.ducking_release_ms", 350.0)),
    )

    runner = DuckingTestRunner(
        DuckingTestConfig(
            input_device_index=in_idx,
            output_device_index=out_idx,
            samplerate=samplerate,
        ),
        params,
    )

    print("\nDucking test running. Talk normally to trigger ducking. Ctrl+C to stop.\n")
    runner.start()
    try:
        while True:
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        runner.stop()
        print("\nStopped.\n")

    return 0



def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
