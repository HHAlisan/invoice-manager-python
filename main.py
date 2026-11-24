import re
import uuid
from datenhaltung.dialoge import FirmendatenDialog
from datenhaltung.einstellungsfenster import oeffnen as einstellungsfenster_oeffnen
from datenhaltung.einstellungen import (
    MODI, STANDARD_EINSTELLUNGEN, einstellungen_laden, firmendaten_laden,
    lieferkosten_berechnen, positive_zahl,
)
from kundenverwaltung.kundendatenbank import Kundendatenbank
from rechnungsverwaltung.pdf_quittung import quittung_speichern
import tkinter as tk
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from tkinter import filedialog, messagebox, ttk

kundendb = Kundendatenbank()
ausgewaehlter_kunde = None
vorgang_id = str(uuid.uuid4())

fenster = tk.Tk()
fenster.title("Quittung")
try:
    liefer_einstellungen = einstellungen_laden()
except (OSError, ValueError) as fehler:
    messagebox.showwarning(
        "Lieferpreise", f"Die Lieferpreise konnten nicht geladen werden. Es gelten Beispieltarife.\n{fehler}",
        parent=fenster,
    )
    liefer_einstellungen = STANDARD_EINSTELLUNGEN

fenster.geometry("980x820")
fenster.minsize(720, 560)
BG = "#F3F5F7"
INK = "#24333D"
MUTED = "#667580"
fenster.configure(bg=BG)
fenster.option_add("*Font", "{Helvetica} 12")
style = ttk.Style(fenster)
style.theme_use("clam")
style.configure("TFrame", background="white")
style.configure("TLabel", background="white", foreground=INK, font=("Helvetica", 12))
style.configure("Hint.TLabel", foreground=MUTED, font=("Helvetica", 10))
style.configure("Title.TLabel", font=("Helvetica", 17, "bold"))
style.configure("TEntry", padding=7, fieldbackground="white", foreground=INK)
style.configure("TCombobox", padding=7, fieldbackground="white")
style.map("TCombobox", fieldbackground=[("readonly", "white")], foreground=[("readonly", INK)])
for widget_style in ("TEntry", "TCombobox"):
    style.map(widget_style,
              fieldbackground=[("invalid", "#FFF0F0"), ("readonly", "white")],
              bordercolor=[("invalid", "#B42029")],
              lightcolor=[("invalid", "#B42029")],
              darkcolor=[("invalid", "#B42029")])
style.configure("TRadiobutton", background="white", foreground=INK, padding=(0, 6, 14, 6))
style.configure("TButton", padding=(14, 9), font=("Helvetica", 11))
style.configure("Reset.TButton", padding=(9, 9), font=("Helvetica", 11))
zahnrad_schrift = "Segoe UI Symbol" if fenster.tk.call("tk", "windowingsystem") == "win32" else "TkDefaultFont"
style.configure("Settings.TMenubutton", padding=(6, 2), font=(zahnrad_schrift, 13))
style.configure("Primary.TButton", background="#235B4B", foreground="white", font=("Helvetica", 12, "bold"))
style.map("Primary.TButton", background=[("active", "#194535")])
style.configure("Danger.TButton", foreground="#A52E39", padding=(8, 6))
style.configure("Total.TLabel", font=("Helvetica", 22, "bold"), foreground="#235B4B")
header = tk.Frame(fenster, bg=BG)
header.pack(fill="x", padx=28, pady=(22, 14))
dokumentart = tk.StringVar(value="Quittung")
dokument_titel = tk.StringVar(value="Quittung erstellen")
pdf_button_text = tk.StringVar(value="Quittung speichern")
titelleiste = tk.Frame(header, bg=BG)
titelleiste.pack(fill="x")
einstellungen_button = ttk.Menubutton(
    titelleiste, text="⚙ Einstellungen", style="Settings.TMenubutton", takefocus=True
)
einstellungen_button.pack(side="right", anchor="n", padx=(12, 0))
tk.Label(titelleiste, textvariable=dokument_titel, bg=BG, fg=INK, font=("Helvetica", 24, "bold"), wraplength=600, justify="left").pack(side="left")
tk.Label(header, text="Kundendaten erfassen, Artikel hinzufügen und als PDF speichern.", bg=BG, fg=MUTED).pack(anchor="w", pady=(5, 0))
style.configure("Header.TRadiobutton", background=BG, foreground=INK,
                padding=(0, 6, 16, 6), font=("Helvetica", 11))
dokument_auswahl = tk.Frame(header, bg=BG)
dokument_auswahl.pack(fill="x", pady=(14, 0))
tk.Label(dokument_auswahl, text="Dokumentart", bg=BG, fg=INK).pack(anchor="w")
dokument_optionen = tk.Frame(dokument_auswahl, bg=BG)
dokument_optionen.pack(anchor="w", pady=(4, 0))
for label, value in (
    ("Quittung", "Quittung"),
    ("Kostenvoranschlag /\nReservierungsbestätigung", "Kostenvoranschlag / Reservierungsbestätigung"),
    ("Rechnung", "Rechnung"),
):
    ttk.Radiobutton(
        dokument_optionen, text=label, variable=dokumentart, value=value,
        style="Header.TRadiobutton"
    ).pack(side="left", anchor="n")


def dokumentart_aktualisieren(*args):
    art = dokumentart.get()
    dokument_titel.set(art + " erstellen")
    fenster.title("Quittung · " + art)
    pdf_button_text.set(("KV" if "/" in art else art) + " speichern")
    if "reservierung_card" in globals():
        if art == "Kostenvoranschlag / Reservierungsbestätigung":
            reservierung_card.pack(fill="x", padx=24, pady=(0, 16), before=bemerkungen_card)
        else:
            reservierung_card.pack_forget()
    if "rechnung_card" in globals():
        if art == "Rechnung":
            rechnung_card.pack(fill="x", padx=24, pady=(0, 16), before=bemerkungen_card)
        else:
            rechnung_card.pack_forget()


dokumentart.trace_add("write", dokumentart_aktualisieren)
footer = ttk.Frame(fenster, padding=(24, 14))
footer.pack(side="bottom", fill="x")


