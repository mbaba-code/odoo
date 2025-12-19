#!/bin/bash
# Script automatique pour configurer domaine client + SSL + Nginx
# Usage: ./setup_client_domain.sh <domain> <database_name>
<<<<<<< HEAD
#
# Nouvelle approche: Config HTTP d'abord, puis certbot ajoute SSL automatiquement
=======
>>>>>>> f77f6aa9199 (🌐 FEATURE: Domaines Personnalisés SaaS - Auto Nginx + SSL)

set -e  # Exit on error

DOMAIN=$1
DATABASE=$2
ODOO_PORT=8069
NGINX_SITES="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"
LOG_FILE="/var/log/onedesk/domain_setup.log"

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

<<<<<<< HEAD
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
=======
# 1. Créer configuration Nginx
echo "[$(date)] Création configuration Nginx..." | tee -a "$LOG_FILE"

cat > "$NGINX_SITES/$DOMAIN" <<EOF
# Configuration Nginx pour client SaaS: $DOMAIN
# Database: $DATABASE
# Généré automatiquement le $(date)

# HTTP → HTTPS redirect
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
>>>>>>> f77f6aa9199 (🌐 FEATURE: Domaines Personnalisés SaaS - Auto Nginx + SSL)

    # Pour Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

<<<<<<< HEAD
=======
    location / {
        return 301 https://\$host\$request_uri;
    }
}

# HTTPS - Configuration principale
server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

    # SSL certificates (seront créés par certbot)
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    # SSL configuration moderne
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

>>>>>>> f77f6aa9199 (🌐 FEATURE: Domaines Personnalisés SaaS - Auto Nginx + SSL)
    # Timeouts
    proxy_read_timeout 720s;
    proxy_connect_timeout 720s;
    proxy_send_timeout 720s;

    # Headers
<<<<<<< HEAD
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
=======
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;

    # IMPORTANT: Force la sélection de la base de données
    proxy_set_header X-Odoo-dbfilter ^$DATABASE\$;

    # Logs
    access_log /var/log/nginx/${DOMAIN}_access.log;
    error_log /var/log/nginx/${DOMAIN}_error.log;

    # Proxy vers Odoo
    location / {
        proxy_pass http://127.0.0.1:$ODOO_PORT/web?db=$DATABASE;
>>>>>>> f77f6aa9199 (🌐 FEATURE: Domaines Personnalisés SaaS - Auto Nginx + SSL)
        proxy_redirect off;
    }

    # WebSocket pour live chat
    location /websocket {
<<<<<<< HEAD
        proxy_pass http://127.0.0.1:ODOO_PORT_PLACEHOLDER/websocket?db=DATABASE_PLACEHOLDER;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
=======
        proxy_pass http://127.0.0.1:$ODOO_PORT/websocket?db=$DATABASE;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
>>>>>>> f77f6aa9199 (🌐 FEATURE: Domaines Personnalisés SaaS - Auto Nginx + SSL)
        proxy_set_header Connection "upgrade";
    }

    # Static files caching
    location ~* /web/static/ {
<<<<<<< HEAD
        proxy_pass http://127.0.0.1:ODOO_PORT_PLACEHOLDER;
=======
        proxy_pass http://127.0.0.1:$ODOO_PORT;
>>>>>>> f77f6aa9199 (🌐 FEATURE: Domaines Personnalisés SaaS - Auto Nginx + SSL)
        proxy_cache_valid 200 302 60m;
        proxy_cache_valid 404 1m;
        proxy_buffering on;
        expires 864000;
    }
}
<<<<<<< HEAD
EOF_NGINX

# Remplacer les placeholders
sed -i "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" "$NGINX_SITES/$DOMAIN"
sed -i "s/DATABASE_PLACEHOLDER/$DATABASE/g" "$NGINX_SITES/$DOMAIN"
sed -i "s/ODOO_PORT_PLACEHOLDER/$ODOO_PORT/g" "$NGINX_SITES/$DOMAIN"

echo "[$(date)] Configuration HTTP créée: $NGINX_SITES/$DOMAIN" | tee -a "$LOG_FILE"

# 2. Activer le site
=======
EOF

# 2. Activer le site (sans SSL pour l'instant)
>>>>>>> f77f6aa9199 (🌐 FEATURE: Domaines Personnalisés SaaS - Auto Nginx + SSL)
echo "[$(date)] Activation du site..." | tee -a "$LOG_FILE"
ln -sf "$NGINX_SITES/$DOMAIN" "$NGINX_ENABLED/$DOMAIN"

# 3. Créer répertoire pour certbot challenge
mkdir -p /var/www/certbot

# 4. Test configuration Nginx
echo "[$(date)] Test configuration Nginx..." | tee -a "$LOG_FILE"
if ! nginx -t; then
    echo "Erreur: Configuration Nginx invalide"
    rm -f "$NGINX_ENABLED/$DOMAIN"
    exit 1
fi

# 5. Reload Nginx pour activer HTTP (nécessaire pour Let's Encrypt)
echo "[$(date)] Reload Nginx..." | tee -a "$LOG_FILE"
systemctl reload nginx

# 6. Attendre que DNS se propage (optionnel)
echo "[$(date)] Vérification DNS..." | tee -a "$LOG_FILE"
for i in {1..30}; do
    if host "$DOMAIN" >/dev/null 2>&1; then
        echo "DNS OK pour $DOMAIN"
        break
    fi
    echo "Attente propagation DNS... ($i/30)"
    sleep 2
done

# 7. Obtenir certificat SSL avec Let's Encrypt
echo "[$(date)] Obtention certificat SSL..." | tee -a "$LOG_FILE"

# Vérifier si certificat existe déjà
if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    echo "Certificat existe déjà pour $DOMAIN, renouvellement..."
    certbot renew --cert-name "$DOMAIN" --nginx --non-interactive
else
    echo "Création nouveau certificat pour $DOMAIN..."
    certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" \
        --non-interactive \
        --agree-tos \
        --email admin@basatechno.fr \
        --redirect
fi

if [ $? -ne 0 ]; then
    echo "ERREUR: Échec obtention certificat SSL"
    echo "Vérifiez que:"
    echo "  - Le DNS pointe vers ce serveur"
    echo "  - Le port 80 est ouvert"
    echo "  - Le domaine est valide"
    exit 1
fi

# 8. Reload final Nginx avec SSL
echo "[$(date)] Reload final Nginx avec SSL..." | tee -a "$LOG_FILE"
nginx -t && systemctl reload nginx

# 9. Configuration auto-renewal SSL (cron)
if ! grep -q "certbot renew" /etc/crontab 2>/dev/null; then
    echo "0 3 * * * root certbot renew --quiet --post-hook 'systemctl reload nginx'" >> /etc/crontab
    echo "[$(date)] Cron auto-renewal SSL configuré" | tee -a "$LOG_FILE"
fi

# 10. Succès
echo "[$(date)] ✅ Configuration terminée avec succès pour $DOMAIN!" | tee -a "$LOG_FILE"
echo ""
echo "=========================================="
echo "Configuration complète:"
echo "  - Domain: $DOMAIN"
echo "  - Database: $DATABASE"
echo "  - SSL: Actif (Let's Encrypt)"
echo "  - Nginx: Configuré et actif"
echo "  - Auto-renewal: Actif"
echo "=========================================="
echo ""
echo "Le client peut maintenant accéder à: https://$DOMAIN"

exit 0
