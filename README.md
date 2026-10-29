# invoice-manager-python / Rechnungs Manager

Eine Python-Desktopanwendung zur Erfassung von Kundendaten und Artikelpositionen. Sie berechnet Warenwert, Liefer- und Aufbaukosten und erstellt daraus einen Rechnungsentwurf als PDF.

## Ziel / Problemstellung

Beim Erfassen eines Verkaufs müssen Artikelpreise, Mengen und zusätzliche Leistungen zusammengeführt werden. Der RechnungsManager bündelt diese Eingaben in einer grafischen Oberfläche, berechnet die Beträge und überträgt sie in einen PDF-Entwurf.

## Funktionen

- Kundendaten erfassen: Name, Anschrift und Telefonnummer
- Kaufdatum, optionales Lieferdatum und Verkäufer erfassen
- Artikelpositionen hinzufügen und entfernen
- Positionspreise und Warenwert automatisch berechnen
- Zwischen Abholung, keiner Lieferung, Lieferung bis Treppenhaus und Lieferung in die Wohnung wählen
- Lieferkosten anhand von Warenwert und Etage berechnen
- Etagen vom Erdgeschoss bis zum 20. Obergeschoss auswählen
- Optionale Aufbaukosten berücksichtigen
- Eingaben auf gültige Datumswerte, Mengen und Geldbeträge prüfen
- Zusammenfassung der erfassten Daten anzeigen
- Rechnungsentwurf im A4-Format als PDF an einem frei gewählten Speicherort ablegen

## Technologien

- **Python 3** – Programmlogik und Datenverarbeitung
- **Tkinter** – grafische Benutzeroberfläche und Dialoge
- **ReportLab** – Erstellung der PDF-Dateien
- **decimal.Decimal** – Berechnung von Geldbeträgen
- **datetime und re** – Datumsverarbeitung und Eingabeprüfung

## Voraussetzungen

- Python 3 mit `pip` und Unterstützung für virtuelle Umgebungen
- Eine Python-Installation mit Tkinter
- ReportLab
- Eine grafische Desktopumgebung

Konkrete getestete Python- und ReportLab-Versionen sind derzeit nicht dokumentiert.

## Installation

Alle folgenden Befehle werden im Terminal beziehungsweise in PowerShell ausgeführt, nicht in der Python-Shell.

### 1. Projekt herunterladen

Das Repository als ZIP herunterladen, entpacken und ein Terminal im Projektordner öffnen. In diesem Ordner muss sich `main.py` befinden.

### 2. Virtuelle Umgebung erstellen

**macOS / Linux:**

```bash
python3 -m venv .venv
```

**Windows:**

```powershell
py -m venv .venv
```

### 3. ReportLab installieren

**macOS / Linux:**

```bash
.venv/bin/python -m pip install reportlab
```

**Windows:**

```powershell
.\.venv\Scripts\python.exe -m pip install reportlab
```

Die Befehle verwenden den Python-Interpreter der virtuellen Umgebung direkt. Eine Aktivierung ist dafür nicht erforderlich.

Falls beim Start `No module named 'tkinter'` erscheint, muss Tkinter für die verwendete Python-Installation ergänzt werden. Die Einrichtung hängt vom Betriebssystem und der Python-Distribution ab.

## Verwendung

### Anwendung starten

**macOS / Linux:**

```bash
.venv/bin/python main.py
```

**Windows:**

```powershell
.\.venv\Scripts\python.exe main.py
```

### Verkauf erfassen

1. Kundennamen eingeben; Anschrift und Telefonnummer bei Bedarf ergänzen.
2. Mindestens eine Artikelposition mit Bezeichnung, Menge und Einzelpreis ausfüllen.
3. Kaufdatum prüfen und bei Bedarf Verkäufer und Lieferdatum eintragen.
4. Die gewünschte Lieferart auswählen:
   - **Abholung:** Ein Abholdatum ab heute ist erforderlich.
   - **Keine Lieferung:** Es fallen keine Lieferkosten an.
   - **Bis Treppenhaus:** Die Lieferkosten richten sich nach dem Warenwert.
   - **Bis in die Wohnung:** Zusätzlich muss eine Etage ausgewählt werden.
