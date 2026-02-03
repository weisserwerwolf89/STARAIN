# STARAIN - Stefan Aretz AI Navidrome Architect
# Copyright (C) 2026 Stefan Aretz

import os
import json
import sqlite3
import shutil
import logging
import numpy as np
import uuid
import time
import re
import csv
import random
from datetime import datetime, timezone
from collections import defaultdict
from mutagen.flac import FLAC
from mutagen.id3 import ID3

import starain_config as cfg

# --------------------------------------------------
# Konfiguration
# --------------------------------------------------

DB_PATH = os.getenv("ND_DB_PATH", "/data/navidrome.db")
TEMP_DB_PATH = os.getenv("ND_TEMP_DB_PATH", "/data/navidrome_snap.db")
MUSIC_DIR = os.getenv("ND_MUSIC_DIR", "/music")
PLAYLIST_LIMIT = int(os.getenv("ND_PLAYLIST_LIMIT", "30"))

BLACKLIST_NAME = cfg.get_text("pl_blacklist")

MOOD_BLACKLIST_FILE = "/data/mood_blacklist.csv"
MOOD_HISTORY_FILE = "/data/mood_history.json"

TARGET_MOODS = cfg.translate_list([
    "Explosiv", "Aggressiv", "Friedlich", "Melancholisch", "Party",
    "Tanzbar", "Romantisch", "Gefühlvoll", "Energetisch", "Treibend",
    "Groovy", "Cool"
])

logger = logging.getLogger("DJ_Architect")

# --------------------------------------------------
# Core Class
# --------------------------------------------------

