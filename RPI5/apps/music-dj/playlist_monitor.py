import os
import time
import sqlite3
import logging
import signal
import sys
from datetime import datetime, timedelta, date
from dj_loop import NavidromeDJ, TARGET_MOODS

# Konfiguration
DB_PATH = os.getenv("ND_DB_PATH", "/data/navidrome.db")
CHECK_INTERVAL = 20
RATING_STAGES = [(35, 4, 5), (15, 3, 4), (5, 0, 3)]
LOCK_DAYS = 1095
COOLDOWN_MINUTES = 1

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [MONITOR] - %(message)s', stream=sys.stdout)
logger = logging.getLogger("PlaylistMonitor")

class PlaylistMonitor:
    def __init__(self):
        self.dj = None
        self.running = True
        self.cooldowns = {}
        self.last_mood_gen_date = None

        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def shutdown(self, signum, frame):
        logger.info("Fahre Monitor sauber herunter...")
        self.running = False

    def get_all_users(self):
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                return conn.execute("SELECT id, user_name FROM user").fetchall()
        except: return []

    def ensure_dj_initialized(self):
        if not self.dj:
            self.dj = NavidromeDJ()
            if self.dj.create_safe_snapshot():
                self.dj.index_library()

    def check_startup_missing_playlists(self):
        """Prüft, ob Mood-Playlists fehlen und erstellt sie sofort."""
        logger.info("🕵️ Prüfe auf fehlende Mood-Playlists...")
        self.ensure_dj_initialized()

        users = self.get_all_users()
        for uid, uname in users:
            try:
                with sqlite3.connect(DB_PATH, timeout=10) as conn:
                    rows = conn.execute("SELECT name FROM playlist WHERE owner_id = ?", (uid,)).fetchall()
                    existing_names = {r[0] for r in rows}

                missing_found = False
                for mood in TARGET_MOODS:
                    target_name = f"Mood: {mood}"
                    if target_name not in existing_names:
                        logger.info(f"⚠️ {uname}: Playlist '{target_name}' fehlt. Starte Sofort-Generierung.")
                        missing_found = True
                        break

                if missing_found:
                    self.dj.process_daily_moods(uid)
                    self.last_mood_gen_date = date.today()

            except Exception as e:
                logger.error(f"Startup-Check Fehler bei {uname}: {e}")

    def check_daily_schedule(self):
        now = datetime.now()
        if now.hour >= 4 and self.last_mood_gen_date != date.today():
            logger.info("🕓 Es ist 4 Uhr durch - Zeit für die Daily Moods!")
            self.ensure_dj_initialized()

            if time.time() - self.dj.last_index_time > 86000:
                if self.dj.create_safe_snapshot():
                    self.dj.index_library()

            users = self.get_all_users()
            for uid, uname in users:
                self.dj.process_daily_moods(uid)

            self.last_mood_gen_date = date.today()
            logger.info("✅ Daily Moods abgeschlossen.")

    def check_ratings(self, user_id, user_name):
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                lock_date = (datetime.now() - timedelta(days=LOCK_DAYS)).isoformat()
                cursor = conn.cursor()
                for plays, cur, new in RATING_STAGES:
                    cond = "(ann.rating IS NULL OR ann.rating = 0)" if cur == 0 else f"ann.rating = {cur}"
                    query = f"""
                        SELECT ann.item_id, mf.title FROM annotation ann
                        JOIN media_file mf ON ann.item_id = mf.id
                        WHERE ann.user_id = ? AND ann.play_count >= ? AND {cond}
                        AND (ann.rated_at IS NULL OR ann.rated_at < ?)
                    """
                    cursor.execute(query, (user_id, plays, lock_date))
                    for rid, title in cursor.fetchall():
                        logger.info(f"🚀 {user_name}: '{title}' -> {new} Sterne")
                        cursor.execute("UPDATE annotation SET rating = ? WHERE user_id = ? AND item_id = ?", (new, user_id, rid))
                conn.commit()
        except Exception as e: logger.error(f"Rating-Fehler: {e}")

    def is_in_cooldown(self, pl_id):
        if pl_id not in self.cooldowns: return False
        return (time.time() - self.cooldowns[pl_id]) < (COOLDOWN_MINUTES * 60)

    def check_playlists(self, user_id, user_name):
        try:
            queue = []
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                favs = conn.execute("""
                    SELECT mf.id, mf.title, mf.artist FROM annotation ann
                    JOIN media_file mf ON ann.item_id = mf.id
                    WHERE ann.user_id = ? AND ann.starred = 1
                """, (user_id,)).fetchall()

                for fid, title, artist in favs:
                    name = f"KI-Mix: {title} - {artist}"
                    row = conn.execute("SELECT id FROM playlist WHERE owner_id = ? AND name = ?", (user_id, name)).fetchone()

                    if not row:
                        queue.append((fid, name, None))
                    else:
                        pl_id = row[0]
                        if self.is_in_cooldown(pl_id): continue

                        cnt = conn.execute("SELECT COUNT(*) FROM playlist_tracks WHERE playlist_id = ?", (pl_id,)).fetchone()[0]
                        bad_songs = conn.execute("""
                            SELECT COUNT(*) FROM playlist_tracks pt
                            LEFT JOIN annotation ann ON pt.media_file_id = ann.item_id AND ann.user_id = ?
                            WHERE pt.playlist_id = ?
                            AND (
                                ann.rating BETWEEN 1 AND 2
                                OR pt.media_file_id IN (
                                    SELECT media_file_id FROM playlist_tracks pt2
                                    JOIN playlist p ON pt2.playlist_id = p.id
                                    WHERE p.name = 'KI-Blacklist' AND p.owner_id = ?
                                )
                            )
                        """, (user_id, pl_id, user_id)).fetchone()[0]

                        if cnt < 30 or bad_songs > 0:
                            queue.append((fid, name, pl_id))
                            self.cooldowns[pl_id] = time.time()

            if queue:
                self.ensure_dj_initialized()
                for fid, name, plid in queue:
                    if fid in self.dj.library:
                        self.dj.generate_mix(user_id, fid, name, refill_id=plid)
        except Exception as e: logger.error(f"Playlist-Fehler: {e}")

    def run(self):
        logger.info(f"🚀 Monitor aktiv (Intervall: {CHECK_INTERVAL}s)")
        time.sleep(5)

        self.check_startup_missing_playlists()

        while self.running:
            self.check_daily_schedule()
            for uid, uname in self.get_all_users():
                self.check_ratings(uid, uname)
                self.check_playlists(uid, uname)
            for _ in range(CHECK_INTERVAL):
                if not self.running: break
                time.sleep(1)

if __name__ == "__main__":
    PlaylistMonitor().run()
