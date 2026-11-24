"""Einfaches Einstellungsfenster; Änderungen werden erst nach Passwort übernommen."""
from copy import deepcopy
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from .einstellungen import (
    STANDARD_EINSTELLUNGEN, einstellungen_pruefen, einstellungen_speichern, passwort_hash, passwort_stimmt,
)

NAMEN = {"warenwert": "Nach Warenwert (€)", "entfernung": "Nach Entfernung (km)",
         "volumen": "Nach Volumen (m³)"}
FELDER = {
    "grundpreis": "Grundpreis (€)",
    "preis_pro_km": "Preis je Kilometer (€)",
    "preis_pro_m3": "Preis je Kubikmeter (€)",
    "treppenhaus_zuschlag": "Zuschlag Treppenhaus (€)",
    "eg_zuschlag": "Zuschlag Wohnung EG (€)",
    "og_zuschlag": "Zuschlag je Obergeschoss (€)",
}


def oeffnen(master, aktuelle_einstellungen, nach_speichern):
    kennwort = aktuelle_einstellungen.get("passwort")
    fenster = tk.Toplevel(master)
    fenster.title("Lieferpreise · Einstellungen")
    fenster.geometry("790x690")
    fenster.minsize(640, 480)
    fenster.transient(master)
    fenster.grab_set()
    fenster.protocol("WM_DELETE_WINDOW", fenster.destroy)
    arbeit = deepcopy(aktuelle_einstellungen)
    modell = tk.StringVar(value=arbeit["aktives_modell"])

    kopf = ttk.Frame(fenster, padding=16)
    kopf.pack(fill="x")
    ttk.Label(kopf, text="Lieferpreise festlegen", font=("Helvetica", 17, "bold")).pack(anchor="w")
    ttk.Label(kopf, text="Ein Modell gilt für alle neuen Vorgänge. Andere Preislisten bleiben erhalten.").pack(anchor="w", pady=6)
    zeile = ttk.Frame(kopf)
    zeile.pack(fill="x", pady=(8, 0))
    ttk.Label(zeile, text="Berechnung nach:").pack(side="left", padx=(0, 12))
    auswahl = ttk.Combobox(zeile, width=26, state="readonly", values=list(NAMEN.values()))
    auswahl.set(NAMEN[modell.get()])
    auswahl.pack(side="left")

    bereich = ttk.Frame(fenster, padding=(16, 8))
    bereich.pack(fill="both", expand=True)
    canvas = tk.Canvas(bereich, highlightthickness=0)
    scrollbar = ttk.Scrollbar(bereich, orient="vertical", command=canvas.yview)
    innen = ttk.Frame(canvas, padding=8)
    innen.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=innen, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    eingaben = []

    def feld(parent, value, breite=12):
        var = tk.StringVar(value=str(value).replace(".", ","))
        ttk.Entry(parent, textvariable=var, width=breite).pack(side="left", padx=(0, 10))
        return var

    def sammeln():
        ziel = modell.get()
        if ziel == "warenwert":
            stufen = []
            for werte in eingaben:
                grenze = werte["bis"].get().strip().replace(",", ".")
                try:
                    stufe = {"bis": int(grenze)}
                except ValueError:
                    stufe = {"bis": grenze}
                for schluessel in ("treppenhaus", "eg", "og"):
                    stufe[schluessel] = werte[schluessel].get().strip().replace(",", ".")
                stufen.append(stufe)
            arbeit["warenwert"] = stufen
        else:
            arbeit[ziel] = {key: var.get().strip().replace(",", ".") for key, var in eingaben}
        arbeit["aktives_modell"] = ziel

    def anzeigen():
        for widget in innen.winfo_children():
            widget.destroy()
        eingaben.clear()
        canvas.yview_moveto(0)
        if modell.get() == "warenwert":
            ttk.Label(innen, text="Preisstufen (bis einschließlich) · Preise in Euro").grid(
                row=0, column=0, columnspan=4, sticky="w", pady=(0, 14))
            for spalte, titel in enumerate(("Bis Warenwert (€)", "Treppenhaus (€)", "Wohnung EG (€)", "Je OG (€)")):
                ttk.Label(innen, text=titel).grid(row=1, column=spalte, sticky="w", padx=4)
            for nummer, stufe in enumerate(arbeit["warenwert"], 2):
                werte = {}
                for spalte, key in enumerate(("bis", "treppenhaus", "eg", "og")):
                    var = tk.StringVar(value=str(stufe[key]).replace(".", ","))
                    ttk.Entry(innen, textvariable=var, width=15).grid(
                        row=nummer, column=spalte, sticky="w", padx=4, pady=4)
                    werte[key] = var
                eingaben.append(werte)
            ttk.Label(innen, text="Oberhalb der höchsten Stufe gilt deren Preis.", foreground="#666").grid(
                row=len(arbeit["warenwert"]) + 2, column=0, columnspan=4, sticky="w", pady=10)
        else:
            ttk.Label(innen, text="Bitte die Preise selbst festlegen. 0 bedeutet kein Aufpreis.").pack(anchor="w", pady=(0, 12))
            for key, wert in arbeit[modell.get()].items():
                row = ttk.Frame(innen)
                row.pack(fill="x", pady=6)
                ttk.Label(row, text=FELDER[key], width=32).pack(side="left")
                eingaben.append((key, feld(row, wert)))

    def wechseln(event=None):
        sammeln()
        modell.set(next(key for key, name in NAMEN.items() if name == auswahl.get()))
        anzeigen()

    auswahl.bind("<<ComboboxSelected>>", wechseln)

    def standard():
        if not messagebox.askyesno("Standardwerte", "Alle Preislisten auf die Standardwerte zurücksetzen?\nErst Speichern übernimmt die Änderung.", parent=fenster):
            return
        arbeit.clear()
        arbeit.update(deepcopy(STANDARD_EINSTELLUNGEN))
        modell.set(arbeit["aktives_modell"])
        auswahl.set(NAMEN[modell.get()])
        anzeigen()

    def speichern():
        sammeln()
        try:
            daten = deepcopy(arbeit)
            einstellungen_pruefen(daten, nachkommastellen=2)
            if kennwort is None:
                pw = simpledialog.askstring(
                    "Passwort einrichten", "Passwort für die Lieferpreise (mindestens 8 Zeichen):",
                    show="*", parent=fenster,
                )
                if pw is None:
                    return
                if len(pw) < 8:
                    raise ValueError("Das Passwort benötigt mindestens 8 Zeichen.")
                bestaetigung = simpledialog.askstring(
                    "Passwort bestätigen", "Passwort wiederholen:", show="*", parent=fenster,
                )
                if bestaetigung is None:
                    return
                if bestaetigung != pw:
                    raise ValueError("Die Passwörter stimmen nicht überein.")
                daten["passwort"] = passwort_hash(pw)
            else:
                pw = simpledialog.askstring("Administrator", "Passwort zum Speichern:", show="*", parent=fenster)
                if pw is None:
                    return
                if not passwort_stimmt(pw, kennwort):
                    raise ValueError("Das Passwort ist nicht korrekt.")
                daten["passwort"] = kennwort
            einstellungen_speichern(daten)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            messagebox.showerror("Speichern fehlgeschlagen", str(exc), parent=fenster)
            return
        nach_speichern(daten)
        messagebox.showinfo("Gespeichert", "Die Lieferpreise wurden gespeichert und sind jetzt aktiv.", parent=fenster)
        fenster.destroy()

    buttons = ttk.Frame(fenster, padding=16)
    buttons.pack(fill="x")
    ttk.Button(buttons, text="Standardwerte", command=standard).pack(side="left")
    ttk.Button(buttons, text="Abbrechen", command=fenster.destroy).pack(side="right")
    ttk.Button(buttons, text="Mit Passwort speichern", command=speichern).pack(side="right", padx=12)
    anzeigen()
