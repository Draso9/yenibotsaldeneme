#!/usr/bin/env python
from __future__ import annotations

import subprocess
import sys


def run(args):
    print("+", " ".join(args))
    return subprocess.call(args)


def main():
    return run([sys.executable, "-m", "pytest", "-q"])


if __name__ == "__main__":
    raise SystemExit(main())
