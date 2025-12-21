#!/bin/bash
# Script SIMULATION pour tester l'intégration Odoo
# N'installe PAS vraiment Nginx/SSL, juste simule le succès
# Usage: ./simulate_domain_setup.sh <domain> <database_name>

DOMAIN=$1
DATABASE=$2
LOG_FILE="/var/log/onedesk/domain_setup.log"

echo "[$(date)] 🧪 MODE SIMULATION - Configuration domaine $DOMAIN → $DATABASE" | tee -a "$LOG_FILE"

if [ -z "$DOMAIN" ] || [ -z "$DATABASE" ]; then
    echo "Usage: $0 <domain> <database_name>" >&2
    exit 1
fi

# Créer le répertoire de logs
mkdir -p /var/log/onedesk

# Simuler la configuration
echo "[$(date)] ✅ Validation domaine: $DOMAIN" | tee -a "$LOG_FILE"
sleep 1

echo "[$(date)] ✅ Validation base de données: $DATABASE" | tee -a "$LOG_FILE"
sleep 1

echo "[$(date)] ✅ [SIMULÉ] Configuration Nginx créée" | tee -a "$LOG_FILE"
echo "[$(date)]    → /etc/nginx/sites-available/$DOMAIN (simulé)" | tee -a "$LOG_FILE"
sleep 1

echo "[$(date)] ✅ [SIMULÉ] Activation site Nginx" | tee -a "$LOG_FILE"
echo "[$(date)]    → /etc/nginx/sites-enabled/$DOMAIN (simulé)" | tee -a "$LOG_FILE"
sleep 1

echo "[$(date)] ✅ [SIMULÉ] Certificat SSL obtenu" | tee -a "$LOG_FILE"
echo "[$(date)]    → Let's Encrypt pour $DOMAIN (simulé)" | tee -a "$LOG_FILE"
sleep 1

echo "[$(date)] ✅ [SIMULÉ] Nginx rechargé" | tee -a "$LOG_FILE"
sleep 1

echo "" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"
echo "✅ Configuration SIMULÉE avec succès!" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "⚠️  MODE SIMULATION:" | tee -a "$LOG_FILE"
echo "   - Aucun fichier Nginx créé" | tee -a "$LOG_FILE"
echo "   - Aucun certificat SSL" | tee -a "$LOG_FILE"
echo "   - Teste uniquement l'intégration Odoo" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Pour production réelle:" | tee -a "$LOG_FILE"
echo "   1. Installer Nginx: apt install nginx" | tee -a "$LOG_FILE"
echo "   2. Installer Certbot: apt install certbot" | tee -a "$LOG_FILE"
echo "   3. Utiliser setup_client_domain.sh" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"

exit 0
