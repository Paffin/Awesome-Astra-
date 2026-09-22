#!/usr/bin/env python3
"""Compatibility entrypoint; installed skill owns the implementation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/astra-code/scripts"))
from check_integration import check, main

if __name__ == "__main__":
    raise SystemExit(main())
