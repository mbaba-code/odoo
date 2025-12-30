#!/bin/bash
#
# Script de nettoyage des configurations Nginx cassées
# Usage: sudo ./cleanup_nginx_configs.sh
#

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧹 Nettoyage configurations Nginx - Odoo SaaS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Vérifier qu'on est root
if [ "$EUID" -ne 0 ]; then
    echo "❌ ERREUR: Ce script doit être exécuté avec sudo"
    exit 1
fi

# Vérifier que Nginx est installé
if ! command -v nginx &> /dev/null; then
    echo "⚠️  Nginx n'est pas installé - rien à nettoyer"
    exit 0
fi

echo "1️⃣ Sauvegarde des configurations existantes..."
BACKUP_DIR="/root/nginx_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -d /etc/nginx/sites-available ]; then
    cp -r /etc/nginx/sites-available "$BACKUP_DIR/" 2>/dev/null || true
fi
if [ -d /etc/nginx/sites-enabled ]; then
    cp -r /etc/nginx/sites-enabled "$BACKUP_DIR/" 2>/dev/null || true
fi

echo "   ✅ Sauvegarde créée: $BACKUP_DIR"
echo ""

echo "2️⃣ Liste des configurations actuelles..."
echo ""
echo "   Sites disponibles:"
ls -1 /etc/nginx/sites-available/ 2>/dev/null | sed 's/^/      - /' || echo "      (aucun)"
echo ""
echo "   Sites activés:"
ls -1 /etc/nginx/sites-enabled/ 2>/dev/null | sed 's/^/      - /' || echo "      (aucun)"
echo ""

echo "3️⃣ Recherche de configurations cassées..."
echo ""

BROKEN_CONFIGS=()

# Vérifier chaque fichier dans sites-enabled
if [ -d /etc/nginx/sites-enabled ]; then
    for config in /etc/nginx/sites-enabled/*; do
        if [ -f "$config" ] || [ -L "$config" ]; then
            filename=$(basename "$config")

            # Vérifier si c'est un lien cassé
            if [ -L "$config" ] && [ ! -e "$config" ]; then
                echo "   ⚠️  Lien cassé: $filename"
                BROKEN_CONFIGS+=("$config")
                continue
            fi

            # Vérifier si le fichier contient des certificats manquants
            if [ -f "$config" ]; then
                missing_certs=$(grep -E "ssl_certificate|ssl_certificate_key" "$config" 2>/dev/null | grep -oP '(?<= )[^;]+(?=;)' || true)
                while IFS= read -r cert_path; do
                    if [ -n "$cert_path" ] && [ ! -f "$cert_path" ]; then
                        echo "   ⚠️  Certificat manquant dans $filename: $cert_path"
                        BROKEN_CONFIGS+=("$config")
                        break
                    fi
                done <<< "$missing_certs"
            fi
        fi
    done
fi

# Vérifier la configuration globale Nginx
echo ""
echo "4️⃣ Test de la configuration Nginx globale..."
if nginx -t 2>&1 | grep -q "emerg\|error"; then
    echo "   ❌ Configuration Nginx invalide"
    nginx -t 2>&1 | grep -E "emerg|error" | head -5 | sed 's/^/      /'
    echo ""
    echo "   ⚠️  Problèmes détectés dans la configuration globale"
else
    echo "   ✅ Configuration globale OK"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Actions proposées:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ ${#BROKEN_CONFIGS[@]} -gt 0 ]; then
    echo "Configurations cassées trouvées:"
    for config in "${BROKEN_CONFIGS[@]}"; do
        echo "  - $(basename "$config")"
    done
    echo ""
    read -p "Supprimer ces configurations cassées? (o/N): " CONFIRM

    if [ "$CONFIRM" = "o" ] || [ "$CONFIRM" = "O" ]; then
        for config in "${BROKEN_CONFIGS[@]}"; do
            rm -f "$config"
            echo "   ✅ Supprimé: $(basename "$config")"
        done
    fi
else
    echo "✅ Aucune configuration cassée trouvée"
fi

echo ""
echo "5️⃣ Nettoyage complet (OPTIONNEL)..."
echo ""
echo "⚠️  ATTENTION: Ceci va supprimer TOUTES les configurations de sites"
echo "   dans /etc/nginx/sites-enabled/ et /etc/nginx/sites-available/"
echo "   (sauf default)"
echo ""
echo "   Sauvegarde disponible dans: $BACKUP_DIR"
echo ""
read -p "Effectuer un nettoyage complet? (o/N): " CONFIRM_CLEAN

if [ "$CONFIRM_CLEAN" = "o" ] || [ "$CONFIRM_CLEAN" = "O" ]; then
    echo ""
    echo "   Suppression des configurations de sites..."

    # Supprimer tous les sites activés (sauf default)
    if [ -d /etc/nginx/sites-enabled ]; then
        find /etc/nginx/sites-enabled/ -type f -not -name "default" -delete 2>/dev/null || true
        find /etc/nginx/sites-enabled/ -type l -not -name "default" -delete 2>/dev/null || true
        echo "   ✅ Sites activés nettoyés"
    fi

    # Supprimer tous les sites disponibles (sauf default)
    if [ -d /etc/nginx/sites-available ]; then
        find /etc/nginx/sites-available/ -type f -not -name "default" -delete 2>/dev/null || true
        echo "   ✅ Sites disponibles nettoyés"
    fi

    echo ""
    echo "   ✅ Nettoyage complet terminé"
fi

echo ""
echo "6️⃣ Test final de Nginx..."
if nginx -t; then
    echo ""
    echo "   ✅ Configuration Nginx valide!"
    echo ""
    read -p "   Redémarrer Nginx maintenant? (o/N): " RESTART
    if [ "$RESTART" = "o" ] || [ "$RESTART" = "O" ]; then
        systemctl restart nginx
        echo "   ✅ Nginx redémarré"
    fi
else
    echo ""
    echo "   ❌ Configuration Nginx toujours invalide"
    echo "   Vérifiez manuellement: nginx -t"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Nettoyage terminé!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📁 Sauvegarde: $BACKUP_DIR"
echo ""
echo "🔍 Pour restaurer en cas de problème:"
echo "   sudo cp -r $BACKUP_DIR/sites-available/* /etc/nginx/sites-available/"
echo "   sudo cp -r $BACKUP_DIR/sites-enabled/* /etc/nginx/sites-enabled/"
echo "   sudo nginx -t && sudo systemctl restart nginx"
echo ""
