"""Lokale Datenbank für Kundendaten und die letzten Einkaufsvorgänge."""
import os
from contextlib import contextmanager
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from datenhaltung.einstellungen import lokaler_ordner


class Kundendatenbank:
    def __init__(self, pfad=None):
        standardpfad = lokaler_ordner() / "kunden.sqlite3"
        self.pfad = Path(pfad or os.environ.get("QUITTUNG_DB_PATH") or standardpfad)
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        with self.verbindung() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS kunden (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gueltig_bis TEXT,
                    zuletzt_geprueft TEXT
                );
                CREATE TABLE IF NOT EXISTS vorgaenge (
                    id TEXT PRIMARY KEY,
                    kunde_id INTEGER NOT NULL REFERENCES kunden(id),
                    dokumentart TEXT NOT NULL,
                    kaufdatum TEXT NOT NULL,
                    warenwert_cent INTEGER NOT NULL CHECK(warenwert_cent >= 0),
                    lieferkosten_cent INTEGER NOT NULL CHECK(lieferkosten_cent >= 0),
                    aufbaukosten_cent INTEGER NOT NULL CHECK(aufbaukosten_cent >= 0),
                    geprueft INTEGER NOT NULL CHECK(geprueft IN (0,1))
                );
                CREATE INDEX IF NOT EXISTS vorgaenge_kunde ON vorgaenge(kunde_id, kaufdatum);
            ''')

            db.execute('BEGIN IMMEDIATE')
            spalten = {row['name'] for row in db.execute('PRAGMA table_info(kunden)')}
            for spalte in ('name', 'anschrift', 'telefon'):
                if spalte not in spalten:
                    db.execute(f'ALTER TABLE kunden ADD COLUMN {spalte} TEXT')

    def suchen(self, name):
        suchtext = ' '.join(name.casefold().split())
        if not suchtext:
            return []
        with self.verbindung() as db:
            return [
                dict(row) for row in db.execute('SELECT id, name FROM kunden WHERE name IS NOT NULL ORDER BY name, id')
                if suchtext in ' '.join(row['name'].casefold().split())
            ]

    def alle_kunden(self):
        with self.verbindung() as db:
            return [dict(row) for row in db.execute(
                'SELECT id, name FROM kunden ORDER BY name COLLATE NOCASE, id')]

    @contextmanager
    def verbindung(self):
        db = sqlite3.connect(self.pfad, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def nummer(kunde_id):
        return f'KD{kunde_id:06d}'

    def anlegen(self):
        with self.verbindung() as db:
            nummer = db.execute('INSERT INTO kunden DEFAULT VALUES').lastrowid
        return self.laden(self.nummer(nummer))

    def laden(self, nummer):
        text = nummer.strip().upper().removeprefix('KD')
        if not text.isdigit():
            return None
        with self.verbindung() as db:
            row = db.execute('''SELECT k.*,
                (SELECT MAX(kaufdatum) FROM vorgaenge v WHERE v.kunde_id=k.id
                 AND dokumentart IN ('Quittung','Rechnung')) AS letzter_einkauf
                FROM kunden k WHERE k.id=?''', (int(text),)).fetchone()
        return dict(row) if row else None

    def speichern(self, vorgang_id, kunde_id, daten, geprueft, gueltig_bis):
        cents = lambda value: int(Decimal(value) * 100)
        with self.verbindung() as db:
            db.execute('BEGIN IMMEDIATE')
            vorhanden = db.execute(
                'SELECT kunde_id FROM vorgaenge WHERE id=?', (vorgang_id,)
            ).fetchone()
            if vorhanden:
                return vorhanden['kunde_id']
            if kunde_id is None:
                kunde_id = db.execute(
                    'INSERT INTO kunden(name, anschrift, telefon) VALUES (?, ?, ?)',
                    (daten['name'], daten['anschrift'], daten['telefon'])).lastrowid
            elif not db.execute('SELECT id FROM kunden WHERE id=?', (kunde_id,)).fetchone():
                raise ValueError('Kundennummer nicht gefunden')
            db.execute('UPDATE kunden SET name=?, anschrift=?, telefon=? WHERE id=?',
                       (daten['name'], daten['anschrift'], daten['telefon'], kunde_id))
            # Ein erneuter Export desselben Formulars erzeugt keinen zweiten Einkauf.
            db.execute('''INSERT INTO vorgaenge VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO NOTHING''', (
                vorgang_id, kunde_id, daten['dokumentart'],
                datetime.strptime(daten['kaufdatum'], '%d.%m.%Y').date().isoformat(),
                cents(daten['warenwert']), cents(daten['lieferkosten']),
                cents(daten['aufbaukosten']), int(geprueft)))
            if geprueft:
                db.execute('UPDATE kunden SET gueltig_bis=?, zuletzt_geprueft=? WHERE id=?',
                           (gueltig_bis, datetime.now().isoformat(timespec='seconds'), kunde_id))
            return kunde_id
