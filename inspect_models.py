from pathlib import Path
import tensorflow as tf
import openwakeword
import importlib.metadata as md

def pkg_version(name: str) -> str:
    try:
        return md.version(name)
    except Exception:
        return "unknown"

print("python:", __import__("sys").version.split()[0])
print("openwakeword version:", pkg_version("openwakeword"))
print("tensorflow version:", pkg_version("tensorflow"))
print("openwakeword module path:", Path(openwakeword.__file__).resolve())
print()

wake_model = Path(r"C:\Coding\jared\third_party\openwakeword_models\hey_jared_float32.tflite")
oww_base = Path(openwakeword.__file__).resolve().parent
melspec_model = oww_base / "resources" / "models" / "melspectrogram.tflite"
embedding_model = oww_base / "resources" / "models" / "embedding_model.tflite"

models = [
    ("WAKE MODEL", wake_model),
    ("MELSPEC MODEL", melspec_model),
    ("EMBEDDING MODEL", embedding_model),
]

for name, path in models:
    print("=" * 60)
    print(name)
    print("Path:", path)

    if not path.exists():
        print("❌ FILE NOT FOUND")
        print()
        continue

    interpreter = tf.lite.Interpreter(model_path=str(path))
    interpreter.allocate_tensors()

    print("\nINPUTS:")
    for inp in interpreter.get_input_details():
        print(" ", inp["name"], "shape:", inp["shape"], "dtype:", inp["dtype"])

    print("\nOUTPUTS:")
    for out in interpreter.get_output_details():
        print(" ", out["name"], "shape:", out["shape"], "dtype:", out["dtype"])

    print()
