# Studien-Dashboard (Python Prototyp)

Dieses Projekt ist ein konsolenbasiertes Studien-Dashboard und das Ergebnis der Phase 1+2 des Projektes.
Es dient als Prototyp für das Modul **„Objektorientierte und funktionale Programmierung mit Python"**.

Das Dashboard zeigt:
- Studienfortschritt in ECTS
- Durchschnittsnote
- Soll-/Ist-Vergleich
- Offene und überfällige Prüfungen
- Kritische Module

Die Anwendung läuft vollständig in der Konsole.

---

## Installation

### Voraussetzungen
- Python **3.10 oder neuer**
- Python **3.10 oder neuer**
- Keine externen Bibliotheken erforderlich. Es werden ausschließlich die Python-Standardbibliothek verwendet

### Datenbasis

Die Datei `data/studiengang.json` enthält die Beispieldaten des Studiengangs. 
Ohne diese Datei kann die Anwendung nicht gestartet werden.

---

## Start der Anwendung

Auf dem System muss die Console gestartet sein und der Kontext muss sich im Projektverzeichnis befinden. Danach kann die Anwendung wie folgt gestartet werden:

```bash
python run.py
```

oder je nach Installationsvariante:

```bash
python3 run.py
```

Beim Start kann optional ein Stichtag eingegeben werden, um zeitabhängige Berechnungen reproduzierbar auszuführen. Der Standard ist eine leere Eingabe um die gegebenen Daten aus der JSON zu analysieren.

---

## Bedienung

Nach dem Start erscheint das Hauptmenü:

```
1) Dashboard anzeigen
2) Module auflisten
3) Offene Prüfungen anzeigen
4) Note eintragen/ändern
5) Prüfungstermin planen/ändern
6) Speichern
0) Beenden
```

Alle Eingaben erfolgen interaktiv in der Konsole.

---

## Dateibeschreibung

### `run.py`
Einfaches Startskript. Fügt das `src`-Verzeichnis zum Python-Pfad hinzu und startet die Anwendung.

### `main.py`
Einstiegspunkt der Anwendung. Initialisiert Repository, Service, View und Controller.

### `controller.py`
Steuert den Programmablauf. Verarbeitet Benutzereingaben und delegiert an Service und View.

### `service.py`
Berechnet alle Kennzahlen (KPIs). Erzeugt einen `DashboardState` für die Anzeige.

### `domain.py`
Enthält die fachliche Domäne:
* Studiengang
* Semester
* Modul
* Prüfungsleistung
* Enums für Status und Typen

### `persistence.py`
JSON-Persistenzschicht:
* Laden und Speichern der Daten
* Mapping zwischen Domain-Objekten und JSON

### `view.py`
Konsolenbasierte Darstellung:
* ASCII-Dashboard
* Menüführung
* Formatierte Ausgabe

### `data/studiengang.json`
Beispieldaten des Studiengangs. Kann angepasst werden, um andere Studienverläufe zu testen.

### `requirements.txt`
Keine externen Abhängigkeiten erforderlich. Das Projekt basiert vollständig auf der Python-Standardbibliothek.
Daher ist diese Datei leer. Wurde aber doch nach "best practice" angelegt.

---

## Hinweis

Dieses Projekt ist ein Prototyp. Es beschreibt die objektorientierte Modellierung, Schichtenarchitektur und Persistenz in Python anhand des Projektes.
Für das Projekt werden in der Phase 3 zusätzlich noch folgende Dokumentationen erstellt: Installationsanleitung und Abstract.