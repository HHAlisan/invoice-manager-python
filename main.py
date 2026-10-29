# --------------------------------
# 1. IMPORTE
# --------------------------------

import re
import tkinter as tk
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from html import escape
from tkinter import filedialog, messagebox

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)


# --------------------------------
# 2. LIEFERPREISTABELLE
# --------------------------------

# Aufsteigend sortieren: Die Berechnung verwendet die erste passende Stufe.
# „bis“ ist einschließlich; „eg“ ist der Wohnungspreis im Erdgeschoss,
# „og“ der Zuschlag je Obergeschoss. Alle Beträge sind in Euro.
lieferpreise = [
    {"bis": 50, "treppenhaus": 10, "eg": 15, "og": 2.50},
    {"bis": 100, "treppenhaus": 15, "eg": 30, "og": 5.00},
    {"bis": 200, "treppenhaus": 20, "eg": 40, "og": 7.50},
    {"bis": 300, "treppenhaus": 25, "eg": 50, "og": 10.00},
    {"bis": 400, "treppenhaus": 30, "eg": 60, "og": 10.00},
    {"bis": 500, "treppenhaus": 35, "eg": 70, "og": 10.00},
    {"bis": 600, "treppenhaus": 40, "eg": 80, "og": 10.00},
    {"bis": 700, "treppenhaus": 45, "eg": 90, "og": 10.00},
    {"bis": 800, "treppenhaus": 50, "eg": 100, "og": 10.00},
    {"bis": 1000, "treppenhaus": 55, "eg": 110, "og": 10.00},
    {"bis": 1500, "treppenhaus": 60, "eg": 120, "og": 15.00}
]


# --------------------------------
# 3. HAUPTFENSTER UND VARIABLEN
# --------------------------------

fenster = tk.Tk()
fenster.title("RechnungsManager")
fenster.geometry("900x750")

# Pro Zeile werden die drei Eingabefelder und der Entfernen-Button gespeichert.
# Die fachlichen Artikelwerte werden daraus erst beim Auslesen erzeugt.
artikel_positionen = []

warenwert_text = tk.StringVar(value="– €")
lieferkosten_text = tk.StringVar(value="0,00 €")

lieferart = tk.StringVar(value="Keine Lieferung")
etage = tk.StringVar(value="Bitte wählen")
aufbau_aktiv = tk.StringVar(value="Nein")


# --------------------------------
# 4. HILFSFUNKTIONEN
# --------------------------------

def euro(betrag):
    text = f"{Decimal(str(betrag)):,.2f}"

    # Zwischenzeichen verhindert, dass sich Tausender- und Dezimaltrennzeichen
    # beim Wechsel zur deutschen Darstellung gegenseitig überschreiben.
    text = text.replace(",", "X")
    text = text.replace(".", ",")
    text = text.replace("X", ".")

    return text + " €"


def datum_pruefen(text):

    # Das Muster prüft das feste Format; strptime prüft danach das Kalenderdatum.
    if not re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", text):
        return False

    try:
        datetime.strptime(text, "%d.%m.%Y")
        return True

    except ValueError:
        return False


def abholdatum_pruefen(text):

    if not datum_pruefen(text):
        return False

    abholdatum = datetime.strptime(
        text, "%d.%m.%Y"
    ).date()

    return abholdatum >= date.today()


def betrag_lesen(text):

    # Direkt aus Text konvertieren, um keine float-Rundungsfehler zu übernehmen.
    # Komma und Punkt sind als Dezimaltrenner erlaubt, Tausendertrenner nicht.
    betrag = Decimal(
        text.strip().replace(",", ".")
    )

    # Decimal akzeptiert auch NaN und Infinity; für Preise sind sie unzulässig.
    if not betrag.is_finite():
        raise ValueError("Ungültiger Geldbetrag")

    if betrag < 0:
        raise ValueError("Preis darf nicht negativ sein")

    # Zusätzliche Nachkommastellen werden abgewiesen statt still gerundet.
    if betrag.as_tuple().exponent < -2:
        raise ValueError("Maximal zwei Nachkommastellen erlaubt")

    return betrag


# --------------------------------
# 5. ARTIKEL AUSLESEN
# --------------------------------