# Gesamtes Formular scrollbar halten, auch bei zusätzlichen Artikelzeilen.
scroll_container = tk.Frame(fenster, bg=BG)
scroll_container.pack(fill="both", expand=True)
scroll_container.rowconfigure(0, weight=1)
scroll_container.columnconfigure(0, weight=1)
formular_canvas = tk.Canvas(scroll_container, highlightthickness=0, bg=BG, yscrollincrement=12)
formular_canvas.grid(row=0, column=0, sticky="nsew")
scrollbar = tk.Scrollbar(scroll_container, orient="vertical", command=formular_canvas.yview)
scrollbar.grid(row=0, column=1, sticky="ns")
quer_scrollbar = tk.Scrollbar(scroll_container, orient="horizontal", command=formular_canvas.xview)
quer_scrollbar.grid(row=1, column=0, sticky="ew")
formular_canvas.configure(yscrollcommand=scrollbar.set, xscrollcommand=quer_scrollbar.set)
formular_frame = tk.Frame(formular_canvas, bg=BG)
formular_window = formular_canvas.create_window((0, 0), window=formular_frame, anchor="nw")


def formular_groesse_aktualisieren(event=None):
    formular_canvas.itemconfigure(
        formular_window,
        width=max(formular_canvas.winfo_width(), formular_frame.winfo_reqwidth())
    )
    formular_canvas.configure(scrollregion=formular_canvas.bbox("all"))


def formular_scrollen(event):
    if formular_frame.winfo_height() <= formular_canvas.winfo_height():
        return
    if getattr(event, "num", None) == 4:
        schritte = -3
    elif getattr(event, "num", None) == 5:
        schritte = 3
    elif fenster.tk.call("tk", "windowingsystem") == "aqua":
        schritte = -int(event.delta)
    else:
        schritte = -int(event.delta / 120)
    formular_canvas.yview_scroll(schritte, "units")


formular_frame.bind("<Configure>", formular_groesse_aktualisieren)
formular_canvas.bind("<Configure>", formular_groesse_aktualisieren)
fenster.bind("<MouseWheel>", formular_scrollen)
fenster.bind("<Button-4>", formular_scrollen)
fenster.bind("<Button-5>", formular_scrollen)

artikel_positionen = []

warenwert_text = tk.StringVar(value="– €")
lieferkosten_text = tk.StringVar(value="0,00 €")
gesamt_text = tk.StringVar(value="– €")
status_text = tk.StringVar(value="Bitte mindestens einen Artikel mit Preis eingeben.")
aufbaupreis_text = tk.StringVar(value="")

lieferart = tk.StringVar(value="Keine Lieferung")
etage = tk.StringVar(value="Bitte wählen")
fahrstuhl = tk.StringVar(value="Nein")
fahrstuhlpauschale = tk.StringVar(value="")
aufbau_aktiv = tk.StringVar(value="Nein")
liefermenge_text = tk.StringVar()


# --------------------------------
# 3. HILFSFUNKTIONEN
# --------------------------------

def euro(betrag):
    text = f"{Decimal(str(betrag)):,.2f}"

    text = text.replace(",", "X")
    text = text.replace(".", ",")
    text = text.replace("X", ".")

    return text + " €"


def datum_pruefen(text):

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

    betrag = Decimal(
        text.strip().replace(",", ".")
    )

    if not betrag.is_finite():
        raise ValueError("Ungültiger Geldbetrag")

    if betrag < 0:
        raise ValueError("Preis darf nicht negativ sein")

    if betrag.as_tuple().exponent < -2:
        raise ValueError("Maximal zwei Nachkommastellen erlaubt")

    return betrag


# --------------------------------
# 4. ARTIKEL AUSLESEN
# --------------------------------

