#!/usr/bin/env python3
"""Compile FIW Python sources in memory without creating bytecode."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    compiled = []
    for directory_name in ("scripts", "tests"):
        directory = root / directory_name
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.py")):
            relative = path.relative_to(root).as_posix()
            compile(path.read_text(encoding="utf-8"), relative, "exec")
            compiled.append(relative)
    print(f"Python syntax: PASS ({len(compiled)} files; no bytecode written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
