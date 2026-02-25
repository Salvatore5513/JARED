from __future__ import annotations

# This is a shim so libraries that do:
#   import tflite_runtime.interpreter as tflite
# can work on Windows/Python builds where `tflite-runtime` wheels aren't available.

import tensorflow as tf


# Mirror the interface openwakeword expects: tflite.Interpreter(...)
Interpreter = tf.lite.Interpreter


def load_delegate(*args, **kwargs):
    # Delegates are optional; most libs won't need this on desktop CPU.
    # If something tries to use it, fail loudly with a clear message.
    raise NotImplementedError("TFLite delegates are not supported by this shim on this platform.")
