import os

EXCLUDE = {".venv", "__pycache__", ".git"}

with open("structure.txt", "w", encoding="utf-8") as f:
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in EXCLUDE]
        level = root.count(os.sep)
        indent = "  " * level
        f.write(f"{indent}{root}\n")
        for file in files:
            f.write(f"{indent}  {file}\n")