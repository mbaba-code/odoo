#!/bin/bash
#
# Script pour identifier l'utilisateur qui exécute Odoo en production
# Usage: ./identify_odoo_user.sh
#

echo "🔍 Identification de l'utilisateur Odoo..."
echo ""

# Méthode 1: Chercher le processus odoo-bin
echo "1️⃣ Recherche du processus odoo-bin:"
ODOO_PROCESS=$(ps aux | grep -E "odoo-bin|openerp-server" | grep -v grep | head -1)
if [ -n "$ODOO_PROCESS" ]; then
    ODOO_USER=$(echo "$ODOO_PROCESS" | awk '{print $1}')
    echo "   ✅ Trouvé: $ODOO_USER"
else
    echo "   ❌ Aucun processus Odoo en cours d'exécution"
fi
echo ""

# Méthode 2: Vérifier le service systemd
echo "2️⃣ Vérification du service systemd:"
for SERVICE in odoo odoo-server odoo.service; do
    if systemctl status "$SERVICE" &>/dev/null; then
        echo "   ✅ Service trouvé: $SERVICE"
        SERVICE_USER=$(systemctl show -p User "$SERVICE" 2>/dev/null | cut -d= -f2)
        if [ -n "$SERVICE_USER" ]; then
            echo "   ✅ Utilisateur configuré: $SERVICE_USER"
        fi
    fi
done
echo ""

# Méthode 3: Vérifier le propriétaire des fichiers
echo "3️⃣ Propriétaire des fichiers Odoo:"
if [ -f "/opt/odoo/odoo-bin" ]; then
    FILE_OWNER=$(stat -c '%U' /opt/odoo/odoo-bin 2>/dev/null)
    echo "   Propriétaire de /opt/odoo/odoo-bin: $FILE_OWNER"
elif [ -f "/usr/bin/odoo" ]; then
    FILE_OWNER=$(stat -c '%U' /usr/bin/odoo 2>/dev/null)
    echo "   Propriétaire de /usr/bin/odoo: $FILE_OWNER"
fi
echo ""

# Méthode 4: Vérifier les utilisateurs système
echo "4️⃣ Utilisateurs système liés à Odoo:"
grep -E "^odoo:|^openerp:" /etc/passwd 2>/dev/null || echo "   ❌ Aucun utilisateur 'odoo' ou 'openerp' trouvé dans /etc/passwd"
echo ""

# Recommandation
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 RECOMMANDATION:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -n "$ODOO_USER" ]; then
    echo ""
    echo "Modifiez /etc/sudoers.d/odoo-saas avec:"
    echo ""
    echo "  $ODOO_USER ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh"
    echo "  $ODOO_USER ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/test_client_domain_local.sh"
    echo "  $ODOO_USER ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh"
    echo "  $ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx"
    echo "  $ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx"
    echo "  $ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/nginx -t"
    echo "  $ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/certbot --nginx *"
    echo "  $ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/certbot renew"
    echo "  $ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-enabled/*"
    echo "  $ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-available/*"
    echo ""
else
    echo ""
    echo "⚠️  Impossible de déterminer l'utilisateur Odoo automatiquement."
    echo "   L'utilisateur le plus commun est 'odoo'."
    echo ""
    echo "Si Odoo n'est pas encore installé, créez l'utilisateur:"
    echo "  sudo adduser --system --group --home /opt/odoo --shell /bin/bash odoo"
    echo ""
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
