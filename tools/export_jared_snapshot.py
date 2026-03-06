from __future__ import annotations

import os
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SNAPSHOT_NAME = f"jared_snapshot_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
OUT_DIR = ROOT / "snapshot_exports" / SNAPSHOT_NAME
ZIP_PATH = OUT_DIR / "repo.zip"
STRUCTURE_PATH = OUT_DIR / "structure.txt"

# Directories to exclude anywhere in the tree
EXCLUDE_DIRS = {
    ".git",
    ".venv",
    ".venv-tts",
    "tts_venv",          # in case this is the actual folder name instead
    "__pycache__",
    "third_party",
    "tflite_runtime",
    "voices",            # data/voices
    "tts_sidecar_out",   # data/tts_sidecar_out
    "snapshot_exports",  # do not zip previous exports
}

# Specific root-level files to exclude
EXCLUDE_ROOT_FILES = {
    ".gitignore",
    ".env.example",
    "line_count.txt",
    "structure.txt",
}

# Specific files to exclude anywhere
EXCLUDE_FILES = {
    "system.log",
}

# File extensions to include in the zip
INCLUDE_EXTENSIONS = {
    ".py",
    ".json",
    ".toml",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".db",
}

def should_skip_dir(path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in path.parts)

def should_skip_file(path: Path) -> bool:
    if path.name in EXCLUDE_FILES:
        return True

    rel_parts = path.relative_to(ROOT).parts
    if len(rel_parts) == 1 and path.name in EXCLUDE_ROOT_FILES:
        return True

    return False

def allowed_file(path: Path) -> bool:
    return path.suffix.lower() in INCLUDE_EXTENSIONS

def generate_structure() -> None:
    with STRUCTURE_PATH.open("w", encoding="utf-8") as f:
        f.write("JARED PROJECT STRUCTURE\n")
        f.write("=" * 80 + "\n\n")

        for current_root, dirs, files in os.walk(ROOT):
            root_path = Path(current_root)

            # prune excluded directories in-place so os.walk does not descend into them
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            if should_skip_dir(root_path):
                continue

            rel_root = root_path.relative_to(ROOT)
            depth = len(rel_root.parts)
            display_root = "." if str(rel_root) == "." else str(rel_root).replace("\\", "/")
            indent = "    " * depth
            f.write(f"{indent}{display_root}/\n")

            visible_files = []
            for name in sorted(files):
                file_path = root_path / name
                if should_skip_file(file_path):
                    continue
                if not allowed_file(file_path):
                    continue
                visible_files.append(name)

            for name in visible_files:
                f.write(f"{indent}    {name}\n")

def create_zip() -> None:
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for current_root, dirs, files in os.walk(ROOT):
            root_path = Path(current_root)

            # prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            if should_skip_dir(root_path):
                continue

            for name in files:
                file_path = root_path / name

                if should_skip_file(file_path):
                    continue
                if not allowed_file(file_path):
                    continue

                arcname = file_path.relative_to(ROOT)
                zf.write(file_path, arcname)

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Creating snapshot in: {OUT_DIR}")
    print("Generating structure.txt ...")
    generate_structure()

    print("Creating repo.zip ...")
    create_zip()

    print("\nDone.")
    print(f"ZIP:       {ZIP_PATH}")
    print(f"Structure: {STRUCTURE_PATH}")

if __name__ == "__main__":
    main()