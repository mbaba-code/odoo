#!/bin/bash
# Backup d'une base client spécifique
#
# Usage: ./backup_client_database.sh <database_name>
# Exemple: ./backup_client_database.sh onedesk_client_1

set -e

# Configuration
DB_NAME=$1
BACKUP_DIR="/var/backups/onedesk/clients"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Validation
if [ -z "$DB_NAME" ]; then
    echo "Usage: $0 <database_name>"
    echo "Exemple: $0 onedesk_client_1"
    exit 1
fi

# Créer le répertoire de backup
mkdir -p "$BACKUP_DIR/$DB_NAME"

# Backup PostgreSQL (format custom, compressé)
BACKUP_FILE="$BACKUP_DIR/$DB_NAME/${DB_NAME}_${TIMESTAMP}.dump"

echo "🔄 Backup de $DB_NAME en cours..."
pg_dump -U odoo -Fc -d "$DB_NAME" -f "$BACKUP_FILE"

# Backup du filestore
FILESTORE_SRC="/opt/odoo/filestore/$DB_NAME"
FILESTORE_BACKUP="$BACKUP_DIR/$DB_NAME/${DB_NAME}_filestore_${TIMESTAMP}.tar.gz"

if [ -d "$FILESTORE_SRC" ]; then
    echo "📁 Backup du filestore en cours..."
    tar -czf "$FILESTORE_BACKUP" -C "/opt/odoo/filestore" "$DB_NAME"
fi

# Nettoyer les anciens backups (> RETENTION_DAYS jours)
echo "🧹 Nettoyage des anciens backups (> $RETENTION_DAYS jours)..."
find "$BACKUP_DIR/$DB_NAME" -type f -name "*.dump" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR/$DB_NAME" -type f -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "✅ Backup terminé: $BACKUP_FILE"
echo "📊 Taille: $(du -h $BACKUP_FILE | cut -f1)"
