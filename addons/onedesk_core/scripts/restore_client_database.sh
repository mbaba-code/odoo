#!/bin/bash
# Restauration d'une base client
#
# Usage: ./restore_client_database.sh <database_name> <backup_file>
# Exemple: ./restore_client_database.sh onedesk_client_1 /var/backups/onedesk/clients/onedesk_client_1/onedesk_client_1_20251218_140000.dump

set -e

DB_NAME=$1
BACKUP_FILE=$2

if [ -z "$DB_NAME" ] || [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <database_name> <backup_file>"
    exit 1
fi

# Confirmation
read -p "⚠️  Restaurer $DB_NAME depuis $BACKUP_FILE ? (yes/no) " -r
if [[ ! $REPLY =~ ^yes$ ]]; then
    echo "Annulé"
    exit 1
fi

# Déconnecter tous les utilisateurs de la base
echo "🔌 Déconnexion des utilisateurs..."
psql -U odoo -d postgres -c "
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid()
"

# Supprimer la base existante
echo "🗑️  Suppression de la base existante..."
dropdb -U odoo "$DB_NAME"

# Créer une nouvelle base vide
echo "📦 Création de la nouvelle base..."
createdb -U odoo "$DB_NAME"

# Restaurer le dump
echo "📥 Restauration des données..."
pg_restore -U odoo -d "$DB_NAME" "$BACKUP_FILE"

# Restaurer le filestore (si existe)
FILESTORE_BACKUP="${BACKUP_FILE%.dump}_filestore.tar.gz"
if [ -f "$FILESTORE_BACKUP" ]; then
    echo "📁 Restauration du filestore..."
    rm -rf "/opt/odoo/filestore/$DB_NAME"
    tar -xzf "$FILESTORE_BACKUP" -C "/opt/odoo/filestore/"
fi

echo "✅ Restauration terminée!"
