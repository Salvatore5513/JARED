from app.bootstrap import build_runtime
from ui.app import launch_ui


def main():
    runtime = build_runtime()
    runtime.start()
    raise SystemExit(launch_ui(runtime))


if __name__ == "__main__":
    main()