def artikel_auslesen(mit_fehler=True):

    positionen = []
    summe = Decimal("0.00")

    for nummer, position in enumerate(
        artikel_positionen, start=1
    ):

        artikel, menge, preis, entfernen_button = position

        bezeichnung = artikel.get().strip()

        try:
            fehlerfeld = menge
            anzahl = int(menge.get())
            if anzahl < 1:
                raise ValueError(
                    "Die Menge muss mindestens 1 betragen"
                )

            fehlerfeld = preis
            einzelpreis = betrag_lesen(preis.get())
            fehlerfeld = artikel
            if mit_fehler and not bezeichnung:
                raise ValueError(
                    "Artikelbezeichnung fehlt"
                )

        except (ValueError, InvalidOperation) as fehler:

            if mit_fehler:
                eingabefehler(
                    fehlerfeld, "Artikel prüfen",
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


def liefermenge_lesen():
    if lieferart.get() in ("Treppenhaus", "Wohnung") and liefer_einstellungen["aktives_modell"] != "warenwert":
        return positive_zahl(liefermenge_text.get(), null_erlaubt=False, nachkommastellen=2)
    return None


def lieferpreise_uebernehmen(neue_einstellungen):
    global liefer_einstellungen
    altes_modell = liefer_einstellungen["aktives_modell"]
    liefer_einstellungen = neue_einstellungen
    if neue_einstellungen["aktives_modell"] != altes_modell:
        liefermenge_text.set("")
    lieferoptionen_aktualisieren()


def fahrstuhlpauschale_lesen():
    if (lieferart.get() == "Wohnung" and fahrstuhl.get() == "Ja"
            and fahrstuhlpauschale.get().strip()):
        return betrag_lesen(fahrstuhlpauschale.get())
    return None


# --------------------------------
# 6. WARENWERT AKTUALISIEREN
# --------------------------------

def warenwert_aktualisieren(event=None):

    positionen, warenwert = artikel_auslesen(
        mit_fehler=False
    )

    if warenwert is None:
        warenwert_text.set("– €")

    else:
        warenwert_text.set(euro(warenwert))

    lieferkosten_aktualisieren()


def lieferkosten_aktualisieren(*args):
    positionen, warenwert = artikel_auslesen(mit_fehler=False)
    try:
        pauschale = fahrstuhlpauschale_lesen()
        kosten = (lieferkosten_berechnen(liefer_einstellungen, warenwert, lieferart.get(),
                                         etage.get(), pauschale, liefermenge_lesen())
                  if warenwert is not None else None)
    except (ValueError, InvalidOperation):
        kosten = None
    lieferkosten_text.set(euro(kosten) if kosten is not None else "– €")

    if "lieferkosten_label" in globals():
        if kosten is not None and kosten > 0:
            lieferkosten_label.grid(row=8, column=0, sticky="w", pady=(8, 0))
            lieferkosten_wert.grid(row=8, column=1, sticky="w", pady=(8, 0))
        else:
            lieferkosten_label.grid_remove()
            lieferkosten_wert.grid_remove()
    try:
        aufbau = betrag_lesen(aufbaupreis_text.get()) if lieferart.get() == "Wohnung" and aufbau_aktiv.get() == "Ja" else Decimal("0")
        if warenwert is None:
            raise ValueError("Bitte Menge und Preis der Artikel prüfen.")
        if kosten is None:
            raise ValueError("Bitte Lieferangaben und Preise prüfen.")
        gesamt_text.set(euro(warenwert + kosten + aufbau))
        status_text.set("Warenwert " + euro(warenwert) +
                        ("  ·  Lieferung " + euro(kosten) if kosten > 0 else "") +
                        ("  ·  Aufbau " + euro(aufbau) if aufbau > 0 else ""))
    except (ValueError, InvalidOperation):
        gesamt_text.set("– €")
        status_text.set("Bitte Preise und gegebenenfalls Lieferangaben oder Zusatzkosten ergänzen.")


# --------------------------------
# 7. RECHNUNGSDATEN SAMMELN
# --------------------------------

def fehlermarkierungen_loeschen(parent):
    for widget in parent.winfo_children():
        if isinstance(widget, (ttk.Entry, ttk.Combobox)):
            widget.state(["!invalid"])
        fehlermarkierungen_loeschen(widget)


def eingabefehler(widget, titel, meldung):
    widget.state(["invalid"])
    fenster.update_idletasks()
    # Auch Fehler weiter unten im Formular direkt sichtbar machen.
    position = widget.winfo_rooty() - formular_frame.winfo_rooty()
    formular_canvas.yview_moveto(max(0, (position - 60) / max(formular_frame.winfo_height(), 1)))
    widget.focus_set()
    status_text.set(meldung)
    messagebox.showerror(titel, meldung)


def kunde_status_anzeigen():
    if ausgewaehlter_kunde is None:
        kundenstatus.set("Kein Kunde ausgewählt")
        berechtigungsstatus.set("Berechtigung nicht geprüft")
        letzter_einkauf_text.set("Letzter Einkauf: –")
        return
    kunde = kundendb.laden(kundendb.nummer(ausgewaehlter_kunde))
    kundenstatus.set("Kunde: " + kundendb.nummer(kunde['id']))
    gueltig = kunde['gueltig_bis']
    berechtigungsstatus.set("Berechtigung gültig bis: " + date.fromisoformat(gueltig).strftime("%d.%m.%Y")
                           if gueltig else "Berechtigung nicht geprüft")
    letzter = kunde['letzter_einkauf']
    letzter_einkauf_text.set("Letzter Einkauf: " + (date.fromisoformat(letzter).strftime("%d.%m.%Y") if letzter else "–"))


def namenssuche(*args):
    global ausgewaehlter_kunde, namens_treffer, neuer_kunde_bestaetigt
    if ausgewaehlter_kunde is not None:
        pruefung_zuruecksetzen()
    ausgewaehlter_kunde = None
    neuer_kunde_bestaetigt = False
    kunde_status_anzeigen()
    namens_treffer = kundendb.suchen(name_text.get())
    popup_schliessen()
    if name_text.get().strip():
        if not namens_treffer:
            kundenstatus.set("Neue Kundennummer beim Speichern")


def popup_schliessen():
    global such_popup
    if such_popup is not None:
        such_popup.destroy()
        such_popup = None


def popup_anzeigen(von_oben=False, alle=False):
    global such_popup
    suchtext = "" if alle else (kunden_suchtext.get().strip() if von_oben else name_text.get().strip())
    if (not alle and not suchtext) or (not von_oben and (ausgewaehlter_kunde is not None or neuer_kunde_bestaetigt)):
        return
    if not alle and not kundendb.suchen(suchtext) and not von_oben:
        return
    popup_schliessen()
    such_popup = tk.Toplevel(fenster)
    such_popup.title("Alle Kunden" if alle else "Kunde auswählen")
    such_popup.transient(fenster)
    such_popup.resizable(False, False)
    ttk.Label(such_popup, text="Passenden Kunden auswählen", padding=10).pack(anchor="w")
    popup_suchtext = tk.StringVar(value=suchtext)
    suche = ttk.Entry(such_popup, textvariable=popup_suchtext)
    suche.pack(fill="x", padx=10, pady=(0, 8))
    listenrahmen = ttk.Frame(such_popup)
    listenrahmen.pack(fill="both", expand=True, padx=10)
    liste = tk.Listbox(listenrahmen, height=8, activestyle="none")
    liste.pack(side="left", fill="both", expand=True)
    scrollbar = ttk.Scrollbar(listenrahmen, orient="vertical", command=liste.yview)
    scrollbar.pack(side="right", fill="y")
    liste.configure(yscrollcommand=scrollbar.set)
    sichtbare_treffer = []

    def liste_aktualisieren(*args):
        sichtbare_treffer[:] = (kundendb.suchen(popup_suchtext.get().strip())
                               if popup_suchtext.get().strip() else kundendb.alle_kunden())
        liste.delete(0, tk.END)
        for kunde in sichtbare_treffer:
            liste.insert(tk.END, f"{kunde['name']} · {kundendb.nummer(kunde['id'])}")
        if sichtbare_treffer:
            liste.selection_set(0)

    popup_suchtext.trace_add("write", liste_aktualisieren)
    liste_aktualisieren()

    def treffer_uebernehmen():
        auswahl = liste.curselection()
        if auswahl:
            kunde_auswaehlen(kundendb.nummer(sichtbare_treffer[auswahl[0]]['id']))

    liste.bind("<Double-Button-1>", lambda event: treffer_uebernehmen())
    liste.bind("<Return>", lambda event: treffer_uebernehmen())
    suche.bind("<Return>", lambda event: treffer_uebernehmen())
    ttk.Button(such_popup, text="Ausgewählten Kunden übernehmen",
               command=treffer_uebernehmen).pack(fill="x", padx=10, pady=5)
    ttk.Button(such_popup, text="Neuen Kunden anlegen",
               command=neuen_kunden_waehlen).pack(fill="x", padx=10, pady=(0, 10))
    such_popup.update_idletasks()
    breite = max(420, such_popup.winfo_reqwidth())
    hoehe = such_popup.winfo_reqheight()
    anker = kunden_suche_entry if von_oben else name_entry
    x = min(anker.winfo_rootx(), such_popup.winfo_screenwidth() - breite - 20)
    y = anker.winfo_rooty() + anker.winfo_height() + 4
    if y + hoehe > such_popup.winfo_screenheight() - 20:
        y = anker.winfo_rooty() - hoehe - 4
    such_popup.geometry(f"{breite}x{hoehe}+{max(0, x)}+{max(0, y)}")
    suche.focus_set()


def pruefung_zuruecksetzen():
    gueltigkeit_entry.configure(state="normal")
    gueltigkeit_entry.delete(0, tk.END)
    nicht_geprueft.set(True)
    berechtigung_umschalten()


def kunde_auswaehlen(nummer):
    global ausgewaehlter_kunde
    try:
        kunde = kundendb.laden(nummer)
        if kunde is None:
            messagebox.showerror("Kundensuche", "Dieser Kunde wurde nicht gefunden.")
            return
        popup_schliessen()
        if kunde['name']:
            name_text.set(kunde['name'])
        for feld, wert in ((anschrift_entry, kunde['anschrift']),
                           (telefon_entry, kunde['telefon'])):
            feld.delete(0, tk.END)
            if wert:
                feld.insert(0, wert)
        ausgewaehlter_kunde = kunde['id']
        pruefung_zuruecksetzen()
        kunde_status_anzeigen()
    except Exception as fehler:
        messagebox.showerror("Kundendatenbank", str(fehler))


def neuen_kunden_waehlen():
    global ausgewaehlter_kunde, neuer_kunde_bestaetigt
    popup_schliessen()
    ausgewaehlter_kunde = None
    neuer_kunde_bestaetigt = True
    pruefung_zuruecksetzen()
    kunde_status_anzeigen()
    kundenstatus.set("Neue Kundennummer beim Speichern")


def berechtigung_umschalten():
    gueltigkeit_entry.configure(state="disabled" if nicht_geprueft.get() else "normal")
    gueltigkeit_entry.state(["!invalid"])


def daten_sammeln():
    fehlermarkierungen_loeschen(formular_frame)
    mit_datenbank = kundendaten_speichern.get()
    if mit_datenbank and ausgewaehlter_kunde is None and namens_treffer and not neuer_kunde_bestaetigt:
        name_entry.focus_set()
        popup_anzeigen()
        messagebox.showwarning("Kunde", "Bitte einen passenden Kunden auswählen oder „Neuen Kunden anlegen“ wählen.")
        return None
    if mit_datenbank and not nicht_geprueft.get() and not datum_pruefen(gueltigkeit_entry.get().strip()):
        eingabefehler(gueltigkeit_entry, "Berechtigung", "Bitte das Gültigkeitsdatum im Format TT.MM.JJJJ eingeben oder Nicht geprüft auswählen.")
        return None

    kundenname = name_entry.get().strip()
    anschrift = anschrift_entry.get().strip()
    telefon = telefon_entry.get().strip()

    kaufdatum = kaufdatum_entry.get().strip()
    lieferdatum = (lieferdatum_entry.get().strip()
                   if lieferart.get() in ("Treppenhaus", "Wohnung") else "")
    verkaeufer = verkaeufer_entry.get().strip()

    art = lieferart.get()
    stockwerk = etage.get()
    abholdatum = abholung_entry.get().strip()

    # Kundennamen prüfen
    if not kundenname:
        eingabefehler(name_entry, "Kundendaten", "Bitte einen Kundennamen eingeben.")
        return None

    if not anschrift:
        eingabefehler(anschrift_entry, "Anschrift", "Bitte eine Anschrift eingeben.")
        anschrift_entry.focus_set()
        return None

    if not telefon:
        eingabefehler(telefon_entry, "Telefon", "Bitte eine Telefonnummer eingeben.")
        telefon_entry.focus_set()
        return None

    if not verkaeufer:
        eingabefehler(verkaeufer_entry, "Verkäufer", "Bitte den Verkäufer eingeben.")
        verkaeufer_entry.focus_set()
        return None

    # Kaufdatum prüfen
    if not datum_pruefen(kaufdatum):
        eingabefehler(kaufdatum_entry, "Kaufdatum", "Bitte ein gültiges Kaufdatum im Format TT.MM.JJJJ eingeben.")
        return None

    if datetime.strptime(
        kaufdatum, "%d.%m.%Y"
    ).date() > date.today():

        eingabefehler(kaufdatum_entry, "Kaufdatum", "Das Kaufdatum darf nicht in der Zukunft liegen.")
        return None

    # Abholdatum prüfen
    if art == "Abholung":

        if not abholdatum_pruefen(abholdatum):
            eingabefehler(abholung_entry, "Abholung", "Bitte ein gültiges Abholdatum ab heute angeben.")
            return None

    # Lieferdatum prüfen, sofern angegeben
    if art in ("Treppenhaus", "Wohnung") and lieferdatum:

        if not datum_pruefen(lieferdatum):
            eingabefehler(lieferdatum_entry, "Lieferdatum", "Bitte ein gültiges Lieferdatum eingeben.")
            return None

        if datetime.strptime(
            lieferdatum, "%d.%m.%Y"
        ).date() < date.today():

            eingabefehler(lieferdatum_entry, "Lieferdatum", "Das Lieferdatum muss heute oder in der Zukunft liegen.")
            return None

    # Etage prüfen
    if art == "Wohnung" and stockwerk == "Bitte wählen":

        eingabefehler(etage_dropdown, "Etage", "Bitte eine Etage auswählen.")
        return None

    # Artikel erfassen
    positionen, warenwert = artikel_auslesen()

    if positionen is None:
        return None

    # Fahrstuhlpauschale vor der endgültigen Berechnung prüfen.
    try:
        pauschale = fahrstuhlpauschale_lesen()
    except (ValueError, InvalidOperation):
        eingabefehler(fahrstuhlpauschale_entry, "Fahrstuhlpauschale", "Bitte einen gültigen Betrag mit maximal zwei Nachkommastellen eingeben oder das Feld leer lassen.")
        return None

    try:
        liefermenge = liefermenge_lesen()
    except ValueError as fehler:
        eingabefehler(liefermenge_entry, MODI[liefer_einstellungen["aktives_modell"]], str(fehler))
        return None

    try:
        lieferkosten = lieferkosten_berechnen(
            liefer_einstellungen, warenwert, art, stockwerk, pauschale, liefermenge
        )
    except (ValueError, InvalidOperation) as fehler:
        eingabefehler(artikel_positionen[0][2], "Lieferkosten", str(fehler))
        return None

    # Aufbaukosten prüfen
    aufbaukosten = Decimal("0.00")

    if art == "Wohnung" and aufbau_aktiv.get() == "Ja":

        try:
            aufbaukosten = betrag_lesen(
                aufbau_entry.get()
            )

        except (ValueError, InvalidOperation):
            eingabefehler(aufbau_entry, "Aufbau", "Bitte einen gültigen Aufbaupreis eingeben.")
            return None

    gesamtbetrag = (
        warenwert + lieferkosten + aufbaukosten
    )

    reserviert_bis = ""
    anzahlung = Decimal("0.00")
    if dokumentart.get() == "Kostenvoranschlag / Reservierungsbestätigung":
        reserviert_bis = reserviert_bis_entry.get().strip()
        if not abholdatum_pruefen(reserviert_bis):
            eingabefehler(reserviert_bis_entry, "Reservierungsfrist", "Bitte ein gültiges Datum ab heute im Format TT.MM.JJJJ eingeben.")
            reserviert_bis_entry.focus_set()
            return None
        try:
            anzahlung = betrag_lesen(anzahlung_entry.get())
            if anzahlung > gesamtbetrag:
                raise ValueError("Die Anzahlung darf den Gesamtbetrag nicht übersteigen.")
        except (ValueError, InvalidOperation):
            eingabefehler(anzahlung_entry, "Anzahlung", "Bitte einen gültigen Anzahlungsbetrag zwischen 0 und dem Gesamtbetrag eingeben.")
            anzahlung_entry.focus_set()
            return None

    verwendungszweck = ""
    lieferanschrift = ""
    if dokumentart.get() == "Rechnung":
        verwendungszweck = verwendungszweck_entry.get().strip()
        if not verwendungszweck:
            eingabefehler(verwendungszweck_entry, "Verwendungszweck", "Bitte einen Verwendungszweck eingeben.")
            verwendungszweck_entry.focus_set()
            return None
        if art in ("Treppenhaus", "Wohnung"):
            lieferanschrift = lieferanschrift_entry.get().strip() or anschrift

    bemerkungen = bemerkungen_entry.get("1.0", "end-1c").strip() if bemerkungen_aktiv.get() else ""
    if len(bemerkungen) > 1500:
        messagebox.showerror("Bemerkung", "Die Bemerkung darf maximal 1.500 Zeichen enthalten.", parent=fenster)
        bemerkungen_entry.focus_set()
        return None

    return {
        "dokumentart": dokumentart.get(),
        "bemerkungen": bemerkungen,
        "verwendungszweck": verwendungszweck,
        "lieferanschrift": lieferanschrift,
        "reserviert_bis": reserviert_bis,
        "anzahlung": anzahlung,
        "restbetrag": gesamtbetrag - anzahlung,
        "name": kundenname,
        "anschrift": anschrift,
        "telefon": telefon,
        "kaufdatum": kaufdatum,
        "lieferdatum": lieferdatum,
        "verkaeufer": verkaeufer,
        "art": art,
        "etage": stockwerk,
        "fahrstuhlpauschale": pauschale,
        "fahrstuhl": fahrstuhl.get() if art == "Wohnung" else None,
        "abholdatum": abholdatum,
        "positionen": positionen,
        "warenwert": warenwert,
        "lieferkosten": lieferkosten,
        "aufbaukosten": aufbaukosten,
        "gesamt": gesamtbetrag
    }


# --------------------------------
# 8. DATEN ANZEIGEN
# --------------------------------

def daten_anzeigen():

    daten = daten_sammeln()

    if daten is None:
        return

    rechnungsinfo = (
        f"\nVerwendungszweck: {daten['verwendungszweck']}"
        + (f"\nLieferung an: {daten['lieferanschrift']}" if daten['lieferanschrift'] else "")
        if daten['dokumentart'] == "Rechnung" else ""
    )
    reservierungsinfo = (
        f"\nReserviert bis: {daten['reserviert_bis']}\n"
        f"Anzahlung: {euro(daten['anzahlung'])}\nRestbetrag: {euro(daten['restbetrag'])}"
        if daten['reserviert_bis'] else ""
    )
    bemerkungen = f"\nBemerkungen: {daten['bemerkungen']}" if daten["bemerkungen"] else ""
    messagebox.showinfo(
        dokumentart.get() + " · Daten",
        f"Kunde: {daten['name']}\n"
        f"Kaufdatum: {daten['kaufdatum']}\n"
        f"Verkäufer: {daten['verkaeufer']}\n"
        f"Lieferart: {daten['art']}\n"
        f"Etage: {daten['etage'] if daten['art'] == 'Wohnung' else '-'}\n"
        f"Fahrstuhl: {daten['fahrstuhl'] or '-'}\n"
        f"Warenwert: {euro(daten['warenwert'])}\n"
        f"Lieferkosten: {euro(daten['lieferkosten'])}\n"
        f"Aufbaukosten: {euro(daten['aufbaukosten'])}\n"
        f"Gesamtbetrag: {euro(daten['gesamt'])}{reservierungsinfo}{rechnungsinfo}{bemerkungen}"
    )


# --------------------------------
# 9. ARTIKEL HINZUFÜGEN
# --------------------------------

def artikel_hinzufuegen():
    zeile = len(artikel_positionen) + 1
    artikel = ttk.Entry(artikel_frame, width=34)
    artikel.grid(row=zeile, column=0, sticky="ew", padx=(0, 12), pady=5)
    menge_var = tk.StringVar(value="1")
    preis_var = tk.StringVar(value="")
    menge = ttk.Entry(artikel_frame, textvariable=menge_var, width=7, justify="right")
    menge.grid(row=zeile, column=1, padx=(0, 12), pady=5)
    preis = ttk.Entry(artikel_frame, textvariable=preis_var, width=12, justify="right")
    preis.grid(row=zeile, column=2, padx=(0, 12), pady=5)
    # Referenzen halten, damit Tk-Variablen während der Eingabe bestehen bleiben.
    menge.variable, preis.variable = menge_var, preis_var
    position = [artikel, menge, preis]
    entfernen_button = ttk.Button(artikel_frame, text="Entfernen", style="Danger.TButton",
                                  command=lambda: artikel_entfernen(position))
    entfernen_button.grid(row=zeile, column=3, pady=5)
    position.append(entfernen_button)
    artikel_positionen.append(position)
    menge_var.trace_add("write", lambda *args: warenwert_aktualisieren())
    preis_var.trace_add("write", lambda *args: warenwert_aktualisieren())
    warenwert_aktualisieren()
    if len(artikel_positionen) > 1:
        artikel.focus_set()
        fenster.after_idle(lambda: formular_canvas.yview_moveto(
            max(0, (artikel_frame.winfo_y() + artikel.winfo_y() - 80) / max(formular_frame.winfo_height(), 1)))
            if artikel.winfo_exists() else None)


# --------------------------------
# 10. ARTIKEL ENTFERNEN
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
# 11. LIEFEROPTIONEN
# --------------------------------

def lieferoptionen_aktualisieren():
    lieferung = lieferart.get() in ("Treppenhaus", "Wohnung")
    wohnung = lieferart.get() == "Wohnung"
    if wohnung:
        aufbau_card.pack(fill="x", padx=24, pady=(0, 16), after=liefer_card)
    else:
        aufbau_card.pack_forget()
        aufbau_aktiv.set("Nein")
        aufbaupreis_text.set("")
    aufbau_aktualisieren()
    modell = liefer_einstellungen["aktives_modell"]
    liefermodell_label.configure(text="Lieferkosten nach " + MODI[modell])
    if lieferung and modell != "warenwert":
        liefermenge_label.configure(text="Entfernung (km) *" if modell == "entfernung" else "Volumen (m³) *")
        liefermenge_label.grid()
        liefermenge_entry.grid()
    else:
        liefermenge_label.grid_remove()
        liefermenge_entry.grid_remove()
    for widget in (lieferdatum_label, lieferdatum_entry):
        if lieferung:
            widget.grid()
        else:
            widget.grid_remove()
    for widget in (etage_label, etage_dropdown, fahrstuhl_frame):
        if wohnung:
            widget.grid()
        else:
            widget.grid_remove()
    if not wohnung:
        etage.set("Bitte wählen")
    if not wohnung:
        fahrstuhl.set("Nein")
    for widget in (abholung_label, abholung_entry):
        if lieferart.get() == "Abholung":
            widget.grid()
        else:
            widget.grid_remove()
    fahrstuhloptionen_aktualisieren()


def fahrstuhloptionen_aktualisieren(*args):
    if lieferart.get() == "Wohnung" and fahrstuhl.get() == "Ja":
        fahrstuhlpauschale_frame.grid()
    else:
        fahrstuhlpauschale_frame.grid_remove()
    lieferkosten_aktualisieren()


def aufbau_aktualisieren():
    for widget in (aufbau_label, aufbau_entry):
        if lieferart.get() == "Wohnung" and aufbau_aktiv.get() == "Ja":
            widget.grid()
        else:
            widget.grid_remove()
    if lieferart.get() != "Wohnung" or aufbau_aktiv.get() != "Ja":
        aufbaupreis_text.set("")
    lieferkosten_aktualisieren()


# --------------------------------
# 12. PDF-RECHNUNG ERSTELLEN
# --------------------------------

def formular_leeren(kunde_behalten=False):
    """Beginnt einen neuen Vorgang und übernimmt bei Bedarf die Kundendaten."""
    global ausgewaehlter_kunde, vorgang_id
    popup_schliessen()
    if not kunde_behalten:
        kunden_suchtext.set("")
        ausgewaehlter_kunde = None
        for entry in (name_entry, anschrift_entry, telefon_entry, verkaeufer_entry):
            entry.delete(0, tk.END)
    vorgang_id = str(uuid.uuid4())
    pruefung_zuruecksetzen()
    kunde_status_anzeigen()
    kundendaten_speichern.set(False)
    for entry in (kaufdatum_entry, lieferdatum_entry, abholung_entry, reserviert_bis_entry,
                  anzahlung_entry, verwendungszweck_entry, lieferanschrift_entry):
        entry.delete(0, tk.END)
    bemerkungen_entry.delete("1.0", "end")
    bemerkungen_aktiv.set(False)
    liefermenge_text.set("")
    fehlermarkierungen_loeschen(formular_frame)
    kaufdatum_entry.insert(0, date.today().strftime("%d.%m.%Y"))
    anzahlung_entry.insert(0, "0,00")
    for position in artikel_positionen:
        for widget in position:
            widget.destroy()
    artikel_positionen.clear()
    lieferart.set("Keine Lieferung")
    etage.set("Bitte wählen")
    fahrstuhl.set("Nein")
    fahrstuhlpauschale.set("")
    aufbau_aktiv.set("Nein")
    aufbaupreis_text.set("")
    artikel_hinzufuegen()
    lieferoptionen_aktualisieren()
    aufbau_aktualisieren()
    formular_canvas.yview_moveto(0)
    formular_canvas.xview_moveto(0)
    ziel = artikel_positionen[0][0] if kunde_behalten else name_entry
    ziel.focus_set()


def rechnung_als_pdf_speichern():
    global ausgewaehlter_kunde

    daten = daten_sammeln()

    if daten is None:
        return

    # Speicherort auswählen
    dateipfad = filedialog.asksaveasfilename(
        title=dokumentart.get() + " als PDF speichern",
        defaultextension=".pdf",
        filetypes=[("PDF-Dateien", "*.pdf")],
        initialfile=dokumentart.get().replace(" / ", " - ") + ".pdf"
    )

    if not dateipfad:
        return

    try:
        daten["firma"] = firmendaten_laden()
        quittung_speichern(dateipfad, daten)
    except Exception as fehler:
        messagebox.showerror("PDF-Fehler", f"PDF konnte nicht erstellt werden:\n{fehler}")
        return
    if kundendaten_speichern.get():
        try:
            gueltig_bis = (
                datetime.strptime(gueltigkeit_entry.get().strip(), "%d.%m.%Y").date().isoformat()
                if not nicht_geprueft.get()
                else None
            )
            ausgewaehlter_kunde = kundendb.speichern(
                vorgang_id, ausgewaehlter_kunde, daten,
                not nicht_geprueft.get(), gueltig_bis,
            )
        except Exception as fehler:
            messagebox.showerror(
                "Datenbank",
                f"PDF wurde gespeichert, der Datenbankeintrag ist fehlgeschlagen. "
                f"Die Eingaben bleiben erhalten.\n{fehler}",
            )
            return

    messagebox.showinfo("PDF erstellt", f"Gespeichert unter:\n{dateipfad}")
    formular_leeren(kunde_behalten=True)



# --------------------------------
# 13. FORMULAR
# --------------------------------
def bereich(titel, hinweis):
    card = ttk.Frame(formular_frame, padding=22)
    card.pack(fill="x", padx=24, pady=(0, 16))
    ttk.Label(card, text=titel, style="Title.TLabel").pack(anchor="w")
    ttk.Label(card, text=hinweis, style="Hint.TLabel", wraplength=620).pack(anchor="w", pady=(4, 16))
    body = ttk.Frame(card)
    body.pack(fill="x")
    body.columnconfigure(1, weight=1)
    return card, body


def eingabe(parent, row, label, width=36, value=""):
    ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 20), pady=6)
    widget = ttk.Entry(parent, width=width)
    widget.grid(row=row, column=1, sticky="ew", pady=6)
    if value:
        widget.insert(0, value)
    return widget


