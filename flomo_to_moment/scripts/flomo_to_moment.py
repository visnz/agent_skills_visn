#!/usr/bin/env python3
"""Deprecated path. Implementation is maintained under blog_setup; defaults to preview."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    target = Path(__file__).resolve().parents[2] / 'blog_setup/scripts/flomo_to_moment.py'
    runpy.run_path(str(target), run_name='__main__')
