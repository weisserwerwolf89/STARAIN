import os
import shutil
import argparse
import logging
import re
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.id3 import ID3

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [ORGANIZER] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def clean_name(name):
    """Entfernt ungültige Zeichen für Dateinamen."""
    if not name: return "Unknown"
    # Ersetze / : * ? " < > | durch Unterstrich
    name = re.sub(r'[\\/*?:"<>|]', '_', str(name))
    return name.strip()

def get_tag(tags, key, default="Unknown"):
    """Holt einen Standard-Tag sicher aus den Metadaten."""
    if key in tags and tags[key]:
        return str(tags[key][0]).strip()
    return default

def has_embedding_tag(filepath, ext):
    """
    Prüft direkt in den Metadaten, ob die KI-Analyse (XX_EMBEDDING_JSON) vorhanden ist.
    Nutzt ID3 direkt für MP3, da EasyID3 keine TXXX-Frames liest.
    """
    try:
        if ext == '.flac':
            audio = FLAC(filepath)
            return "XX_EMBEDDING_JSON" in audio #
        elif ext == '.mp3':
            # ID3 direkt nutzen für TXXX-Frames
            audio = ID3(filepath)
            for frame in audio.getall("TXXX"):
                if frame.desc == "XX_EMBEDDING_JSON": #
                    return True
    except Exception:
        pass
    return False

def get_track_disc_info(tags):
    """Holt Track- und Disc-Nummer und formatiert sie (z.B. 1#01)."""
    disc = "1"
    if 'discnumber' in tags and tags['discnumber']:
        raw = str(tags['discnumber'][0])
        disc = raw.split('/')[0].strip()
        if not disc.isdigit(): disc = "1"

    track = "00"
    if 'tracknumber' in tags and tags['tracknumber']:
        raw = str(tags['tracknumber'][0])
        track_raw = raw.split('/')[0].strip()
        if track_raw.isdigit():
            track = track_raw.zfill(2)

    return disc, track

def process_file(filepath, target_root):
    """Verarbeitet eine einzelne Datei inkl. KI-Aware-Kollisionsprüfung."""
    try:
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filename)[1].lower()

        if ext not in ['.flac', '.mp3']:
            return

        # 1. Metadaten laden für Namensgebung
        try:
            if ext == '.flac':
                audio = FLAC(filepath) #
            elif ext == '.mp3':
                # EasyID3 für Standard-Tags wie Artist/Album
                audio = MP3(filepath, ID3=EasyID3)
            else:
                return
        except Exception as e:
            logging.error(f"Konnte Tags nicht lesen: {filename} ({e})")
            return

        # 2. Infos sammeln
        artist = clean_name(get_tag(audio, 'artist', 'Unknown Artist'))
        album_artist = clean_name(get_tag(audio, 'albumartist', artist))
        album = clean_name(get_tag(audio, 'album', 'Unknown Album'))
        title = clean_name(get_tag(audio, 'title', filename))
        disc_num, track_num = get_track_disc_info(audio)

        # 3. Zielstruktur bauen
        new_filename = f"{disc_num}#{track_num} - {artist} - {title}{ext}"
        target_dir = os.path.join(target_root, album_artist, album)
        target_path = os.path.join(target_dir, new_filename)

        # 4. Prüfen ob Verschiebung nötig ist
        if os.path.normpath(filepath) == os.path.normpath(target_path):
            return

        # 5. KI-AWARE KOLLISIONS-CHECK
        if os.path.exists(target_path):
            source_has_emb = has_embedding_tag(filepath, ext)
            target_has_emb = has_embedding_tag(target_path, ext)

            if target_has_emb and not source_has_emb:
                logging.info(f"Überspringe: Ziel hat bereits KI-Tags, Quelle nicht. ({filename})")
                return

            if source_has_emb and not target_has_emb:
                logging.info(f"Ersetze: Quelle hat KI-Tags, Ziel noch nicht. ({filename})")
                # Explizites Löschen vor move für maximale Kontrolle
                os.remove(target_path)

            elif source_has_emb and target_has_emb:
                logging.info(f"Kollision: Beide analysiert. Behalte bestehende Datei. ({filename})")
                return
            else:
                logging.info(f"Kollision: Keine KI-Tags. Behalte bestehende Datei. ({filename})")
                return

        # 6. Verschieben
        os.makedirs(target_dir, exist_ok=True)
        try:
            shutil.move(filepath, target_path)
            logging.info(f"Verschoben: {filename} -> {album_artist}/{album}/{new_filename}")

            # Alten Ordner aufräumen, falls leer
            old_dir = os.path.dirname(filepath)
            if old_dir != target_root and os.path.exists(old_dir) and not os.listdir(old_dir):
                os.rmdir(old_dir)

        except Exception as e:
            logging.error(f"Fehler beim Verschieben: {e}")

    except Exception as e:
        logging.error(f"General Error {filepath}: {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--music_dir", required=True, help="Wurzelverzeichnis der Musikbibliothek")
    args = parser.parse_args()

    abs_music_dir = os.path.abspath(args.music_dir)

    # 1. Liste aller Dateien sammeln, um Endlosschleifen beim Verschieben zu vermeiden
    files_to_process = []
    for root, dirs, files in os.walk(abs_music_dir):
        for file in files:
            files_to_process.append(os.path.join(root, file))

    # 2. Dateien abarbeiten
    for file_path in files_to_process:
        process_file(file_path, abs_music_dir)

if __name__ == "__main__":
    main()