kundenwahl_card, kundenwahl_frame = bereich(
    "Kundenverwaltung · lokaler Test", "Gespeicherte Kunden können über die Suche übernommen werden."
)
kundenstatus = tk.StringVar(value="Kein Kunde ausgewählt")
berechtigungsstatus = tk.StringVar(value="Berechtigung nicht geprüft")
letzter_einkauf_text = tk.StringVar(value="Letzter Einkauf: –")
nicht_geprueft = tk.BooleanVar(value=True)
kunden_suchtext = tk.StringVar()
kunden_suche_entry = eingabe(kundenwahl_frame, 0, "Kunden suchen")
kunden_suche_entry.configure(textvariable=kunden_suchtext)
kunden_suche_entry.bind("<Return>", lambda event: popup_anzeigen(True))
ttk.Button(kundenwahl_frame, text="Suchen", command=lambda: popup_anzeigen(True)).grid(row=0, column=2, padx=(10, 0))
ttk.Button(kundenwahl_frame, text="Alle Kunden", command=lambda: popup_anzeigen(True, alle=True)).grid(row=0, column=3, padx=(10, 0))
kundendaten_speichern = tk.BooleanVar(value=False)
ttk.Checkbutton(
    kundenwahl_frame,
    text="Kundendaten in der Datenbank speichern",
    variable=kundendaten_speichern,
).grid(row=1, column=0, columnspan=4, sticky="w", pady=(4, 8))