def artikel_auslesen(mit_fehler=True):

    # Bei Live-Berechnungen keine Dialoge öffnen und leere Bezeichnungen zulassen.
    # Menge und Preis müssen auch dann gültig sein; sonst folgt (None, None).
    positionen = []
    summe = Decimal("0.00")

    for nummer, position in enumerate(
        artikel_positionen, start=1
    ):

        artikel, menge, preis, entfernen_button = position

        bezeichnung = artikel.get().strip()

        try:
            anzahl = int(menge.get())
            einzelpreis = betrag_lesen(preis.get())

            if anzahl < 1:
                raise ValueError(
                    "Die Menge muss mindestens 1 betragen"
                )

            if mit_fehler and not bezeichnung:
                raise ValueError(
                    "Artikelbezeichnung fehlt"
                )

        except (ValueError, InvalidOperation) as fehler:

            if mit_fehler:
                messagebox.showerror(
                    "Artikel prüfen",
                    f"Artikel {nummer}: {fehler}"
                )

            return None, None

        positionspreis = anzahl * einzelpreis

        positionen.append((
            bezeichnung,
            anzahl,
            einzelpreis,
            positionspreis
        ))

        summe += positionspreis

    return positionen, summe


# --------------------------------
# 6. LIEFERKOSTEN BERECHNEN
# --------------------------------

def lieferkosten_berechnen(warenwert, art, stockwerk):

    if art in ("Abholung", "Keine Lieferung"):
        return Decimal("0.00")

    if warenwert <= 0:
        return None

    # Die erste einschließlich passende Obergrenze bestimmt den Tarif.
    # Aktueller Fallback: Über 1.500 Euro bleibt die letzte Stufe unverändert.
    # Diese fachliche Regel vor einem produktiven Einsatz bestätigen.
    preisstufe = next(
        (
            preis for preis in lieferpreise
            if warenwert <= preis["bis"]
        ),
        lieferpreise[-1]
    )

    if art == "Treppenhaus":
        return Decimal(str(preisstufe["treppenhaus"]))

    if art == "Wohnung":

        if stockwerk == "EG":
            anzahl_og = 0

        elif stockwerk.isdigit() and 1 <= int(stockwerk) <= 20:
            anzahl_og = int(stockwerk)

        else:
            return None

        grundpreis = Decimal(str(preisstufe["eg"]))
        zuschlag = Decimal(str(preisstufe["og"]))

        # EG benötigt keinen Zuschlag; jedes Obergeschoss erhöht den Grundpreis.
        return grundpreis + anzahl_og * zuschlag

    return None


# --------------------------------
# 7. WARENWERTANZEIGE AKTUALISIEREN
# --------------------------------

def warenwert_aktualisieren(event=None):

    positionen, warenwert = artikel_auslesen(
        mit_fehler=False
    )

    # Unvollständige Eingaben nicht als gültigen Nullbetrag darstellen.
    if warenwert is None:
        warenwert_text.set("– €")

    else:
        warenwert_text.set(euro(warenwert))

    lieferkosten_aktualisieren()


# --------------------------------
# 8. LIEFERKOSTENANZEIGE AKTUALISIEREN
# --------------------------------

# trace_add übergibt zusätzliche Callback-Argumente; benötigt werden nur
# die aktuellen Eingabewerte, daher bleiben diese Argumente ungenutzt.
def lieferkosten_aktualisieren(*args):

    positionen, warenwert = artikel_auslesen(
        mit_fehler=False
    )

    if warenwert is None:
        lieferkosten_text.set("– €")
        return

    kosten = lieferkosten_berechnen(
        warenwert,
        lieferart.get(),
        etage.get()
    )

    if kosten is None:
        lieferkosten_text.set("– €")

    else:
        lieferkosten_text.set(euro(kosten))


# --------------------------------
# 9. RECHNUNGSDATEN PRÜFEN UND SAMMELN
# --------------------------------

