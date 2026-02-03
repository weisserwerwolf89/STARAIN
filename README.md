# **🌟 STARAIN**

Stefan Aretz AI for Navidrome — Let it rain smart playlists.

**Turn your Navidrome server into an intelligent, AI-powered music machine.**

This project acts as a "Sidecar" to [Navidrome](https://www.navidrome.org/). It monitors your library, uses advanced audio analysis (Essentia & TensorFlow) to enrich your files with metadata, and acts as an automatic DJ that creates flow-perfect playlists based on Mood, Key, and BPM.


## ✨ Features

### 🧠 The Analyzer (music-analyze)

1. Vector Embeddings (Sonic DNA): Extracts high-dimensional feature vectors (Embeddings) for every track. This maps the mathematical "soul" of the music, allowing the AI to find songs that sound similar, regardless of their genre tags.

2. Deep Audio Analysis: Uses the Essentia library to extract precise technical metrics: BPM, Key, Danceability, Energy, and Dynamic Range.

3. Mood Detection: Classifies songs into distinct emotional categories (e.g., Happy, Aggressive, Relaxed, Party) using pre-trained TensorFlow models.

4. Quality Gate: Acts as a proactive filter. Automatically detects corrupted files, 0-byte errors, or fake extensions and moves them to a secure "Quarantine" area for manual inspection, keeping your main library pristine.

5. Anchor System: Uses your manually selected reference tracks ("Anchors") to calibrate the AI's predictions to your specific personal taste.
    

### 🎧 The DJ (`music-dj`)

1. Seed-Based Instant Mixes Instead of random shuffling, STARAIN uses your interaction as a trigger. Liking (by clicking on the heart at your app or navidrome) a song immediately defines it as a "Seed Track". The system then generates a cohesive playlist built around the sonic characteristics of that specific track.

2. Adaptive Mood Playlists (The "One-Strike" Rule) Daily generated playlists based on detected moods. It features a strict Invisible Blacklist: If you delete a song from a mood playlist once, STARAIN learns that this track never belongs in that specific mood again.

3. Intelligent Auto-Rating System Stars are earned, not just given. The system manages ratings based on your listening habits:

    5 Plays → ⭐⭐⭐ (Good)

    15 Plays → ⭐⭐⭐⭐ (Great)

    30 Plays → ⭐⭐⭐⭐⭐ (Favorite)

    Manual Override: If you set a rating manually, it is locked and protected from auto-updates for 3 years.

    Soft Ban: Songs with 1 or 2 stars are automatically excluded from all generated playlists.

4. Global AI Blacklist A dedicated system playlist acts as a Global Blocklist. Any song added here is strictly forbidden for the Auto-DJ to choose, regardless of its other metrics.

5. Playlist Lifecycle & Permanence Your manually created playlists are sacred and never touched.

    The "Save" Mechanic: AI-generated Mood-playlists are ephemeral. To keep one forever, simply rename it. STARAIN recognizes the name change, treats it as a manual user playlist, and generates a fresh new Mix in its place.

## ⚓ The Anchor System (BPM Calibration)

To ensure maximum BPM accuracy, organize your `music_anchors` folder as follows, and fill the folder with suitable songs:

1.  **/SLOW**: Place tracks here that are clearly slow (e.g., 60-80 BPM).
2.  **/MIDDLE**: Place tracks here with average tempo (e.g., 100-120 BPM).
3.  **/FAST**: Place tracks here with high energy (e.g., 140+ BPM).

The AI compares new uploads against these reference points to choose the correct BPM range.
(Tested only with .flac)

IMPORTANT!:
## The Janitor
* If desired, the system automatically sorts your files into a clean `artist/album/title.flac` structure after analysis.
* If this is not desired, omit the file ./music-analyze/organize_worker.py!
---

## ⚠️ Disclaimer & Warning & Logic

**This software writes directly to the Navidrome SQLite database (`navidrome.db`).**

* This is **not** an official Navidrome plugin.
* While tested carefully, direct database manipulation always carries a risk.
* **ALWAYS backup your `navidrome.db` before using this software.**
* Use at your own risk.

* **High CPU Load:** On a Raspberry Pi 5, the analysis of a single song takes about **20 minutes at 100% CPU load**. A **cooling fan is strictly required** to prevent thermal throttling or damage.
* **Auto-Rating:** Once a song is played **5 times**, it automatically receives a **3-star rating**.
* **Playlist Logic:** * Songs with **2 stars or less** are automatically removed from active playlists.
    * Playlists are recalculated immediately after a rating change.
    * Songs in the **"KI-Blacklist"** playlist are ignored by the auto-rating system.

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
```
📜 License

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.---

### 💶 Donate the next songs for my library:

[![PayPal](https://img.shields.io/badge/PayPal-004595?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/StefanAretz89)

### 🤝 Acknowledgements & Third-Party Tech

STARAIN stands on the shoulders of giants. This project would not be possible without the following amazing Open Source projects:

* **[Navidrome](https://www.navidrome.org/)** (GPLv3) – The core music server we all love.
* **[Essentia](https://essentia.upf.edu/)** (AGPLv3/GPLv3) – The powerful audio analysis library from MTG UPF.
* **[TensorFlow](https://www.tensorflow.org/)** (Apache 2.0) – Providing the machine learning muscle for mood detection.
* **[Librosa](https://librosa.org/)** (ISC) – Essential for audio processing and spectrograms.
* **[Mutagen](https://mutagen.readthedocs.io/)** (GPLv2+) – Handling all the heavy lifting for audio metadata and tags.
* **[OpenL3](https://github.com/marl/openl3)** (Apache 2.0) – Deep audio embeddings for similarity matching.

