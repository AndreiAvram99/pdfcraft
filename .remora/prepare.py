#!/usr/bin/env python3
"""Apply the owner's personal Craft icon and interface changes before packaging."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
slug = root.name.lower()
if not slug.endswith('craft'):
    raise SystemExit(f'Unexpected Craft checkout name: {slug}')
title = slug[:-5].capitalize() + 'Craft'
subprocess.run([sys.executable, str(root / '.remora' / 'overlay.py'), title, str(root)], check=True)