def daten_sammeln():

    # Vorschau und PDF verwenden dieselbe Prüfung und Berechnung,
    # damit ihre Beträge auf denselben Regeln beruhen.
    kundenname = name_entry.get().strip()
    anschrift = anschrift_entry.get().strip()
    telefon = telefon_entry.get().strip()

    kaufdatum = kaufdatum_entry.get().strip()
    lieferdatum = lieferdatum_entry.get().strip()
    verkaeufer = verkaeufer_entry.get().strip()

    art = lieferart.get()
    stockwerk = etage.get()
    abholdatum = abholung_entry.get().strip()

    # Kundennamen prüfen
    if not kundenname:
        messagebox.showerror(
            "Kundendaten",
            "Bitte einen Kundennamen eingeben."
        )
        return None

    # Kaufdatum prüfen
    if not datum_pruefen(kaufdatum):
        messagebox.showerror(
            "Kaufdatum",
            "Bitte ein gültiges Kaufdatum im Format TT.MM.JJJJ eingeben."
        )
        return None

    if datetime.strptime(
        kaufdatum, "%d.%m.%Y"
    ).date() > date.today():

        messagebox.showerror(
            "Kaufdatum",
            "Das Kaufdatum darf nicht in der Zukunft liegen."
        )
        return None

    # Abholdatum prüfen
    if art == "Abholung":

        if not abholdatum_pruefen(abholdatum):
            messagebox.showerror(
                "Abholung",
                "Bitte ein gültiges Abholdatum ab heute angeben."
            )
            return None

    # Ein Lieferdatum ist optional; bei tatsächlicher Lieferung darf ein
    # angegebenes Datum jedoch nicht in der Vergangenheit liegen.
    if art in ("Treppenhaus", "Wohnung") and lieferdatum:

        if not datum_pruefen(lieferdatum):
            messagebox.showerror(
                "Lieferdatum",
                "Bitte ein gültiges Lieferdatum eingeben."
            )
            return None

        if datetime.strptime(
            lieferdatum, "%d.%m.%Y"
        ).date() < date.today():

            messagebox.showerror(
                "Lieferdatum",
                "Das Lieferdatum muss heute oder in der Zukunft liegen."
            )
            return None

    # Etage prüfen
    if art == "Wohnung" and stockwerk == "Bitte wählen":

        messagebox.showerror(
            "Etage",
            "Bitte eine Etage auswählen."
        )
        return None

    # Artikel erfassen
    positionen, warenwert = artikel_auslesen()

    if positionen is None:
        return None

    # Lieferkosten berechnen
    lieferkosten = lieferkosten_berechnen(
        warenwert,
        art,
        stockwerk
    )

    if lieferkosten is None:
        messagebox.showerror(
            "Lieferkosten",
            "Die Lieferkosten konnten nicht berechnet werden."
        )
        return None

    # Aufbaukosten prüfen
    aufbaukosten = Decimal("0.00")

    if aufbau_aktiv.get() == "Ja":

        try:
            aufbaukosten = betrag_lesen(
                aufbau_entry.get()
            )

        except (ValueError, InvalidOperation):
            messagebox.showerror(
                "Aufbau",
                "Bitte einen gültigen Aufbaupreis eingeben."
            )
            return None

    gesamtbetrag = (
        warenwert + lieferkosten + aufbaukosten
    )

    # Hier werden nur Daten zurückgegeben; eine Kundendatenbank wird nicht befüllt.
    return {
        "name": kundenname,
        "anschrift": anschrift,
        "telefon": telefon,
        "kaufdatum": kaufdatum,
        "lieferdatum": lieferdatum,
        "verkaeufer": verkaeufer,
        "art": art,
        "etage": stockwerk,
        "abholdatum": abholdatum,
        "positionen": positionen,
        "warenwert": warenwert,
        "lieferkosten": lieferkosten,
        "aufbaukosten": aufbaukosten,
        "gesamt": gesamtbetrag
    }


# --------------------------------
# 10. DATEN ANZEIGEN
# --------------------------------

def daten_anzeigen():

    daten = daten_sammeln()

    if daten is None:
        return

    messagebox.showinfo(
        "Rechnungsdaten",
        f"Kunde: {daten['name']}\n"
        f"Kaufdatum: {daten['kaufdatum']}\n"
        f"Verkäufer: {daten['verkaeufer']}\n"
        f"Lieferart: {daten['art']}\n"
        f"Etage: {daten['etage'] if daten['art'] == 'Wohnung' else '-'}\n"
        f"Warenwert: {euro(daten['warenwert'])}\n"
        f"Lieferkosten: {euro(daten['lieferkosten'])}\n"
        f"Aufbaukosten: {euro(daten['aufbaukosten'])}\n"
        f"Gesamtbetrag: {euro(daten['gesamt'])}"
    )


# --------------------------------
# 11. ARTIKEL HINZUFÜGEN
# --------------------------------