for row, variable in enumerate((kundenstatus, berechtigungsstatus, letzter_einkauf_text), 2):
    ttk.Label(kundenwahl_frame, textvariable=variable).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)
ttk.Label(kundenwahl_frame, text="Berechtigung gültig bis · TT.MM.JJJJ").grid(row=5, column=0, sticky="w", pady=8, padx=(0, 20))
pruefung_frame = ttk.Frame(kundenwahl_frame)
pruefung_frame.grid(row=5, column=1, sticky="w")
gueltigkeit_entry = ttk.Entry(pruefung_frame, width=14)
gueltigkeit_entry.pack(side="left", padx=(0, 12))
ttk.Checkbutton(pruefung_frame, text="Nicht geprüft", variable=nicht_geprueft,
                command=berechtigung_umschalten).pack(side="left")
ttk.Label(kundenwahl_frame, text="Diese Berechtigungsangaben erscheinen niemals auf dem PDF.", style="Hint.TLabel").grid(row=6, column=0, columnspan=2, sticky="w", pady=6)
berechtigung_umschalten()

kunden_card, kunden_frame = bereich("1  Kundendaten", "Alle Felder in diesem Bereich sind Pflichtfelder.")
name_entry = eingabe(kunden_frame, 0, "Name *")
name_text = tk.StringVar()
name_entry.configure(textvariable=name_text)
namens_treffer = []
neuer_kunde_bestaetigt = False
such_popup = None
name_text.trace_add("write", namenssuche)
name_entry.bind("<FocusOut>", lambda event: fenster.after_idle(lambda: popup_anzeigen(False)))
anschrift_entry = eingabe(kunden_frame, 1, "Anschrift *")
telefon_entry = eingabe(kunden_frame, 2, "Telefon *")
kaufdatum_entry = eingabe(kunden_frame, 3, "Kaufdatum * · TT.MM.JJJJ", value=date.today().strftime("%d.%m.%Y"))
verkaeufer_entry = eingabe(kunden_frame, 4, "Verkäufer *")

