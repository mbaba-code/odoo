# Configuration Domaines Personnalisés SaaS

Guide complet pour permettre aux clients SaaS d'avoir leur propre domaine avec SSL automatique.

## 📋 Prérequis

- Serveur VPS avec Nginx installé
- Certbot (Let's Encrypt) installé
- Accès root/sudo
- Ports 80 et 443 ouverts

## 🔧 Installation Initiale

### 1. Installer Certbot (si pas déjà fait)

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install certbot python3-certbot-nginx -y

# Vérifier l'installation
certbot --version
```

### 2. Configuration Sudo pour Odoo

Le script doit être exécuté avec sudo. Créer un fichier sudoers spécifique:

```bash
sudo visudo -f /etc/sudoers.d/odoo-saas
```

Ajouter ces lignes (remplacez `odoo` par votre utilisateur Odoo):

```
# Permettre à odoo d'exécuter le script de configuration domaine
odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh
odoo ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-enabled/*
odoo ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-available/*
odoo ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
odoo ALL=(ALL) NOPASSWD: /usr/bin/certbot
```

Sauvegarder et quitter (Ctrl+X, puis Y, puis Enter).

### 3. Créer le répertoire pour certbot

```bash
sudo mkdir -p /var/www/certbot
sudo chown -R www-data:www-data /var/www/certbot
```

### 4. Créer le répertoire de logs

```bash
sudo mkdir -p /var/log/onedesk
sudo chown odoo:odoo /var/log/onedesk
```

### 5. Configurer Odoo pour multi-database

Éditer votre fichier `odoo.conf`:

```ini
[options]
# Permettre l'accès à toutes les bases
list_db = True

# Filtre pour sécurité (ajustez selon vos besoins)
dbfilter = ^(base_master|onedesk_client_.*)$

# Workers pour gérer plusieurs clients
workers = 4

# Paramètre important pour Nginx
proxy_mode = True
```

Redémarrer Odoo:
```bash
sudo systemctl restart odoo
# OU
# Ctrl+C dans tmux, puis relancer
```

## 🚀 Utilisation

### Côté Administrateur

1. **Ouvrir un client SaaS** dans Odoo
2. **Provisionner la base** si pas déjà fait
3. **Section "Domaine Personnalisé":**
   - Saisir le domaine (ex: `monentreprise.com`)
   - Cliquer sur "🔧 Configurer Domaine + SSL"

### Côté Client

Le client doit configurer son DNS:

1. **Créer un enregistrement A** dans son DNS:
   ```
   Type: A
   Nom: @  (ou monentreprise.com)
   Valeur: [IP_DE_VOTRE_SERVEUR]
   TTL: 3600
   ```

2. **Optionnel - Redirection www:**
   ```
   Type: CNAME
   Nom: www
   Valeur: monentreprise.com
   TTL: 3600
   ```

3. **Attendre la propagation DNS** (5-30 minutes)

4. **Tester le DNS:**
   ```bash
   nslookup monentreprise.com
   # Doit retourner l'IP de votre serveur
   ```

## 🔄 Processus Automatique

Quand vous cliquez sur "Configurer Domaine + SSL", le système:

1. ✅ Crée la configuration Nginx pour le domaine
2. ✅ Configure le routage vers la bonne base de données Odoo
3. ✅ Obtient un certificat SSL gratuit (Let's Encrypt)
4. ✅ Configure HTTPS avec redirection automatique
5. ✅ Configure le renouvellement automatique du SSL
6. ✅ Met à jour l'URL du client dans Odoo

**Durée:** 1-3 minutes (selon propagation DNS)

## 📁 Structure Nginx Générée

Pour chaque domaine client, le système crée:

```
/etc/nginx/sites-available/monentreprise.com
/etc/nginx/sites-enabled/monentreprise.com → symlink
/etc/letsencrypt/live/monentreprise.com/  → certificats SSL
/var/log/nginx/monentreprise.com_access.log
/var/log/nginx/monentreprise.com_error.log
```

## 🛡️ Sécurité

Le script implémente:

- ✅ Validation du format de domaine
- ✅ Vérification unicité du domaine
- ✅ SSL moderne (TLS 1.2+)
- ✅ Headers de sécurité
- ✅ Isolation par base de données (proxy_set_header X-Odoo-dbfilter)
- ✅ Logs séparés par domaine
- ✅ Auto-renewal SSL

## 🔍 Vérification et Debug

### Vérifier les logs

```bash
# Logs du script
sudo tail -f /var/log/onedesk/domain_setup.log

# Logs Nginx
sudo tail -f /var/log/nginx/error.log

# Logs Odoo
sudo journalctl -u odoo -f
```

### Tester la configuration

```bash
# Test DNS
nslookup monentreprise.com

# Test Nginx config
sudo nginx -t

# Test SSL
curl -I https://monentreprise.com

# Test accès Odoo
curl -L https://monentreprise.com
```

### Renouvellement SSL manuel

```bash
sudo certbot renew --dry-run  # Test
sudo certbot renew            # Réel
```

## ⚠️ Dépannage

### Erreur: "DNS ne pointe pas vers ce serveur"

```bash
# Vérifier IP du domaine
nslookup monentreprise.com

# Vérifier IP de votre serveur
curl ifconfig.me

# Doivent correspondre!
```

### Erreur: "Certificat SSL échoué"

```bash
# Vérifier que les ports sont ouverts
sudo netstat -tlnp | grep -E ':80|:443'

# Vérifier firewall
sudo ufw status
# Si actif:
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### Erreur: "Configuration Nginx invalide"

```bash
# Test configuration
sudo nginx -t

# Voir logs détaillés
sudo tail -50 /var/log/nginx/error.log
```

### Supprimer manuellement un domaine

```bash
DOMAIN="monentreprise.com"
sudo rm /etc/nginx/sites-enabled/$DOMAIN
sudo rm /etc/nginx/sites-available/$DOMAIN
sudo systemctl reload nginx
```

## 📊 Monitoring

### Vérifier l'état des certificats

```bash
# Liste tous les certificats
sudo certbot certificates

# Voir expiration d'un certificat
sudo openssl x509 -noout -dates -in /etc/letsencrypt/live/monentreprise.com/fullchain.pem
```

### Statistiques d'accès

```bash
# Top 10 des IPs par domaine
sudo awk '{print $1}' /var/log/nginx/monentreprise.com_access.log | sort | uniq -c | sort -rn | head -10

# Nombre de requêtes aujourd'hui
sudo grep "$(date +%d/%b/%Y)" /var/log/nginx/monentreprise.com_access.log | wc -l
```

## 🔄 Automatisation Avancée

### Script de nettoyage des domaines expirés

```bash
#!/bin/bash
# Nettoie les domaines qui ne sont plus utilisés

for domain_file in /etc/nginx/sites-available/*; do
    domain=$(basename "$domain_file")

    # Vérifier si le domaine existe encore dans Odoo
    # (à implémenter selon votre logique)

    # Si pas utilisé depuis 90 jours:
    if [ -f "/etc/nginx/sites-enabled/$domain" ]; then
        last_access=$(stat -c %Y "/var/log/nginx/${domain}_access.log" 2>/dev/null || echo 0)
        now=$(date +%s)
        diff=$((now - last_access))

        if [ $diff -gt 7776000 ]; then  # 90 jours
            echo "Domaine inactif: $domain"
            # sudo rm /etc/nginx/sites-enabled/$domain
        fi
    fi
done
```

## 📝 Notes Importantes

1. **Limite Let's Encrypt:** 50 certificats/domaine par semaine. Utilisez staging en dev!
2. **Renouvellement:** Automatique tous les 60 jours (certs valables 90 jours)
3. **Performance:** Chaque domaine client utilise le MÊME processus Odoo
4. **Backup:** Les configs Nginx ne sont pas backup automatiquement - ajoutez-les à votre backup!

## 🎯 Améliorations Futures

- [ ] Interface client pour gérer leur domaine eux-mêmes
- [ ] Support sous-domaines multiples par client
- [ ] Monitoring automatique des certificats expirés
- [ ] Email d'alerte avant expiration
- [ ] Wildcard SSL pour sous-domaines
- [ ] CDN integration (Cloudflare, etc.)

## 🆘 Support

En cas de problème:
1. Vérifier les logs (`/var/log/onedesk/domain_setup.log`)
2. Vérifier la configuration Nginx (`sudo nginx -t`)
3. Vérifier le DNS du domaine (`nslookup`)
4. Contacter l'administrateur système
