#!/bin/bash

# Ruta absoluta del proyecto
PROYECTO="/home/obpro/medicamentos_scraper"
LOGS="$PROYECTO/logs"
DB_DIR="$PROYECTO/db"

# Crear carpeta de logs si no existe
mkdir -p "$LOGS"
mkdir -p "$DB_DIR"
chmod 777 "$DB_DIR"

# Timestamp para el log
TIMESTAMP=$(date "+%Y-%m-%d_%H-%M-%S")
LOG_FILE="$LOGS/scraper_$TIMESTAMP.log"

# Construir imagen (opcional, puedes comentar esta línea si no necesitas rebuild)
docker build -t medicamentos-scraper "$PROYECTO"

# Ejecutar el contenedor
docker run --rm \
  -v "$PROYECTO:/app" \
  medicamentos-scraper | tee "$LOG_FILE"
