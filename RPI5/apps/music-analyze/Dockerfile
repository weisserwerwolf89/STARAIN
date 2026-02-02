# apps/music-analyze/Dockerfile
FROM python:3.10-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive
ENV PKG_CONFIG_PATH="/usr/lib/aarch64-linux-gnu/pkgconfig:/usr/lib/pkgconfig:/usr/share/pkgconfig"
# Damit Librosa/Numba den Compiler findet (WICHTIG für Bullseye!)
ENV LLVM_CONFIG=/usr/bin/llvm-config-11

# ==========================================
# 1. SYSTEM-UPDATES & BUILD TOOLS
# ==========================================
# Wir brauchen viele Dev-Tools für Essentia und Librosa
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    ffmpeg \
    python3-dev \
    libyaml-dev \
    libfftw3-dev \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libavresample-dev \
    libsamplerate0-dev \
    libtag1-dev \
    libchromaprint-dev \
    libeigen3-dev \
    llvm-11-dev \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ==========================================
# 2. PYTHON PACKAGES
# ==========================================
RUN pip install --no-cache-dir --upgrade pip

# Numpy zuerst (wichtig für Essentia Kompilierung)
RUN pip install --no-cache-dir "numpy<2.0.0"

# Essentia bauen (Das dauert lange, ist aber notwendig für die AI)
RUN git clone https://github.com/MTG/essentia.git && \
    cd essentia && \
    ./waf configure --mode=release --with-python && \
    ./waf && \
    ./waf install && \
    cd .. && \
    rm -rf essentia

# Restliche AI-Pakete
# Wir installieren librosa, tensorflow und mutagen
RUN pip install --no-cache-dir tensorflow openl3 soundfile mutagen scipy librosa && \
    pip install --no-cache-dir "numpy<2.0.0" --force-reinstall

# ==========================================
# 3. CODE KOPIEREN
# ==========================================
# Wir kopieren alle Python-Skripte aus dem Ordner in den Container
COPY . .

# Environment Variablen setzen
ENV PYTHONUNBUFFERED=1

# Start-Befehl (Standardmäßig analyze_loop, kann via Docker-Compose überschrieben werden)
CMD ["python3", "analyze_loop.py"]
