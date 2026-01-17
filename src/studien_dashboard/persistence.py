"""
Persistence layer (JSON)

Hier liegt die Speicherung in JSON wie in den Phasen 1+2 beschrieben. Die Domain selbst bleibt frei von JSON-Details.
- StudiengangRepository: Schnittstelle (lade / speichere)
- JsonStudiengangRepository: Datei-Repository
- JsonSerializer: Mapping zwischen Entities und JSON

Für eine bessere Fehlerbehandlung:
- Enum-Parsing ist tolerant (name/value, Groß/Klein).
- Daten werden beim Laden geprüft.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from typing import Any, Dict, Protocol, Optional

from .domain import (
    Studiengang,
    Semester,
    Modul,
    Pruefungsleistung,
    Abschluss,
    Studienmodell,
    Pruefungsart,
)


class StudiengangRepository(Protocol):
    """
    Schnittstelle für Persistenz.
    """
    def lade(self) -> Studiengang:
        """Lädt einen Studiengang."""
        ...

    def speichere(self, stg: Studiengang) -> None:
        """Speichert einen Studiengang."""
        ...


class FileStorage:
    """
    Klasse für Dateihandling beim laden und speichern.
    - Nur lesen/schreiben.
    - UTF-8 wird fest genutzt.
    """

    def lese_text(self, pfad: str) -> str:
        """
        Liest eine Datei als Text.
        Fehlerbehandlung:
        - FileNotFoundError, wenn Datei fehlt
        - IOError bei Leseproblemen (Format oder sonstige)
        """
        with open(pfad, "r", encoding="utf-8") as f:
            return f.read()

    def schreibe_text(self, pfad: str, content: str) -> None:
        """
        Schreibt Text in eine Datei.
        """
        with open(pfad, "w", encoding="utf-8") as f:
            f.write(content)


class JsonSerializer:
    """
    Wandelt Studiengang <-> JSON.
    - Enums: meist per name gespeichert.
    - Datum: ISO-Format (YYYY-MM-DD) - wird dem Nutzer als Information auch angezeigt.
    - Parsing ist tolerant.
    """

    def to_json(self, stg: Studiengang) -> str:
        """
        Macht aus dem Studiengang einen JSON-String.
        Der String ist formatiert indent = 2.
        """
        payload = self._studiengang_to_dict(stg)
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def from_json(self, raw: str) -> Studiengang:
        """
        Baut einen Studiengang aus JSON.
        """
        payload = json.loads(raw)
        return self._studiengang_from_dict(payload)

    def _parse_enum(self, enum_cls, raw, default=None):
        """
        Parst einen Enum-Wert.

        Wenn nichts passt:
        - default wird zurückgegeben.
        """
        if raw is None:
            return default

        s = str(raw).strip()
        if not s:
            return default

        # Member-Name direkt.
        if s in enum_cls.__members__:
            return enum_cls[s]

        # Vergleich über value.
        for m in enum_cls:
            if str(m.value) == s:
                return m

        # Fallback: case-insensitive.
        low = s.lower()
        for name, m in enum_cls.__members__.items():
            if name.lower() == low:
                return m
        for m in enum_cls:
            if str(m.value).lower() == low:
                return m

        return default

    def _studiengang_to_dict(self, stg: Studiengang) -> Dict[str, Any]:
        """Studiengang Mapping für JSON."""
        return {
            "name": stg.name,
            "abschluss": stg.abschluss.name,
            "studienmodell": stg.studienmodell.name,
            "gesamt_ects": stg.gesamt_ects,
            "regelstudienzeit_monate": stg.regelstudienzeit_monate,
            "start_datum": stg.start_datum.isoformat(),
            "semester": [self._semester_to_dict(s) for s in stg.semester],
        }

    def _semester_to_dict(self, s: Semester) -> Dict[str, Any]:
        """Semester Mapping für JSON."""
        return {
            "nummer": s.nummer,
            "geplante_ects": s.geplante_ects,
            "start_datum": s.start_datum.isoformat() if s.start_datum else None,
            "end_datum": s.end_datum.isoformat() if s.end_datum else None,
            "module": [self._modul_to_dict(m) for m in s.module],
        }

    def _modul_to_dict(self, m: Modul) -> Dict[str, Any]:
        """Modul Mapping für JSON."""
        return {
            "modul_code": m.modul_code,
            "titel": m.titel,
            "ects": m.ects,
            "empfohlenes_semester": m.empfohlenes_semester,
            "pruefungen": [self._pruefung_to_dict(p) for p in m.pruefungen],
        }

    def _pruefung_to_dict(self, p: Pruefungsleistung) -> Dict[str, Any]:
        """Pruefungsleistung Mapping für JSON."""
        return {
            "pruefung_id": p.pruefung_id,
            "art": p.art.value,
            "pruefungsdatum": p.pruefungsdatum.isoformat() if p.pruefungsdatum else None,
            "versuch": p.versuch,
            "note": p.note,
        }

    def _studiengang_from_dict(self, d: Dict[str, Any]) -> Studiengang:
        """
        Mapping für Studiengang.
        Enum-Werte werden tolerant geparst.
        Es gibt Defaults für alte Datenstände.
        """
        stg = Studiengang(
            name=d["name"],
            abschluss=self._parse_enum(Abschluss, d.get('abschluss'), Abschluss.BSc),
            studienmodell=self._parse_enum(Studienmodell, d.get('studienmodell'), Studienmodell.TeilzeitI),
            gesamt_ects=int(d["gesamt_ects"]),
            regelstudienzeit_monate=int(d["regelstudienzeit_monate"]),
            start_datum=date.fromisoformat(d["start_datum"]),
            semester=[self._semester_from_dict(x) for x in d["semester"]],
        )

        # wie gehabt werden doppelte Modul-Codes erkennen.
        module_codes = [m.modul_code for m in stg.alle_module()]
        duplicates = [code for code in set(module_codes) if module_codes.count(code) > 1]
        if duplicates:
            pass

        return stg

    def _semester_from_dict(self, d: Dict[str, Any]) -> Semester:
        """Mapping für Semester."""
        start = date.fromisoformat(d["start_datum"]) if d.get("start_datum") else None
        end = date.fromisoformat(d["end_datum"]) if d.get("end_datum") else None

        s = Semester(
            nummer=int(d["nummer"]),
            geplante_ects=float(d["geplante_ects"]),
            start_datum=start,
            end_datum=end,
            module=[self._modul_from_dict(x) for x in d.get("module", [])],
        )
        return s

    def _modul_from_dict(self, d: Dict[str, Any]) -> Modul:
        """Mapping für Modul."""
        m = Modul(
            modul_code=str(d.get('modul_code', '')).strip(),
            titel=d["titel"],
            ects=int(d["ects"]),
            empfohlenes_semester=int(d["empfohlenes_semester"]),
            pruefungen=[self._pruefung_from_dict(x) for x in d["pruefungen"]],
        )
        return m

    def _pruefung_from_dict(self, d: Dict[str, Any]) -> Pruefungsleistung:
        """Mapping für Prüfungsleistung."""
        pdate = date.fromisoformat(d["pruefungsdatum"]) if d.get("pruefungsdatum") else None

        return Pruefungsleistung(
            pruefung_id=str(d.get('pruefung_id', '')).strip(),
            art=self._parse_enum(Pruefungsart, d.get('art'), Pruefungsart.Sonstiges),
            pruefungsdatum=pdate,
            versuch=int(d["versuch"]),
            note=d.get("note", None),
        )

class JsonStudiengangRepository:
    """
    Repository für eine JSON-Datei.
    - FileStorage für Datei-Zugriff
    - JsonSerializer für Mapping
    """

    def __init__(
        self,
        pfad: str,
        storage: Optional[FileStorage] = None,
        serializer: Optional[JsonSerializer] = None
    ) -> None:
        """
        Erstellt das Repository.
        """
        self._pfad = pfad
        self._storage = storage or FileStorage()
        self._serializer = serializer or JsonSerializer()

    def lade(self) -> Studiengang:
        """
        Lädt die Datei und baut die Domain-Objekte.
        """
        raw = self._storage.lese_text(self._pfad)
        stg = self._serializer.from_json(raw)
        return stg

    def speichere(self, stg: Studiengang) -> None:
        """
        Serialisiert und schreibt in die Datei.
        """
        raw = self._serializer.to_json(stg)
        self._storage.schreibe_text(self._pfad, raw)