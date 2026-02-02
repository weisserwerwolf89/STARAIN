import os
import sys
import argparse
import datetime
import logging
import gc
import json
import csv
import subprocess
import shutil
import numpy as np
import soundfile as sf
import essentia.standard as es
import librosa
from scipy.spatial.distance import cosine
import mutagen
from mutagen.id3 import ID3, TXXX, TBPM, TKEY, TMOO
from mutagen.flac import FLAC

logging.basicConfig(level=logging.ERROR)
TIME_FMT = "%Y-%m-%d %H:%M:%S"
ANCHOR_BASE_PATH = "/anker"
CSV_LOG_PATH = os.path.join(ANCHOR_BASE_PATH, "analysis_history.csv")
AUSSORTIERT_PATH = os.getenv("AUSSORTIERT_PATH", "/aussortiert")

# --- VERSIONIERUNG & KONFIGURATION ---
ALGO_VERSION = "2026-02-01-v2-robust"  # Damit du später weißt, wer das war
FFMPEG_TIMEOUT = 30                    # Sekunden, bevor FFmpeg abgeschossen wird
BPM_LIMITS = (40, 210)                 # Alles außerhalb ist Müll/Fehler

# --- MOOD TABLE ---
MOOD_TABLE = {
    "Explosiv":      {"min_int": 0.85, "min_dance": 1.5},
    "Aggressiv":     {"min_int": 0.80, "scale": "minor"},
    "Friedlich":     {"max_int": 0.45, "scale": "major"},
    "Melancholisch": {"max_int": 0.60, "scale": "minor"},
    "Party":         {"min_dance": 1.6, "scale": "major", "min_int": 0.6},
    "Tanzbar":       {"min_dance": 1.4},
    "Romantisch":    {"min_bpm": 40, "max_bpm": 100, "max_dance": 1.2, "max_int": 0.55},
    "Gefühlvoll":    {"min_bpm": 50, "max_bpm": 110, "max_dance": 1.3},
    "Energetisch":   {"min_bpm": 128, "min_int": 0.7},
    "Treibend":      {"min_bpm": 130, "min_dance": 1.6},
    "Groovy":        {"min_dance": 1.5, "max_bpm": 125},
    "Cool":          {"min_dance": 1.4, "max_int": 0.65}
}

# --- GPU/KI SETUP ---
openl3, tf = None, None
GPU_INITIALIZED = False
USE_GPU = False
INITIAL_BATCH_SIZE = 1

def ensure_gpu_libraries():
    global tf, openl3, GPU_INITIALIZED, USE_GPU, INITIAL_BATCH_SIZE
    if GPU_INITIALIZED: return
    try:
        import tensorflow as tf
        import openl3
        physical_devices = tf.config.list_physical_devices('GPU')
        USE_GPU = len(physical_devices) > 0
        INITIAL_BATCH_SIZE = 32 if USE_GPU else 1
        print(f" 🖥️  [SYSTEM] KI-Modus: {'GPU 🚀' if USE_GPU else 'CPU 🐢'} (Batch: {INITIAL_BATCH_SIZE})", flush=True)
    except Exception as e:
        sys.stderr.write(f" ⚠️  [WARN] KI-Libs nicht geladen: {e}\n")
    GPU_INITIALIZED = True

def log_to_csv(data):
    try:
        file_exists = os.path.isfile(CSV_LOG_PATH)
        with open(CSV_LOG_PATH, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "Timestamp", "Filename", "Action", "BPM_Final", "Method",
                "Anchor_Ref", "Score", "Confidence", "Essentia_Raw", "Librosa_Raw"
            ])
            if not file_exists: writer.writeheader()
            data["Timestamp"] = datetime.datetime.now().strftime(TIME_FMT)
            writer.writerow(data)
    except Exception as e:
        print(f" ⚠️  [CSV-ERROR] Konnte {CSV_LOG_PATH} nicht schreiben: {e}", flush=True)

def move_to_aussortiert(filepath, reason="Unknown"):
    if not os.path.exists(AUSSORTIERT_PATH):
        try: os.makedirs(AUSSORTIERT_PATH)
        except: return
    filename = os.path.basename(filepath)
    target = os.path.join(AUSSORTIERT_PATH, filename)
    counter = 1
    base, ext = os.path.splitext(target)
    while os.path.exists(target):
        target = f"{base}_{counter}{ext}"
        counter += 1
    try:
        print(f" 🗑️  [AUSSORTIERT] Grund: {reason} -> {os.path.basename(target)}", flush=True)
        shutil.move(filepath, target)
        with open(target + ".log", "w") as f:
            f.write(f"Date: {datetime.datetime.now()}\nReason: {reason}\nOrigin: {filepath}\nVersion: {ALGO_VERSION}")
    except Exception as e:
        print(f" ❌ [ERROR] Verschieben fehlgeschlagen: {e}", flush=True)

