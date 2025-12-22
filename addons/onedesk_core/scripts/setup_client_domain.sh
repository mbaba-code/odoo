#!/bin/bash
# Script automatique pour configurer domaine client + SSL + Nginx
# Usage: ./setup_client_domain.sh <domain> <database_name>
#
# Nouvelle approche: Config HTTP d'abord, puis certbot ajoute SSL automatiquement

set -e  # Exit on error

DOMAIN=$1
DATABASE=$2
ODOO_PORT=8069
NGINX_SITES="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"
LOG_FILE="/var/log/onedesk/domain_setup.log"

# Créer le dossier de logs si nécessaire
mkdir -p /var/log/onedesk

# Créer le dossier de logs si nécessaire
mkdir -p /var/log/onedesk

<<<<<<< HEAD
# Créer le dossier de logs si nécessaire
mkdir -p /var/log/onedesk

=======
>>>>>>> f77f6aa9199 (🌐 FEATURE: Domaines Personnalisés SaaS - Auto Nginx + SSL)
# Vérifications
if [ -z "$DOMAIN" ] || [ -z "$DATABASE" ]; then
    echo "Usage: $0 <domain> <database_name>"
    exit 1
fi

if [ "$EUID" -ne 0 ]; then
    echo "Ce script doit être exécuté en tant que root"
    exit 1
fi

echo "[$(date)] Début configuration pour $DOMAIN → $DATABASE" | tee -a "$LOG_FILE"

# 1. Créer configuration Nginx HTTP SEULEMENT (sans SSL pour l'instant)
echo "[$(date)] Création configuration Nginx HTTP..." | tee -a "$LOG_FILE"

cat > "$NGINX_SITES/$DOMAIN" <<'EOF_NGINX'
# Configuration Nginx pour client SaaS: DOMAIN_PLACEHOLDER
# Database: DATABASE_PLACEHOLDER
# Généré automatiquement