def artikel_hinzufuegen():

    # Grid-Zeile 0 bleibt für die Spaltenüberschriften reserviert.
    zeile = len(artikel_positionen) + 1

    artikel = tk.Entry(artikel_frame, width=35)
    artikel.grid(row=zeile, column=0, padx=5, pady=5)

    menge = tk.Entry(artikel_frame, width=8)
    menge.grid(row=zeile, column=1, padx=5, pady=5)
    menge.insert(0, "1")

    preis = tk.Entry(artikel_frame, width=12)
    preis.grid(row=zeile, column=2, padx=5, pady=5)

    position = [artikel, menge, preis]

    entfernen_button = tk.Button(
        artikel_frame,
        text="✕",
        fg="red",
        command=lambda: artikel_entfernen(position)
    )

    entfernen_button.grid(
        row=zeile, column=3, padx=5, pady=5
    )

    position.append(entfernen_button)
    artikel_positionen.append(position)

    menge.bind(
        "<KeyRelease>",
        warenwert_aktualisieren
    )

    preis.bind(
        "<KeyRelease>",
        warenwert_aktualisieren
    )

    warenwert_aktualisieren()


# --------------------------------
# 12. ARTIKEL ENTFERNEN
# --------------------------------

def artikel_entfernen(position):

    if len(artikel_positionen) <= 1:
        messagebox.showwarning(
            "Artikel",
            "Mindestens eine Artikelposition muss erhalten bleiben."
        )
        return

    for widget in position:
        widget.destroy()

    artikel_positionen.remove(position)

    # Lücken schließen, damit neue Positionen keine bestehenden Zeilen überlagern.
    for zeile, verbleibende_position in enumerate(
        artikel_positionen, start=1
    ):

        for spalte, widget in enumerate(
            verbleibende_position
        ):

            widget.grid_configure(
                row=zeile,
                column=spalte
            )

    warenwert_aktualisieren()


# --------------------------------
# 13. LIEFEROPTIONEN EIN- UND AUSBLENDEN
# --------------------------------

def lieferoptionen_aktualisieren():

    if lieferart.get() == "Wohnung":

        etage_label.grid(
            row=7, column=0,
            sticky="w", padx=10, pady=5
        )

        etage_dropdown.grid(
            row=7, column=1,
            sticky="w", padx=10, pady=5
        )

    else:
        etage_label.grid_remove()
        etage_dropdown.grid_remove()
        # Eine frühere Etagenwahl soll nicht unbemerkt erneut verwendet werden.
        etage.set("Bitte wählen")

    if lieferart.get() == "Abholung":

        abholung_label.grid(
            row=3, column=1,
            sticky="w", padx=10, pady=5
        )

        abholung_entry.grid(
            row=3, column=2,
            sticky="w", padx=10, pady=5
        )

    else:
        abholung_label.grid_remove()
        abholung_entry.grid_remove()

    lieferkosten_aktualisieren()


# --------------------------------
# 14. AUFBAUPREIS EIN- UND AUSBLENDEN
# --------------------------------

def aufbau_aktualisieren():

    if aufbau_aktiv.get() == "Ja":

        aufbau_label.grid(
            row=10, column=0,
            sticky="w", padx=10, pady=5
        )

        aufbau_entry.grid(
            row=10, column=1,
            sticky="w", padx=10, pady=5
        )

    else:
        aufbau_label.grid_remove()
        aufbau_entry.grid_remove()
        # Beim Abwählen den alten Preis löschen, damit er nicht versehentlich
        # bei einer späteren erneuten Auswahl übernommen wird.
        aufbau_entry.delete(0, tk.END)


# --------------------------------
# 15. PDF-RECHNUNGSENTWURF ERSTELLEN
# --------------------------------

