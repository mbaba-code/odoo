#!/bin/bash
# Script de vérification pour domaines SaaS
# Vérifie que tout est configuré correctement

echo "🔍 Vérification Configuration SaaS Domaines"
echo "=========================================="
echo ""

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_ok() {
    echo -e "${GREEN}✅${NC} $1"
}

check_fail() {
    echo -e "${RED}❌${NC} $1"
}

check_warn() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

# 1. Vérifier scripts
echo "1️⃣ Scripts de configuration"
if [ -x "/home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh" ]; then
    check_ok "Script production exécutable"
else
    check_fail "Script production manquant ou pas exécutable"
fi

if [ -x "/home/user/odoo/addons/onedesk_core/scripts/test_client_domain_local.sh" ]; then
    check_ok "Script test exécutable"
else
    check_fail "Script test manquant ou pas exécutable"
fi

# 2. Vérifier sudo
echo ""
echo "2️⃣ Configuration sudo"
if [ -f "/etc/sudoers.d/odoo-saas" ]; then
    check_ok "Fichier sudoers existe"

    # Tester sudo
    if sudo -n true 2>/dev/null; then
        check_ok "Sudo fonctionne sans mot de passe"
    else
        check_fail "Sudo demande un mot de passe"
    fi
else
    check_fail "Fichier sudoers manquant"
fi

# 3. Vérifier Nginx
echo ""
echo "3️⃣ Nginx"
if command -v nginx &> /dev/null; then
    check_ok "Nginx installé"

    if nginx -t &> /dev/null; then
        check_ok "Configuration Nginx valide"
    else
        check_warn "Configuration Nginx avec warnings"
    fi

    if systemctl is-active --quiet nginx 2>/dev/null; then
        check_ok "Nginx actif"
    else
        check_warn "Nginx pas actif"
    fi
else
    check_fail "Nginx pas installé"
fi

# 4. Vérifier Certbot
echo ""
echo "4️⃣ Certbot (SSL)"
if command -v certbot &> /dev/null; then
    check_ok "Certbot installé"
    VERSION=$(certbot --version 2>&1 | grep -oP '\d+\.\d+\.\d+' | head -1)
    echo "   Version: $VERSION"
else
    check_fail "Certbot pas installé - Installer: apt install certbot python3-certbot-nginx"
fi

# 5. Vérifier répertoires
echo ""
echo "5️⃣ Répertoires nécessaires"
if [ -d "/var/www/certbot" ]; then
    check_ok "/var/www/certbot existe"
else
    check_warn "/var/www/certbot manquant - Créer: mkdir -p /var/www/certbot"
fi

if [ -d "/var/log/onedesk" ]; then
    check_ok "/var/log/onedesk existe"
else
    check_warn "/var/log/onedesk manquant - Créer: mkdir -p /var/log/onedesk"
fi

if [ -d "/etc/nginx/sites-available" ]; then
    check_ok "/etc/nginx/sites-available existe"
else
    check_fail "/etc/nginx/sites-available manquant"
fi

# 6. Vérifier ports
echo ""
echo "6️⃣ Ports réseau"
if netstat -tlnp 2>/dev/null | grep -q ":80 " || ss -tlnp 2>/dev/null | grep -q ":80 "; then
    check_ok "Port 80 ouvert"
else
    check_warn "Port 80 pas détecté"
fi

if netstat -tlnp 2>/dev/null | grep -q ":443 " || ss -tlnp 2>/dev/null | grep -q ":443 "; then
    check_ok "Port 443 ouvert"
else
    check_warn "Port 443 pas détecté"
fi

# 7. Vérifier Odoo
echo ""
echo "7️⃣ Processus Odoo"
if pgrep -f "odoo-bin" > /dev/null || pgrep -f "openerp" > /dev/null; then
    check_ok "Odoo en cours d'exécution"
    ODOO_USER=$(ps aux | grep -E "odoo-bin|openerp" | grep -v grep | awk '{print $1}' | head -1)
    echo "   Utilisateur: $ODOO_USER"
else
    check_warn "Odoo ne semble pas actif"
fi

# Résumé
echo ""
echo "=========================================="
echo "📊 Résumé"
echo ""
echo "Pour tester maintenant:"
echo "  1. Ouvrir Odoo: SaaS Manager → Clients"
echo "  2. Créer/Ouvrir un client"
echo "  3. Section 'Domaine Personnalisé'"
echo "  4. Saisir: test.local"
echo "  5. Cliquer: '🧪 Test Local'"
echo ""
echo "Si erreur, vérifier les ❌ ci-dessus"
echo "=========================================="