5. Falls ein Aufbau gewünscht ist, „Ja“ wählen und den Aufbaupreis eingeben.
6. Über **„Daten anzeigen“** die Zusammenfassung prüfen.
7. Über **„Rechnung als PDF speichern“** den Speicherort auswählen.

### Eingabeformat

- Datum: `TT.MM.JJJJ`
- Menge: positive ganze Zahl
- Geldbetrag: nicht negativ, mit höchstens zwei Nachkommastellen
- Dezimaltrennzeichen: Komma oder Punkt, beispielsweise `49,90` oder `49.90`

Das Kaufdatum darf nicht in der Zukunft liegen. Ein bei Lieferung angegebenes Lieferdatum darf nicht in der Vergangenheit liegen.

### Berechnung

Der Gesamtbetrag setzt sich aus Warenwert, Lieferkosten und optionalen Aufbaukosten zusammen.

Die Lieferpreistabelle ist in `main.py` hinterlegt. Bei einem Warenwert über 1.500 € verwendet die Anwendung weiterhin die letzte Preisstufe.

## Projektstruktur

- `main.py` – Benutzeroberfläche, Eingabeprüfung, Preisberechnung und PDF-Erstellung
- `.gitignore` – vorgesehene Ausschlussregeln für lokale Dateien

## Beispiel / Ausgabe

Der PDF-Export enthält:

- die Überschrift **RECHNUNGSENTWURF**
- die eingegebenen Kundendaten
- Kaufdatum, Verkäufer und Lieferart
- je nach Auswahl Etage, Abhol- oder Lieferdatum
- eine Artikeltabelle mit Menge, Einzelpreis und Positionssumme
- Warenwert, Lieferkosten, Aufbaukosten und Gesamtbetrag

Als Dateiname wird `Rechnungsentwurf.pdf` vorgeschlagen.

**Aktuelle Einschränkung:** Vollständige Rechnungsstellerdaten, Rechnungsnummer und Steuerangaben sind noch zu ergänzen. Die erzeugte Datei ist ausdrücklich als Entwurf gekennzeichnet.

Die Anwendung besitzt derzeit keine dauerhafte Kunden- oder Verkaufsdatenbank. Formulareingaben werden beim Beenden nicht als bearbeitbarer Datensatz gespeichert.

[Screenshot hier einfügen]

## Was ich dabei gelernt habe

Das Projekt zeigt praktische Arbeit mit:

- grafischen Oberflächen und ereignisgesteuerter Verarbeitung in Tkinter
- dynamisch hinzugefügten und entfernten Eingabefeldern
- strukturierten Daten in Listen, Tupeln und Dictionaries
- Eingabevalidierung und Fehlerbehandlung
- Geldberechnungen mit `Decimal`
- regelbasierter Berechnung von Lieferkosten
- PDF-Erstellung mit Tabellen und formatierten Texten
- Maskierung von Benutzereingaben für ReportLab-Absätze

## Mögliche Weiterentwicklungen

**Geplant / mögliche Erweiterung – bisher nicht umgesetzt:**

- **Installierbare Windows-Version:** Eine Anwendung mit ausführbarer `.exe` bereitstellen, die ohne separate Installation von Python und Abhängigkeiten genutzt werden kann
- Zusätzliche PDF-Exporte für Quittungen, Kostenvoranschläge und Kostenaufstellungen ergänzen
- Kunden- und Verkaufsdaten dauerhaft speichern und erneut laden
- Die Gültigkeit der Einkaufsberechtigung pro Kunde hinterlegen und bei abgelaufener Berechtigung automatisch einen Hinweis anzeigen
- Lieferpreise über eine separate Konfigurationsdatei verwalten
- Rechnungsstellerdaten, Rechnungsnummer und Steuerangaben ergänzen
- Automatisierte Tests für Preisberechnung und Eingabeprüfung hinzufügen
- Benutzeroberfläche, Berechnungen und PDF-Export in separate Module aufteilen

## Status

**In Entwicklung**

Die unter „Funktionen“ beschriebenen Abläufe sind im Quellcode implementiert. Ein dokumentierter Test auf verschiedenen Betriebssystemen steht noch aus.

## Autor

GitHub: [HHAlisan](https://github.com/HHAlisan)
