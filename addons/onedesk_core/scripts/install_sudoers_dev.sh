#!/bin/bash
#
# Installation Sudoers pour Odoo SaaS - DEV/TEST
# Usage: sudo ./install_sudoers_dev.sh
#

set -e  # Arrêter en cas d'erreur

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 Installation Sudoers - DÉVELOPPEMENT/TEST"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Vérifier qu'on est root
if [ "$EUID" -ne 0 ]; then
    echo "❌ ERREUR: Ce script doit être exécuté avec sudo"
    echo "   Usage: sudo ./install_sudoers_dev.sh"
    exit 1
fi

echo "⚠️  ATTENTION: Configuration DÉVELOPPEMENT"
echo "   Cette configuration est plus permissive et N'EST PAS"
echo "   recommandée pour la production!"
echo ""
read -p "Continuer? (o/N): " CONFIRM

if [ "$CONFIRM" != "o" ] && [ "$CONFIRM" != "O" ]; then
    echo "❌ Installation annulée"
    exit 1
fi

echo ""
echo "1️⃣ Détection des utilisateurs système..."
echo ""

# Détecter l'utilisateur actuel (non-root)
CURRENT_USER=$(logname 2>/dev/null || echo "$SUDO_USER")
if [ -z "$CURRENT_USER" ]; then
    CURRENT_USER="user"
fi

echo "   Utilisateur détecté: $CURRENT_USER"

# Détecter l'utilisateur Odoo si existe
ODOO_USER=""
if id "odoo" &>/dev/null; then
    ODOO_USER="odoo"
    echo "   Utilisateur Odoo trouvé: $ODOO_USER"
fi

echo ""
echo "2️⃣ Création du fichier sudoers développement..."
echo ""

# Créer le fichier sudoers
cat > /etc/sudoers.d/odoo-saas << 'EOF'
# Odoo SaaS - Configuration DÉVELOPPEMENT/TEST
# ⚠️  NE PAS UTILISER EN PRODUCTION
EOF

echo "# Généré automatiquement le $(date)" >> /etc/sudoers.d/odoo-saas
echo "" >> /etc/sudoers.d/odoo-saas

# Ajouter permissions pour utilisateur odoo si existe
if [ -n "$ODOO_USER" ]; then
    cat >> /etc/sudoers.d/odoo-saas << EOF
# Configuration pour utilisateur Odoo (PRODUCTION)
$ODOO_USER ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh
$ODOO_USER ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/test_client_domain_local.sh
$ODOO_USER ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/nginx -t
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/certbot --nginx *
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/certbot renew
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-enabled/*
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-available/*

EOF
fi

# Ajouter permissions pour utilisateur de dev
cat >> /etc/sudoers.d/odoo-saas << EOF
# Configuration pour utilisateur DEV/TEST (à retirer en production)
$CURRENT_USER ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh
$CURRENT_USER ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/test_client_domain_local.sh
$CURRENT_USER ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/nginx -t
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/certbot --nginx *
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/certbot renew
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-enabled/*
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-available/*
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/whoami
EOF

echo "   ✅ Fichier créé: /etc/sudoers.d/odoo-saas"

echo ""
echo "3️⃣ Configuration des permissions..."
echo ""

# Permissions strictes
chmod 0440 /etc/sudoers.d/odoo-saas
chown root:root /etc/sudoers.d/odoo-saas

echo "   ✅ Permissions configurées: 0440 root:root"

echo ""
echo "4️⃣ Vérification de la syntaxe..."
echo ""

# Vérifier la syntaxe
if visudo -c -f /etc/sudoers.d/odoo-saas; then
    echo "   ✅ Syntaxe valide"
else
    echo "   ❌ ERREUR: Syntaxe invalide!"
    echo "   Suppression du fichier corrompu..."
    rm -f /etc/sudoers.d/odoo-saas
    exit 1
fi

echo ""
echo "5️⃣ Test de la configuration..."
echo ""

# Test sudo avec utilisateur courant
if sudo -n whoami &>/dev/null; then
    echo "   ✅ Test sudo réussi (utilisateur: $CURRENT_USER)"
else
    echo "   ⚠️  Test sudo échoué"
fi

echo ""
echo "6️⃣ Création du dossier de logs..."
echo ""

# Créer le dossier de logs
mkdir -p /var/log/onedesk
if [ -n "$ODOO_USER" ]; then
    chown "$ODOO_USER:$ODOO_USER" /var/log/onedesk 2>/dev/null || chown "$ODOO_USER" /var/log/onedesk
else
    chown "$CURRENT_USER:$CURRENT_USER" /var/log/onedesk 2>/dev/null || chown "$CURRENT_USER" /var/log/onedesk
fi
chmod 755 /var/log/onedesk

echo "   ✅ Dossier créé: /var/log/onedesk"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Installation RÉUSSIE (DEV/TEST)!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Résumé de la configuration:"
echo "   • Environnement: DÉVELOPPEMENT/TEST"
echo "   • Utilisateur dev: $CURRENT_USER"
if [ -n "$ODOO_USER" ]; then
    echo "   • Utilisateur Odoo: $ODOO_USER"
fi
echo "   • Fichier: /etc/sudoers.d/odoo-saas"
echo "   • Permissions: 0440 root:root"
echo "   • Logs: /var/log/onedesk"
echo ""
echo "🔍 Vérification manuelle:"
echo "   sudo -n whoami"
echo ""
echo "⚠️  RAPPEL IMPORTANT:"
echo "   Cette configuration est pour DEV/TEST uniquement!"
echo "   Pour la production, utiliser: install_sudoers_production.sh"
echo ""
echo "📚 Documentation:"
echo "   /home/user/odoo/addons/onedesk_core/docs/DEPLOIEMENT_PRODUCTION_SECURISE.md"
echo ""
