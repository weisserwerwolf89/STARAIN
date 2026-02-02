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

# Konfiguration
DB_PATH = os.getenv("ND_DB_PATH", "/data/navidrome.db")
TEMP_DB_PATH = os.getenv("ND_TEMP_DB_PATH", "/data/navidrome_snap.db")
MUSIC_DIR = os.getenv("ND_MUSIC_DIR", "/music")
PLAYLIST_LIMIT = int(os.getenv("ND_PLAYLIST_LIMIT", "30"))
BLACKLIST_NAME = "KI-Blacklist"

# Neue Dateien für Mood-Logik
MOOD_BLACKLIST_FILE = "/data/mood_blacklist.csv"
MOOD_HISTORY_FILE = "/data/mood_history.json"

# Die gewünschten Moods (müssen exakt so heißen wie im Tag oder Mapping)
TARGET_MOODS = [
    "Explosiv", "Aggressiv", "Friedlich", "Melancholisch", "Party",
    "Tanzbar", "Romantisch", "Gefühlvoll", "Energetisch", "Treibend",
    "Groovy", "Cool"
]

logger = logging.getLogger("DJ_Architect")

class NavidromeDJ:
    def __init__(self):
        self.library = {}        # {song_id: vector}
        self.mood_library = defaultdict(list) # {mood_name: [song_ids]}
        self.dim_detected = None
        self.last_index_time = 0

    # --- Hilfsfunktionen ---

    def _load_history(self):
        """Lädt den Zustand der Playlists von gestern."""
        if os.path.exists(MOOD_HISTORY_FILE):
            try:
                with open(MOOD_HISTORY_FILE, 'r') as f:
                    return json.load(f)
            except: pass
        return {}

    def _save_history(self, history):
        """Speichert den aktuellen Zustand."""
        try:
            with open(MOOD_HISTORY_FILE, 'w') as f:
                json.dump(history, f)
        except Exception as e:
            logger.error(f"Fehler beim Speichern der History: {e}")

    def _append_to_mood_blacklist(self, user_id, mood, song_id):
        """Schreibt einen Eintrag in die CSV."""
        try:
            file_exists = os.path.exists(MOOD_BLACKLIST_FILE)
            with open(MOOD_BLACKLIST_FILE, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["user_id", "mood", "song_id", "timestamp"])
                writer.writerow([str(user_id), mood, str(song_id), datetime.now().isoformat()])
        except Exception as e:
            logger.error(f"Fehler beim Schreiben der Mood-Blacklist: {e}")

    def _get_mood_blacklist(self, user_id, mood):
        """Liest gesperrte Songs für User+Mood aus CSV."""
        blocked_ids = set()
        if not os.path.exists(MOOD_BLACKLIST_FILE):
            return blocked_ids
        try:
            with open(MOOD_BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None) # Header überspringen
                for row in reader:
                    if len(row) >= 3:
                        u, m, s = row[0], row[1], row[2]
                        if str(u) == str(user_id) and m == mood:
                            blocked_ids.add(s)
        except Exception as e:
            logger.error(f"Fehler beim Lesen der Mood-Blacklist: {e}")
        return blocked_ids

    # --- Core Logic ---

    def create_safe_snapshot(self):
        try:
            if not os.path.exists(DB_PATH):
                logger.error(f"❌ Original DB fehlt: {DB_PATH}")
                return False
            shutil.copy2(DB_PATH, TEMP_DB_PATH)
            return True
        except Exception as e:
            logger.error(f"Snapshot Fehler: {e}")
            return False

    def extract_metadata(self, filepath):
        """Liest Embedding UND Mood Tags."""
        vec = None
        moods_found = []
        try:
            ext = os.path.splitext(filepath)[1].lower()
            tags = None

            if ext == '.flac':
                tags = FLAC(filepath)
                # Embedding
                if "XX_EMBEDDING_JSON" in tags:
                    vec = np.array(json.loads(tags["XX_EMBEDDING_JSON"][0]))
                # Mood (Priorität: "Stimmung" -> "MOOD")
                if "Stimmung" in tags:
                    moods_found = tags["Stimmung"]
                elif "MOOD" in tags:
                    moods_found = tags["MOOD"]

            elif ext == '.mp3':
                tags = ID3(filepath)
                # Embedding
                for frame in tags.getall("TXXX"):
                    if frame.desc == "XX_EMBEDDING_JSON":
                        vec = np.array(json.loads(frame.text[0]))
                    # Mood Check ID3
                    if frame.desc.lower() in ["stimmung", "mood"]:
                        moods_found.extend(frame.text)

            # Normalisierung Vektor
            if vec is not None:
                if self.dim_detected is None: self.dim_detected = vec.shape[0]
                elif vec.shape[0] == self.dim_detected:
                    norm = np.linalg.norm(vec)
                    if norm > 0: vec = vec / norm
                    else: vec = None
                else: vec = None # Falsche Dimension

        except Exception as e:
            pass # Silent fail bei defekten Dateien

        return vec, moods_found

    def index_library(self):
        logger.info("📚 Indiziere Bibliothek (inkl. Moods)...")
        self.library = {}
        self.mood_library = defaultdict(list)
        self.dim_detected = None

        try:
            with sqlite3.connect(TEMP_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, path FROM media_file")
                rows = cursor.fetchall()

            for song_id, rel_path in rows:
                full_path = os.path.join(MUSIC_DIR, rel_path)
                if not os.path.exists(full_path): continue

                vec, raw_moods = self.extract_metadata(full_path)

                # Embedding speichern
                if vec is not None:
                    self.library[song_id] = vec

                # Moods speichern
                if raw_moods:
                    for m_entry in raw_moods:
                        parts = re.split(r'[;,\/]', m_entry)
                        for part in parts:
                            clean_mood = part.strip()
                            for target in TARGET_MOODS:
                                if clean_mood.lower() == target.lower():
                                    self.mood_library[target].append(song_id)

            self.last_index_time = time.time()
            logger.info(f"✅ {len(self.library)} Songs mit Embeddings.")
            total_mood_entries = sum(len(v) for v in self.mood_library.values())
            logger.info(f"✅ {total_mood_entries} Mood-Zuordnungen gefunden.")

        except Exception as e:
            logger.error(f"Index Fehler: {e}")

    # --- Blacklist Helper ---

    def get_user_blacklist_ids(self, user_id):
        blacklisted = set()
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                cursor = conn.cursor()
                query = """
                    SELECT pt.media_file_id FROM playlist_tracks pt
                    JOIN playlist p ON pt.playlist_id = p.id
                    WHERE p.name = ? AND p.owner_id = ?
                """
                cursor.execute(query, (BLACKLIST_NAME, user_id))
                rows = cursor.fetchall()
                blacklisted = {str(row[0]) for row in rows}
        except Exception as e:
            logger.error(f"Fehler beim Laden der User-Blacklist: {e}")
        return blacklisted

    def get_low_rated_ids(self, user_id, max_rating=2):
        low_rated = set()
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT item_id FROM annotation
                    WHERE user_id = ? AND rating BETWEEN 1 AND ?
                """, (user_id, max_rating))
                rows = cursor.fetchall()
                low_rated = {str(row[0]) for row in rows}
        except Exception as e:
            logger.error(f"Fehler beim Laden der Low-Rated Songs: {e}")
        return low_rated

    # --- DB Write Helper ---

    def overwrite_playlist(self, user_id, playlist_name, song_ids):
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT id FROM playlist WHERE name = ? AND owner_id = ?", (playlist_name, user_id))
                row = cursor.fetchone()
                if row:
                    pl_id = row[0]
                else:
                    pl_id = str(uuid.uuid4())
                    now = datetime.now(timezone.utc).isoformat()
                    cursor.execute("""
                        INSERT INTO playlist (id, name, owner_id, public, created_at, updated_at)
                        VALUES (?, ?, ?, 0, ?, ?)
                    """, (pl_id, playlist_name, user_id, now, now))

                cursor.execute("DELETE FROM playlist_tracks WHERE playlist_id = ?", (pl_id,))

                data = []
                for sid in song_ids:
                    data.append((str(uuid.uuid4()), pl_id, sid))

                cursor.executemany("INSERT INTO playlist_tracks (id, playlist_id, media_file_id) VALUES (?, ?, ?)", data)

                now = datetime.now(timezone.utc).isoformat()
                cursor.execute("UPDATE playlist SET song_count = ?, updated_at = ? WHERE id = ?", (len(song_ids), now, pl_id))
                conn.commit()
                return pl_id
        except Exception as e:
            logger.error(f"Fehler beim Schreiben der Playlist {playlist_name}: {e}")
            return None

    # --- Daily Routine ---

    def process_daily_moods(self, user_id):
        logger.info(f"🌙 Starte Daily Mood Mix für User {user_id}")

        history = self._load_history()
        user_history = history.get(str(user_id), {})

        global_blacklist = self.get_user_blacklist_ids(user_id)
        low_rated = self.get_low_rated_ids(user_id)

        new_user_history = {}

        for mood in TARGET_MOODS:
            pl_name = f"Mood: {mood}"

            candidate_ids = self.mood_library.get(mood, [])
            if not candidate_ids:
                continue

            current_ids_in_playlist = set()
            try:
                with sqlite3.connect(DB_PATH, timeout=10) as conn:
                    row = conn.execute("SELECT id FROM playlist WHERE name = ? AND owner_id = ?", (pl_name, user_id)).fetchone()
                    if row:
                        pl_id = row[0]
                        rows = conn.execute("SELECT media_file_id FROM playlist_tracks WHERE playlist_id = ?", (pl_id,)).fetchall()
                        current_ids_in_playlist = {str(r[0]) for r in rows}
            except Exception as e:
                logger.error(f"Fehler beim Checken alter Playlist {pl_name}: {e}")

            if mood in user_history:
                old_ids = set(user_history[mood])
                if current_ids_in_playlist:
                    deleted_ids = old_ids - current_ids_in_playlist
                    for did in deleted_ids:
                        logger.info(f"🚫 User {user_id} hat Song {did} aus '{mood}' entfernt -> Blacklist.")
                        self._append_to_mood_blacklist(user_id, mood, did)

            mood_blacklist = self._get_mood_blacklist(user_id, mood)

            valid_pool = []
            backup_pool = []

            for sid in candidate_ids:
                sid_str = str(sid)

                if sid_str in global_blacklist: continue
                if sid_str in mood_blacklist: continue

                if sid_str in low_rated:
                    backup_pool.append(sid)
                else:
                    valid_pool.append(sid)

            random.shuffle(valid_pool)
            random.shuffle(backup_pool)

            final_selection = valid_pool[:PLAYLIST_LIMIT]

            if len(final_selection) < PLAYLIST_LIMIT:
                needed = PLAYLIST_LIMIT - len(final_selection)
                final_selection.extend(backup_pool[:needed])

            if final_selection:
                self.overwrite_playlist(user_id, pl_name, final_selection)
                new_user_history[mood] = [str(s) for s in final_selection]
                logger.info(f"✅ Mix '{pl_name}' erstellt ({len(final_selection)} Songs).")

        history[str(user_id)] = new_user_history
        self._save_history(history)

    # --- Integration für normalen Loop (Legacy Support) ---

    def normalize_string(self, text):
        if not text: return ""
        text = re.sub(r'[\(\[].*?[\)\]]', '', text)
        return "".join(re.findall(r'\w+', text.lower()))

    def normalize_artist(self, artist):
        if not artist: return ""
        artist = artist.lower().replace("•", ",")
        parts = re.split(r'[,&]|\bfeat\b|\bft\b', artist, flags=re.IGNORECASE)
        main_artist = parts[0].strip()
        return self.normalize_string(main_artist)

    def get_song_metadata(self, song_id):
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                return conn.execute("SELECT artist, title FROM media_file WHERE id = ?", (song_id,)).fetchone()
        except: return None, None

    def ensure_playlist(self, user_id, name):
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM playlist WHERE name = ? AND owner_id = ?", (name, user_id))
                row = cursor.fetchone()
                if row: return row[0]
                pl_uuid = str(uuid.uuid4())
                now = datetime.now(timezone.utc).isoformat()
                cursor.execute("""
                    INSERT INTO playlist (id, name, owner_id, public, created_at, updated_at)
                    VALUES (?, ?, ?, 0, ?, ?)
                """, (pl_uuid, name, user_id, now, now))
                conn.commit()
                return pl_uuid
        except: return None

    def generate_mix(self, user_id, seed_id, mix_name, refill_id=None):
        if len(self.library) < 2: return False
        seed_vec = self.library.get(seed_id)
        if seed_vec is None: return False
        scores = []
        for sid, vec in self.library.items():
            if sid == seed_id: continue
            dist = 1.0 - np.dot(seed_vec, vec)
            scores.append((sid, dist))
        scores.sort(key=lambda x: x[1])
        candidate_ids = [seed_id] + [s[0] for s in scores[:PLAYLIST_LIMIT + 100]]
        user_blacklist = self.get_user_blacklist_ids(user_id)
        low_rated = self.get_low_rated_ids(user_id)
        final_track_list = []
        seen_fingerprints = set()
        for sid in candidate_ids:
            sid_str = str(sid)
            if sid_str in user_blacklist or sid_str in low_rated: continue
            artist, title = self.get_song_metadata(sid)
            if artist and title:
                fingerprint = f"{self.normalize_artist(artist)}_{self.normalize_string(title)}"
                if fingerprint in seen_fingerprints: continue
                seen_fingerprints.add(fingerprint)
            final_track_list.append(sid)
            if len(final_track_list) >= PLAYLIST_LIMIT: break
        try:
            pl_id = refill_id if refill_id else self.ensure_playlist(user_id, mix_name)
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute("BEGIN IMMEDIATE")
                cursor.execute("DELETE FROM playlist_tracks WHERE playlist_id = ?", (pl_id,))
                data = [(str(uuid.uuid4()), pl_id, sid) for sid in final_track_list]
                cursor.executemany("INSERT INTO playlist_tracks (id, playlist_id, media_file_id) VALUES (?, ?, ?)", data)
                now = datetime.now(timezone.utc).isoformat()
                cursor.execute("UPDATE playlist SET song_count = ?, updated_at = ? WHERE id = ?", (len(final_track_list), now, pl_id))
                conn.commit()
            logger.info(f"💾 Mix '{mix_name}' gespeichert ({len(final_track_list)} Tracks).")
            return True
        except Exception as e:
            logger.error(f"Speicherfehler: {e}")
            return False
