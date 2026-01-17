"""
Controller layer

Der DashboardController steuert die App. Er verbindet Repository, Service und View.

Aufgaben:
- Studiengang laden
- KPIs über DashboardService berechnen
- Ausgabe über ConsoleDashboardView
- Menü anzeigen und Eingaben verarbeiten
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional, List

from .domain import Studiengang, Modul, Pruefungsleistung, Pruefungsart
from .persistence import StudiengangRepository
from .service import DashboardService
from .view import ConsoleDashboardView


class DashboardController:
    """
    Hauptcontroller für das Dashboard.

    Aufgaben:
    - Menü-Schleife
    - Aufrufe an Service und View
    - Speichern von Änderungen
    """

    def __init__(
        self,
        repo: StudiengangRepository,
        service: DashboardService,
        view: ConsoleDashboardView
    ) -> None:
        """
        Erstellt den Controller.

        - repo: Laden/Speichern
        - service: KPI-Logik
        - view: Ein-/Ausgabe
        """
        self._repo = repo
        self._service = service
        self._view = view
        self._stg: Optional[Studiengang] = None
        self._heute: date = date.today()
        self._aenderungen_seit_speicherung: bool = False

    def starte_app(self) -> None:
        """
        Startet die Anwendung.

        - Daten laden
        - optional Stichtag setzen
        - Menü-Schleife starten
        """
        try:
            self._stg = self._repo.lade()
        except Exception as e:
            self._view.show_message(f"FEHLER beim Laden der Daten: {e}")
            return

        # Optionaler Stichtag.
        # Leere Eingabe bedeutet: heute.
        eingabe = self._view.prompt("Stichtag (TT.MM.JJJJ, leer = heute): ").strip()
        if eingabe:
            try:
                self._heute = datetime.strptime(eingabe, "%d.%m.%Y").date()
            except ValueError:
                self._view.show_message("Ungültiges Datum. Verwende 'heute'.")
                self._heute = date.today()

        self._view.show_message(f"Studien-Dashboard gestartet ({self._stg.name}).\n")

        # Endlosschleife bis Abbruch.
        while True:
            self._view.render_menue()
            choice = self._view.prompt("Auswahl: ").strip()

            if choice == "1":
                self.zeige_dashboard()
            elif choice == "2":
                self.liste_module()
            elif choice == "3":
                self.zeige_offene_pruefungen()
            elif choice == "4":
                self.trage_note_ein()
            elif choice == "5":
                self.plane_pruefungstermin()
            elif choice == "6":
                self.speichere()
            elif choice == "0":
                self._beenden()
                break
            else:
                self._view.show_message("Ungültige Auswahl.")

    def zeige_dashboard(self) -> None:
        """Zeigt die KPI-Übersicht."""
        assert self._stg is not None
        try:
            state = self._service.erzeuge_dashboard_state(self._stg, self._heute)
            self._view.render(state)
        except Exception as e:
            self._view.show_message(f"Fehler bei Dashboard-Anzeige: {e}")

    def liste_module(self) -> None:
        """Zeigt alle Module mit Status und Note."""
        assert self._stg is not None
        self._view.show_message("\n=== ALLE MODULE ===")

        # Module sammeln.
        # Danach nach Semester sortieren.
        module_mit_semester = []
        for sem in self._stg.semester:
            for m in sem.module:
                module_mit_semester.append((sem.nummer, m))

        module_mit_semester.sort(key=lambda x: (x[0], x[1].empfohlenes_semester))

        # Ausgabe pro Modul.
        for sem_nr, m in module_mit_semester:
            status = m.berechne_status(self._heute).value
            note = m.ermittle_note()
            note_txt = "-" if note is None else f"{note:.1f}".replace(".", ",")
            self._view.show_message(
                f"  Sem {sem_nr} | {m.modul_code:20} | {m.titel:40} | "
                f"ECTS {m.ects:2d} | Status: {status:15} | Note: {note_txt}"
            )

        self._view.show_message("")

    def zeige_offene_pruefungen(self) -> None:
        """Zeigt Prüfungen ohne Note."""
        assert self._stg is not None
        self._view.show_message("\n=== OFFENE PRÜFUNGEN ===")
        found = False

        # Alle Module und alle Prüfungen prüfen.
        for m in self._stg.alle_module():
            for p in m.pruefungen:
                if p.note is not None:
                    continue  # Nur offene Prüfungen.

                status = p.berechne_status(self._heute).value
                datum = p.pruefungsdatum.strftime("%d.%m.%Y") if p.pruefungsdatum else "-"
                self._view.show_message(
                    f"  {m.modul_code:20} | {m.titel:40} | "
                    f"Versuch {p.versuch} | {datum:10} | {status}"
                )
                found = True

        if not found:
            self._view.show_message("Keine offenen Prüfungen.")
        self._view.show_message("")

    def speichere(self) -> None:
        """
        Speichert den Studiengang.
        """
        assert self._stg is not None
        try:
            self._repo.speichere(self._stg)
            self._aenderungen_seit_speicherung = False
            self._view.show_message("Daten erfolgreich gespeichert.")
        except Exception as e:
            self._view.show_message(f"FEHLER beim Speichern: {e}")

    def trage_note_ein(self) -> None:
        """
        Setzt oder löscht eine Note.
        Bei doppelten Modul-Codes wird gefragt.
        Nach erfolgreicher Änderung wird automatisch gespeichert, damit der Nutzer das nicht vergisst.
        """
        assert self._stg is not None

        modul_code = self._view.prompt("Modulcode: ").strip()
        if not modul_code:
            return

        # Alle passenden Module finden.
        module = self._find_all_module(modul_code)
        if not module:
            self._view.show_message("Modul nicht gefunden.")
            return

        # Wenn mehrere Treffer: Auswahl.
        modul = self._waehle_modul(module) if len(module) > 1 else module[0]
        if modul is None:
            return

        versuch = self._prompt_versuch()
        if versuch is None:
            return

        pruefung = self._find_or_create_pruefung(modul, versuch)
        if pruefung is None:
            return

        # Note lesen.
        # Leere Eingabe bedeutet: löschen.
        raw = self._view.prompt(f"Note (1,0..5,0) — leer = löschen (aktuell: {pruefung.note or '-'}): ").strip()
        if raw == "":
            pruefung.note = None
            self._view.show_message("Note gelöscht (None).")
            self._aenderungen_seit_speicherung = True
            self._auto_save()
            return

        # Zahl umwandeln.
        try:
            note = float(raw.replace(",", "."))
        except ValueError:
            self._view.show_message("Ungültige Note (muss Zahl sein).")
            return

        # Bereich prüfen.
        if not (1.0 <= note <= 5.0):
            self._view.show_message("Note muss im Bereich 1,0..5,0 liegen.")
            return

        pruefung.note = note
        bestanden = "bestanden" if note < 4.0 else "nicht bestanden"
        self._view.show_message(f"Note gesetzt/aktualisiert: {note:.1f} ({bestanden})")

        self._aenderungen_seit_speicherung = True
        self._auto_save()

    def plane_pruefungstermin(self) -> None:
        """
        Setzt oder löscht ein Prüfungsdatum.
        Bei doppelten Modul-Codes wird wie oben gefragt.
        Nach erfolgreicher Änderung wird automatisch gespeichert, damit der Nutzer das nicht vergisst.
        """
        assert self._stg is not None

        modul_code = self._view.prompt("Modulcode: ").strip()
        if not modul_code:
            return

        # Alle passenden Module finden.
        module = self._find_all_module(modul_code)
        if not module:
            self._view.show_message("Modul nicht gefunden.")
            return

        # Wenn mehrere Treffer: Auswahl.
        modul = self._waehle_modul(module) if len(module) > 1 else module[0]
        if modul is None:
            return

        versuch = self._prompt_versuch()
        if versuch is None:
            return

        pruefung = self._find_or_create_pruefung(modul, versuch)
        if pruefung is None:
            return

        # Datum lesen.
        # Leere Eingabe bedeutet: löschen.
        aktuell = pruefung.pruefungsdatum.strftime("%d.%m.%Y") if pruefung.pruefungsdatum else "-"
        raw = self._view.prompt(
            f"Prüfungsdatum (TT.MM.JJJJ oder YYYY-MM-DD) — leer = löschen (aktuell: {aktuell}): "
        ).strip()

        if raw == "":
            pruefung.pruefungsdatum = None
            self._view.show_message("Prüfungsdatum gelöscht (None).")
            self._aenderungen_seit_speicherung = True
            self._auto_save()
            return

        parsed = self._parse_date(raw)
        if parsed is None:
            self._view.show_message("Ungültiges Datum (verwende TT.MM.JJJJ oder YYYY-MM-DD).")
            return

        pruefung.pruefungsdatum = parsed
        self._view.show_message(f"Prüfungsdatum gesetzt/aktualisiert: {parsed.strftime('%d.%m.%Y')}")

        self._aenderungen_seit_speicherung = True
        self._auto_save()

    def _find_all_module(self, modul_code: str) -> List[Modul]:
        """
        Findet alle Module zu einem Code.
        - Ein Code kann mehrfach vorkommen, wenn der User fehlerhafte Daten liefert.
        - Deshalb wird eine Liste zurückgegeben.
        """
        needle = modul_code.strip()
        gefunden = []
        for m in self._stg.alle_module():
            if m.modul_code.strip() == needle:
                gefunden.append(m)
        return gefunden

    def _waehle_modul(self, module: List[Modul]) -> Optional[Modul]:
        """
        Auswahl bei mehreren Treffern.
        - Modul oder None bei Abbruch.
        """
        self._view.show_message(f"\nMehrere Module mit Code '{module[0].modul_code}' gefunden:")
        for i, m in enumerate(module, 1):
            self._view.show_message(f"  {i}) {m.titel} (Semester {m.empfohlenes_semester}, {m.ects} ECTS)")

        raw = self._view.prompt(f"Wähle Modul (1-{len(module)}, 0 = Abbruch): ").strip()
        try:
            wahl = int(raw)
            if wahl == 0:
                return None
            if 1 <= wahl <= len(module):
                return module[wahl - 1]
            else:
                self._view.show_message("Ungültige Auswahl.")
                return None
        except ValueError:
            self._view.show_message("Ungültige Eingabe.")
            return None

    def _prompt_versuch(self) -> Optional[int]:
        """
        Fragt den Versuch ab.

        Nach Prüfungsrichtlinie sind 1 bis 3 Versuche erlaubt.
        """
        raw = self._view.prompt("Versuch (1..3): ").strip()
        try:
            v = int(raw)
        except ValueError:
            self._view.show_message("Ungültige Versuchsnummer (muss Zahl sein).")
            return None

        if v not in (1, 2, 3):
            self._view.show_message("Versuch muss 1, 2 oder 3 sein.")
            return None

        return v

    def _find_or_create_pruefung(self, modul: Modul, versuch: int) -> Optional[Pruefungsleistung]:
        """
        Sucht eine Prüfung.
        Legt sie an, wenn sie fehlt.
        - Maximal 3 Versuche.
        - Neue Prüfung nutzt die Art von Versuch 1.
        """
        # Existierende Prüfung suchen.
        for p in modul.pruefungen:
            if p.versuch == versuch:
                return p

        # Limit prüfen.
        if len(modul.pruefungen) >= 3:
            self._view.show_message("Maximal 3 Prüfungsversuche pro Modul erlaubt.")
            return None

        # Neue Prüfung anlegen.
        basis = sorted(modul.pruefungen, key=lambda x: x.versuch)[0]
        new_id = f"{modul.modul_code}-V{versuch}"
        neu = Pruefungsleistung(
            pruefung_id=new_id,
            art=basis.art if isinstance(basis.art, Pruefungsart) else Pruefungsart.Sonstiges,
            pruefungsdatum=None,
            versuch=versuch,
            note=None,
        )
        modul.pruefungen.append(neu)
        modul.pruefungen.sort(key=lambda x: x.versuch)

        self._view.show_message(f"Hinweis: Neuer Versuch {versuch} für {modul.modul_code} wurde angelegt.")

        return neu

    def _parse_date(self, raw: str) -> Optional[date]:
        """
        Liest ein Datum aus Text.
        Unterstützte Formate:
        - TT.MM.JJJJ
        - YYYY-MM-DD
        """
        s = raw.strip()
        for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        return None

    def _auto_save(self) -> None:
        """
        Speichert automatisch.
        """
        if self._aenderungen_seit_speicherung:
            try:
                self._repo.speichere(self._stg)
                self._aenderungen_seit_speicherung = False
            except Exception:
                # Auto-Save fehlgeschlagen.
                # Keine Ausgabe, kein Abbruch.
                pass

    def _beenden(self) -> None:
        """
        Beendet das Programm.
        Bei Änderungen wird gefragt, ob gespeichert werden soll.
        """
        if self._aenderungen_seit_speicherung:
            antwort = self._view.prompt(
                "Es gibt ungespeicherte Änderungen! Jetzt speichern? (j/n): "
            ).strip().lower()
            if antwort in ('j', 'y', 'ja', 'yes'):
                self.speichere()

        self._view.show_message("Programm wird beendet.")