def robust_heal_and_verify(filepath):
    """
    Versucht Reparatur mit Timeout. Gibt True zurück, wenn erfolgreich.
    """
    temp_repaired = filepath + ".repaired_temp" + os.path.splitext(filepath)[1]
    print(f" 🔧 [HEAL] Versuche Reparatur via FFmpeg (Timeout: {FFMPEG_TIMEOUT}s)...", flush=True)

    cmd = []
    if filepath.lower().endswith(".flac"):
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", filepath, "-c:a", "flac", temp_repaired]
    else:
        # MP3: Erst copy versuchen
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", filepath, "-c:a", "copy", temp_repaired]

    try:
        # NEU: Timeout hinzugefügt, damit Worker nicht einfriert
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=FFMPEG_TIMEOUT)
    except subprocess.TimeoutExpired:
        print(f" ❌ [HEAL-FAIL] FFmpeg Timeout nach {FFMPEG_TIMEOUT}s!", flush=True)
        if os.path.exists(temp_repaired): os.remove(temp_repaired)
        return False
    except subprocess.CalledProcessError:
        # Fallback: Re-Encode
        try:
            cmd = ["ffmpeg", "-y", "-v", "error", "-i", filepath, temp_repaired]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=FFMPEG_TIMEOUT)
        except:
            if os.path.exists(temp_repaired): os.remove(temp_repaired)
            return False

    # PRÜFUNG:
    try:
        loader = es.MonoLoader(filename=temp_repaired, sampleRate=44100)
        test_audio = loader()
        if len(test_audio) < 1000: raise ValueError("Audio leer")
    except Exception:
        if os.path.exists(temp_repaired): os.remove(temp_repaired)
        return False

    # ERFOLG:
    try:
        shutil.move(temp_repaired, filepath)
        print(f" ✅ [HEAL-OK] Datei repariert.", flush=True)
        return True
    except Exception:
        return False

def read_metadata_for_embedding(filepath):
    # ... (Code wie zuvor) ...
    try:
        f = mutagen.File(filepath)
        if isinstance(f, FLAC) and "XX_EMBEDDING_JSON" in f:
            return json.loads(f["XX_EMBEDDING_JSON"][0])
        elif f.tags and isinstance(f.tags, ID3):
            for frame in f.tags.getall("TXXX"):
                if frame.desc == "XX_EMBEDDING_JSON": return json.loads(frame.text[0])
    except: pass
    return None

def read_metadata_from_tag(filepath):
    # ... (Code wie zuvor) ...
    try:
        f = mutagen.File(filepath)
        data = {"emb": None, "bpm": 120}
        if isinstance(f, FLAC):
            if "XX_EMBEDDING_JSON" in f: data["emb"] = json.loads(f["XX_EMBEDDING_JSON"][0])
            if "BPM" in f: data["bpm"] = float(f["BPM"][0])
        elif f.tags and isinstance(f.tags, ID3):
            for frame in f.tags.getall("TXXX"):
                if frame.desc == "XX_EMBEDDING_JSON": data["emb"] = json.loads(frame.text[0])
            if "TBPM" in f.tags: data["bpm"] = float(f.tags["TBPM"].text[0])
        return data
    except: return {"emb": None, "bpm": 120}

def load_all_anchors():
    # ... (Code wie zuvor) ...
    anchors = []
    if not os.path.exists(ANCHOR_BASE_PATH): return anchors
    for category in ["FAST", "MID", "SLOW"]:
        cat_path = os.path.join(ANCHOR_BASE_PATH, category)
        if not os.path.exists(cat_path): continue
        for f_name in os.listdir(cat_path):
            if f_name.lower().endswith((".flac", ".mp3")):
                meta = read_metadata_from_tag(os.path.join(cat_path, f_name))
                if meta["emb"]:
                    anchors.append({"category": category, "name": f_name, "embedding": meta["emb"], "bpm": meta.get("bpm", 120)})
    return anchors

