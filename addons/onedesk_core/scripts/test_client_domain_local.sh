#!/bin/bash
# Script de test LOCAL pour domaines (sans SSL réel)
# Usage: ./test_client_domain_local.sh <domain> <database_name>

set -e

DOMAIN=$1
DATABASE=$2
ODOO_PORT=8069
NGINX_SITES="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"

echo "🧪 MODE TEST LOCAL - Configuration sans SSL"

if [ -z "$DOMAIN" ] || [ -z "$DATABASE" ]; then
    echo "Usage: $0 <domain> <database_name>"
    exit 1
fi

# 1. Créer configuration Nginx TEST (HTTP seulement, pas de SSL)
echo "Création configuration Nginx TEST..."

cat > "$NGINX_SITES/$DOMAIN" <<EOF
# TEST LOCAL - Configuration Nginx pour: $DOMAIN
# Database: $DATABASE

server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN localhost;

    # Logs
    access_log /var/log/nginx/${DOMAIN}_test_access.log;
    error_log /var/log/nginx/${DOMAIN}_test_error.log;

    # Headers
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto http;
    proxy_set_header X-Odoo-dbfilter ^$DATABASE\$;

    # Proxy vers Odoo
    location / {
        proxy_pass http://127.0.0.1:$ODOO_PORT/web?db=$DATABASE;
        proxy_redirect off;
    }

    # WebSocket
    location /websocket {
        proxy_pass http://127.0.0.1:$ODOO_PORT/websocket?db=$DATABASE;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# 2. Activer le site
ln -sf "$NGINX_SITES/$DOMAIN" "$NGINX_ENABLED/$DOMAIN"

# 3. Test configuration
echo "Test configuration Nginx..."
if ! nginx -t; then
    echo "❌ Configuration invalide"
    exit 1
fi

# 4. Reload Nginx
systemctl reload nginx

echo ""
echo "✅ Configuration TEST créée avec succès!"
echo ""
echo "=========================================="
echo "POUR TESTER EN LOCAL:"
echo "=========================================="
echo ""
echo "1. Ajouter dans /etc/hosts:"
echo "   echo '127.0.0.1 $DOMAIN' | sudo tee -a /etc/hosts"
echo ""
echo "2. Tester dans le navigateur:"
echo "   http://$DOMAIN"
echo ""
echo "3. Vérifier les logs:"
echo "   tail -f /var/log/nginx/${DOMAIN}_test_access.log"
echo ""
echo "⚠️  PAS DE SSL en mode test local"
echo "=========================================="

exit 0