def rechnung_als_pdf_speichern():

    daten = daten_sammeln()

    if daten is None:
        return

    # Speicherort auswählen
    dateipfad = filedialog.asksaveasfilename(
        title="Rechnung als PDF speichern",
        defaultextension=".pdf",
        filetypes=[("PDF-Dateien", "*.pdf")],
        initialfile="Rechnungsentwurf.pdf"
    )

    if not dateipfad:
        return

    # PDF-Formatierung
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ArtikelText",
            parent=styles["Normal"],
            fontSize=9,
            leading=12
        )
    )

    elemente = []

    # Überschrift
    elemente.append(
        Paragraph(
            "RECHNUNGSENTWURF",
            styles["Title"]
        )
    )

    elemente.append(Spacer(1, 9 * mm))

    # ReportLab-Paragraphs interpretieren Markup. Benutzereingaben deshalb
    # mit escape() als Text behandeln; dies ist keine Anonymisierung.
    # Kundendaten
    elemente.append(
        Paragraph(
            "<b>Rechnungsempfänger</b>",
            styles["Normal"]
        )
    )

    for feld in (
        daten["name"],
        daten["anschrift"],
        daten["telefon"]
    ):

        for zeile in feld.splitlines():

            if zeile.strip():
                elemente.append(
                    Paragraph(
                        escape(zeile),
                        styles["Normal"]
                    )
                )

    elemente.append(Spacer(1, 7 * mm))

    # Rechnungsinformationen
    informationen = [
        ("Kaufdatum", daten["kaufdatum"]),
        ("Verkäufer", daten["verkaeufer"] or "-"),
        ("Lieferart", daten["art"])
    ]

    if daten["art"] == "Wohnung":

        etagen_text = (
            "EG"
            if daten["etage"] == "EG"
            else daten["etage"] + ". OG"
        )

        informationen.append(
            ("Etage", etagen_text)
        )

    if daten["art"] == "Abholung":

        informationen.append(
            ("Abholung bis", daten["abholdatum"])
        )

    # Bekannte Einschränkung: Ein gefülltes Lieferdatum erscheint derzeit auch
    # bei „Keine Lieferung“, obwohl es für diese Auswahl nicht geprüft wird.
    elif daten["lieferdatum"]:

        informationen.append(
            ("Lieferdatum", daten["lieferdatum"])
        )

    for titel, wert in informationen:

        elemente.append(
            Paragraph(
                f"<b>{titel}:</b> {escape(wert)}",
                styles["Normal"]
            )
        )

    elemente.append(Spacer(1, 9 * mm))

    # Artikeltabelle
    zeilen = [[
        "Artikel",
        "Menge",
        "Einzelpreis",
        "Gesamt"
    ]]

    for (
        bezeichnung,
        anzahl,
        einzelpreis,
        positionspreis
    ) in daten["positionen"]:

        zeilen.append([
            Paragraph(
                escape(bezeichnung),
                styles["ArtikelText"]
            ),
            str(anzahl),
            euro(einzelpreis),
            euro(positionspreis)
        ])

    # Paragraph erlaubt Umbrüche bei langen Artikelbezeichnungen; repeatRows
    # wiederholt die Tabellenüberschrift beim Aufteilen über mehrere Seiten.
    artikel_tabelle = Table(
        zeilen,
        colWidths=[
            75 * mm,
            20 * mm,
            35 * mm,
            40 * mm
        ],
        repeatRows=1,
        hAlign="LEFT"
    )

    artikel_tabelle.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0), (-1, 0),
                colors.HexColor("#E5E7EB")
            ),
            (
                "FONTNAME",
                (0, 0), (-1, 0),
                "Helvetica-Bold"
            ),
            (
                "VALIGN",
                (0, 0), (-1, -1),
                "TOP"
            ),
            (
                "ALIGN",
                (1, 1), (-1, -1),
                "RIGHT"
            ),
            (
                "TOPPADDING",
                (0, 0), (-1, -1),
                7
            ),
            (
                "BOTTOMPADDING",
                (0, 0), (-1, -1),
                7
            ),
            (
                "LINEBELOW",
                (0, 0), (-1, 0),
                0.8, colors.grey
            ),
            (
                "LINEBELOW",
                (0, 1), (-1, -1),
                0.25, colors.lightgrey
            )
        ])
    )

    elemente.append(artikel_tabelle)
    elemente.append(Spacer(1, 9 * mm))

    # Summenberechnung
    summen = [
        ["Warenwert:", euro(daten["warenwert"])],
        ["Lieferkosten:", euro(daten["lieferkosten"])],
        ["Aufbaukosten:", euro(daten["aufbaukosten"])],
        ["GESAMTBETRAG:", euro(daten["gesamt"])]
    ]

    summen_tabelle = Table(
        summen,
        colWidths=[
            105 * mm,
            65 * mm
        ],
        hAlign="LEFT"
    )

    summen_tabelle.setStyle(
        TableStyle([
            (
                "ALIGN",
                (1, 0), (1, -1),
                "RIGHT"
            ),
            (
                "TOPPADDING",
                (0, 0), (-1, -1),
                6
            ),
            (
                "BOTTOMPADDING",
                (0, 0), (-1, -1),
                6
            ),
            (
                "LINEABOVE",
                (0, -1), (-1, -1),
                1, colors.black
            ),
            (
                "FONTNAME",
                (0, -1), (-1, -1),
                "Helvetica-Bold"
            ),
            (
                "FONTSIZE",
                (0, -1), (-1, -1),
                12
            )
        ])
    )

    elemente.append(summen_tabelle)
    elemente.append(Spacer(1, 12 * mm))

    elemente.append(
        Paragraph(
            "Entwurf – vollständige Rechnungsstellerdaten, "
            "Rechnungsnummer und Steuerangaben "
            "sind noch zu ergänzen.",
            styles["Normal"]
        )
    )

    # Die Ausgabe bleibt ein Entwurf; fehlende Rechnungsangaben werden oben
    # im Dokument benannt. Erst build() schreibt das PDF an den gewählten Ort.
    # PDF speichern
    try:

        pdf = SimpleDocTemplate(
            dateipfad,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm
        )

        pdf.build(elemente)

    except Exception as fehler:

        messagebox.showerror(
            "PDF-Fehler",
            f"PDF konnte nicht erstellt werden:\n{fehler}"
        )
        return

    messagebox.showinfo(
        "PDF erstellt",
        f"Gespeichert unter:\n{dateipfad}"
    )


