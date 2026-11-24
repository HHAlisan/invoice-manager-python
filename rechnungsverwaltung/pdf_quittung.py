"""PDF-Ausgabe für Quittungen, Rechnungen und Reservierungen."""
from decimal import Decimal, ROUND_HALF_UP
from html import escape
from pathlib import Path

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FONT_ORDNER = Path(reportlab.__file__).parent / "fonts"
pdfmetrics.registerFont(TTFont("Vera", str(FONT_ORDNER / "Vera.ttf")))
pdfmetrics.registerFont(TTFont("Vera-Bold", str(FONT_ORDNER / "VeraBd.ttf")))
GRAU = colors.HexColor("#E9EEF2")
DUNKEL = colors.HexColor("#24333D")
MWST_SATZ = Decimal("0.19")

NORMAL = ParagraphStyle("Normal", fontName="Vera", fontSize=10, leading=14)
FETT = ParagraphStyle("Fett", parent=NORMAL, fontName="Vera-Bold")
TITEL = ParagraphStyle("Titel", parent=FETT, fontSize=21, leading=26, textColor=DUNKEL)
ABSENDER = ParagraphStyle("Absender", parent=FETT, fontSize=13, leading=18)
ZAHL = ParagraphStyle("Zahl", parent=NORMAL, alignment=TA_RIGHT)
ZAHL_FETT = ParagraphStyle("ZahlFett", parent=FETT, alignment=TA_RIGHT)


def euro(wert):
    return f"{wert:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def absatz(text, stil=NORMAL):
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), stil)


def summen(daten, reservierung):
    betrag = daten["anzahlung"] if reservierung else daten["gesamt"]
    netto = (betrag / (1 + MWST_SATZ)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    zeilen = [
        ("Warenwert", daten["warenwert"]),
        ("Lieferkosten", daten["lieferkosten"]),
        ("Aufbaukosten", daten["aufbaukosten"]),
    ]
    if reservierung:
        return zeilen + [
            ("Anzahlung", betrag), ("Nettowert der Anzahlung", netto),
            ("19 % MwSt. der Anzahlung", betrag - netto),
            ("Restbetrag", daten["gesamt"] - betrag), ("Gesamtbetrag", daten["gesamt"]),
        ]
    return zeilen + [("Nettowert", netto), ("19 % MwSt.", betrag - netto), ("Gesamtbetrag", betrag)]


def seitennummer(canvas, dokument):
    canvas.setFont("Vera", 8)
    canvas.setFillColor(DUNKEL)
    canvas.drawRightString(A4[0] - dokument.rightMargin, 11 * mm, f"Seite {dokument.page}")


def quittung_speichern(dateipfad, daten):
    dokumentart = daten.get("dokumentart", "Quittung")
    rechnung = dokumentart == "Rechnung"
    reservierung = dokumentart == "Kostenvoranschlag / Reservierungsbestätigung"
    firma = daten.get("firma") or {}
    doc = SimpleDocTemplate(
        str(dateipfad), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=16 * mm, bottomMargin=20 * mm, title=dokumentart,
        author=firma.get("name", ""), subject=dokumentart,
    )
    inhalt = []
    if firma.get("name"):
        inhalt.append(absatz(firma["name"], ABSENDER))
    inhalt.extend(absatz(firma[k]) for k in ("anschrift", "ort", "telefon", "email") if firma.get(k))
    if inhalt:
        inhalt.append(Spacer(1, 8 * mm))

    inhalt.extend([
        absatz(dokumentart, TITEL), Spacer(1, 4 * mm),
        absatz("Datum: " + daten["kaufdatum"]), Spacer(1, 3 * mm),
        absatz(daten["name"], FETT), absatz(daten["anschrift"]), absatz("Telefon: " + daten["telefon"]),
        Spacer(1, 4 * mm),
    ])
    if rechnung and daten.get("verwendungszweck"):
        inhalt.append(absatz("Verwendungszweck: " + daten["verwendungszweck"]))
    elif reservierung:
        inhalt.append(absatz("Reserviert bis: " + daten["reserviert_bis"], FETT))
    if daten["art"] == "Abholung":
        inhalt.append(absatz("Abholung bis: " + daten["abholdatum"]))
    elif daten["art"] in ("Treppenhaus", "Wohnung"):
        lieferung = "Lieferung bis ins Treppenhaus"
        if daten["art"] == "Wohnung":
            etage = "EG" if daten["etage"] == "EG" else daten["etage"] + ". OG"
            lieferung = f"Lieferung in die Wohnung ({etage})"
            if daten.get("fahrstuhl") in ("Ja", "Nein"):
                lieferung += " · " + ("mit Fahrstuhl" if daten["fahrstuhl"] == "Ja" else "ohne Fahrstuhl")
        inhalt.append(absatz(lieferung))
        if daten.get("lieferanschrift"):
            inhalt.append(absatz("Lieferanschrift: " + daten["lieferanschrift"]))
        if daten.get("lieferdatum"):
            inhalt.append(absatz("Lieferdatum: " + daten["lieferdatum"]))

    zeilen = [[absatz("Artikel", FETT), *(absatz(label, ZAHL_FETT) for label in ("Menge", "Einzelpreis", "Gesamt"))]]
    for artikel, menge, preis, gesamt in daten["positionen"]:
        zeilen.append([absatz(artikel), absatz(menge, ZAHL), absatz(euro(preis), ZAHL), absatz(euro(gesamt), ZAHL)])
    tabelle = LongTable(zeilen, colWidths=[80 * mm, 16 * mm, 37 * mm, 40 * mm], repeatRows=1, splitInRow=1, hAlign="LEFT")
    tabelle.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GRAU), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, GRAU),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    inhalt.extend([Spacer(1, 4 * mm), tabelle])
    summenzeilen = [
        [absatz(label, FETT if label == "Gesamtbetrag" else NORMAL),
         absatz(euro(wert), ZAHL_FETT if label == "Gesamtbetrag" else ZAHL)]
        for label, wert in summen(daten, reservierung)
    ]
    summen_tabelle = Table(summenzeilen, colWidths=[55 * mm, 40 * mm], hAlign="RIGHT")
    summen_tabelle.setStyle(TableStyle([("BACKGROUND", (0, -1), (-1, -1), GRAU)]))
    inhalt.append(KeepTogether([Spacer(1, 4 * mm), summen_tabelle]))

    if daten.get("bemerkungen"):
        inhalt.extend([Spacer(1, 4 * mm), absatz("Bemerkungen", FETT), absatz(daten["bemerkungen"])])
    if rechnung and any(firma.get(k) for k in ("bank", "iban", "bic")):
        inhalt.extend([Spacer(1, 4 * mm), absatz("Bankverbindung", FETT)])
        for k, label in (("bank", ""), ("iban", "IBAN: "), ("bic", "BIC: ")):
            if firma.get(k):
                inhalt.append(absatz(label + firma[k]))

    abschluss = [Spacer(1, 5 * mm), absatz("Mitarbeiter: " + daten["verkaeufer"])]
    if dokumentart == "Quittung" or (reservierung and daten["anzahlung"] > 0):
        abschluss.append(absatz("Betrag erhalten"))
    if dokumentart == "Quittung":
        abschluss.append(absatz("Ware erhalten: ____________________    Datum: ____________________"))
    inhalt.append(KeepTogether(abschluss))
    doc.build(inhalt, onFirstPage=seitennummer, onLaterPages=seitennummer)
