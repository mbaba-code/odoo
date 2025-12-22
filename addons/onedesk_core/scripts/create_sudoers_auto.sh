#!/bin/bash
#
# Création automatique fichier sudoers avec chemin Odoo auto-détecté
# Usage: sudo ./create_sudoers_auto.sh
#

set -e

echo "🔍 Détection automatique de la configuration Odoo..."
echo ""

# Vérifier qu'on est root
if [ "$EUID" -ne 0 ]; then
    echo "❌ ERREUR: Ce script doit être exécuté avec sudo"
    exit 1
fi

# Détecter le chemin d'Odoo
ODOO_PATH=""
if [ -d "/home/user/odoo/addons/onedesk_core" ]; then
    ODOO_PATH="/home/user/odoo"
elif [ -d "/opt/odoo_test/addons/onedesk_core" ]; then
    ODOO_PATH="/opt/odoo_test"
elif [ -d "/opt/odoo/addons/onedesk_core" ]; then
    ODOO_PATH="/opt/odoo"
else
    echo "⚠️  Chemin Odoo non détecté automatiquement"
    read -p "Entrez le chemin complet d'Odoo (ex: /opt/odoo_test): " ODOO_PATH

    if [ ! -d "$ODOO_PATH/addons/onedesk_core" ]; then
        echo "❌ ERREUR: addons/onedesk_core introuvable dans $ODOO_PATH"
        exit 1
    fi
fi

echo "✅ Chemin Odoo détecté: $ODOO_PATH"
echo ""

# Détecter l'utilisateur qui exécute Odoo
ODOO_USER=""
PROCESS_USER=$(ps aux | grep -E "odoo-bin|python.*odoo" | grep -v grep | head -1 | awk '{print $1}' 2>/dev/null || true)
if [ -n "$PROCESS_USER" ] && [ "$PROCESS_USER" != "root" ]; then
    ODOO_USER="$PROCESS_USER"
    echo "✅ Utilisateur Odoo (processus): $ODOO_USER"
elif id "odoo" &>/dev/null; then
    ODOO_USER="odoo"
    echo "✅ Utilisateur système 'odoo' trouvé"
else
    echo "⚠️  Utilisateur Odoo non détecté"
    read -p "Entrez le nom de l'utilisateur Odoo (défaut: odoo): " INPUT_USER
    ODOO_USER="${INPUT_USER:-odoo}"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Configuration détectée:"
echo "   • Chemin Odoo: $ODOO_PATH"
echo "   • Utilisateur: $ODOO_USER"
echo "   • Scripts: $ODOO_PATH/addons/onedesk_core/scripts/"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "Confirmer et créer sudoers? (o/N): " CONFIRM

if [ "$CONFIRM" != "o" ] && [ "$CONFIRM" != "O" ]; then
    echo "❌ Annulé"
    exit 1
fi

# Créer le fichier sudoers
cat > /etc/sudoers.d/odoo-saas << EOF
# Odoo SaaS - Configuration Auto-Générée
# Date: $(date)
# Chemin Odoo: $ODOO_PATH
# Utilisateur: $ODOO_USER

# Scripts de configuration domaines
$ODOO_USER ALL=(ALL) NOPASSWD: $ODOO_PATH/addons/onedesk_core/scripts/setup_client_domain.sh
$ODOO_USER ALL=(ALL) NOPASSWD: $ODOO_PATH/addons/onedesk_core/scripts/test_client_domain_local.sh
$ODOO_USER ALL=(ALL) NOPASSWD: $ODOO_PATH/addons/onedesk_core/scripts/simulate_domain_setup.sh

# Commandes Nginx
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/nginx -t

# Certbot SSL
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/certbot --nginx *
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/certbot renew

# Nettoyage Nginx
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-enabled/*
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-available/*
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/whoami

# Configuration additionnelle pour baba_odoo
baba_odoo ALL=(ALL) NOPASSWD: $ODOO_PATH/addons/onedesk_core/scripts/setup_client_domain.sh
baba_odoo ALL=(ALL) NOPASSWD: $ODOO_PATH/addons/onedesk_core/scripts/test_client_domain_local.sh
baba_odoo ALL=(ALL) NOPASSWD: $ODOO_PATH/addons/onedesk_core/scripts/simulate_domain_setup.sh
baba_odoo ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
baba_odoo ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
baba_odoo ALL=(ALL) NOPASSWD: /usr/bin/nginx -t
baba_odoo ALL=(ALL) NOPASSWD: /usr/bin/certbot --nginx *
baba_odoo ALL=(ALL) NOPASSWD: /usr/bin/certbot renew
baba_odoo ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-enabled/*
baba_odoo ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-available/*
baba_odoo ALL=(ALL) NOPASSWD: /usr/bin/whoami
EOF

# Permissions
chmod 0440 /etc/sudoers.d/odoo-saas
chown root:root /etc/sudoers.d/odoo-saas

# Vérifier syntaxe
if visudo -c -f /etc/sudoers.d/odoo-saas; then
    echo ""
    echo "✅ Fichier sudoers créé et validé!"
    echo ""
    echo "📝 Fichier créé: /etc/sudoers.d/odoo-saas"
    echo ""
    echo "🔍 Test:"
    if id "$ODOO_USER" &>/dev/null; then
        echo "   sudo -u $ODOO_USER sudo -n whoami"
        sudo -u "$ODOO_USER" sudo -n whoami 2>/dev/null && echo "   ✅ Test réussi!" || echo "   ⚠️  Test échoué"
    else
        echo "   Utilisateur $ODOO_USER n'existe pas encore (sera créé au démarrage Odoo)"
    fi
    echo ""
    echo "⚠️  N'oubliez pas de redémarrer Odoo:"
    echo "   sudo systemctl restart odoo"
else
    echo "❌ ERREUR: Syntaxe invalide!"
    rm -f /etc/sudoers.d/odoo-saas
    exit 1
fi