artikel_card, artikel_frame = bereich("2  Artikel", "Je Zeile einen Artikel eintragen. Preise in Euro, zum Beispiel 25,50.")
artikel_frame.columnconfigure(0, weight=1)
artikel_frame.columnconfigure(1, weight=0)
for col, label in enumerate(("Artikelbezeichnung *", "Menge *", "Einzelpreis (€) *", "")):
    ttk.Label(artikel_frame, text=label, style="Hint.TLabel").grid(row=0, column=col, sticky="w", pady=(0, 6))
artikel_actions = ttk.Frame(artikel_card)
artikel_actions.pack(fill="x", pady=(12, 0))
ttk.Button(artikel_actions, text="+ Artikel hinzufügen", command=artikel_hinzufuegen).pack(side="left")
ttk.Label(artikel_actions, textvariable=warenwert_text, font=("Helvetica", 14, "bold")).pack(side="right")
ttk.Label(artikel_actions, text="Warenwert  ", style="Hint.TLabel").pack(side="right")

liefer_card, verkauf_frame = bereich("3  Lieferung oder Abholung", "Wähle die gewünschte Übergabe. Passende Zusatzfelder erscheinen automatisch.")
options = ttk.Frame(verkauf_frame)
options.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
for i, (label, value) in enumerate((("Keine Lieferung", "Keine Lieferung"), ("Abholung", "Abholung"),
                                    ("Bis Treppenhaus", "Treppenhaus"), ("Bis in die Wohnung", "Wohnung"))):
    ttk.Radiobutton(options, text=label, variable=lieferart, value=value,
                    command=lieferoptionen_aktualisieren).grid(row=i//2, column=i%2, sticky="w", padx=(0, 20))
abholung_label = ttk.Label(verkauf_frame, text="Abholung bis * · TT.MM.JJJJ")
abholung_label.grid(row=1, column=0, sticky="w", padx=(0, 20), pady=6)
abholung_entry = ttk.Entry(verkauf_frame, width=18)
abholung_entry.grid(row=1, column=1, sticky="w", pady=6)
etage_label = ttk.Label(verkauf_frame, text="Etage *")
etage_label.grid(row=2, column=0, sticky="w", pady=6)
etage_dropdown = ttk.Combobox(verkauf_frame, textvariable=etage, state="readonly", width=16,
                              values=["EG"] + [str(n) for n in range(1, 21)])
etage_dropdown.grid(row=2, column=1, sticky="w", pady=6)
fahrstuhl_frame = ttk.Frame(verkauf_frame)
fahrstuhl_frame.grid(row=3, column=0, columnspan=2, sticky="w", pady=6)
ttk.Label(fahrstuhl_frame, text="Fahrstuhl vorhanden?").pack(side="left", padx=(0, 24))
for value in ("Ja", "Nein"):
    ttk.Radiobutton(fahrstuhl_frame, text=value, variable=fahrstuhl, value=value).pack(side="left")
fahrstuhlpauschale_frame = ttk.Frame(verkauf_frame)
fahrstuhlpauschale_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 12))
ttk.Label(fahrstuhlpauschale_frame, text="Fahrstuhlpauschale:").grid(row=0, column=0, sticky="w", padx=(0, 20))
fahrstuhlpauschale_entry = ttk.Entry(fahrstuhlpauschale_frame, textvariable=fahrstuhlpauschale, width=12, justify="right")
fahrstuhlpauschale_entry.grid(row=0, column=1, sticky="w")
ttk.Label(fahrstuhlpauschale_frame, text="€").grid(row=0, column=2, padx=6)
ttk.Label(fahrstuhlpauschale_frame,
          text="Leer lassen: Berechnung nach Etage.\nMit Betrag: Grundpreis + Pauschale statt Etagenzuschlag.",
          style="Hint.TLabel", justify="left", wraplength=560).grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))
