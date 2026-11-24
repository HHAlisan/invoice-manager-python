"""Dialog für die Absenderdaten."""
from tkinter import messagebox, simpledialog, ttk

from .einstellungen import FIRMENDATEN_DATEI, firmendaten_laden, json_speichern


def eingabefelder(parent, daten, felder):
    eingaben = {}
    for row, (schluessel, label) in enumerate(felder):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=3)
        entry = ttk.Entry(parent, width=34)
        entry.insert(0, daten.get(schluessel, ""))
        entry.grid(row=row, column=1, sticky="ew", pady=3)
        eingaben[schluessel] = entry
    return eingaben


class FirmendatenDialog(simpledialog.Dialog):
    def body(self, parent):
        try:
            daten = firmendaten_laden()
        except (OSError, ValueError) as fehler:
            messagebox.showwarning("Firmendaten", str(fehler), parent=self)
            daten = {}
        self.felder = eingabefelder(parent, daten, (
            ("name", "Name / Firma"), ("anschrift", "Straße und Hausnummer"),
            ("ort", "Postleitzahl und Ort"), ("telefon", "Telefon"), ("email", "E-Mail"),
            ("bank", "Kreditinstitut"), ("iban", "IBAN"), ("bic", "BIC"),
        ))
        return self.felder["name"]

    def validate(self):
        try:
            json_speichern(FIRMENDATEN_DATEI, {k: entry.get().strip() for k, entry in self.felder.items()})
        except OSError as fehler:
            messagebox.showerror("Firmendaten", str(fehler), parent=self)
            return False
        return True
