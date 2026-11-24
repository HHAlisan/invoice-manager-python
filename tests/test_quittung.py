import itertools
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from datenhaltung import einstellungen
from kundenverwaltung.kundendatenbank import Kundendatenbank
from rechnungsverwaltung.pdf_quittung import quittung_speichern, summen


def beispieldaten(dokumentart="Quittung"):
    return {
        "dokumentart": dokumentart, "name": "Alex Beispiel", "anschrift": "Musterweg 1",
        "telefon": "01234 000000", "kaufdatum": "24.11.2026", "verkaeufer": "Sam Beispiel",
        "art": "Wohnung", "etage": "2", "fahrstuhl": "Ja", "lieferdatum": "26.11.2026",
        "lieferanschrift": "Beispielweg 5", "reserviert_bis": "28.11.2026",
        "verwendungszweck": "Beleg DEMO-001", "bemerkungen": "Fiktiver Vorgang für die Dokumentation.",
        "positionen": [("Artikel A", 2, Decimal("30"), Decimal("60")),
                      ("Artikel B", 1, Decimal("25"), Decimal("25"))],
        "warenwert": Decimal("85"), "lieferkosten": Decimal("28"), "aufbaukosten": Decimal("15"),
        "gesamt": Decimal("128"), "anzahlung": Decimal("25"),
        "firma": {"name": "Beispielbetrieb", "anschrift": "Beispielstraße 10", "ort": "12345 Musterstadt",
                  "email": "kontakt@example.com"},
    }


class LieferkostenTest(unittest.TestCase):
    def setUp(self):
        self.tarife = deepcopy(einstellungen.STANDARD_EINSTELLUNGEN)

    def test_warenwert_und_fahrstuhl(self):
        self.assertEqual(einstellungen.lieferkosten_berechnen(
            self.tarife, Decimal("85"), "Wohnung", "2"
        ), Decimal("28"))
        self.assertEqual(einstellungen.lieferkosten_berechnen(
            self.tarife, Decimal("85"), "Wohnung", "2", Decimal("7")
        ), Decimal("27"))

    def test_entfernung_volumen_und_abholung(self):
        for modell, preisfeld, faktor, preis in (
            ("entfernung", "preis_pro_km", 2, "25"),
            ("volumen", "preis_pro_m3", 5, "40"),
        ):
            with self.subTest(modell=modell):
                self.tarife["aktives_modell"] = modell
                self.tarife[modell].update({"grundpreis": 12, "treppenhaus_zuschlag": 3, preisfeld: faktor})
                self.assertEqual(einstellungen.lieferkosten_berechnen(
                    self.tarife, Decimal("85"), "Treppenhaus", "", liefermenge="5"
                ), Decimal(preis))
                self.assertEqual(einstellungen.lieferkosten_berechnen(
                    self.tarife, Decimal("85"), "Abholung", ""
                ), 0)
                with self.assertRaises(ValueError):
                    einstellungen.lieferkosten_berechnen(self.tarife, Decimal("85"), "Treppenhaus", "")
                with self.assertRaises(ValueError):
                    einstellungen.lieferkosten_berechnen(
                        self.tarife, Decimal("85"), "Treppenhaus", "", liefermenge="1,234"
                    )

    def test_einstellungen_und_passwort(self):
        self.tarife["passwort"] = einstellungen.passwort_hash("test-passwort")
        with TemporaryDirectory() as ordner:
            pfad = Path(ordner) / "lieferpreise.json"
            with patch.object(einstellungen, "EINSTELLUNGEN_DATEI", pfad):
                einstellungen.einstellungen_speichern(self.tarife)
                geladen = einstellungen.einstellungen_laden()
                einstellungen.einstellungen_speichern(dict(geladen, aktives_modell="volumen"))
                self.assertEqual(einstellungen.einstellungen_laden()["aktives_modell"], "volumen")
                self.assertTrue(pfad.with_suffix(".json.bak").is_file())
        self.assertEqual(geladen, self.tarife)
        self.assertTrue(einstellungen.passwort_stimmt("test-passwort", geladen["passwort"]))
        self.assertFalse(einstellungen.passwort_stimmt("falsch", geladen["passwort"]))

    def test_ungueltige_preisstufe(self):
        self.tarife["warenwert"][1]["bis"] = self.tarife["warenwert"][0]["bis"]
        with self.assertRaises(ValueError):
            einstellungen.einstellungen_pruefen(self.tarife)


class KundendatenbankTest(unittest.TestCase):
    def test_leere_db_suche_berechtigung_und_kein_doppelter_vorgang(self):
        with TemporaryDirectory() as ordner:
            db = Kundendatenbank(Path(ordner) / "kunden.sqlite3")
            self.assertEqual(db.alle_kunden(), [])
            daten = beispieldaten()
            ident = db.speichern("erster-vorgang", None, daten, True, "2027-01-01")
            self.assertEqual(db.speichern("erster-vorgang", None, daten, False, None), ident)
            db.speichern("zweiter-vorgang", ident, daten, False, None)
            self.assertEqual(db.suchen("ALEX")[0]["id"], ident)
            kunde = db.laden(db.nummer(ident))
            self.assertEqual(kunde["letzter_einkauf"], "2026-11-24")
            self.assertEqual(kunde["gueltig_bis"], "2027-01-01")
            with db.verbindung() as verbindung:
                self.assertEqual(verbindung.execute("SELECT COUNT(*) FROM vorgaenge").fetchone()[0], 2)


class PDFTest(unittest.TestCase):
    def test_alle_dokumentarten_und_mehrseitige_tabelle(self):
        with TemporaryDirectory() as ordner:
            for index, art in enumerate(("Quittung", "Rechnung", "Kostenvoranschlag / Reservierungsbestätigung")):
                with self.subTest(art=art):
                    daten = beispieldaten(art)
                    daten["positionen"] = list(itertools.islice(itertools.cycle(daten["positionen"]), 60))
                    pfad = Path(ordner) / f"beleg-{index}.pdf"
                    quittung_speichern(pfad, daten)
                    self.assertTrue(pfad.read_bytes().startswith(b"%PDF"))
                    if art.startswith("Kostenvoranschlag"):
                        self.assertIn(("Restbetrag", Decimal("103")), summen(daten, True))
