#!/bin/bash
#
# Installation SÉCURISÉE Sudoers pour Odoo SaaS - PRODUCTION
<<<<<<< HEAD
# Utilisateurs configurés: odoo, baba_odoo
=======
>>>>>>> bf69dd4e6a9 (🚀 SCRIPTS: Installation automatique sudoers (PROD + DEV))
# Usage: sudo ./install_sudoers_production.sh
#

set -e  # Arrêter en cas d'erreur

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔐 Installation Sudoers SÉCURISÉE - PRODUCTION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Vérifier qu'on est root
if [ "$EUID" -ne 0 ]; then
    echo "❌ ERREUR: Ce script doit être exécuté avec sudo"
    echo "   Usage: sudo ./install_sudoers_production.sh"
    exit 1
fi

<<<<<<< HEAD
echo "📋 Configuration pour PRODUCTION"
echo "   Utilisateurs autorisés:"
echo "   • odoo (utilisateur système Odoo)"
echo "   • baba_odoo (utilisateur admin)"
echo ""

read -p "Confirmer l'installation? (o/N): " CONFIRM
=======
echo "1️⃣ Détection de l'utilisateur Odoo..."
echo ""

# Détecter l'utilisateur Odoo
ODOO_USER=""

# Méthode 1: Processus odoo-bin
PROCESS_USER=$(ps aux | grep -E "odoo-bin|openerp-server" | grep -v grep | head -1 | awk '{print $1}' 2>/dev/null || true)
if [ -n "$PROCESS_USER" ]; then
    ODOO_USER="$PROCESS_USER"
    echo "   ✅ Trouvé via processus: $ODOO_USER"
fi

# Méthode 2: Service systemd
if [ -z "$ODOO_USER" ]; then
    for SERVICE in odoo odoo-server odoo.service; do
        if systemctl status "$SERVICE" &>/dev/null; then
            SERVICE_USER=$(systemctl show -p User "$SERVICE" 2>/dev/null | cut -d= -f2)
            if [ -n "$SERVICE_USER" ] && [ "$SERVICE_USER" != "" ]; then
                ODOO_USER="$SERVICE_USER"
                echo "   ✅ Trouvé via service $SERVICE: $ODOO_USER"
                break
            fi
        fi
    done
fi

# Méthode 3: Vérifier si utilisateur 'odoo' existe
if [ -z "$ODOO_USER" ]; then
    if id "odoo" &>/dev/null; then
        ODOO_USER="odoo"
        echo "   ✅ Utilisateur 'odoo' existe dans le système"
    fi
fi

# Si toujours pas trouvé, demander à l'utilisateur
if [ -z "$ODOO_USER" ]; then
    echo "   ⚠️  Impossible de détecter automatiquement l'utilisateur Odoo"
    echo ""
    echo "   Utilisateurs courants: odoo, www-data, openerp"
    echo ""
    read -p "   Entrez le nom de l'utilisateur Odoo: " ODOO_USER

    if [ -z "$ODOO_USER" ]; then
        echo "❌ ERREUR: Aucun utilisateur spécifié"
        exit 1
    fi

    # Vérifier que l'utilisateur existe
    if ! id "$ODOO_USER" &>/dev/null; then
        echo "   ⚠️  ATTENTION: L'utilisateur '$ODOO_USER' n'existe pas encore"
        read -p "   Continuer quand même? (o/N): " CONFIRM
        if [ "$CONFIRM" != "o" ] && [ "$CONFIRM" != "O" ]; then
            echo "❌ Installation annulée"
            exit 1
        fi
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "👤 Utilisateur Odoo détecté: $ODOO_USER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "Confirmer et continuer? (o/N): " CONFIRM
>>>>>>> bf69dd4e6a9 (🚀 SCRIPTS: Installation automatique sudoers (PROD + DEV))

if [ "$CONFIRM" != "o" ] && [ "$CONFIRM" != "O" ]; then
    echo "❌ Installation annulée"
    exit 1
fi

echo ""
<<<<<<< HEAD
echo "1️⃣ Vérification des utilisateurs..."
echo ""

# Vérifier si les utilisateurs existent
USER_ODOO_EXISTS=false
USER_BABA_ODOO_EXISTS=false

if id "odoo" &>/dev/null; then
    echo "   ✅ Utilisateur 'odoo' trouvé"
    USER_ODOO_EXISTS=true
else
    echo "   ⚠️  Utilisateur 'odoo' n'existe pas encore (sera créé au démarrage Odoo)"
fi

if id "baba_odoo" &>/dev/null; then
    echo "   ✅ Utilisateur 'baba_odoo' trouvé"
    USER_BABA_ODOO_EXISTS=true
else
    echo "   ⚠️  Utilisateur 'baba_odoo' n'existe pas"
    echo "   Créer maintenant? (o/N):"
    read -p "   " CREATE_USER
    if [ "$CREATE_USER" = "o" ] || [ "$CREATE_USER" = "O" ]; then
        echo "   Création de l'utilisateur baba_odoo..."
        useradd -m -s /bin/bash baba_odoo 2>/dev/null || true
        echo "   ✅ Utilisateur 'baba_odoo' créé"
        USER_BABA_ODOO_EXISTS=true
    fi
fi

echo ""
=======
>>>>>>> bf69dd4e6a9 (🚀 SCRIPTS: Installation automatique sudoers (PROD + DEV))
echo "2️⃣ Création du fichier sudoers sécurisé..."
echo ""

