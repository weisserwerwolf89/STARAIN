# apps/music-dj/Dockerfile
FROM python:3.10-slim-bullseye

WORKDIR /app

# ==========================================
# 1. PYTHON PACKAGES
# ==========================================
# Der DJ braucht nur wenig: Numpy (für Vektoren) und Mutagen (für Tags)
RUN pip install --no-cache-dir \
    "numpy<2.0.0" \
    "mutagen>=1.46.0"

# ==========================================
# 2. CODE KOPIEREN
# ==========================================
COPY . .

# Environment
ENV PYTHONUNBUFFERED=1

# ==========================================
# 3. HEALTHCHECK
# ==========================================
# Prüft, ob Python läuft und Zugriff auf die DB möglich wäre
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python3 -c "import sqlite3; print('Ready')" || exit 1

# Start (Standardmäßig der Monitor)
CMD ["python3", "playlist_monitor.py"]
