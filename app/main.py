from __future__ import annotations

import sys
import traceback

from core.observability.logger import get_logger
from app.bootstrap import build_runtime


def main() -> None:
    log = get_logger("JARED")
    try:
        runtime = build_runtime()
        runtime.run_forever()
    except KeyboardInterrupt:
        log.info("Shutdown requested")
        sys.exit(0)
    except Exception:
        log.critical("Fatal startup error")
        log.critical(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()