FROM python:3.11-slim

# Installation de FFmpeg et des dépendances système
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# On expose le port que Render va utiliser
EXPOSE 10000

# Gunicorn est le serveur de production (plus robuste que Flask dev)
RUN pip install gunicorn

CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
