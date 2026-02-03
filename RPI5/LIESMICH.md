# **🌟 STARAIN**

Stefan Aretz KI für Navidrome – Lässt Playlists regnen.

**Verwandle deinen Navidrome-Server in eine intelligente, KI-gestützte Musikmaschine.**

Dieses Projekt fungiert als „Sidecar” für [Navidrome](https://www.navidrome.org/). Es überwacht Ihre Bibliothek, verwendet fortschrittliche Audioanalyse (Essentia & TensorFlow), um Ihre Dateien mit Metadaten anzureichern, und fungiert als automatischer DJ, der auf der Grundlage von Stimmung, Tonart und BPM perfekt abgestimmte Playlists erstellt.


## ✨ Funktionen

### 🧠 Der Analyzer (Musikanalyse)

1. Vektor-Embeddings (Sonic DNA): Extrahiert hochdimensionale Merkmalsvektoren (Embeddings) für jeden Titel. Dadurch wird die mathematische „Seele” der Musik abgebildet, sodass die KI Songs finden kann, die ähnlich klingen, unabhängig von ihren Genre-Tags.

2. Deep Audio Analysis: Verwendet die Essentia-Bibliothek, um präzise technische Metriken zu extrahieren: BPM, Tonart, Tanzbarkeit, Energie und Dynamikbereich.

3. Mood Detection: Klassifiziert Songs anhand vortrainierter TensorFlow-Modelle in verschiedene emotionale Kategorien (z. B. fröhlich, aggressiv, entspannt, Party).

4. Qualitätskontrolle: Dient als proaktiver Filter. Erkennt automatisch beschädigte Dateien, 0-Byte-Fehler oder gefälschte Erweiterungen und verschiebt sie zur manuellen Überprüfung in einen sicheren „Quarantänebereich“, sodass Ihre Hauptbibliothek makellos bleibt.

5. Ankersystem: Verwendet Ihre manuell ausgewählten Referenztitel („Anker“), um die Vorhersagen der KI auf Ihren persönlichen Geschmack abzustimmen.
    

### 🎧 Der DJ (`music-dj`)

1. Anstelle von zufälligem Shuffling nutzt STARAIN  Seed-basierte Instant-Mixes Ihrer Interaktion als Auslöser. Wenn Sie einen Song liken (durch Klicken auf das Herz in Ihrer App oder auf Navidrome), wird er sofort als „Seed-Track” definiert. Das System generiert dann eine zusammenhängende Playlist, die auf den klanglichen Eigenschaften dieses bestimmten Tracks basiert.

2. Adaptive Mood-Playlists (die „One-Strike“-Regel) Täglich generierte Playlists basierend auf erkannten Stimmungen. Das System verfügt über eine strenge unsichtbare Blacklist: Wenn Sie einen Song einmal aus einer Mood-Playlist löschen, lernt STARAIN, dass dieser Track nie wieder zu dieser bestimmten Stimmung passt.

3. Intelligentes automatisches Bewertungssystem Sterne werden verdient, nicht einfach vergeben. Das System verwaltet Bewertungen basierend auf Ihren Hörgewohnheiten:

5 Wiedergaben → ⭐⭐⭐ (Gut)

15 Wiedergaben → ⭐⭐⭐⭐ (Großartig)

30 Wiedergaben → ⭐⭐⭐⭐⭐ (Favorit)

    Manuelle Überschreibung: Wenn Sie eine Bewertung manuell festlegen, wird diese gesperrt und 3 Jahre lang vor automatischen Aktualisierungen geschützt.

    Soft Ban: Songs mit 1 oder 2 Sternen werden automatisch aus allen generierten Playlists ausgeschlossen.

4. Globale KI-Blacklist Eine spezielle System-Playlist fungiert als globale Blockliste. Jeder Song, der hier hinzugefügt wird, darf vom Auto-DJ unabhängig von seinen anderen Metriken nicht ausgewählt werden.

5. Lebenszyklus und Dauerhaftigkeit von Wiedergabelisten Ihre manuell erstellten Wiedergabelisten sind heilig und werden niemals verändert.

    Die „Speichern”-Funktion: Von der KI generierte Mood-Wiedergabelisten sind vergänglich. Um eine Wiedergabeliste für immer zu behalten, benennen Sie sie einfach um. STARAIN erkennt die Namensänderung, behandelt sie wie eine manuelle Benutzer-Wiedergabeliste und generiert an ihrer Stelle einen neuen Mix.

## ⚓ Das Ankersystem (BPM-Kalibrierung)

Um eine maximale BPM-Genauigkeit zu gewährleisten, organisieren Sie Ihren Ordner „music_anchors“ wie folgt und füllen Sie ihn mit geeigneten Songs:

1.  **/SLOW**: Platzieren Sie hier Titel, die eindeutig langsam sind (z. B. 60–80 BPM).
2.  **/MIDDLE**: Legen Sie hier Titel mit durchschnittlichem Tempo ab (z. B. 100–120 BPM).
3.  **/FAST**: Legen Sie hier Titel mit hoher Energie ab (z. B. 140+ BPM).

Die KI vergleicht neue Uploads mit diesen Referenzpunkten, um den richtigen BPM-Bereich auszuwählen.
(Nur mit .flac getestet)

WICHTIG!:
## Der Hausmeister
* Auf Wunsch sortiert das System Ihre Dateien nach der Analyse automatisch in eine übersichtliche Struktur `Künstler/Album/Titel.flac`.
* Wenn Sie dies nicht wünschen, lassen Sie die Datei ./music-analyze/organize_worker.py weg!
---

## ⚠️ Haftungsausschluss & Warnung & Logik

**Diese Software schreibt direkt in die Navidrome-SQLite-Datenbank (`navidrome.db`).**

* Dies ist **kein** offizielles Navidrome-Plugin.
* Obwohl sorgfältig getestet, birgt die direkte Manipulation der Datenbank immer ein Risiko.
* **Erstellen Sie IMMER eine Sicherungskopie Ihrer `navidrome.db`, bevor Sie diese Software verwenden.**
* Die Verwendung erfolgt auf eigene Gefahr.

* **Hohe CPU-Auslastung:** Auf einem Raspberry Pi 5 dauert die Analyse eines einzelnen Songs etwa **20 Minuten bei 100 % CPU-Auslastung**. Ein **Kühlventilator ist unbedingt erforderlich**, um eine thermische Drosselung oder Beschädigung zu verhindern.

---

## 🚀 Installation

### 1. Voraussetzungen
* Ein Rechner, auf dem Docker & Docker Compose läuft (getestet auf Raspberry Pi 5 / Debian).
* Eine vorhandene Musiksammlung.

### 2. Klonen Sie das Repository
```bash
git clone [https://github.com/weisserwerwolf89/STARAIN.git](https://github.com/weisserwerwolf89/STARAIN.git)
cd STARAIN

3. Konfigurieren Sie die Umgebung

Erstellen Sie Ihre Konfigurationsdatei anhand des Beispiels:
Bash

cp .env.example .env

Öffnen Sie .env und passen Sie die Pfade an Ihr Host-System an:
Ini, TOML

# Beispiel-Einstellungen in .env
HOST_MUSIC_DIR=/home/user/music        # Speicherort Ihrer MP3-Dateien
HOST_DATA_DIR=/home/user/navidrome     # Speicherort Ihrer Datenbank
HOST_SORT_DIR=/home/user/trash         # Speicherort für fehlerhafte Dateien

4. Erstellen und ausführen

Hinweis zur Leistung: Die erste Erstellung dauert relativ lange (15 bis 30 Minuten auf einem Raspberry Pi), da die Essentia-Audiobibliothek aus dem Quellcode kompiliert wird, um eine maximale Leistung auf Ihrer Hardware zu gewährleisten.
Bash

docker-compose up -d --build

📂 Architektur und Verzeichnisstruktur

Dieses Projekt verwendet eine Architektur mit drei Containern:

    navidrome: Der Standard-Musikserver.

    music-analyze: Der Schwerarbeiter. Scannt Dateien, berechnet ReplayGain, BPM, Stimmung und verwaltet die Dateiorganisation.

    music-dj: Die Logikeinheit. Überwacht die Datenbank auf Benutzerinteraktionen (Likes/Bans) und generiert Wiedergabelisten.

Empfohlene Host-Ordnerstruktur

Um Ordnung zu halten, organisieren Sie Ihre Host-Ordner wie folgt:
Klartext

/home/your-user/docker/STARAIN
├── music/              <-- Ihre Songsammlung
├── navidrome/          <-- Datenbank
├── cache/              
├── music_anchors/      <-- (Optional) Referenztitel für KI
└── music_trash/        <-- Quarantäne für fehlerhafte/beschädigte Dateien

```
📜 Lizenz

Dieses Projekt unterliegt der GNU General Public License v3.0 – weitere Informationen finden Sie in der Datei LICENSE.---

### 💶 Spenden Sie die nächsten Songs für meine Bibliothek:

[![PayPal](https://img.shields.io/badge/PayPal-004595?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/StefanAretz89)

### 🤝 Danksagungen & Technologien von Drittanbietern

STARAIN steht auf den Schultern von Giganten. Dieses Projekt wäre ohne die folgenden großartigen Open-Source-Projekte nicht möglich gewesen:

* **[Navidrome](https://www.navidrome.org/)** (GPLv3) – Der Kern-Musikserver, den wir alle lieben.
* **[Essentia](https://essentia.upf.edu/)** (AGPLv3/GPLv3) – Die leistungsstarke Audioanalyse-Bibliothek von MTG UPF.
* **[TensorFlow](https://www.tensorflow.org/)** (Apache 2.0) – Liefert die Machine-Learning-Leistung für die Stimmungserkennung.
* **[Librosa](https://librosa.org/)** (ISC) – Unverzichtbar für die Audioverarbeitung und Spektrogramme.
* **[Mutagen](https://mutagen.readthedocs.io/)** (GPLv2+) – Übernimmt alle aufwendigen Aufgaben im Zusammenhang mit Audio-Metadaten und Tags.
* **[OpenL3](https://github.com/marl/openl3)** (Apache 2.0) – Tiefe Audio-Einbettungen für Ähnlichkeitsabgleiche.
