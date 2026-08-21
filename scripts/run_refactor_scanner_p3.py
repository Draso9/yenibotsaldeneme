"""Robust runner for the temporary Scanner P3 refactor helper.

The original helper accepts both LF and CRLF markers. For markers without a
newline, LF and CRLF variants are identical; deduplicate them before matching.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("refactor_scanner_p3.py")
spec = importlib.util.spec_from_file_location("refactor_scanner_p3", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("Scanner P3 refactor helper could not be loaded")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _variants(text: str):
    yield text, "\n"
    crlf = text.replace("\n", "\r\n")
    if crlf != text:
        yield crlf, "\r\n"


module._variants = _variants
module.main()