class NavidromeDJ:
    def __init__(self):
        self.library = {}
        self.mood_library = defaultdict(list)
        self.dim_detected = None
        self.last_index_time = 0

    # --------------------------------------------------
    # History
    # --------------------------------------------------

    def _load_history(self):
        if os.path.exists(MOOD_HISTORY_FILE):
            try:
                with open(MOOD_HISTORY_FILE, "r") as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_history(self, history):
        try:
            with open(MOOD_HISTORY_FILE, "w") as f:
                json.dump(history, f)
        except Exception as e:
            logger.error(f"History Save Error: {e}")

    # --------------------------------------------------
    # Mood Blacklist (menschenlesbar)
    # --------------------------------------------------

    def _append_to_mood_blacklist(self, user_id, mood, song_id):
        try:
            artist = album = title = "Unknown"

            try:
                with sqlite3.connect(DB_PATH, timeout=10) as conn:
                    row = conn.execute(
                        "SELECT artist, album, title FROM media_file WHERE id = ?",
                        (song_id,)
                    ).fetchone()
                    if row:
                        artist, album, title = row
            except:
                pass

            file_exists = os.path.exists(MOOD_BLACKLIST_FILE)

            with open(MOOD_BLACKLIST_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow([
                        "user_id",
                        "mood",
                        "song_id",
                        "artist",
                        "album",
                        "title",
                        "timestamp"
                    ])
                writer.writerow([
                    str(user_id),
                    mood,
                    str(song_id),
                    artist,
                    album,
                    title,
                    datetime.now().isoformat()
                ])
        except Exception as e:
            logger.error(f"Mood Blacklist Write Error: {e}")

    def _get_mood_blacklist(self, user_id, mood):
        blocked_ids = set()
        if not os.path.exists(MOOD_BLACKLIST_FILE):
            return blocked_ids

        try:
            with open(MOOD_BLACKLIST_FILE, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 3 and str(row[0]) == str(user_id) and row[1] == mood:
                        blocked_ids.add(str(row[2]))
        except:
            pass

        return blocked_ids

    # --------------------------------------------------
    # DB Snapshot
    # --------------------------------------------------

    def create_safe_snapshot(self):
        try:
            if not os.path.exists(DB_PATH):
                return False
            shutil.copy2(DB_PATH, TEMP_DB_PATH)
            return True
        except:
            return False

    # --------------------------------------------------
    # Metadata
    # --------------------------------------------------

    def extract_metadata(self, filepath):
        vec = None
        moods_found = []

        try:
            ext = os.path.splitext(filepath)[1].lower()

            if ext == ".flac":
                tags = FLAC(filepath)
                if "XX_EMBEDDING_JSON" in tags:
                    vec = np.array(json.loads(tags["XX_EMBEDDING_JSON"][0]))
                if "Stimmung" in tags:
                    moods_found = tags["Stimmung"]
                elif "MOOD" in tags:
                    moods_found = tags["MOOD"]

            elif ext == ".mp3":
                tags = ID3(filepath)
                for frame in tags.getall("TXXX"):
                    if frame.desc == "XX_EMBEDDING_JSON":
                        vec = np.array(json.loads(frame.text[0]))
                    if frame.desc.lower() in ["stimmung", "mood"]:
                        moods_found.extend(frame.text)

            if vec is not None:
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
                else:
                    vec = None

        except:
            pass

        return vec, moods_found

    # --------------------------------------------------
    # Index
    # --------------------------------------------------

    def index_library(self):
        self.library = {}
        self.mood_library = defaultdict(list)

        with sqlite3.connect(TEMP_DB_PATH) as conn:
            rows = conn.execute("SELECT id, path FROM media_file").fetchall()

        for song_id, rel_path in rows:
            full_path = os.path.join(MUSIC_DIR, rel_path)
            if not os.path.exists(full_path):
                continue

            vec, raw_moods = self.extract_metadata(full_path)

            if vec is not None:
                self.library[song_id] = vec

            for entry in raw_moods:
                for part in re.split(r"[;,/]", entry):
                    clean = part.strip()
                    for target in TARGET_MOODS:
                        if clean.lower() == target.lower():
                            self.mood_library[target].append(song_id)

        self.last_index_time = time.time()

    # --------------------------------------------------
    # Blacklists / Ratings
    # --------------------------------------------------

    def get_user_blacklist_ids(self, user_id):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                rows = conn.execute("""
                    SELECT pt.media_file_id
                    FROM playlist_tracks pt
                    JOIN playlist p ON pt.playlist_id = p.id
                    WHERE p.name = ? AND p.owner_id = ?
                """, (BLACKLIST_NAME, user_id)).fetchall()
                return {str(r[0]) for r in rows}
        except:
            return set()

    def get_low_rated_ids(self, user_id):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                rows = conn.execute("""
                    SELECT item_id FROM annotation
                    WHERE user_id = ? AND rating BETWEEN 1 AND 2
                """, (user_id,)).fetchall()
                return {str(r[0]) for r in rows}
        except:
            return set()

    # --------------------------------------------------
    # Playlist Write
    # --------------------------------------------------

    def overwrite_playlist(self, user_id, name, song_ids):
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT id FROM playlist WHERE name = ? AND owner_id = ?",
                    (name, user_id)
                )
                row = cursor.fetchone()

                if row:
                    pl_id = row[0]
                else:
                    pl_id = str(uuid.uuid4())
                    now = datetime.now(timezone.utc).isoformat()
                    cursor.execute("""
                        INSERT INTO playlist (id, name, owner_id, public, created_at, updated_at)
                        VALUES (?, ?, ?, 0, ?, ?)
                    """, (pl_id, name, user_id, now, now))

                cursor.execute("DELETE FROM playlist_tracks WHERE playlist_id = ?", (pl_id,))
                data = [(str(uuid.uuid4()), pl_id, sid) for sid in song_ids]
                cursor.executemany(
                    "INSERT INTO playlist_tracks (id, playlist_id, media_file_id) VALUES (?, ?, ?)",
                    data
                )

                cursor.execute(
                    "UPDATE playlist SET song_count = ?, updated_at = ? WHERE id = ?",
                    (len(song_ids), datetime.now(timezone.utc).isoformat(), pl_id)
                )

                conn.commit()
                return pl_id
        except:
            return None

    # --------------------------------------------------
    # Daily Mood Processing (UNVERÄNDERT)
    # --------------------------------------------------

    def process_daily_moods(self, user_id):
        history = self._load_history()
        user_history = history.get(str(user_id), {})

        global_blacklist = self.get_user_blacklist_ids(user_id)
        low_rated = self.get_low_rated_ids(user_id)

        new_user_history = {}

        for mood in TARGET_MOODS:
            pl_name = f"{cfg.MOOD_PREFIX} {mood}"
            candidate_ids = self.mood_library.get(mood, [])
            if not candidate_ids:
                continue

            current_ids = set()
            with sqlite3.connect(DB_PATH) as conn:
                row = conn.execute(
                    "SELECT id FROM playlist WHERE name = ? AND owner_id = ?",
                    (pl_name, user_id)
                ).fetchone()
                if row:
                    tracks = conn.execute(
                        "SELECT media_file_id FROM playlist_tracks WHERE playlist_id = ?",
                        (row[0],)
                    ).fetchall()
                    current_ids = {str(r[0]) for r in tracks}

            if mood in user_history:
                deleted = set(user_history[mood]) - current_ids
                for did in deleted:
                    self._append_to_mood_blacklist(user_id, mood, did)

            mood_blacklist = self._get_mood_blacklist(user_id, mood)

            valid_pool = [
                sid for sid in candidate_ids
                if str(sid) not in global_blacklist
                and str(sid) not in mood_blacklist
                and str(sid) not in low_rated
            ]

            random.shuffle(valid_pool)
            final_selection = valid_pool[:PLAYLIST_LIMIT]

            if final_selection:
                self.overwrite_playlist(user_id, pl_name, final_selection)
                new_user_history[mood] = [str(s) for s in final_selection]

        history[str(user_id)] = new_user_history
        self._save_history(history)

    # --------------------------------------------------
    # Similarity / Heart / Seed Mix (LEGACY – required)
    # --------------------------------------------------

    def normalize_string(self, text):
        if not text:
            return ""
        return "".join(re.findall(r"\w+", text.lower()))

    def normalize_artist(self, artist):
        if not artist:
            return ""
        artist = artist.lower().replace("•", ",")
        parts = re.split(r"[,&]|\bfeat\b|\bft\b", artist, flags=re.IGNORECASE)
        return self.normalize_string(parts[0].strip())

    def get_song_metadata(self, song_id):
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                return conn.execute(
                    "SELECT artist, title FROM media_file WHERE id = ?",
                    (song_id,)
                ).fetchone()
        except:
            return None, None

    def ensure_playlist(self, user_id, name):
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM playlist WHERE name = ? AND owner_id = ?",
                    (name, user_id)
                )
                row = cursor.fetchone()
                if row:
                    return row[0]

                pl_id = str(uuid.uuid4())
                now = datetime.now(timezone.utc).isoformat()
                cursor.execute("""
                    INSERT INTO playlist (id, name, owner_id, public, created_at, updated_at)
                    VALUES (?, ?, ?, 0, ?, ?)
                """, (pl_id, name, user_id, now, now))
                conn.commit()
                return pl_id
        except:
            return None

    def generate_mix(self, user_id, seed_id, mix_name, refill_id=None):
        if seed_id not in self.library or len(self.library) < 2:
            return False

        seed_vec = self.library.get(seed_id)
        if seed_vec is None:
            return False

        scores = []
        for sid, vec in self.library.items():
            if sid == seed_id:
                continue
            dist = 1.0 - np.dot(seed_vec, vec)
            scores.append((sid, dist))

        scores.sort(key=lambda x: x[1])

        candidate_ids = [seed_id] + [sid for sid, _ in scores[:PLAYLIST_LIMIT + 100]]

        user_blacklist = self.get_user_blacklist_ids(user_id)
        low_rated = self.get_low_rated_ids(user_id)

        final_tracks = []
        seen_fingerprints = set()

        for sid in candidate_ids:
            sid_str = str(sid)
            if sid_str in user_blacklist or sid_str in low_rated:
                continue

            artist, title = self.get_song_metadata(sid)
            if artist and title:
                fp = f"{self.normalize_artist(artist)}_{self.normalize_string(title)}"
                if fp in seen_fingerprints:
                    continue
                seen_fingerprints.add(fp)

            final_tracks.append(sid)
            if len(final_tracks) >= PLAYLIST_LIMIT:
                break

        if not final_tracks:
            return False

        pl_id = refill_id if refill_id else self.ensure_playlist(user_id, mix_name)
        if not pl_id:
            return False

        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM playlist_tracks WHERE playlist_id = ?", (pl_id,))
                data = [(str(uuid.uuid4()), pl_id, sid) for sid in final_tracks]
                cursor.executemany(
                    "INSERT INTO playlist_tracks (id, playlist_id, media_file_id) VALUES (?, ?, ?)",
                    data
                )
                cursor.execute(
                    "UPDATE playlist SET song_count = ?, updated_at = ? WHERE id = ?",
                    (len(final_tracks), datetime.now(timezone.utc).isoformat(), pl_id)
                )
                conn.commit()

            logger.info(f"💾 Mix '{mix_name}' gespeichert ({len(final_tracks)} Tracks).")
            return True

        except Exception as e:
            logger.error(f"Mix-Speicherfehler: {e}")
            return False
