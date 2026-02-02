# **🌟 STARAIN**

Stefan Aretz AI for Navidrome — Let it rain smart playlists.

**Bring intelligence and sanity to your Navidrome library.**
## 🤝 Acknowledgements & Third-Party Tech

STARAIN stands on the shoulders of giants. This project would not be possible without the following amazing Open Source projects:

* **[Navidrome](https://www.navidrome.org/)** (GPLv3) – The core music server we all love.
* **[Essentia](https://essentia.upf.edu/)** (AGPLv3/GPLv3) – The powerful audio analysis library from MTG UPF.
* **[TensorFlow](https://www.tensorflow.org/)** (Apache 2.0) – Providing the machine learning muscle for mood detection.
* **[Librosa](https://librosa.org/)** (ISC) – Essential for audio processing and spectrograms.
* **[Mutagen](https://mutagen.readthedocs.io/)** (GPLv2+) – Handling all the heavy lifting for audio metadata and tags.
* **[OpenL3](https://github.com/marl/openl3)** (Apache 2.0) – Deep audio embeddings for similarity matching.

**Turn your Navidrome server into an intelligent, AI-powered music machine.**

This project acts as a "Sidecar" to [Navidrome](https://www.navidrome.org/). It monitors your library, uses advanced audio analysis (Essentia & TensorFlow) to enrich your files with metadata, and acts as an automatic DJ that creates flow-perfect playlists based on Mood, Key, and BPM.

---

## ✨ Features

### 🧠 The Analyzer (`music-analyze`)
* **Deep Audio Analysis:** Uses the `Essentia` library to extract BPM, Key, Danceability, and Intensity.
* **Mood Detection:** Classifies songs into moods (e.g., *Happy, Aggressive, Relaxed, Party*) using TensorFlow models.
* **Quality Gate:** Automatically detects corrupted files or fake extensions and moves them to a "Trash" folder.
* **Anchor System:** Uses reference tracks ("Anchors") to calibrate the analysis to your personal taste.

### 🎧 The DJ (`music-dj`)
* **Smart Playlists:** Generates new mixes automatically based on user ratings and listening history.
* **Harmonic Mixing:** Creates "Flow-Mixes" by matching songs with compatible musical Keys (Camelot Wheel) and similar BPM.
* **Database Integration:** Writes playlists and tags directly into the Navidrome SQLite database for instant availability in any client.

## ⚓ The Anchor System (BPM Calibration)

To ensure maximum BPM accuracy, organize your `music_anchors` folder as follows, and fill the folder with suitable songs:

1.  **/SLOW**: Place tracks here that are clearly slow (e.g., 60-80 BPM).
2.  **/MIDDLE**: Place tracks here with average tempo (e.g., 100-120 BPM).
3.  **/FAST**: Place tracks here with high energy (e.g., 140+ BPM).

The AI compares new uploads against these reference points to choose the correct BPM range.
(Tested only with .flac)

IMPORTANT!:
## The janitor
* If desired, the system automatically sorts your files into a clean `artist/album/title.flac` structure after analysis.
* If this is not desired, omit the file ./music-analyze/organize_worker.py!
---

## ⚠️ Disclaimer & Warning

**This software writes directly to the Navidrome SQLite database (`navidrome.db`).**

* This is **not** an official Navidrome plugin.
* While tested carefully, direct database manipulation always carries a risk.
* **ALWAYS backup your `navidrome.db` before using this software.**
* Use at your own risk.

---

## 🚀 Installation

### 1. Prerequisites
* A machine running Docker & Docker Compose (tested on Raspberry Pi 5 / Debian).
* An existing music collection.

### 2. Clone the Repository
```bash
git clone [https://github.com/YOUR_USERNAME/navidrome-ai-architect.git](https://github.com/YOUR_USERNAME/navidrome-ai-architect.git)
cd navidrome-ai-architect

3. Configure Environment

Create your configuration file from the example:
Bash

cp .env.example .env

Open .env and adjust the paths to match your host system:
Ini, TOML

# Example settings in .env
HOST_MUSIC_DIR=/home/user/music        # Where your MP3s are
HOST_DATA_DIR=/home/user/navidrome     # Where your DB is
HOST_SORT_DIR=/home/user/trash         # Where bad files go

4. Build & Run

Note on Performance: The first build will take significant time (15-30 minutes on a Raspberry Pi) because it compiles the Essentia audio library from source to ensure maximum performance on your hardware.
Bash

docker-compose up -d --build

📂 Architecture & Directory Structure

This project uses a 3-container architecture:

    navidrome: The standard music server.

    music-analyze: The heavy worker. Scans files, calculates ReplayGain, BPM, Mood, and manages file organization.

    music-dj: The logic unit. Monitors the database for user interactions (likes/bans) and generates playlists.

Recommended Host Folder Structure

To keep things clean, organize your host folders like this:
Plaintext

/home/your-user/
├── music/              <-- Your Song Collection
├── navidrome/          <-- Database & Cache (Backup this!)
├── music_anchors/      <-- (Optional) Reference tracks for AI
└── music_trash/        <-- Quarantine for bad/corrupted files

📜 License

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.
