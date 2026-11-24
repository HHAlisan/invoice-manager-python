"""Lokale Einstellungen und Lieferkostenberechnung."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
from shutil import copy2
import sys
from tempfile import NamedTemporaryFile

MODI = {"warenwert": "Warenwert", "entfernung": "Entfernung", "volumen": "Volumen"}
TARIF_FELDER = ("grundpreis", "treppenhaus_zuschlag", "eg_zuschlag", "og_zuschlag")
WARENWERT_GRENZEN = (50, 100, 200, 300, 400, 500, 600, 700, 800, 1000, 1500)

# Fiktive Beispieltabelle. Vor der geschäftlichen Verwendung eigene Tarife hinterlegen.
STANDARD_EINSTELLUNGEN = {
    "aktives_modell": "warenwert",
    "warenwert": [
        {"bis": grenze, "treppenhaus": treppenhaus, "eg": eg, "og": og}
        for grenzen, (treppenhaus, eg, og) in (
            (WARENWERT_GRENZEN[:2], (12, 20, 4)),
            (WARENWERT_GRENZEN[2:6], (30, 45, 8)),
            (WARENWERT_GRENZEN[6:], (55, 70, 12)),
        )
        for grenze in grenzen
    ],
    "entfernung": dict.fromkeys((*TARIF_FELDER, "preis_pro_km"), 0),
    "volumen": dict.fromkeys((*TARIF_FELDER, "preis_pro_m3"), 0),
}


def lokaler_ordner():
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Quittung"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Quittung"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "quittung"


EINSTELLUNGEN_DATEI = lokaler_ordner() / "lieferpreise.json"
FIRMENDATEN_DATEI = lokaler_ordner() / "firmendaten.json"


def positive_zahl(wert, *, null_erlaubt=True, nachkommastellen=None):
    try:
        zahl = Decimal(str(wert).strip().replace(",", "."))
        if zahl.is_finite() and (zahl >= 0 if null_erlaubt else zahl > 0):
            if nachkommastellen is not None and zahl.as_tuple().exponent < -nachkommastellen:
                raise ValueError(f"Bitte höchstens {nachkommastellen} Nachkommastellen eingeben.")
            return zahl
    except InvalidOperation:
        pass
    raise ValueError("Bitte einen gültigen positiven Zahlenwert eingeben."
                     if not null_erlaubt else "Bitte einen gültigen, nicht negativen Zahlenwert eingeben.")


def einstellungen_pruefen(daten, *, nachkommastellen=None):
    try:
        if daten["aktives_modell"] not in MODI or not daten["warenwert"]:
            raise ValueError("Bitte ein Modell und mindestens eine Warenwertstufe angeben.")
        letzte_grenze = Decimal(0)
        for stufe in daten["warenwert"]:
            grenze = positive_zahl(stufe["bis"], null_erlaubt=False)
            if grenze <= letzte_grenze:
                raise ValueError("Warenwertgrenzen müssen streng aufsteigend sein.")
            letzte_grenze = grenze
            for feld in ("treppenhaus", "eg", "og"):
                positive_zahl(stufe[feld], nachkommastellen=nachkommastellen)
        for modell, preisfeld in (("entfernung", "preis_pro_km"), ("volumen", "preis_pro_m3")):
            for feld in (*TARIF_FELDER, preisfeld):
                positive_zahl(daten[modell][feld], nachkommastellen=nachkommastellen)
    except (TypeError, KeyError) as fehler:
        raise ValueError("Die Lieferpreise sind unvollständig oder ungültig.") from fehler


def json_speichern(pfad, daten):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    temp_pfad = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=pfad.parent, delete=False) as datei:
            temp_pfad = Path(datei.name)
            json.dump(daten, datei, ensure_ascii=False, indent=2)
            datei.write("\n")
        temp_pfad.replace(pfad)
    finally:
        if temp_pfad is not None:
            temp_pfad.unlink(missing_ok=True)


def einstellungen_laden():
    try:
        daten = json.loads(EINSTELLUNGEN_DATEI.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return deepcopy(STANDARD_EINSTELLUNGEN)
    einstellungen_pruefen(daten)
    return daten


def einstellungen_speichern(daten):
    einstellungen_pruefen(daten, nachkommastellen=2)
    if EINSTELLUNGEN_DATEI.exists():
        copy2(EINSTELLUNGEN_DATEI, EINSTELLUNGEN_DATEI.with_suffix(".json.bak"))
    json_speichern(EINSTELLUNGEN_DATEI, daten)


def firmendaten_laden():
    try:
        daten = json.loads(FIRMENDATEN_DATEI.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(daten, dict) or any(not isinstance(wert, str) for wert in daten.values()):
        raise ValueError("Firmendaten müssen als JSON-Objekt mit Textwerten vorliegen.")
    return daten


def passwort_hash(passwort, salz=None):
    salz = salz if salz is not None else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", passwort.encode("utf-8"), salz, 600_000)
    return {"salz": salz.hex(), "hash": digest.hex()}


def passwort_stimmt(passwort, eintrag):
    erwartet = passwort_hash(passwort, bytes.fromhex(eintrag["salz"]))
    return hmac.compare_digest(erwartet["hash"], eintrag["hash"])


def lieferkosten_berechnen(einstellungen, warenwert, lieferart, etage,
                           fahrstuhlpauschale=None, liefermenge=None):
    if lieferart in ("Abholung", "Keine Lieferung"):
        return Decimal("0.00")
    if warenwert <= 0:
        raise ValueError("Der Warenwert muss für eine Lieferung positiv sein.")
    modell = einstellungen["aktives_modell"]
    if modell == "warenwert":
        tabelle = einstellungen[modell]
        stufe = next((stufe for stufe in tabelle if warenwert <= positive_zahl(stufe["bis"])), tabelle[-1])
        grundpreis = Decimal(0)
        treppenhaus, eg, og = (positive_zahl(stufe[k]) for k in ("treppenhaus", "eg", "og"))
    else:
        tarif = einstellungen[modell]
        preisfeld = "preis_pro_km" if modell == "entfernung" else "preis_pro_m3"
        grundpreis, treppenhaus, eg, og = (positive_zahl(tarif[k]) for k in TARIF_FELDER)
        grundpreis += positive_zahl(
            liefermenge, null_erlaubt=False, nachkommastellen=2
        ) * positive_zahl(tarif[preisfeld])
    if lieferart == "Treppenhaus":
        preis = grundpreis + treppenhaus
    else:
        if etage != "EG" and (etage not in {str(n) for n in range(1, 21)}):
            raise ValueError("Bitte eine Etage auswählen.")
        etagen = 0 if etage == "EG" else int(etage)
        zuschlag = etagen * og if fahrstuhlpauschale is None else fahrstuhlpauschale
        preis = grundpreis + eg + zuschlag
    return preis.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
