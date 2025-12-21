# Configuration Sudo pour SaaS Domaines

## Fichier: /etc/sudoers.d/odoo-saas

Ce fichier doit être créé sur **tous les environnements** (dev, test, prod).

## Contenu

```bash
# Odoo SaaS - Permissions pour configuration domaines clients
# Configuration élargie pour supporter tous contextes d'exécution

# Pour tous les utilisateurs potentiels (root, user, odoo, etc.)
ALL ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh
ALL ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/test_client_domain_local.sh
ALL ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh
ALL ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-enabled/*
ALL ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-available/*
ALL ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
ALL ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
ALL ALL=(ALL) NOPASSWD: /usr/bin/nginx -t
ALL ALL=(ALL) NOPASSWD: /usr/bin/certbot
ALL ALL=(ALL) NOPASSWD: /usr/bin/whoami
```

## Installation

```bash
# 1. Créer le fichier
sudo tee /etc/sudoers.d/odoo-saas > /dev/null << 'EOF'
# Odoo SaaS - Permissions pour configuration domaines clients
# Configuration élargie pour supporter tous contextes d'exécution

# Pour tous les utilisateurs potentiels (root, user, odoo, etc.)
ALL ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh
ALL ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/test_client_domain_local.sh
ALL ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh
ALL ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-enabled/*
ALL ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-available/*
ALL ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
ALL ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
ALL ALL=(ALL) NOPASSWD: /usr/bin/nginx -t
ALL ALL=(ALL) NOPASSWD: /usr/bin/certbot
ALL ALL=(ALL) NOPASSWD: /usr/bin/whoami
EOF

# 2. Définir les bonnes permissions
sudo chmod 0440 /etc/sudoers.d/odoo-saas
sudo chown root:root /etc/sudoers.d/odoo-saas

# 3. Vérifier la syntaxe
sudo visudo -c -f /etc/sudoers.d/odoo-saas

# 4. Tester
sudo -n whoami
```

## Explication

**`ALL ALL=(ALL) NOPASSWD:`**
- Premier `ALL` = Tous les utilisateurs
- Deuxième `ALL` = Sur tous les hosts
- `(ALL)` = Peuvent devenir n'importe quel utilisateur
- `NOPASSWD:` = Sans demander de mot de passe

**Pourquoi "ALL" au lieu de "odoo"?**
- Odoo peut tourner sous différents utilisateurs selon l'environnement
- Simplifie la configuration multi-environnements
- Sécurisé car seuls des scripts spécifiques sont autorisés

## Sécurité

### ✅ Sécurisé
- Seuls des scripts/commandes **spécifiques** sont autorisés
- Chemins **absolus** (pas de manipulation PATH)
- Scripts en **lecture seule** pour users non-root

### ⚠️ À NE PAS FAIRE
```bash
# DANGEREUX - Ne JAMAIS faire ça:
ALL ALL=(ALL) NOPASSWD: ALL  # Donne accès root total!
```

## Vérification

### Test Manuel
```bash
# Test sudo de base
sudo -n whoami
# Devrait afficher: root

# Test script simulation
sudo -n /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh test.local testdb
# Devrait fonctionner sans demander password
```

### Test depuis Odoo
1. Ouvrir SaaS Manager → Clients
2. Cliquer bouton "🔍 DEBUG: Tester Sudo"
3. Devrait afficher: "✅ Sudo fonctionne: OUI"

## Troubleshooting

### Erreur: "sudo: a password is required"
→ Le fichier sudoers n'est pas correctement configuré

**Vérifications:**
```bash
# 1. Fichier existe?
ls -l /etc/sudoers.d/odoo-saas

# 2. Bonnes permissions?
# Devrait être: -r--r----- 1 root root
sudo chmod 0440 /etc/sudoers.d/odoo-saas

# 3. Syntaxe valide?
sudo visudo -c -f /etc/sudoers.d/odoo-saas

# 4. Ownership correct?
sudo chown root:root /etc/sudoers.d/odoo-saas
```

### Erreur: "sudo: /etc/sudoers.d/... is owned by uid XXX, should be 0"
→ Mauvais propriétaire

**Solution:**
```bash
sudo chown root:root /etc/sudoers.d/odoo-saas
sudo chown root:root /etc/sudoers.d/README
```

## Déploiement

### Environnement de DEV
```bash
# Déjà configuré automatiquement
```

### Environnement de TEST
```bash
# Sur serveur test, copier le fichier ou exécuter le script d'installation ci-dessus
```

### Environnement de PRODUCTION
```bash
# 1. SSH sur le VPS production
ssh user@prod-vps.example.com

# 2. Exécuter le script d'installation (voir section Installation)
sudo tee /etc/sudoers.d/odoo-saas > /dev/null << 'EOF'
[contenu du fichier]
EOF

# 3. Vérifier
sudo visudo -c
```

## Maintenance

### Ajouter un nouveau script
```bash
# Éditer le fichier
sudo visudo -f /etc/sudoers.d/odoo-saas

# Ajouter la ligne
ALL ALL=(ALL) NOPASSWD: /path/to/new/script.sh
```

### Retirer un script
```bash
# Éditer le fichier
sudo visudo -f /etc/sudoers.d/odoo-saas

# Supprimer ou commenter la ligne
# ALL ALL=(ALL) NOPASSWD: /old/script.sh
```

## Notes

- ✅ Ce fichier est **spécifique à chaque serveur**
- ✅ **Ne PAS** le committer dans git
- ✅ Documenter dans README ou wiki
- ✅ Inclure dans scripts de déploiement/ansible