# Créer le fichier sudoers
<<<<<<< HEAD
cat > /etc/sudoers.d/odoo-saas << 'EOF'
# Odoo SaaS - Configuration SÉCURISÉE PRODUCTION
# Généré automatiquement le $(date)
# Utilisateurs autorisés: odoo, baba_odoo

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
EOF

# Ajouter la date de génération
sed -i "s/\$(date)/$(date)/" /etc/sudoers.d/odoo-saas

=======
cat > /etc/sudoers.d/odoo-saas << EOF
# Odoo SaaS - Configuration SÉCURISÉE PRODUCTION
# Généré automatiquement le $(date)
# Utilisateur Odoo: $ODOO_USER

# Scripts de configuration domaines
$ODOO_USER ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh
$ODOO_USER ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/test_client_domain_local.sh
$ODOO_USER ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh

# Commandes Nginx
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/nginx -t

# Certbot SSL
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/certbot --nginx *
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/certbot renew

# Nettoyage Nginx (limité aux dossiers spécifiques)
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-enabled/*
$ODOO_USER ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-available/*
EOF

>>>>>>> bf69dd4e6a9 (🚀 SCRIPTS: Installation automatique sudoers (PROD + DEV))
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

<<<<<<< HEAD
# Test sudo pour chaque utilisateur qui existe
if [ "$USER_ODOO_EXISTS" = true ]; then
    if sudo -u odoo sudo -n whoami &>/dev/null; then
        echo "   ✅ Test sudo réussi pour utilisateur 'odoo'"
    else
        echo "   ⚠️  Test sudo échoué pour 'odoo' (normal si Odoo pas encore démarré)"
    fi
fi

if [ "$USER_BABA_ODOO_EXISTS" = true ]; then
    if sudo -u baba_odoo sudo -n whoami &>/dev/null; then
        echo "   ✅ Test sudo réussi pour utilisateur 'baba_odoo'"
    else
        echo "   ⚠️  Test sudo échoué pour 'baba_odoo'"
    fi
=======
# Test sudo
if sudo -u "$ODOO_USER" sudo -n whoami &>/dev/null; then
    echo "   ✅ Test sudo réussi"
else
    echo "   ⚠️  Test sudo échoué (normal si Odoo pas encore démarré)"
>>>>>>> bf69dd4e6a9 (🚀 SCRIPTS: Installation automatique sudoers (PROD + DEV))
fi

echo ""
echo "6️⃣ Création du dossier de logs..."
echo ""

# Créer le dossier de logs
mkdir -p /var/log/onedesk
<<<<<<< HEAD

# Donner les permissions à odoo si existe, sinon à baba_odoo
if [ "$USER_ODOO_EXISTS" = true ]; then
    chown odoo:odoo /var/log/onedesk 2>/dev/null || chown odoo /var/log/onedesk
elif [ "$USER_BABA_ODOO_EXISTS" = true ]; then
    chown baba_odoo:baba_odoo /var/log/onedesk 2>/dev/null || chown baba_odoo /var/log/onedesk
fi

=======
chown "$ODOO_USER:$ODOO_USER" /var/log/onedesk 2>/dev/null || chown "$ODOO_USER" /var/log/onedesk
>>>>>>> bf69dd4e6a9 (🚀 SCRIPTS: Installation automatique sudoers (PROD + DEV))
chmod 755 /var/log/onedesk

echo "   ✅ Dossier créé: /var/log/onedesk"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
<<<<<<< HEAD
echo "✅ Installation RÉUSSIE - PRODUCTION!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Résumé de la configuration:"
echo "   • Environnement: PRODUCTION"
echo "   • Utilisateurs autorisés:"
if [ "$USER_ODOO_EXISTS" = true ]; then
    echo "     ✅ odoo"
fi
if [ "$USER_BABA_ODOO_EXISTS" = true ]; then
    echo "     ✅ baba_odoo"
fi
=======
echo "✅ Installation RÉUSSIE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Résumé de la configuration:"
echo "   • Utilisateur: $ODOO_USER"
>>>>>>> bf69dd4e6a9 (🚀 SCRIPTS: Installation automatique sudoers (PROD + DEV))
echo "   • Fichier: /etc/sudoers.d/odoo-saas"
echo "   • Permissions: 0440 root:root"
echo "   • Logs: /var/log/onedesk"
echo ""
echo "🔍 Vérification manuelle:"
<<<<<<< HEAD
if [ "$USER_ODOO_EXISTS" = true ]; then
    echo "   sudo -u odoo sudo -n whoami"
fi
if [ "$USER_BABA_ODOO_EXISTS" = true ]; then
    echo "   sudo -u baba_odoo sudo -n whoami"
fi
=======
echo "   sudo -u $ODOO_USER sudo -n whoami"
echo ""
echo "📚 Documentation:"
echo "   /home/user/odoo/addons/onedesk_core/docs/DEPLOIEMENT_PRODUCTION_SECURISE.md"
>>>>>>> bf69dd4e6a9 (🚀 SCRIPTS: Installation automatique sudoers (PROD + DEV))
echo ""
echo "⚠️  IMPORTANT:"
echo "   • Redémarrer Odoo: sudo systemctl restart odoo"
echo "   • Tester depuis l'interface Odoo: Bouton 'DEBUG: Tester Sudo'"
echo ""
<<<<<<< HEAD
echo "📚 Documentation:"
echo "   /home/user/odoo/addons/onedesk_core/docs/DEPLOIEMENT_PRODUCTION_SECURISE.md"
echo ""
=======
>>>>>>> bf69dd4e6a9 (🚀 SCRIPTS: Installation automatique sudoers (PROD + DEV))
