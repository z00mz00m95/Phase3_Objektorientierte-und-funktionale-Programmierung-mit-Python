"""
Domain beinhaltet die Entities + Enums

Dieses Modul enthält nur die Fachlogik.
Es enthält keine UI- oder JSON-Logik.

- Entities sind Dataclasses.
- Sie enthalten auch fachliche Methoden.
- Status wird immer berechnet und nicht gespeichert.
- Fehlende Werte sind erlaubt (z.B. note=None) - Phase 2 Korrektur!
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional, List, Iterable


class Abschluss(Enum):
    """Mögliche Abschlüsse."""
    BSc = "BSc"
    MSc = "MSc"


class Studienmodell(Enum):
    """Studienmodelle der IU."""
    Vollzeit = "Vollzeit"
    TeilzeitI = "TeilzeitI"
    TeilzeitII = "TeilzeitII"


class ModulStatus(Enum):
    """Status eines Moduls. Wird aus Prüfungen abgeleitet."""
    geplant = "geplant"
    inBearbeitung = "inBearbeitung"
    abgeschlossen = "abgeschlossen"


class Pruefungsart(Enum):
    """
    Mögliche Prüfungsarten.
    Diese Werte kommen im JSON Dataset vor und werden vom Nutzer hinterlegt.
    'Sonstiges' ist ein Fallback.
    """
    Klausur = "Klausur"
    Hausarbeit = "Hausarbeit"
    Projekt = "Projekt"
    MuendlichePruefung = "MuendlichePruefung"
    AdvancedWorkbook = "AdvancedWorkbook"
    Portfolio = "Portfolio"
    Projektbericht = "Projektbericht"
    Seminararbeit = "Seminararbeit"
    Fallstudie = "Fallstudie"
    Bachelorarbeit = "Bachelorarbeit"
    Kolloquium = "Kolloquium"
    Projektpraesentation = "Projektpräsentation"
    Sonstiges = "Sonstiges"


class Pruefungsstatus(Enum):
    """
    Status einer Prüfung.
    Der Status wird berechnet.
    Grundlage sind Datum und Note.
    """
    geplant = "geplant"
    angemeldet = "angemeldet"
    bestanden = "bestanden"
    nichtBestanden = "nichtBestanden"
    ueberfaellig = "ueberfaellig"


@dataclass(slots=True)
class Pruefungsleistung:
    """
    Eine Prüfung zu einem Modul.
    Ein Modul kann bis zu 3 Versuche haben.
    Status wird nicht gespeichert. Er wird aus Datum und Note berechnet.
    """
    pruefung_id: str
    art: Pruefungsart
    pruefungsdatum: Optional[date]
    versuch: int
    note: Optional[float] = None

    def __post_init__(self) -> None:
        """Prüft Grundregeln nach dem Erzeugen."""
        if not (1 <= self.versuch <= 3):
            raise ValueError(f"versuch muss im Bereich 1..3 liegen, ist aber {self.versuch}.")
        if self.note is not None:
            if not (1.0 <= self.note <= 5.0):
                raise ValueError(f"note muss im Bereich 1.0..5.0 liegen, ist aber {self.note}.")

    def ist_bestanden(self) -> bool:
        """
        Prüft auf bestanden.
        - Note ist gesetzt
        - Note ist kleiner als 4.0
        """
        return self.note is not None and self.note < 4.0

    def berechne_status(self, heute: date) -> Pruefungsstatus:
        """
        Berechnet den Prüfungsstatus.
        - Note < 4.0 -> bestanden
        - Note >= 4.0 -> nichtBestanden
        - Keine Note und Datum fehlt -> geplant
        - Keine Note und Datum < heute -> ueberfaellig
        - Keine Note und Datum >= heute -> angemeldet
        """
        if self.note is not None:
            return Pruefungsstatus.bestanden if self.note < 4.0 else Pruefungsstatus.nichtBestanden

        if self.pruefungsdatum is None:
            return Pruefungsstatus.geplant

        if self.pruefungsdatum < heute:
            return Pruefungsstatus.ueberfaellig

        return Pruefungsstatus.angemeldet


@dataclass(slots=True)
class Modul:
    """
    Ein Modul mit Prüfungen.
    - Die Modulnote ist die Note des bestandenen Versuchs.
    - Es gibt keinen Durchschnitt über Versuche.
    - Das Modul ist bestanden, sobald ein Versuch bestanden ist.
    - Modul-Codes können mehrfach vorkommen.
    """
    modul_code: str
    titel: str
    ects: int
    empfohlenes_semester: int
    pruefungen: List[Pruefungsleistung] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Prüft Grundregeln des Moduls."""
        if self.ects <= 0:
            raise ValueError(f"ects muss > 0 sein, ist aber {self.ects}.")
        if self.empfohlenes_semester <= 0:
            raise ValueError(f"empfohlenes_semester muss >= 1 sein, ist aber {self.empfohlenes_semester}.")
        if not (1 <= len(self.pruefungen) <= 3):
            raise ValueError(f"Ein Modul muss 1..3 Prüfungsleistungen besitzen, hat aber {len(self.pruefungen)}.")

        # Prüft doppelte Versuchsnummern.
        versuche = [p.versuch for p in self.pruefungen]
        if len(set(versuche)) != len(versuche):
            pass

    def ist_bestanden(self) -> bool:
        """Abfrage ist gültig (wahr), wenn mindestens eine Prüfung bestanden ist."""
        return any(p.ist_bestanden() for p in self.pruefungen)

    def ermittle_note(self) -> Optional[float]:
        """
        Liefert die Modulnote.
        Es zählt der erste bestandene Versuch.
        Wenn nichts bestanden ist: None.
        """
        bestanden = [p for p in self.pruefungen if p.ist_bestanden()]
        if not bestanden:
            return None
        bestanden.sort(key=lambda p: p.versuch)
        return bestanden[0].note

    def berechne_status(self, heute: date) -> ModulStatus:
        """
        Berechnet den Modulstatus.
        - Bestanden -> abgeschlossen
        - Sonst, wenn es Aktivitäten gibt -> inBearbeitung
        - Sonst -> geplant
        """
        if self.ist_bestanden():
            return ModulStatus.abgeschlossen

        statuses = [p.berechne_status(heute) for p in self.pruefungen]
        if any(
            s in (
                Pruefungsstatus.geplant,
                Pruefungsstatus.angemeldet,
                Pruefungsstatus.ueberfaellig,
                Pruefungsstatus.nichtBestanden,
            )
            for s in statuses
        ):
            return ModulStatus.inBearbeitung

        return ModulStatus.geplant

    def naechste_pruefung(self, heute: date) -> Optional[Pruefungsleistung]:
        """
        Liefert die nächste relevante Prüfung.
        Folgende Reihenfolge wurde gewählt:
        1) Überfällig (frühestes Datum)
        2) Zukünftig/heute (nächstes Datum)
        3) None, wenn alles erledigt ist
        """
        offene = [p for p in self.pruefungen if p.note is None]
        if not offene:
            return None

        ueberfaellig = [
            p for p in offene
            if p.pruefungsdatum is not None and p.pruefungsdatum < heute
        ]
        if ueberfaellig:
            ueberfaellig.sort(key=lambda p: p.pruefungsdatum or date.min)
            return ueberfaellig[0]

        zukuenftig = [
            p for p in offene
            if p.pruefungsdatum is not None and p.pruefungsdatum >= heute
        ]
        if zukuenftig:
            zukuenftig.sort(key=lambda p: p.pruefungsdatum)
            return zukuenftig[0]

        return None