def determine_bpm_logic(essentia_bpm, librosa_bpm, anchor_bpm):
    # ... (Code wie zuvor) ...
    TOLERANCE = 4.0
    if abs(essentia_bpm - anchor_bpm) <= TOLERANCE: return int(round(essentia_bpm)), "Essentia (Direct)"
    if librosa_bpm > 0 and abs(librosa_bpm - anchor_bpm) <= TOLERANCE: return int(round(librosa_bpm)), "Librosa (Direct)"
    candidates = []
    for factor in [1, 2, 3]:
        candidates.append((essentia_bpm * factor, f"Essentia x{factor}"))
        candidates.append((essentia_bpm / factor, f"Essentia /{factor}"))
    if librosa_bpm > 0:
        for factor in [1, 2, 3]:
            candidates.append((librosa_bpm * factor, f"Librosa x{factor}"))
            candidates.append((librosa_bpm / factor, f"Librosa /{factor}"))
    if not candidates: return int(round(anchor_bpm)), "Anchor-Fallback"
    best_val, best_desc = min(candidates, key=lambda x: abs(x[0] - anchor_bpm))
    return int(round(best_val)), best_desc

def determine_moods(bpm, key_str, dance, intensity):
    # ... (Code wie zuvor) ...
    matches = []
    scale = "major" if any(x in key_str.lower() for x in ["major", "dur"]) else "minor"
    is_slow_ballad = (dance < 1.35) and (bpm < 95)
    for mood, c in MOOD_TABLE.items():
        if is_slow_ballad and mood in ["Party", "Treibend", "Explosiv", "Energetisch"]: continue
        match = True
        if "min_bpm" in c and bpm < c["min_bpm"]: match = False
        if "max_bpm" in c and bpm > c["max_bpm"]: match = False
        if "min_dance" in c and dance < c["min_dance"]: match = False
        if "max_dance" in c and dance > c["max_dance"]: match = False
        if "min_int" in c and intensity < c["min_int"]: match = False
        if "max_int" in c and intensity > c["max_int"]: match = False
        if "scale" in c and scale != c["scale"]: match = False
        if match: matches.append(mood)
    return matches if matches else ["Ernst"]

