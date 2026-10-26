#!/usr/bin/env python3
"""Apply personal icons, interface changes and Ray display branding."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
slug = root.name.lower()
if not slug.endswith('craft'):
    raise SystemExit(f'Unexpected Craft checkout name: {slug}')
title = slug[:-5].capitalize() + 'Craft'
subprocess.run([sys.executable, str(root / '.remora' / 'overlay.py'), title, str(root)], check=True)
ray_title = 'PhotRay' if slug == 'photocraft' else title[:-5] + 'Ray'
subprocess.run([sys.executable, str(root / '.remora' / 'ray_branding.py'), title, ray_title, str(root)], check=True)
