#!/usr/bin/env python3
"""双语构建编排器:en(根)→ zh(/zh)→ finalize(favicon/robots/sitemap)"""
import subprocess, sys
from pathlib import Path
HERE = Path(__file__).parent
for script in ("build_en.py", "build_zh.py", "finalize.py"):
    subprocess.run([sys.executable, str(HERE/script)], check=True, cwd=HERE)