lieferdatum_label = ttk.Label(verkauf_frame, text="Lieferdatum · optional · TT.MM.JJJJ")
lieferdatum_label.grid(row=5, column=0, sticky="w", padx=(0, 20), pady=6)
lieferdatum_entry = ttk.Entry(verkauf_frame, width=18)
lieferdatum_entry.grid(row=5, column=1, sticky="w", pady=6)
liefermenge_label = ttk.Label(verkauf_frame)
liefermenge_label.grid(row=6, column=0, sticky="w", pady=6)
liefermenge_entry = ttk.Entry(verkauf_frame, textvariable=liefermenge_text, width=18)
liefermenge_entry.grid(row=6, column=1, sticky="w", pady=6)
liefermodell_label = ttk.Label(verkauf_frame, style="Hint.TLabel")
liefermodell_label.grid(row=7, column=0, columnspan=2, sticky="w", pady=6)
lieferkosten_label = ttk.Label(verkauf_frame, text="Lieferkosten")
lieferkosten_wert = ttk.Label(verkauf_frame, textvariable=lieferkosten_text, font=("Helvetica", 13, "bold"))

aufbau_card, aufbau_frame = bereich("4  Aufbau / Montage", "Bei Bedarf einen zusätzlichen Aufbaupreis erfassen.")
aufbau_choice = ttk.Frame(aufbau_frame)
aufbau_choice.grid(row=0, column=0, columnspan=2, sticky="w")
for label, value in (("Kein Aufbau", "Nein"), ("Aufbau gewünscht", "Ja")):
    ttk.Radiobutton(aufbau_choice, text=label, variable=aufbau_aktiv, value=value,
                    command=aufbau_aktualisieren).pack(side="left")
