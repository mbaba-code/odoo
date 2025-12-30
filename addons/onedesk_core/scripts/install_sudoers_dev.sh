#!/bin/bash
#
# Installation Sudoers pour Odoo SaaS - DEV/TEST
# Utilisateurs configurés: odoo, baba_odoo, babamerveilles
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

echo "⚠️  ATTENTION: Configuration DÉVELOPPEMENT/TEST"
echo "   Cette configuration est plus permissive et N'EST PAS"
echo "   recommandée pour la production!"
echo ""
echo "📋 Utilisateurs configurés:"
echo "   • odoo (utilisateur système Odoo)"
echo "   • baba_odoo (utilisateur admin)"
echo "   • babamerveilles (développeur MacBook)"
echo ""
read -p "Continuer? (o/N): " CONFIRM

if [ "$CONFIRM" != "o" ] && [ "$CONFIRM" != "O" ]; then
    echo "❌ Installation annulée"
    exit 1
fi

echo ""
echo "1️⃣ Vérification des utilisateurs..."
echo ""

# Vérifier quels utilisateurs existent
USER_ODOO_EXISTS=false
USER_BABA_ODOO_EXISTS=false
USER_BABAMERVEILLES_EXISTS=false

if id "odoo" &>/dev/null; then
    echo "   ✅ Utilisateur 'odoo' trouvé"
    USER_ODOO_EXISTS=true
else
    echo "   ⚠️  Utilisateur 'odoo' n'existe pas (configuré quand même)"
fi

if id "baba_odoo" &>/dev/null; then
    echo "   ✅ Utilisateur 'baba_odoo' trouvé"
    USER_BABA_ODOO_EXISTS=true
else
    echo "   ⚠️  Utilisateur 'baba_odoo' n'existe pas (configuré quand même)"
fi

if id "babamerveilles" &>/dev/null; then
    echo "   ✅ Utilisateur 'babamerveilles' trouvé"
    USER_BABAMERVEILLES_EXISTS=true
else
    echo "   ⚠️  Utilisateur 'babamerveilles' n'existe pas (configuré quand même)"
fi

echo ""
echo "2️⃣ Création du fichier sudoers développement..."
echo ""

# Créer le fichier sudoers
cat > /etc/sudoers.d/odoo-saas << 'EOF'
# Odoo SaaS - Configuration DÉVELOPPEMENT/TEST
# ⚠️  NE PAS UTILISER EN PRODUCTION
# Généré automatiquement le $(date)
# Utilisateurs autorisés: odoo, baba_odoo, babamerveilles

# ==========================================
# Utilisateur: odoo (service Odoo système)
# ==========================================
odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh
odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/test_client_domain_local.sh
odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh
odoo ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
odoo ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
odoo ALL=(ALL) NOPASSWD: /usr/bin/nginx -t
odoo ALL=(ALL) NOPASSWD: /usr/bin/certbot --nginx *
odoo ALL=(ALL) NOPASSWD: /usr/bin/certbot renew
odoo ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-enabled/*
odoo ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-available/*
odoo ALL=(ALL) NOPASSWD: /usr/bin/whoami

# ==========================================
# Utilisateur: baba_odoo (admin Odoo)
# ==========================================
baba_odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh
baba_odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/test_client_domain_local.sh
baba_odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh
baba_odoo ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
baba_odoo ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
baba_odoo ALL=(ALL) NOPASSWD: /usr/bin/nginx -t
baba_odoo ALL=(ALL) NOPASSWD: /usr/bin/certbot --nginx *
baba_odoo ALL=(ALL) NOPASSWD: /usr/bin/certbot renew
baba_odoo ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-enabled/*
baba_odoo ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-available/*
baba_odoo ALL=(ALL) NOPASSWD: /usr/bin/whoami

# ==========================================
# Utilisateur: babamerveilles (dev MacBook)
# ==========================================
babamerveilles ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh
babamerveilles ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/test_client_domain_local.sh
babamerveilles ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh
babamerveilles ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
babamerveilles ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
babamerveilles ALL=(ALL) NOPASSWD: /usr/bin/nginx -t
babamerveilles ALL=(ALL) NOPASSWD: /usr/bin/certbot --nginx *
babamerveilles ALL=(ALL) NOPASSWD: /usr/bin/certbot renew
babamerveilles ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-enabled/*
babamerveilles ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-available/*
babamerveilles ALL=(ALL) NOPASSWD: /usr/bin/whoami
EOF

# Ajouter la date de génération
sed -i "s/\$(date)/$(date)/" /etc/sudoers.d/odoo-saas 2>/dev/null || true

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

# Test sudo pour chaque utilisateur qui existe
if [ "$USER_ODOO_EXISTS" = true ]; then
    if sudo -u odoo sudo -n whoami &>/dev/null; then
        echo "   ✅ Test sudo réussi pour 'odoo'"
    else
        echo "   ⚠️  Test sudo échoué pour 'odoo'"
    fi
fi

if [ "$USER_BABA_ODOO_EXISTS" = true ]; then
    if sudo -u baba_odoo sudo -n whoami &>/dev/null; then
        echo "   ✅ Test sudo réussi pour 'baba_odoo'"
    else
        echo "   ⚠️  Test sudo échoué pour 'baba_odoo'"
    fi
fi

if [ "$USER_BABAMERVEILLES_EXISTS" = true ]; then
    if sudo -u babamerveilles sudo -n whoami &>/dev/null; then
        echo "   ✅ Test sudo réussi pour 'babamerveilles'"
    else
        echo "   ⚠️  Test sudo échoué pour 'babamerveilles'"
    fi
fi

echo ""
echo "6️⃣ Création du dossier de logs..."
echo ""

# Créer le dossier de logs
mkdir -p /var/log/onedesk

# Donner les permissions (priorité: odoo > baba_odoo > babamerveilles)
if [ "$USER_ODOO_EXISTS" = true ]; then
    chown odoo:odoo /var/log/onedesk 2>/dev/null || chown odoo /var/log/onedesk
elif [ "$USER_BABA_ODOO_EXISTS" = true ]; then
    chown baba_odoo:baba_odoo /var/log/onedesk 2>/dev/null || chown baba_odoo /var/log/onedesk
elif [ "$USER_BABAMERVEILLES_EXISTS" = true ]; then
    chown babamerveilles:babamerveilles /var/log/onedesk 2>/dev/null || chown babamerveilles /var/log/onedesk
fi

chmod 755 /var/log/onedesk

echo "   ✅ Dossier créé: /var/log/onedesk"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Installation RÉUSSIE - DEV/TEST!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Résumé de la configuration:"
echo "   • Environnement: DÉVELOPPEMENT/TEST"
echo "   • Utilisateurs configurés:"
echo "     • odoo"
echo "     • baba_odoo"
echo "     • babamerveilles"
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
