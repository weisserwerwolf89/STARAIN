# Basis-Image mit TensorFlow & GPU Support
FROM tensorflow/tensorflow:2.15.0-gpu

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV TZ=Europe/Berlin

RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    git \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installation der Audio-Bibliotheken
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    "numpy<2.0.0" \
    essentia \
    openl3 \
    soundfile \
    mutagen \
    scipy \
    librosa

COPY . .

CMD ["python3", "analyze_loop.py"]