aufbau_label = ttk.Label(aufbau_frame, text="Aufbaupreis (€)")
aufbau_label.grid(row=1, column=0, sticky="w", padx=(0, 20), pady=8)
aufbau_entry = ttk.Entry(aufbau_frame, textvariable=aufbaupreis_text, width=18, justify="right")
aufbau_entry.grid(row=1, column=1, sticky="w", pady=8)

reservierung_card, reservierung_frame = bereich(
    "5  Reservierung und Anzahlung",
    "Reservierungsfrist angeben. Ohne Anzahlung 0,00 eintragen; der Restbetrag wird automatisch berechnet."
)
reserviert_bis_entry = eingabe(reservierung_frame, 0, "Reserviert bis * · TT.MM.JJJJ", width=18)
anzahlung_entry = eingabe(reservierung_frame, 1, "Anzahlung (€) *", width=18, value="0,00")
reservierung_card.pack_forget()

rechnung_card, rechnung_frame = bereich(
    "5  Rechnungsangaben",
    "Verwendungszweck für die Überweisung ergänzen. Ohne abweichende Lieferanschrift gilt die Kundenanschrift."
)
verwendungszweck_entry = eingabe(rechnung_frame, 0, "Verwendungszweck *")
lieferanschrift_entry = eingabe(rechnung_frame, 1, "Abweichende Lieferanschrift · optional")
rechnung_card.pack_forget()

einstellungen_menu = tk.Menu(einstellungen_button, tearoff=False)
einstellungen_menu.add_command(
    label="Lieferpreise",
    command=lambda: einstellungsfenster_oeffnen(fenster, liefer_einstellungen, lieferpreise_uebernehmen),
)
einstellungen_menu.add_command(
    label="Firmendaten", command=lambda: FirmendatenDialog(fenster, "Firmendaten für den PDF-Export")
)
einstellungen_button.configure(menu=einstellungen_menu)

bemerkungen_card, bemerkungen_frame = bereich(
    "Optionale Bemerkung", "Nur bei aktivierter Checkbox erscheint der Text im PDF."
)
bemerkungen_aktiv = tk.BooleanVar(value=False)
ttk.Checkbutton(
    bemerkungen_frame, text="Bemerkung hinzufügen", variable=bemerkungen_aktiv
).pack(anchor="w")
bemerkungen_entry = tk.Text(bemerkungen_frame, height=4, width=65, wrap="word")


def bemerkungen_umschalten(*args):
    if bemerkungen_aktiv.get():
        bemerkungen_entry.pack(fill="x", pady=(10, 0))
    else:
        bemerkungen_entry.pack_forget()


bemerkungen_aktiv.trace_add("write", bemerkungen_umschalten)
bemerkungen_umschalten()

# Feste Abschlussleiste: auch beim Scrollen erreichbar.
footer.columnconfigure(0, weight=1)
totals = ttk.Frame(footer)
totals.grid(row=0, column=0, sticky="w")
ttk.Label(totals, text="Gesamtbetrag", style="Hint.TLabel").pack(anchor="w")
ttk.Label(totals, textvariable=gesamt_text, style="Total.TLabel").pack(anchor="w", pady=(2, 0))
ttk.Label(footer, textvariable=status_text, style="Hint.TLabel", wraplength=650).grid(row=1, column=0, columnspan=5, sticky="w", pady=(8, 0))
ttk.Button(footer, text="Neuer Vorgang", style="Reset.TButton",
           command=lambda: formular_leeren(kunde_behalten=True)).grid(row=0, column=1, padx=(10, 6))
ttk.Button(footer, text="Neuer Kunde", style="Reset.TButton",
           command=formular_leeren).grid(row=0, column=2, padx=(0, 12))
ttk.Button(footer, text="Daten prüfen", command=daten_anzeigen).grid(row=0, column=3, padx=(0, 10))
ttk.Button(footer, textvariable=pdf_button_text, style="Primary.TButton",
           command=rechnung_als_pdf_speichern).grid(row=0, column=4)

liefermenge_text.trace_add("write", lieferkosten_aktualisieren)
fahrstuhl.trace_add("write", fahrstuhloptionen_aktualisieren)
fahrstuhlpauschale.trace_add("write", lieferkosten_aktualisieren)
etage.trace_add("write", lieferkosten_aktualisieren)
aufbaupreis_text.trace_add("write", lieferkosten_aktualisieren)
artikel_hinzufuegen()
lieferoptionen_aktualisieren()
aufbau_aktualisieren()
def fehler_beim_bearbeiten_loeschen(event):
    if isinstance(event.widget, (ttk.Entry, ttk.Combobox)):
        event.widget.state(["!invalid"])


fenster.bind("<KeyRelease>", fehler_beim_bearbeiten_loeschen, add="+")
fenster.bind("<<ComboboxSelected>>", fehler_beim_bearbeiten_loeschen, add="+")
name_entry.focus_set()
if __name__ == "__main__":
    fenster.mainloop()
