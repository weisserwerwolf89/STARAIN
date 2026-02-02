# STARAIN - Stefan Aretz AI Navidrome Architect
# Copyright (C) 2026 Stefan Aretz
# Licensed under the GNU General Public License v3.0


import os
import time
import subprocess
import argparse
import sqlite3
import sys
import shutil
import datetime
import logging
import random
import mutagen
from mutagen.id3 import ID3

# --- KONFIGURATION ---
DB_PATH = "/navidrome.db"
MUSIC_DIR = "/music"
WORKER_SCRIPT = "analyze_worker.py"
ORGANIZER_SCRIPT = "organize_worker.py" # <--- Der optionaler Hausmeister

logging.basicConfig(level=logging.INFO, format='%(message)s')

def get_time():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ==========================================
# MANAGER TOOLS (Snapshot & Status)
# ==========================================

def get_file_analyze_status(filepath):
    """Prüft auf XX_ANALYZE_DONE Tag."""
    try:
        f = mutagen.File(filepath)
        if f is None: return 'VIRGIN'

        def read_tag(key):
            v = None
            if hasattr(f, 'get'):
                res = f.get(key)
                if res: v = res[0]
            if v is None and hasattr(f, 'tags') and isinstance(f.tags, ID3):
                for frame in f.tags.getall("TXXX"):
                    if frame.desc == key:
                        v = frame.text[0]; break
            return str(v).strip() if v else None

        val = read_tag("XX_ANALYZE_DONE")
        if val and len(val) > 5: return 'DONE'
        return 'VIRGIN'
    except:
        return 'VIRGIN'

def create_db_snapshot(src_db):
    temp_db = "/tmp/navidrome_snapshot.db"
    if os.path.exists(temp_db):
        try: os.remove(temp_db)
        except: pass
    try:
        if not os.path.exists(src_db): return None
        shutil.copy2(src_db, temp_db)
        if os.path.exists(src_db + "-wal"):
            shutil.copy2(src_db + "-wal", temp_db + "-wal")
        return temp_db
    except Exception as e:
        print(f"❌ Snapshot Fehler: {e}")
        return None

def get_files_from_db(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT path FROM media_file")
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        print(f"❌ SQL Fehler: {e}")
        return []

# ==========================================
# MAIN LOOP
# ==========================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DB_PATH)
    parser.add_argument("--music_dir", default=MUSIC_DIR)
    args = parser.parse_args()

    print(f"--- MANAGER GESTARTET (V5.2 Modular Edition) ---", flush=True)
    print(f"Modus: Random Shuffle + Optionaler Hausmeister", flush=True)

    while True:
        try:
            # 1. ORGANIZER CHECK
            # Wir prüfen, ob das Skript existiert. Wenn ja, führen wir es aus.
            if os.path.exists(ORGANIZER_SCRIPT):
                # print(f"[{get_time()}] 🧹 Starte externen Hausmeister...", flush=True)
                try:
                    subprocess.run(
                        ["python3", ORGANIZER_SCRIPT, "--music_dir", args.music_dir],
                        check=False # Wir wollen nicht crashen, wenn der Hausmeister stolpert
                    )
                except Exception as e:
                    print(f"❌ Fehler beim Hausmeister-Aufruf: {e}")
            else:
                # Silent Skip - Wenn das Skript fehlt, machen wir einfach weiter
                pass

            # 2. SNAPSHOT
            snap_db = create_db_snapshot(args.db)
            if not snap_db:
                print("Warte auf DB...", flush=True)
                time.sleep(10)
                continue

            # 3. DATEIEN HOLEN
            db_files = get_files_from_db(snap_db)

            # 4. QUEUE BAUEN (VOR-FILTER)
            queue = []
            if len(db_files) > 0:
                print(f"[{get_time()}] 🔍 Prüfe DB auf neue Songs...", flush=True)

            for db_path in db_files:
                rel_path = db_path
                if rel_path.startswith("/music/"): rel_path = rel_path[7:]
                elif rel_path.startswith("/"): rel_path = rel_path[1:]

                full_path = os.path.join(args.music_dir, rel_path)
                if not os.path.exists(full_path): continue

                if get_file_analyze_status(full_path) == 'VIRGIN':
                    queue.append(full_path)

            # 5. CLUSTER-LOGIK: MISCHEN!
            if queue:
                random.shuffle(queue)
                print(f"[{get_time()}] 🎲 Queue gemischt ({len(queue)} Songs).", flush=True)
            else:
                print(f"[{get_time()}] ✅ Alles fertig. Schlafe 5 Minuten...", flush=True)
                time.sleep(300)
                continue

            # 6. ABARBEITEN
            for i, full_path in enumerate(queue):
                # Check, falls der Cluster-Partner schneller war
                if get_file_analyze_status(full_path) == 'DONE':
                    continue

                filename = os.path.basename(full_path)
                print(f"\n[{i+1}/{len(queue)}] [START] {filename}", flush=True)

                try:
                    process = subprocess.Popen(
                        ["python3", WORKER_SCRIPT, "--file", full_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1
                    )
                    for line in process.stdout:
                        print(f"   | {line.strip()}", flush=True)
                    process.wait()

                    if process.returncode == 0:
                        print(f"[SUCCESS] {filename}", flush=True)
                    else:
                        print(f"[FAIL] Exit Code {process.returncode}", flush=True)

                except Exception as e:
                    print(f"❌ Worker Start Fehler: {e}", flush=True)

                time.sleep(0.1)

            print(f"[{get_time()}] Runde beendet. Schlafe 5 Minuten...", flush=True)
            time.sleep(300)

        except Exception as e:
            print(f"❌ Loop Fehler: {e}", flush=True)
            time.sleep(60)

if __name__ == "__main__":
    main()
