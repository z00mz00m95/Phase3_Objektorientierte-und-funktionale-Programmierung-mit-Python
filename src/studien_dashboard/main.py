"""
Entry point für den Studien-Dashboard Prototyp.
Dieses Modul startet die Anwendung.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .persistence import JsonStudiengangRepository
from .service import DashboardService
from .view import ConsoleDashboardView
from .controller import DashboardController


def main() -> None:
    """
    Startpunkt der Anwendung.
    Ablauf:
    - Datenpfad bestimmen
    - Datei prüfen
    - Komponenten erstellen
    - Controller starten
    """
    try:
        # Repo-Root bestimmen.
        # Erwartet: data/studiengang.json im Repo-Root.
        repo_root = Path(__file__).resolve().parents[2]  # .../src/studien_dashboard/main.py
        data_path = repo_root / "data" / "studiengang.json"

        # Prüfen, ob die Datei existiert.
        if not data_path.exists():
            print(f"FEHLER: Daten JSON nicht gefunden: {data_path}")
            print("Bitte stelle sicher, dass 'data/studiengang.json' existiert.")
            sys.exit(1)

        # Bausteine der App erstellen.
        repo = JsonStudiengangRepository(str(data_path))
        service = DashboardService()
        view = ConsoleDashboardView()
        controller = DashboardController(repo, service, view)

        # App starten.
        controller.starte_app()

    except KeyboardInterrupt:
        # Sauberer Abbruch per Strg+C.
        print("\nAnwendung beendet.")
        sys.exit(0)

    except Exception as e:
        # Unerwarteter Fehler.
        print(f"\nFEHLER: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()