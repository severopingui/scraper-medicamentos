#!/bin/bash

# Script para ejecutar scraping mensual
# Para usar con cron: 0 2 1 * * /path/to/run_monthly_scraper.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Crear backup de la base actual
if [ -f "db/medicamentos.db" ]; then
    cp "db/medicamentos.db" "db/medicamentos_backup_$(date +%Y%m%d).db"
    echo "Backup creado: medicamentos_backup_$(date +%Y%m%d).db"
fi

# Ejecutar scraper
echo "Iniciando scraping mensual: $(date)"

# Con Docker
docker-compose up scraper

echo "Scraping completado: $(date)"

# Limpiar backups antiguos (mantener solo 3 meses)
find db/ -name "medicamentos_backup_*.db" -mtime +90 -delete