# HTTP - Configuration initiale (SSL sera ajouté par certbot)
server {
    listen 80;
    server_name DOMAIN_PLACEHOLDER www.DOMAIN_PLACEHOLDER;

    # Pour Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

>>>>>>> f77f6aa9199 (🌐 FEATURE: Domaines Personnalisés SaaS - Auto Nginx + SSL)
    # Timeouts
    proxy_read_timeout 720s;
    proxy_connect_timeout 720s;
    proxy_send_timeout 720s;

    # Headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # IMPORTANT: Force la sélection de la base de données
    proxy_set_header X-Odoo-dbfilter ^DATABASE_PLACEHOLDER$;

    # Logs
    access_log /var/log/nginx/DOMAIN_PLACEHOLDER_access.log;
    error_log /var/log/nginx/DOMAIN_PLACEHOLDER_error.log;

    # Proxy vers Odoo
    location / {
        proxy_pass http://127.0.0.1:ODOO_PORT_PLACEHOLDER/web?db=DATABASE_PLACEHOLDER;
        proxy_redirect off;
    }

    # WebSocket pour live chat
    location /websocket {
        proxy_pass http://127.0.0.1:ODOO_PORT_PLACEHOLDER/websocket?db=DATABASE_PLACEHOLDER;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Static files caching
    location ~* /web/static/ {
        proxy_pass http://127.0.0.1:ODOO_PORT_PLACEHOLDER;
        proxy_cache_valid 200 302 60m;
        proxy_cache_valid 404 1m;
        proxy_buffering on;
        expires 864000;
    }
}
EOF_NGINX

# Remplacer les placeholders
sed -i "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" "$NGINX_SITES/$DOMAIN"
sed -i "s/DATABASE_PLACEHOLDER/$DATABASE/g" "$NGINX_SITES/$DOMAIN"
sed -i "s/ODOO_PORT_PLACEHOLDER/$ODOO_PORT/g" "$NGINX_SITES/$DOMAIN"

echo "[$(date)] Configuration HTTP créée: $NGINX_SITES/$DOMAIN" | tee -a "$LOG_FILE"

# 2. Activer le site
echo "[$(date)] Activation du site..." | tee -a "$LOG_FILE"
ln -sf "$NGINX_SITES/$DOMAIN" "$NGINX_ENABLED/$DOMAIN"

# 3. Créer répertoire pour certbot challenge
mkdir -p /var/www/certbot

# 4. Test configuration Nginx
echo "[$(date)] Test configuration Nginx..." | tee -a "$LOG_FILE"
if ! nginx -t 2>&1 | tee -a "$LOG_FILE"; then
    echo "[$(date)] ERREUR: Configuration Nginx invalide" | tee -a "$LOG_FILE"
    rm -f "$NGINX_ENABLED/$DOMAIN"
    rm -f "$NGINX_SITES/$DOMAIN"
    exit 1
fi

# 5. Reload Nginx pour activer HTTP
echo "[$(date)] Reload Nginx..." | tee -a "$LOG_FILE"
systemctl reload nginx

echo "[$(date)] Site HTTP actif sur http://$DOMAIN" | tee -a "$LOG_FILE"

# 6. Obtenir certificat SSL avec Let's Encrypt
echo "[$(date)] Obtention certificat SSL avec Let's Encrypt..." | tee -a "$LOG_FILE"
echo "[$(date)] Cette étape peut prendre 1-2 minutes..." | tee -a "$LOG_FILE"

# Certbot va automatiquement:
# - Obtenir le certificat
# - Modifier la config nginx pour ajouter SSL
# - Configurer la redirection HTTP → HTTPS
certbot_output=$(certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" \
    --non-interactive \
    --agree-tos \
    --email admin@basatechno.fr \
    --redirect \
    2>&1)

certbot_exit=$?

echo "$certbot_output" | tee -a "$LOG_FILE"

if [ $certbot_exit -ne 0 ]; then
    echo "" | tee -a "$LOG_FILE"
    echo "[$(date)] ⚠️  AVERTISSEMENT: Échec obtention certificat SSL" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo "Le site est ACCESSIBLE en HTTP: http://$DOMAIN" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo "Vérifiez que:" | tee -a "$LOG_FILE"
    echo "  - Le DNS pointe vers ce serveur (IP: $(hostname -I | awk '{print $1}'))" | tee -a "$LOG_FILE"
    echo "  - Le port 80 est ouvert et accessible depuis internet" | tee -a "$LOG_FILE"
    echo "  - Le domaine $DOMAIN est valide et résolvable" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo "Pour réessayer plus tard:" | tee -a "$LOG_FILE"
    echo "  sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"

    # Ne pas échouer complètement - le site fonctionne en HTTP
    echo "[$(date)] Configuration terminée en HTTP (SSL à configurer manuellement)" | tee -a "$LOG_FILE"
    exit 0
fi

# 7. Reload final Nginx (certbot l'a déjà fait normalement)
echo "[$(date)] Reload final Nginx..." | tee -a "$LOG_FILE"
nginx -t && systemctl reload nginx

# 8. Configuration auto-renewal SSL (cron)
if ! grep -q "certbot renew" /etc/crontab 2>/dev/null; then
    echo "0 3 * * * root certbot renew --quiet --post-hook 'systemctl reload nginx'" >> /etc/crontab
    echo "[$(date)] Cron auto-renewal SSL configuré" | tee -a "$LOG_FILE"
fi

# 9. Succès
echo "" | tee -a "$LOG_FILE"
echo "[$(date)] ✅ Configuration terminée avec succès pour $DOMAIN!" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"
echo "Configuration complète:" | tee -a "$LOG_FILE"
echo "  - Domain: $DOMAIN" | tee -a "$LOG_FILE"
echo "  - Database: $DATABASE" | tee -a "$LOG_FILE"
echo "  - SSL: Actif (Let's Encrypt)" | tee -a "$LOG_FILE"
echo "  - Nginx: Configuré et actif" | tee -a "$LOG_FILE"
echo "  - Auto-renewal: Actif" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "✅ Le client peut maintenant accéder à: https://$DOMAIN" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

exit 0