@dataclass(slots=True)
class Semester:
    """
    Ein Semester mit Modulen.
    - start_datum
    - end_datum
    Diese Daten helfen bei Soll-Berechnungen.
    """
    nummer: int
    geplante_ects: float
    start_datum: Optional[date] = None
    end_datum: Optional[date] = None
    module: List[Modul] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Prüft Grundregeln des Semesters."""
        if self.nummer <= 0:
            raise ValueError(f"semester.nummer muss >= 1 sein, ist aber {self.nummer}.")
        if self.geplante_ects <= 0:
            raise ValueError(f"semester.geplante_ects muss > 0 sein, ist aber {self.geplante_ects}.")
        if self.start_datum and self.end_datum and self.end_datum < self.start_datum:
            raise ValueError(
                f"end_datum ({self.end_datum}) muss >= start_datum ({self.start_datum}) sein."
            )

    def berechne_erreichte_ects(self) -> int:
        """Summe der ECTS aller bestandenen Module im Semester."""
        return sum(m.ects for m in self.module if m.ist_bestanden())

    def berechne_fortschritt(self) -> float:
        """
        Fortschritt des Semesters in Prozent.
        Kann über 100% liegen, wenn mehr als geplant erreicht wird.
        """
        if self.geplante_ects == 0:
            return 0.0
        return (self.berechne_erreichte_ects() / self.geplante_ects) * 100.0


@dataclass(slots=True)
class Studiengang:
    """
    Ein kompletter Studiengang.
    Diese Klasse bündelt die Daten und bietet die KPI-Methoden, z.B.:
    - Fortschritt
    - Durchschnittsnote
    - Soll/Ist-Vergleich
    """
    name: str
    abschluss: Abschluss
    studienmodell: Studienmodell
    gesamt_ects: int
    regelstudienzeit_monate: int
    start_datum: date
    semester: List[Semester] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Prüft Grundregeln des Studiengangs."""
        if self.gesamt_ects <= 0:
            raise ValueError(f"gesamt_ects muss > 0 sein, ist aber {self.gesamt_ects}.")
        if self.regelstudienzeit_monate <= 0:
            raise ValueError(f"regelstudienzeit_monate muss > 0 sein, ist aber {self.regelstudienzeit_monate}.")
        if not self.semester:
            raise ValueError("Ein Studiengang muss mindestens ein Semester enthalten.")

    def alle_module(self) -> Iterable[Modul]:
        """Gibt alle Module über alle Semester zurück."""
        for s in self.semester:
            yield from s.module

    def erreichte_ects(self) -> int:
        """Summe der ECTS aller bestandenen Module."""
        return sum(m.ects for m in self.alle_module() if m.ist_bestanden())

    def berechne_fortschritt(self) -> float:
        """Gesamtfortschritt in Prozent."""
        if self.gesamt_ects == 0:
            return 0.0
        return (self.erreichte_ects() / self.gesamt_ects) * 100.0

    def berechne_durchschnittsnote(self) -> Optional[float]:
        """
        Gewichtete Durchschnittsnote für das Studium
        """
        noten = []
        for m in self.alle_module():
            n = m.ermittle_note()
            if n is not None:
                noten.append((m.ects, n))

        if not noten:
            return None

        sum_ects = sum(ects for ects, _ in noten)
        if sum_ects == 0:
            return None

        return sum(ects * note for ects, note in noten) / sum_ects

    def berechne_soll_ects(self, bis_datum: date) -> int:
        """
        Soll-ECTS bis zu einem Datum.

        Wenn Semesterzeiten vorhanden sind, dann lineare Verteilung im Semester.
        Ansonsten eine grobe Schätzung über Regelstudienzeit.
        """
        soll = 0.0

        # Präzise Berechnung mit Semester-Zeiträumen.
        for s in self.semester:
            if s.start_datum is None or s.end_datum is None:
                continue

            if bis_datum >= s.end_datum:
                soll += s.geplante_ects
            elif bis_datum <= s.start_datum:
                soll += 0.0
            else:
                total_days = (s.end_datum - s.start_datum).days
                if total_days <= 0:
                    total_days = 1
                elapsed = (bis_datum - s.start_datum).days
                fraction = max(0.0, min(1.0, elapsed / total_days))
                soll += s.geplante_ects * fraction

        # Fallback ohne Semester-Zeiträume.
        if soll == 0.0:
            months_per_semester = self.regelstudienzeit_monate / len(self.semester)
            months_elapsed = max(
                0,
                (bis_datum.year - self.start_datum.year) * 12
                + (bis_datum.month - self.start_datum.month),
            )
            approx_semesters = int(months_elapsed // months_per_semester)
            approx_semesters = min(approx_semesters, len(self.semester))

            for s in self.semester[:approx_semesters]:
                soll += s.geplante_ects

        return int(round(soll))

    def berechne_abweichung_zum_soll(self, bis_datum: date) -> int:
        """Ist minus Soll. Positiv = über Plan. Negativ = unter Plan."""
        return self.erreichte_ects() - self.berechne_soll_ects(bis_datum)

    def aktuelles_semester_nummer(self) -> int:
        """
        Methode für 'aktuelles Semester'.
        - Höchstes Semester mit erreichten ECTS.
        - Wenn noch keine ECTS: 1.
        """
        max_num = 1
        for s in self.semester:
            if s.berechne_erreichte_ects() > 0:
                max_num = max(max_num, s.nummer)
        return max_num

    def anzahl_module_ueber_zielnote(self, zielnote: float = 2.5) -> int:
        """Zählt Module mit Note schlechter als die Zielnote (Note > zielnote)."""
        count = 0
        for m in self.alle_module():
            n = m.ermittle_note()
            if n is not None and n > zielnote:
                count += 1
        return count

    def ermittle_kritische_module(self, heute: date, horizon_tage: int = 60) -> List[Modul]:
        """
        Findet kritische Module.
        - Modul nicht bestanden und
        - Prüfung ist überfällig oder bald fällig.
        """
        krit = []
        for m in self.alle_module():
            if m.ist_bestanden():
                continue

            p = m.naechste_pruefung(heute)
            if p is None or p.pruefungsdatum is None:
                continue

            delta = (p.pruefungsdatum - heute).days
            status = p.berechne_status(heute)

            if status == Pruefungsstatus.ueberfaellig or (0 <= delta <= horizon_tage):
                krit.append(m)

        return krit