# --------------------------------
# 16. GUI: KUNDENDATEN
# --------------------------------

kunden_frame = tk.Frame(fenster)
kunden_frame.pack(padx=20, pady=20)

name_label = tk.Label(
    kunden_frame,
    text="Name:"
)
name_label.grid(row=0, column=0, padx=10, pady=5)

name_entry = tk.Entry(kunden_frame, width=45)
name_entry.grid(row=0, column=1, padx=10, pady=5)

anschrift_label = tk.Label(
    kunden_frame,
    text="Anschrift:"
)
anschrift_label.grid(row=1, column=0, padx=10, pady=5)

anschrift_entry = tk.Entry(kunden_frame, width=45)
anschrift_entry.grid(row=1, column=1, padx=10, pady=5)

telefon_label = tk.Label(
    kunden_frame,
    text="Telefon:"
)
telefon_label.grid(row=2, column=0, padx=10, pady=5)

telefon_entry = tk.Entry(kunden_frame, width=45)
telefon_entry.grid(row=2, column=1, padx=10, pady=5)


# --------------------------------
# 17. GUI: ARTIKELPOSITIONEN
# --------------------------------

artikel_frame = tk.Frame(fenster)
artikel_frame.pack(padx=20, pady=20)

tk.Label(
    artikel_frame,
    text="Artikel"
).grid(row=0, column=0, padx=5)

tk.Label(
    artikel_frame,
    text="Menge"
).grid(row=0, column=1, padx=5)

tk.Label(
    artikel_frame,
    text="Einzelpreis (€)"
).grid(row=0, column=2, padx=5)

tk.Label(
    artikel_frame,
    textvariable=warenwert_text,
    font=("Arial", 12, "bold")
).grid(
    row=0, column=3,
    padx=10, pady=5
)

# Erst nach dem Erstellen von artikel_frame aufrufen: Die Funktion benötigt
# diesen Container und legt mindestens eine bearbeitbare Position an.
# Erste Artikelposition
artikel_hinzufuegen()

# Weitere Artikel
artikel_button = tk.Button(
    fenster,
    text="+ Artikel hinzufügen",
    command=artikel_hinzufuegen
)

artikel_button.pack(pady=10)


# --------------------------------
# 18. GUI: VERKAUFSDATEN
# --------------------------------

verkauf_frame = tk.Frame(fenster)
verkauf_frame.pack(anchor="w", padx=20, pady=20)

# Kaufdatum
tk.Label(
    verkauf_frame,
    text="Kaufdatum:"
).grid(
    row=0, column=0,
    sticky="w", padx=10, pady=5
)

kaufdatum_entry = tk.Entry(
    verkauf_frame,
    width=12
)

kaufdatum_entry.grid(
    row=0, column=1,
    sticky="w", padx=10, pady=5
)

kaufdatum_entry.insert(
    0,
    date.today().strftime("%d.%m.%Y")
)

# Lieferdatum
tk.Label(
    verkauf_frame,
    text="Lieferdatum:"
).grid(
    row=1, column=0,
    sticky="w", padx=10, pady=5
)

lieferdatum_entry = tk.Entry(
    verkauf_frame,
    width=12
)

