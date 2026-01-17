"""
Application/Use-Case layer

Der DashboardService berechnet KPIs und nutzt dafür nur Domain-Objekte.
Er erzeugt einen DashboardState und bildet ein ViewModel für die ConsoleDashboardView.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from .domain import Studiengang, Pruefungsstatus


@dataclass(slots=True)
class KritischerEintrag:
    """
    Ein Eintrag für die Rubrik "kritisch".
    Grund ist z.B. überfällig oder bald fällig.
    """
    modul_code: str
    titel: str
    status_text: str
    pruefungsdatum: Optional[date]
    ist_ueberfaellig: bool


@dataclass(slots=True)
class DashboardState:
    """
    Datenobjekt für die View.
    """
    # Allgemeine Informationen
    studiengang_name: str
    studienmodell_text: str
    regelstudienzeit_monate: int
    start_datum: date
    aktuelles_semester: int
    gesamt_semester: int
    gesamt_ects: int
    ziel_note: float = 2.5

    # Fortschritt
    fortschritt_prozent: float = 0.0
    erreichte_ects: int = 0
    soll_ects: int = 0
    abweichung: int = 0

    # Noten
    durchschnittsnote: Optional[float] = None
    anzahl_module_ueber_zielnote: int = 0

    # Prüfungen
    anzahl_offen: int = 0
    anzahl_ueberfaellig: int = 0
    kritische_eintraege: List[KritischerEintrag] = field(default_factory=list)

    # Tabelle Semester
    semester_zeilen: List[dict] = field(default_factory=list)


class DashboardService:
    """
    Service für die Dashboard-Logik.
    Er liest Daten aus der Domain, berechnet KPIs und baut wieder ein ViewModel.
    """

    def erzeuge_dashboard_state(self, stg: Studiengang, heute: date) -> DashboardState:
        """
        Baut den kompletten DashboardState.
        - Basisdaten setzen
        - Fortschritt berechnen
        - Noten berechnen
        - Prüfungen zählen
        - Kritische Einträge erzeugen
        - Semester-Tabelle erstellen
        """
        # Basisdaten aus dem Studiengang
        state = DashboardState(
            studiengang_name=stg.name,
            studienmodell_text=f"{stg.studienmodell.value}, {stg.regelstudienzeit_monate} Monate",
            regelstudienzeit_monate=stg.regelstudienzeit_monate,
            start_datum=stg.start_datum,
            aktuelles_semester=stg.aktuelles_semester_nummer(),
            gesamt_semester=len(stg.semester),
            gesamt_ects=stg.gesamt_ects,
        )

        # Fortschritt
        state.erreichte_ects = stg.erreichte_ects()
        state.fortschritt_prozent = stg.berechne_fortschritt()
        state.soll_ects = stg.berechne_soll_ects(heute)
        state.abweichung = stg.berechne_abweichung_zum_soll(heute)

        # Noten
        state.durchschnittsnote = stg.berechne_durchschnittsnote()
        state.anzahl_module_ueber_zielnote = stg.anzahl_module_ueber_zielnote(state.ziel_note)

        # Anzahl der Prüfungen
        prueungs_info = self._berechne_pruefungs_kpis(stg, heute)
        state.anzahl_offen = prueungs_info['offen']
        state.anzahl_ueberfaellig = prueungs_info['ueberfaellig']

        # Kritische Einträge
        # Begrenzung auf 10 für bessere Übersicht
        state.kritische_eintraege = self.ermittle_kritische_eintraege(stg, heute)[:10]

        # Semester-Tabelle
        state.semester_zeilen = self._erzeuge_semester_zeilen(stg)

        return state

    def _berechne_pruefungs_kpis(self, stg: Studiengang, heute: date) -> dict:
        """
        Zählt Prüfungen über alle Module.
        - offen: Prüfungen ohne Note
        - ueberfaellig: Teilmenge der offenen Prüfungen
        """
        offene = 0
        ueberfaellig = 0

        for m in stg.alle_module():
            for p in m.pruefungen:
                # Nur ohne Note
                if p.note is None:
                    status = p.berechne_status(heute)
                    if status == Pruefungsstatus.ueberfaellig:
                        ueberfaellig += 1
                        offene += 1
                    elif status in (Pruefungsstatus.geplant, Pruefungsstatus.angemeldet):
                        offene += 1

        return {
            'offen': offene,
            'ueberfaellig': ueberfaellig
        }

    def _erzeuge_semester_zeilen(self, stg: Studiengang) -> List[dict]:
        """
        Baut Zeilen für die Semesterübersicht.
        """
        zeilen = []

        for s in stg.semester:
            ist = s.berechne_erreichte_ects()
            soll = s.geplante_ects

            # Status-Text ableiten
            if ist >= soll:
                status_text = "über Plan" if ist > soll else "im Plan"
            else:
                diff = soll - ist
                status_text = f"unter Plan (-{diff} ECTS)"

            zeilen.append({
                "nummer": s.nummer,
                "soll": soll,
                "ist": ist,
                "status": status_text
            })

        return zeilen

    def ermittle_kritische_eintraege(self, stg: Studiengang, heute: date) -> List[KritischerEintrag]:
        """
        Erzeugt eine Liste kritischer Einträge.
        - Modul ist nicht bestanden
        - und es gibt eine relevante nächste Prüfung
        Reihenfolge:
        1) Überfällig
        2) Anstehend mit Datum
        3) Geplant ohne Datum
        """
        eintraege: List[KritischerEintrag] = []

        for m in stg.alle_module():
            # Bestandene Module ignorieren
            if m.ist_bestanden():
                continue

            # Nächste Prüfung holen
            p = m.naechste_pruefung(heute)
            if p is None:
                continue

            p_status = p.berechne_status(heute)
            ist_ueberfaellig = p_status == Pruefungsstatus.ueberfaellig

            # Text für die Anzeige bauen
            if ist_ueberfaellig:
                datum_str = p.pruefungsdatum.strftime('%d.%m.%Y') if p.pruefungsdatum else '-'
                status_text = f"Prüfung überfällig (geplant: {datum_str})"
            elif p_status == Pruefungsstatus.angemeldet:
                datum_str = p.pruefungsdatum.strftime('%d.%m.%Y') if p.pruefungsdatum else '-'
                if p.pruefungsdatum:
                    tage = (p.pruefungsdatum - heute).days
                    if tage == 0:
                        status_text = f"Prüfung HEUTE: {datum_str}"
                    elif tage == 1:
                        status_text = f"Prüfung MORGEN: {datum_str}"
                    else:
                        status_text = f"Prüfung in {tage} Tagen: {datum_str}"
                else:
                    status_text = f"Prüfung anstehend: {datum_str}"
            else:
                datum_str = p.pruefungsdatum.strftime('%d.%m.%Y') if p.pruefungsdatum else '-'
                status_text = f"Prüfung geplant: {datum_str}"

            eintraege.append(KritischerEintrag(
                modul_code=m.modul_code,
                titel=m.titel,
                status_text=status_text,
                pruefungsdatum=p.pruefungsdatum,
                ist_ueberfaellig=ist_ueberfaellig,
            ))

        # Sortierung nach Priorität
        def sort_key(e: KritischerEintrag):
            """
            Schlüssel:
            - Überfällig zuerst
            - dann nach Datum
            - ohne Datum ganz ans Ende
            """
            if e.pruefungsdatum is None:
                return (2, date.max)
            elif e.ist_ueberfaellig:
                return (0, e.pruefungsdatum)
            else:
                return (1, e.pruefungsdatum)

        eintraege.sort(key=sort_key)

        return eintraege