def write_tags(filepath, data, was_healed=False):
    """Schreibt Metadaten und Audit-Tags."""
    try:
        f = mutagen.File(filepath)
        if f is None: return False
        if f.tags is None: f.add_tags()
        ts = datetime.datetime.now().strftime(TIME_FMT)

        def set_txxx(k, v):
            if isinstance(f, FLAC): f[k] = str(v)
            else: f.tags.add(TXXX(encoding=3, desc=k, text=str(v)))

        new_bpm = str(int(data['bpm']))
        if isinstance(f, FLAC):
            f['BPM'], f['KEY'], f['MOOD'] = new_bpm, data['key'], data['MOOD']
        else:
            f.tags.add(TBPM(encoding=3, text=new_bpm))
            f.tags.add(TKEY(encoding=3, text=data['key']))
            f.tags.add(TMOO(encoding=3, text=",".join(data['MOOD'])))

        set_txxx('XX_DANCEABILITY', data['XX_DANCEABILITY'])
        set_txxx('XX_INTENSITY', data['XX_INTENSITY'])
        set_txxx('XX_EMBEDDING_JSON', data['XX_EMBEDDING_JSON'])
        set_txxx('XX_ANCHOR_MATCH', data['XX_ANCHOR_MATCH'])
        set_txxx('XX_ANALYZE_DONE', ts)

        # NEU: Audit Trails
        set_txxx('XX_ALGO_VERSION', ALGO_VERSION)
        if was_healed:
            set_txxx('XX_MODIFIED_BY', 'Self-Healer-FFmpeg')
            set_txxx('XX_HEALED_DATE', ts)

        f.save(); return True
    except: return False

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--file", required=True); args = parser.parse_args()
    fname = os.path.basename(args.file)

    if not os.path.exists(args.file): sys.exit(0)

    # 1. Metadaten Check
    existing_emb = read_metadata_for_embedding(args.file)
    cache_status = "♻️ (Cache)" if existing_emb else "🆕 (Neu)"
    print(f" 🎵 [START] {fname} {cache_status}", flush=True)

    audio_ess = None
    was_healed = False # Flag für Tags später

    # 2. SAFE LOADING LOOP
    try:
        loader = es.MonoLoader(filename=args.file, sampleRate=44100)
        audio_ess = loader()
    except RuntimeError as e:
        print(f" ⚠️  [CORRUPT] Crash erkannt: {e}. Starte Heilung...", flush=True)

        if robust_heal_and_verify(args.file):
            try:
                print(f" 🔄 [RETRY] Lade geheilte Datei...", flush=True)
                loader = es.MonoLoader(filename=args.file, sampleRate=44100)
                audio_ess = loader()
                was_healed = True # Markieren für Audit-Tag
            except Exception as e2:
                move_to_aussortiert(args.file, reason=f"After Heal: {e2}")
                sys.exit(0)
        else:
            move_to_aussortiert(args.file, reason=f"Initial Crash: {e}")
            sys.exit(0)

    if audio_ess is None or len(audio_ess) < 44100:
        move_to_aussortiert(args.file, reason="Audio empty/too short")
        sys.exit(0)

    # 3. Normale Analyse
    try:
        bpm_ess = es.RhythmExtractor2013(method="multifeature")(audio_ess)[0]
        dance = es.Danceability()(audio_ess)[0]
        intensity = min(1.0, (np.sqrt(np.mean(audio_ess**2)) * 3.5))

        bpm_lib = 0
        try:
            with sf.SoundFile(args.file) as sf_f:
                audio_np = sf_f.read(dtype='float32')
                if len(audio_np.shape) > 1: audio_np = np.mean(audio_np, axis=1)
                tempo_data, _ = librosa.beat.beat_track(y=audio_np, sr=sf_f.samplerate)
                bpm_lib = float(tempo_data[0]) if isinstance(tempo_data, (np.ndarray, list)) else float(tempo_data)
        except Exception: pass

        if existing_emb:
            current_emb = existing_emb
        else:
            ensure_gpu_libraries()
            import openl3
            emb_raw, _ = openl3.get_audio_embedding(audio_ess, 44100, batch_size=INITIAL_BATCH_SIZE, content_type="music", verbose=False)
            current_emb = np.mean(emb_raw, axis=0).tolist()

        anchors = load_all_anchors()
        best_a = None; max_s = -1.0
        if current_emb and anchors:
            target_vec = np.array(current_emb)
            for a in anchors:
                s = 1.0 - cosine(target_vec, np.array(a["embedding"]))
                if s > max_s: max_s = s; best_a = a

        print(f"    ├─ 🎹 Essentia: {bpm_ess:.2f} BPM", flush=True)
        print(f"    ├─ 🎻 Librosa:  {bpm_lib:.2f} BPM", flush=True)

        final_bpm = int(round(bpm_ess))
        method = "Essentia (Fallback)"
        anchor_info = "Keiner"
        confidence = 0

        if best_a and max_s > 0.70:
            final_bpm, method = determine_bpm_logic(bpm_ess, bpm_lib, best_a["bpm"])
            anchor_info = f"{best_a['category']} ({max_s:.2f}) - {best_a['name']}"
            confidence = int(max_s * 100)
            print(f"    ├─ ⚓ Referenz: {best_a['name']} ({confidence}% Match)", flush=True)
            print(f"    └─ 🎯 Entscheidung: {method} -> {final_bpm} BPM", flush=True)
        else:
            print(f"    └─ ⚠️ Warnung: Kein Anker gefunden. Nutze Essentia Standard.", flush=True)

        # NEU: Plausibilitäts-Check für BPM
        if final_bpm < BPM_LIMITS[0] or final_bpm > BPM_LIMITS[1]:
            move_to_aussortiert(args.file, reason=f"BPM implausible: {final_bpm}")
            sys.exit(0)

        try: key, scale = es.KeyExtractor(profileType="edma")(audio_ess)[:2]
        except: key, scale = es.KeyExtractor(profileType="bgate")(audio_ess)[:2]

        moods = determine_moods(final_bpm, f"{key} {scale}", dance, intensity)

        # HIER ÜBERGEBEN WIR 'was_healed'
        write_tags(args.file, {
            'bpm': final_bpm, 'key': f"{key} {scale}",
            'XX_DANCEABILITY': round(dance, 4), 'XX_INTENSITY': round(intensity, 4),
            'XX_EMBEDDING_JSON': json.dumps(current_emb),
            'XX_ANCHOR_MATCH': anchor_info,
            'MOOD': moods
        }, was_healed=was_healed)

        log_to_csv({
            "Filename": fname, "Action": "UPDATE",
            "BPM_Final": final_bpm, "Method": method,
            "Anchor_Ref": anchor_info, "Score": round(max_s, 3), "Confidence": confidence,
            "Essentia_Raw": round(bpm_ess, 1), "Librosa_Raw": round(bpm_lib, 1)
        })

        print(f" ✅ [DONE] {fname}", flush=True)
        global tf;
        if tf: tf.keras.backend.clear_session(); gc.collect()

    except Exception as e:
        sys.stderr.write(f" ❌ [ERROR] {e}\n"); sys.exit(1)

if __name__ == "__main__":
    main()
