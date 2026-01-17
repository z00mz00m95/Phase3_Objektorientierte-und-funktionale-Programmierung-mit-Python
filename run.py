"""
Startskript für das Studien-Dashboard.

Dieses Skript ermöglicht den Start mit:
    python run.py
    oder je nach instalaltion python3 run.py

Es fügt das src-Verzeichnis zum Python-Pfad hinzu.
So kann die Anwendung ohne Installation ausgeführt werden.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Stelle sicher, dass "src" im sys.path ist
repo_root = Path(__file__).resolve().parent
src_path = repo_root / "src"
sys.path.insert(0, str(src_path))

from studien_dashboard.main import main

if __name__ == "__main__":
    main()