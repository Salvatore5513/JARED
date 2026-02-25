import inspect
import numpy as np
from openwakeword.model import Model

m = Model(wakeword_models=[])
pre = m.preprocessor

print("Preprocessor type:", type(pre))
print("\nPublic attributes/methods:")
names = [n for n in dir(pre) if not n.startswith("_")]
for n in names:
    obj = getattr(pre, n)
    if callable(obj):
        try:
            sig = str(inspect.signature(obj))
        except Exception:
            sig = "(signature unavailable)"
        print(f"  {n}{sig}")
    else:
        # show basic attrs that might matter
        if n in {"inference_framework", "melspec_model", "embedding_model"}:
            print(f"  {n} = {obj}")

# Build a 16kHz dummy audio chunk (80ms and 1s)
pcm80 = (np.random.randn(1280) * 200).astype(np.int16)      # 80ms @ 16k
pcm1s = (np.random.randn(16000) * 200).astype(np.int16)     # 1s @ 16k

candidates = [
    "extract_embedding",
    "get_embedding",
    "get_embeddings",
    "embedding",
    "process",
    "predict",
    "__call__",
]

def show_result(tag, out):
    arr = np.asarray(out)
    print(f"    {tag}: type={type(out)} shape={getattr(arr,'shape',None)} dtype={getattr(arr,'dtype',None)}")

print("\n\nTRY CALLS (80ms int16):")
for name in candidates:
    fn = getattr(pre, name, None)
    if fn is None:
        continue
    try:
        out = fn(pcm80)
        show_result(name, out)
    except Exception as e:
        print(f"    {name}: ERROR -> {e!r}")

print("\nTRY CALLS (1s int16):")
for name in candidates:
    fn = getattr(pre, name, None)
    if fn is None:
        continue
    try:
        out = fn(pcm1s)
        show_result(name, out)
    except Exception as e:
        print(f"    {name}: ERROR -> {e!r}")
