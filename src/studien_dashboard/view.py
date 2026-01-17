"""
UI layer für die Console

Diese View zeigt das Dashboard in der Konsole.
- Text formatieren und ausgeben
- Layout als ASCII-Dashboard bauen
- Eingaben und Menü anzeigen
"""

from __future__ import annotations

import shutil
import textwrap
from typing import Optional, List

from .service import DashboardState


class ConsoleDashboardView:
    """
    View für die Konsole.

    Die Breite wird automatisch ermittelt anhand der breite des aktuellen Fensters.
    """

    def __init__(self, width: int | None = None) -> None:
        """
        Erstellt die View.
        - Wenn width None ist, wird die Terminal-Breite genutzt.
        - Es gibt eine Mindestbreite.
        - Die echte Terminal-Breite wird nicht überschritten.
        """
        term_cols = shutil.get_terminal_size(fallback=(140, 24)).columns

        if width is None:
            width = term_cols

        width = max(80, width)
        self._width = min(width, term_cols)

    def render(self, state: DashboardState) -> None:
        """
        Zeichnet das komplette Dashboard.
        Es wird ein String gebaut und dann ausgegeben.
        """
        print(self._build_dashboard(state))

    def render_menue(self) -> None:
        """Zeigt das Hauptmenü."""
        print()
        print("╔═══════════════════════════════════════╗")
        print("║            HAUPTMENÜ                  ║")
        print("╠═══════════════════════════════════════╣")
        print("║  1) Dashboard anzeigen                ║")
        print("║  2) Module auflisten                  ║")
        print("║  3) Offene Prüfungen anzeigen         ║")
        print("║  4) Note eintragen/ändern             ║")
        print("║  5) Prüfungstermin planen/ändern      ║")
        print("║  6) Speichern                         ║")
        print("║  0) Beenden                           ║")
        print("╚═══════════════════════════════════════╝")

    def prompt(self, frage: str) -> str:
        """
        Fragt den Nutzer nach Eingabe.
        """
        return input(frage)

    def show_message(self, text: str) -> None:
        """
        Gibt eine Nachricht aus.
        """
        print(text)

    def _build_dashboard(self, state: DashboardState) -> str:
        """
        Baut das Dashboard als Text.
        """
        w = self._width
        sep_eq = "+" + "═" * (w - 2) + "+"
        sep_dash = "+" + "─" * (w - 2) + "+"

        lines: List[str] = []

        # Kopfbereich
        lines.append(sep_eq)

        title = f"Studien-Dashboard — {state.studiengang_name} ({state.studienmodell_text})"
        lines.extend(self._rows_wrapped(title))

        header2 = (
            f"Start: {state.start_datum.strftime('%d.%m.%Y')}   "
            f"Semester: {state.aktuelles_semester} / {state.gesamt_semester}   "
            f"Ziel-ECTS: {state.gesamt_ects}"
        )
        lines.extend(self._rows_wrapped(header2))
        lines.append(sep_eq)

        # Überschriften in zwei Spalten
        left_h = "STUDIENFORTSCHRITT"
        right_h = "NOTEN & LEISTUNGEN"
        lines.append(self._row_2col(left_h, right_h))

        # Fortschritt und Note
        bar = self._progress_bar(state.fortschritt_prozent, length=20)
        progress_text = (
            f"{bar} {state.erreichte_ects}/{state.gesamt_ects} ECTS "
            f"({self._fmt_int(round(state.fortschritt_prozent))}%)"
        )
        note = self._fmt_note(state.durchschnittsnote)
        right_text = f"Ø-Note: {note} (Ziel {self._fmt_note(state.ziel_note)})"
        lines.append(self._row_2col(progress_text, right_text))

        # Soll und Abweichung
        abw_symbol = "✓" if state.abweichung >= 0 else "X"
        abw = f"{state.abweichung:+d} ECTS {abw_symbol}"
        left2 = f"Soll aktuell: {state.soll_ects} ECTS   Abweichung: {abw}"
        right2 = f"Module > {self._fmt_note(state.ziel_note)}: {state.anzahl_module_ueber_zielnote}"
        lines.append(self._row_2col(left2, right2))

        lines.append(sep_dash)

        # Tabelle pro Semester
        lines.extend(self._semester_table(state))
        lines.append(sep_dash)

        # Kritische Einträge
        lines.extend(self._rows_wrapped("KRITISCHE MODULE & PRÜFUNGEN"))

        if not state.kritische_eintraege:
            lines.extend(self._rows_wrapped(" Keine kritischen Einträge"))
        else:
            # Im Dashboard werden nur die wichtigsten gezeigt
            for e in state.kritische_eintraege[:8]:
                mark = "X" if e.ist_ueberfaellig else "+"
                text = f" {mark} {e.titel[:45]} ({e.modul_code})  {e.status_text}"
                lines.extend(self._rows_wrapped(text))

        # Zusammenfassung der Prüfungen
        pruef_symbol = "X" if state.anzahl_ueberfaellig > 0 else "✓"
        pruef_text = (
            f"Offene Prüfungen: {state.anzahl_offen}    "
            f"Überfällige Prüfungen: {state.anzahl_ueberfaellig} {pruef_symbol}"
        )
        lines.extend(self._rows_wrapped(pruef_text))
        lines.append(sep_eq)

        return "\n".join(lines)

    def _semester_table(self, state: DashboardState) -> List[str]:
        """
        Baut die Semester-Tabelle.

        Spalten:
        - Semester
        - Soll-ECTS
        - Ist-ECTS
        - Status
        """
        cols = [
            ("Semester", 9),
            ("Soll-ECTS", 10),
            ("Ist-ECTS", 9),
            ("Status", 25)
        ]

        header = " │ ".join(name.ljust(width) for name, width in cols)
        out = [self._row(header)]

        # Trennlinie zwischen Kopf und Daten
        sep = "─ │ ─".join("─" * width for _, width in cols)
        out.append(self._row(sep))

        # Zeilen aus state.semester_zeilen
        for z in state.semester_zeilen:
            sem_str = str(z["nummer"]).ljust(cols[0][1])
            soll_str = self._fmt_float_de(z["soll"]).rjust(cols[1][1])
            ist_str = str(z["ist"]).rjust(cols[2][1])
            status_str = str(z["status"]).ljust(cols[3][1])

            row = f"{sem_str} │ {soll_str} │ {ist_str} │ {status_str}"
            out.append(self._row(row))

        return out

    def _row(self, text: str) -> str:
        """
        Baut eine Zeile mit Rahmen.
        - Zu langer Text wird gekürzt um die breite der Konsole nicht zu verändern.
        - Zu kurzer Text wird aufgefüllt um die Tabelle vernünftig anzuzeigen.
        """
        inner = self._width - 2
        content = text[:inner].ljust(inner)
        return "│" + content + "│"

    def _rows_wrapped(self, text: str) -> List[str]:
        """
        Bricht langen Text um.
        """
        inner = self._width - 2
        rows: List[str] = []

        split_lines = text.splitlines() if text else [""]

        for raw in split_lines:
            wrapped = textwrap.wrap(
                raw,
                width=inner,
                break_long_words=False,
                break_on_hyphens=False,
                replace_whitespace=False,
                drop_whitespace=False,
            )

            if not wrapped:
                wrapped = [""]

            for part in wrapped:
                rows.append("│" + part.ljust(inner) + "│")

        return rows

    def _row_2col(self, left: str, right: str) -> str:
        """
        Baut eine Zeile mit zwei Spalten.
        """
        inner = self._width - 2
        sep = " │ "

        left_w = (inner - len(sep)) // 2
        right_w = inner - len(sep) - left_w

        left_content = left[:left_w].ljust(left_w)
        right_content = right[:right_w].ljust(right_w)

        return "│" + left_content + sep + right_content + "│"

    def _progress_bar(self, percent: float, length: int = 20) -> str:
        """
        Erstellt einen Fortschrittsbalken.
        - percent wird auf 0..100 begrenzt.
        - █ = gefüllt, ░ = leer.
        """
        p = max(0.0, min(100.0, percent))
        filled = int(round((p / 100.0) * length))
        bar = "█" * filled + "░" * (length - filled)
        return f"[{bar}]"

    def _fmt_note(self, note: Optional[float]) -> str:
        """
        Formatiert eine Note.
        """
        if note is None:
            return "-"
        return f"{note:.1f}".replace(".", ",")

    def _fmt_float_de(self, value: float) -> str:
        """
        Formatiert eine Zahl im richtigen Stil.
        - Eine Dezimalstelle.
        - ",0" wird entfernt.
        """
        s = f"{value:.1f}".replace(".", ",")
        if s.endswith(",0"):
            s = s[:-2]
        return s

    def _fmt_int(self, value: int) -> str:
        """Formatiert eine ganze Zahl als String."""
        return str(int(value))