lieferdatum_entry.grid(
    row=1, column=1,
    sticky="w", padx=10, pady=5
)

# Verkäufer
tk.Label(
    verkauf_frame,
    text="Verkäufer:"
).grid(
    row=2, column=0,
    sticky="w", padx=10, pady=5
)

verkaeufer_entry = tk.Entry(
    verkauf_frame,
    width=20
)

verkaeufer_entry.grid(
    row=2, column=1,
    sticky="w", padx=10, pady=5
)


# --------------------------------
# 19. GUI: LIEFERUNG UND ABHOLUNG
# --------------------------------

# Abholung
tk.Radiobutton(
    verkauf_frame,
    text="Abholung",
    variable=lieferart,
    value="Abholung",
    command=lieferoptionen_aktualisieren
).grid(
    row=3, column=0,
    sticky="w", padx=10, pady=5
)

# Keine Lieferung
tk.Radiobutton(
    verkauf_frame,
    text="Keine Lieferung",
    variable=lieferart,
    value="Keine Lieferung",
    command=lieferoptionen_aktualisieren
).grid(
    row=4, column=0,
    sticky="w", padx=10, pady=5
)

# Treppenhaus
tk.Radiobutton(
    verkauf_frame,
    text="Bis Treppenhaus",
    variable=lieferart,
    value="Treppenhaus",
    command=lieferoptionen_aktualisieren
).grid(
    row=5, column=0,
    sticky="w", padx=10, pady=5
)

# Wohnung
tk.Radiobutton(
    verkauf_frame,
    text="Bis in die Wohnung",
    variable=lieferart,
    value="Wohnung",
    command=lieferoptionen_aktualisieren
).grid(
    row=6, column=0,
    sticky="w", padx=10, pady=5
)

# Abholdatum
abholung_label = tk.Label(
    verkauf_frame,
    text="Abholung bis:"
)

abholung_entry = tk.Entry(
    verkauf_frame,
    width=12
)

# Etage
etage_label = tk.Label(
    verkauf_frame,
    text="Etage:"
)

etage_dropdown = tk.OptionMenu(
    verkauf_frame,
    etage,
    "EG",
    *[str(n) for n in range(1, 21)]
)

# Lieferkostenanzeige
tk.Label(
    verkauf_frame,
    text="Lieferkosten:"
).grid(
    row=8, column=0,
    sticky="w", padx=10, pady=10
)

tk.Label(
    verkauf_frame,
    textvariable=lieferkosten_text,
    font=("Arial", 12, "bold")
).grid(
    row=8, column=1,
    sticky="w", padx=10, pady=10
)

# Lieferkosten bei Etagenänderung aktualisieren
etage.trace_add(
    "write",
    lieferkosten_aktualisieren
)

lieferoptionen_aktualisieren()


# --------------------------------
# 20. GUI: AUFBAUOPTIONEN
# --------------------------------

tk.Label(
    verkauf_frame,
    text="Aufbau gewünscht?"
).grid(
    row=9, column=0,
    sticky="w", padx=10, pady=5
)

tk.Radiobutton(
    verkauf_frame,
    text="Nein",
    variable=aufbau_aktiv,
    value="Nein",
    command=aufbau_aktualisieren
).grid(
    row=9, column=1,
    sticky="w", padx=10, pady=5
)

tk.Radiobutton(
    verkauf_frame,
    text="Ja",
    variable=aufbau_aktiv,
    value="Ja",
    command=aufbau_aktualisieren
).grid(
    row=9, column=2,
    sticky="w", padx=10, pady=5
)

aufbau_label = tk.Label(
    verkauf_frame,
    text="Aufbaupreis (€):"
)

aufbau_entry = tk.Entry(
    verkauf_frame,
    width=12
)

aufbau_aktualisieren()


# --------------------------------
# 21. GUI: VORSCHAU UND PDF-EXPORT
# --------------------------------

tk.Button(
    fenster,
    text="Daten anzeigen",
    command=daten_anzeigen
).pack(pady=5)

tk.Button(
    fenster,
    text="Rechnung als PDF speichern",
    command=rechnung_als_pdf_speichern,
    font=("Arial", 11, "bold")
).pack(pady=10)


# --------------------------------
# 22. PROGRAMM STARTEN
# --------------------------------

# Ab hier verarbeitet Tkinter Benutzereingaben und ruft registrierte Callbacks auf.
fenster.mainloop()
