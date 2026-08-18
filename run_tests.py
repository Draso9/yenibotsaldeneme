#!/usr/bin/env python
from __future__ import annotations

import subprocess
import sys


def run(args):
    print("+", " ".join(args))
    return subprocess.call(args)


def main():
    pure = [
        sys.executable, "-m", "pytest",
        "tests/test_bist_and_symbols.py",
        "tests/test_decision_engine.py",
        "tests/test_static_integrity.py",
        "-q",
    ]
    rc = run(pure)
    if rc:
        return rc

    smoke = [
        sys.executable, "-m", "pytest",
        "tests/test_apptest_smoke.py",
        "-q",
    ]
    return run(smoke)


if __name__ == "__main__":
    raise SystemExit(main())
