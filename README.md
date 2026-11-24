# Quittung

Eine lokale Python-Desktopanwendung zum Erstellen von PDF-Quittungen, Rechnungen und Kostenvoranschlägen mit Reservierungsbestätigung. Sie verwendet Tkinter für die Oberfläche, ReportLab für den PDF-Export und SQLite für die optionale Kundendatenbank.

## Starten

Voraussetzungen sind Python 3.10 oder neuer, Tkinter und eine grafische Desktopumgebung. Unter Debian oder Ubuntu kann Tkinter je nach Installation über das Paket `python3-tk` ergänzt werden.

**Windows (PowerShell)**

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

**macOS und Linux**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

## Bedienung

Über **⚙ Einstellungen** oben rechts erreichst du Firmendaten und Lieferpreise.

- **Firmendaten** speichert den eigenen Absender für den PDF-Kopf. Die Bankverbindung erscheint nur auf Rechnungen und nur, wenn sie hinterlegt wurde.
- **Lieferpreise** öffnet die Tarife für Warenwert, Entfernung und Volumen. Die Warenwerttabelle enthält fiktive Beispielpreise. Tarife nach Entfernung und Volumen beginnen bei 0 €. Das Passwort wird beim Speichern benötigt und bei der ersten Speicherung selbst gewählt. Bei Lieferung bis zur Wohnung gilt je nach Eingabe der Etagenzuschlag oder eine Fahrstuhlpauschale. Montagekosten können separat erfasst werden.
- **Daten prüfen** zeigt die erfassten Beträge vor dem Export. Mit **Bemerkung hinzufügen** blendest du das Textfeld ein und übernimmst bis zu 1.500 Zeichen ins PDF. Bei einer Reservierung berechnet das Programm den Restbetrag aus Gesamtbetrag und Anzahlung.
- **Kundendaten in der Datenbank speichern** übernimmt den Vorgang erst nach erfolgreichem PDF-Export. Die Checkbox ist für jeden Vorgang standardmäßig aus. Gespeicherte Kunden lassen sich wieder auswählen, einschließlich Status ihrer Einkaufsberechtigung und Datum des letzten eingetragenen Einkaufs.
- **Neuer Vorgang** setzt die Vorgangsdaten zurück und behält die Kundendaten im Formular. **Neuer Kunde** leert auch die Kundenfelder. Nach einem erfolgreichen Export beginnt automatisch ein neuer Vorgang für denselben Kunden.

Die App legt lokale Dateien für Kundendaten, Firmendaten und Tarife außerhalb des Projektordners an. Unter Windows ist das `%LOCALAPPDATA%\Quittung`, unter macOS `~/Library/Application Support/Quittung` und unter Linux `${XDG_DATA_HOME:-$HOME/.local/share}/quittung`. Der Datenbankpfad kann bei Bedarf über `QUITTUNG_DB_PATH` gesetzt werden. PDF-Dateien werden am im Exportdialog gewählten Ort gespeichert.

[Quittung](docs/Beispiel-Quittung.pdf) · [Rechnung](docs/Beispiel-Rechnung.pdf) · [Kostenvoranschlag](docs/Beispiel-Kostenvoranschlag.pdf). Alle Beispiele verwenden fiktive Daten.

## Tests und Windows-Build

```bash
python -m unittest discover -s tests -v
```

Zum Erstellen einer Windows-EXE in Windows PyInstaller in derselben virtuellen Umgebung installieren und `python -m PyInstaller Quittung.spec` ausführen. Die EXE landet unter `dist/Quittung.exe`.
