# 🎵 S_AI_N (Stefan's AI für Navidrome)

![Python](https://img.shields.io/badge/Python-3.10-blue?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-Compose-orange?style=flat-square)
![License](https://img.shields.io/badge/License-GPLv3-green?style=flat-square)

**Verwandle deinen Navidrome Server in eine intelligente Musik-Maschine.**

Dieses Projekt ist ein "Beiwagen" für Navidrome. Es überwacht deine Musiksammlung, nutzt fortschrittliche Audio-Algorithmen (Essentia & TensorFlow), um BPM, Tonart und Stimmung zu erkennen, und fungiert als automatischer DJ, der perfekte Übergänge schafft.

---

## ✨ Funktionen

### 🧠 Der Analysator (`music-analyze`)
* **Tiefenanalyse:** Nutzt die `Essentia` Bibliothek, um BPM, Tonart (Key), Tanzbarkeit und Energie zu berechnen.
* **Stimmungs-Erkennung:** Ordnet Songs Stimmungen zu (z.B. *Aggressiv, Glücklich, Entspannt, Party*) mithilfe von KI-Modellen.
* **Qualitäts-Prüfung:** Findet kaputte Dateien oder falsche Endungen und verschiebt sie automatisch in einen "Aussortiert"-Ordner.
* **Anker-System:** Nutzt Referenz-Tracks ("Anker"), um die KI auf deinen persönlichen Musikgeschmack zu kalibrieren.

### 🎧 Der Smart DJ (`music-dj`)
* **Intelligente Playlisten:** Erstellt automatisch Mixe basierend auf deinen Bewertungen.
* **Harmonisches Mixing:** Erstellt "Flow-Mixe", indem Songs passend nach Tonart (Camelot Wheel) und BPM gemixt werden.
* **Datenbank-Integration:** Schreibt Playlisten und Tags direkt in die Navidrome-Datenbank, damit sie sofort in jeder App verfügbar sind.


## ⚓ Das Anker-System (BPM Kalibrierung)

Für eine exakte BPM-Erkennung musst du deinen `musik_anker` Ordner so strukturieren, und passende Lieder einfügen:

1.  **/SLOW**: Für langsame Tracks (z.B. 60-80 BPM).
2.  **/MIDDLE**: Für Tracks mit mittlerem Tempo (z.B. 100-120 BPM).
3.  **/FAST**: Für schnelle, treibende Tracks (z.B. 140+ BPM).

Der Analyzer vergleicht neue Songs mit diesen Referenzen, um den richtigen Tempobereich zu wählen.

WICHTIG!:
## Der Hausmeister
* Auf Wunsch sortiert das System deine Dateien nach der Analyse automatisch in eine saubere `Interpret/Album/Titel.flac` Struktur um.
* Wenn dies nicht gewünscht ist, lass die Datei ./music-analyze/organize_worker.py weg!
---

## ⚠️ Wichtige Warnung

**Diese Software schreibt direkt in die Navidrome SQLite-Datenbank (`navidrome.db`).**

* Dies ist kein offizielles Navidrome-Plugin.
* Auch wenn es sorgfältig getestet wurde: Direkte Eingriffe in Datenbanken bergen immer ein Risiko.
* **Mache IMMER ein Backup deiner `navidrome.db`, bevor du startest!**
* Die Nutzung erfolgt auf eigene Gefahr.

---

## 🚀 Installation

### 1. Voraussetzungen
* Ein Rechner mit Docker & Docker Compose (getestet auf Raspberry Pi 5 / Debian).
* Eine vorhandene Musiksammlung.

### 2. Herunterladen
Klone das Repository in einen Ordner deiner Wahl:


git clone [https://github.com/DEIN_USER/navidrome-ai-architect.git](https://github.com/DEIN_USER/navidrome-ai-architect.git)
cd navidrome-ai-architect

3. Konfiguration

Erstelle deine persönliche Einstellungsdatei aus der Vorlage:


cp .env.example .env

Öffne die Datei .env mit einem Texteditor und trage deine echten Pfade ein:

    HOST_MUSIC_DIR: Wo liegen deine MP3s?

    HOST_DATA_DIR: Wo liegt dein Navidrome Daten-Ordner?

    PUID/PGID: Deine Benutzer-ID (meistens 1000).

4. Starten

Hinweis zur Dauer: Der erste Start dauert lange (15-30 Minuten auf einem Pi), da die Audio-Bibliothek Essentia speziell für deine Hardware kompiliert wird, um maximale Geschwindigkeit zu erreichen.

docker-compose up -d --build

📂 Ordnerstruktur

Das System besteht aus 3 Containern:

    navidrome: Der normale Musik-Server.

    music-analyze: Der "Arbeiter". Scannt Dateien im Hintergrund.

    music-dj: Der "DJ". Erstellt Playlisten basierend auf Likes/Bans.

Wir empfehlen folgende Struktur auf deinem Rechner:
Plaintext

/home/dein-user/
├── musik/              <-- Deine Musiksammlung
├── navidrome/          <-- Datenbank & Cache (Backup machen!)
├── musik_anker/        <-- (Optional) Referenz-Tracks für die KI
└── musik_aussortiert/  <-- Quarantäne für defekte Dateien

📜 Lizenz

Dieses Projekt steht unter der GNU General Public License v3.0 (GPLv3).
