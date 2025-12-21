<<<<<<< HEAD
<<<<<<< HEAD
# Configuration Sudo SÉCURISÉE pour SaaS Domaines

## ⚠️ AVERTISSEMENT SÉCURITÉ

**NE JAMAIS utiliser `ALL ALL=(ALL) NOPASSWD:`** en production !

Cette configuration est **EXTRÊMEMENT DANGEREUSE** car elle permet à n'importe quel utilisateur d'exécuter ces commandes sans mot de passe. C'est une faille de sécurité majeure.

## ✅ Configuration SÉCURISÉE (Recommandée)

### Fichier: /etc/sudoers.d/odoo-saas

```bash
# Odoo SaaS - Permissions SÉCURISÉES pour configuration domaines clients
#
# SÉCURITÉ: Permissions limitées à l'utilisateur 'odoo' uniquement
# Si votre utilisateur Odoo a un nom différent, modifiez cette ligne
#
# Pour identifier l'utilisateur Odoo en production:
#   ps aux | grep odoo-bin
#   systemctl status odoo
#

# Configuration pour l'utilisateur odoo (remplacer 'odoo' par votre utilisateur si différent)
odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh
odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/test_client_domain_local.sh
odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh
odoo ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
odoo ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
odoo ALL=(ALL) NOPASSWD: /usr/bin/nginx -t
odoo ALL=(ALL) NOPASSWD: /usr/bin/certbot --nginx *
odoo ALL=(ALL) NOPASSWD: /usr/bin/certbot renew

# Permissions limitées pour rm (seulement dans les dossiers Nginx)
odoo ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-enabled/*
odoo ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-available/*

# ALTERNATIVE: Si Odoo s'exécute sous un autre utilisateur (décommenter et adapter):
# www-data ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh
# www-data ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/test_client_domain_local.sh
# www-data ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh
# ... (répéter les autres commandes)
```

### Configuration DEV/TEST (Non-Production)

Pour les environnements de **développement et test** uniquement, vous pouvez ajouter:

```bash
# POUR DÉVELOPPEMENT SEULEMENT (à retirer en production):
# Permet à 'user' et 'root' d'exécuter pour les tests
user ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh
user ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/test_client_domain_local.sh
user ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh
user ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
user ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
user ALL=(ALL) NOPASSWD: /usr/bin/nginx -t
user ALL=(ALL) NOPASSWD: /usr/bin/certbot --nginx *
user ALL=(ALL) NOPASSWD: /usr/bin/certbot renew
user ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-enabled/*
user ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-available/*
user ALL=(ALL) NOPASSWD: /usr/bin/whoami
```

⚠️ **Retirer ces lignes 'user' en production !**

## 🔍 Identifier l'utilisateur Odoo en Production

Avant de configurer sudoers, identifiez l'utilisateur qui exécute Odoo:

```bash
# Méthode automatique (recommandée)
cd /home/user/odoo/addons/onedesk_core/scripts
./identify_odoo_user.sh

# OU manuellement:

# Vérifier le processus en cours
ps aux | grep odoo-bin | grep -v grep

# Vérifier le service systemd
systemctl status odoo
systemctl show -p User odoo

# Vérifier le fichier service
cat /etc/systemd/system/odoo.service | grep User=
```

Les utilisateurs les plus courants:
- `odoo` - Installation standard
- `www-data` - Installation via package
- `openerp` - Anciennes versions

## 📋 Installation Étape par Étape

### 1. Identifier l'utilisateur Odoo

```bash
./addons/onedesk_core/scripts/identify_odoo_user.sh
```

Notez le nom de l'utilisateur (exemple: `odoo`)

### 2. Créer le fichier sudoers

**⚠️ IMPORTANT: Remplacer `odoo` par votre utilisateur réel**

```bash
# Créer le fichier avec l'éditeur sécurisé visudo
sudo visudo -f /etc/sudoers.d/odoo-saas
```

Ou en une seule commande:

```bash
# ATTENTION: Remplacer 'odoo' par votre utilisateur avant d'exécuter!
sudo tee /etc/sudoers.d/odoo-saas > /dev/null << 'EOF'
# Odoo SaaS - Permissions pour configuration domaines clients
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
EOF
```

### 3. Définir les permissions correctes

```bash
sudo chmod 0440 /etc/sudoers.d/odoo-saas
sudo chown root:root /etc/sudoers.d/odoo-saas
```

### 4. Vérifier la syntaxe

```bash
sudo visudo -c -f /etc/sudoers.d/odoo-saas
```

Devrait afficher: `parsed OK`

### 5. Tester

```bash
# En tant qu'utilisateur odoo (ou votre utilisateur Odoo)
sudo -u odoo sudo -n whoami
# Devrait afficher: root (sans demander de password)

# Tester le script
sudo -u odoo sudo -n /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh test.local testdb
```

## 🔐 Comprendre la Syntaxe Sudoers

**Format:** `utilisateur hôte=(run_as) NOPASSWD: commande`

**Exemple:** `odoo ALL=(ALL) NOPASSWD: /path/to/script.sh`

- `odoo` = Seul l'utilisateur 'odoo' peut utiliser cette règle
- `ALL` = Sur tous les hôtes (machines)
- `(ALL)` = Peut s'exécuter en tant que n'importe quel utilisateur (typiquement root)
- `NOPASSWD:` = Sans demander de mot de passe
- `/path/to/script.sh` = Chemin **absolu** du script autorisé

### ❌ DANGEREUX - À NE JAMAIS FAIRE

```bash
# DANGER CRITIQUE - Donne accès root complet à TOUT LE MONDE
ALL ALL=(ALL) NOPASSWD: ALL

# TRÈS DANGEREUX - N'importe qui peut exécuter ces scripts
ALL ALL=(ALL) NOPASSWD: /path/to/script.sh

# DANGEREUX - Wildcard trop large
odoo ALL=(ALL) NOPASSWD: /usr/bin/*

# DANGEREUX - Commandes système critiques sans restriction
odoo ALL=(ALL) NOPASSWD: /usr/bin/rm
odoo ALL=(ALL) NOPASSWD: /bin/bash
```

### ✅ SÉCURISÉ - Configuration Correcte

```bash
# Bon - Utilisateur spécifique, commandes spécifiques, chemins absolus
odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh

# Bon - Wildcard limité à un dossier précis
odoo ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-enabled/*

# Bon - Commande avec arguments spécifiques
odoo ALL=(ALL) NOPASSWD: /usr/bin/certbot --nginx *
```

## 🔍 Vérification et Tests

### Test Manuel Depuis la Ligne de Commande

```bash
# 1. Test sudo basique (en tant qu'utilisateur odoo)
sudo -u odoo sudo -n whoami
# Résultat attendu: root

# 2. Test script simulation
sudo -u odoo sudo -n /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh test.local testdb
# Résultat attendu: Configuration simulée réussie

# 3. Vérifier les permissions de l'utilisateur
sudo -u odoo sudo -l
# Devrait lister toutes les commandes autorisées
```

### Test Depuis Odoo Interface

1. Ouvrir **SaaS Manager → Clients**
2. Sélectionner ou créer un client
3. Cliquer sur le bouton **"🔍 DEBUG: Tester Sudo"**
4. Devrait afficher: **"✅ Sudo fonctionne: OUI"**

Si le test échoue: voir section Troubleshooting

## 🔧 Troubleshooting

### Erreur: "sudo: a password is required"

**Cause:** Le fichier sudoers n'est pas correctement configuré ou l'utilisateur ne correspond pas.

**Solutions:**

```bash
# 1. Vérifier que le fichier existe
ls -l /etc/sudoers.d/odoo-saas

# 2. Vérifier les permissions (doit être 440)
sudo chmod 0440 /etc/sudoers.d/odoo-saas

# 3. Vérifier le propriétaire (doit être root:root)
sudo chown root:root /etc/sudoers.d/odoo-saas

# 4. Vérifier la syntaxe
sudo visudo -c -f /etc/sudoers.d/odoo-saas

# 5. Vérifier que l'utilisateur dans le fichier correspond à l'utilisateur Odoo
./addons/onedesk_core/scripts/identify_odoo_user.sh
cat /etc/sudoers.d/odoo-saas | grep -v "^#"

# 6. Tester avec l'utilisateur explicite
sudo -u odoo sudo -n whoami
```

### Erreur: "sudo: /etc/sudoers.d/odoo-saas is owned by uid XXX, should be 0"

**Cause:** Mauvais propriétaire du fichier
=======
# Configuration Sudo pour SaaS Domaines
=======
# Configuration Sudo SÉCURISÉE pour SaaS Domaines
>>>>>>> 85231e3ac39 (🔐 SÉCURITÉ: Configuration sudo utilisateur spécifique (FIX critical))

## ⚠️ AVERTISSEMENT SÉCURITÉ

**NE JAMAIS utiliser `ALL ALL=(ALL) NOPASSWD:`** en production !

Cette configuration est **EXTRÊMEMENT DANGEREUSE** car elle permet à n'importe quel utilisateur d'exécuter ces commandes sans mot de passe. C'est une faille de sécurité majeure.

## ✅ Configuration SÉCURISÉE (Recommandée)

### Fichier: /etc/sudoers.d/odoo-saas

```bash
# Odoo SaaS - Permissions SÉCURISÉES pour configuration domaines clients
#
# SÉCURITÉ: Permissions limitées à l'utilisateur 'odoo' uniquement
# Si votre utilisateur Odoo a un nom différent, modifiez cette ligne
#
# Pour identifier l'utilisateur Odoo en production:
#   ps aux | grep odoo-bin
#   systemctl status odoo
#

# Configuration pour l'utilisateur odoo (remplacer 'odoo' par votre utilisateur si différent)
odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh
odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/test_client_domain_local.sh
odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh
odoo ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
odoo ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
odoo ALL=(ALL) NOPASSWD: /usr/bin/nginx -t
odoo ALL=(ALL) NOPASSWD: /usr/bin/certbot --nginx *
odoo ALL=(ALL) NOPASSWD: /usr/bin/certbot renew

# Permissions limitées pour rm (seulement dans les dossiers Nginx)
odoo ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-enabled/*
odoo ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-available/*

# ALTERNATIVE: Si Odoo s'exécute sous un autre utilisateur (décommenter et adapter):
# www-data ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh
# www-data ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/test_client_domain_local.sh
# www-data ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh
# ... (répéter les autres commandes)
```

### Configuration DEV/TEST (Non-Production)

Pour les environnements de **développement et test** uniquement, vous pouvez ajouter:

```bash
# POUR DÉVELOPPEMENT SEULEMENT (à retirer en production):
# Permet à 'user' et 'root' d'exécuter pour les tests
user ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh
user ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/test_client_domain_local.sh
user ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh
user ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
user ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
user ALL=(ALL) NOPASSWD: /usr/bin/nginx -t
user ALL=(ALL) NOPASSWD: /usr/bin/certbot --nginx *
user ALL=(ALL) NOPASSWD: /usr/bin/certbot renew
user ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-enabled/*
user ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-available/*
user ALL=(ALL) NOPASSWD: /usr/bin/whoami
```

⚠️ **Retirer ces lignes 'user' en production !**

## 🔍 Identifier l'utilisateur Odoo en Production

Avant de configurer sudoers, identifiez l'utilisateur qui exécute Odoo:

```bash
# Méthode automatique (recommandée)
cd /home/user/odoo/addons/onedesk_core/scripts
./identify_odoo_user.sh

# OU manuellement:

# Vérifier le processus en cours
ps aux | grep odoo-bin | grep -v grep

# Vérifier le service systemd
systemctl status odoo
systemctl show -p User odoo

# Vérifier le fichier service
cat /etc/systemd/system/odoo.service | grep User=
```

Les utilisateurs les plus courants:
- `odoo` - Installation standard
- `www-data` - Installation via package
- `openerp` - Anciennes versions

## 📋 Installation Étape par Étape

### 1. Identifier l'utilisateur Odoo

```bash
./addons/onedesk_core/scripts/identify_odoo_user.sh
```

Notez le nom de l'utilisateur (exemple: `odoo`)

### 2. Créer le fichier sudoers

**⚠️ IMPORTANT: Remplacer `odoo` par votre utilisateur réel**

```bash
# Créer le fichier avec l'éditeur sécurisé visudo
sudo visudo -f /etc/sudoers.d/odoo-saas
```

Ou en une seule commande:

```bash
# ATTENTION: Remplacer 'odoo' par votre utilisateur avant d'exécuter!
sudo tee /etc/sudoers.d/odoo-saas > /dev/null << 'EOF'
# Odoo SaaS - Permissions pour configuration domaines clients
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
EOF
```

### 3. Définir les permissions correctes

```bash
sudo chmod 0440 /etc/sudoers.d/odoo-saas
sudo chown root:root /etc/sudoers.d/odoo-saas
```

### 4. Vérifier la syntaxe

```bash
sudo visudo -c -f /etc/sudoers.d/odoo-saas
```

Devrait afficher: `parsed OK`

### 5. Tester

```bash
# En tant qu'utilisateur odoo (ou votre utilisateur Odoo)
sudo -u odoo sudo -n whoami
# Devrait afficher: root (sans demander de password)

# Tester le script
sudo -u odoo sudo -n /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh test.local testdb
```

## 🔐 Comprendre la Syntaxe Sudoers

**Format:** `utilisateur hôte=(run_as) NOPASSWD: commande`

**Exemple:** `odoo ALL=(ALL) NOPASSWD: /path/to/script.sh`

- `odoo` = Seul l'utilisateur 'odoo' peut utiliser cette règle
- `ALL` = Sur tous les hôtes (machines)
- `(ALL)` = Peut s'exécuter en tant que n'importe quel utilisateur (typiquement root)
- `NOPASSWD:` = Sans demander de mot de passe
- `/path/to/script.sh` = Chemin **absolu** du script autorisé

### ❌ DANGEREUX - À NE JAMAIS FAIRE

```bash
# DANGER CRITIQUE - Donne accès root complet à TOUT LE MONDE
ALL ALL=(ALL) NOPASSWD: ALL

# TRÈS DANGEREUX - N'importe qui peut exécuter ces scripts
ALL ALL=(ALL) NOPASSWD: /path/to/script.sh

# DANGEREUX - Wildcard trop large
odoo ALL=(ALL) NOPASSWD: /usr/bin/*

# DANGEREUX - Commandes système critiques sans restriction
odoo ALL=(ALL) NOPASSWD: /usr/bin/rm
odoo ALL=(ALL) NOPASSWD: /bin/bash
```

### ✅ SÉCURISÉ - Configuration Correcte

```bash
# Bon - Utilisateur spécifique, commandes spécifiques, chemins absolus
odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh

# Bon - Wildcard limité à un dossier précis
odoo ALL=(ALL) NOPASSWD: /usr/bin/rm -f /etc/nginx/sites-enabled/*

# Bon - Commande avec arguments spécifiques
odoo ALL=(ALL) NOPASSWD: /usr/bin/certbot --nginx *
```

## 🔍 Vérification et Tests

### Test Manuel Depuis la Ligne de Commande

```bash
# 1. Test sudo basique (en tant qu'utilisateur odoo)
sudo -u odoo sudo -n whoami
# Résultat attendu: root

# 2. Test script simulation
sudo -u odoo sudo -n /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh test.local testdb
# Résultat attendu: Configuration simulée réussie

# 3. Vérifier les permissions de l'utilisateur
sudo -u odoo sudo -l
# Devrait lister toutes les commandes autorisées
```

### Test Depuis Odoo Interface

1. Ouvrir **SaaS Manager → Clients**
2. Sélectionner ou créer un client
3. Cliquer sur le bouton **"🔍 DEBUG: Tester Sudo"**
4. Devrait afficher: **"✅ Sudo fonctionne: OUI"**

Si le test échoue: voir section Troubleshooting

## 🔧 Troubleshooting

### Erreur: "sudo: a password is required"

**Cause:** Le fichier sudoers n'est pas correctement configuré ou l'utilisateur ne correspond pas.

**Solutions:**

```bash
# 1. Vérifier que le fichier existe
ls -l /etc/sudoers.d/odoo-saas

# 2. Vérifier les permissions (doit être 440)
sudo chmod 0440 /etc/sudoers.d/odoo-saas

# 3. Vérifier le propriétaire (doit être root:root)
sudo chown root:root /etc/sudoers.d/odoo-saas

# 4. Vérifier la syntaxe
sudo visudo -c -f /etc/sudoers.d/odoo-saas

# 5. Vérifier que l'utilisateur dans le fichier correspond à l'utilisateur Odoo
./addons/onedesk_core/scripts/identify_odoo_user.sh
cat /etc/sudoers.d/odoo-saas | grep -v "^#"

# 6. Tester avec l'utilisateur explicite
sudo -u odoo sudo -n whoami
```

<<<<<<< HEAD
### Erreur: "sudo: /etc/sudoers.d/... is owned by uid XXX, should be 0"
→ Mauvais propriétaire
>>>>>>> 376f841fdca (📝 DOC: Configuration Sudo pour scripts domaines)
=======
### Erreur: "sudo: /etc/sudoers.d/odoo-saas is owned by uid XXX, should be 0"

**Cause:** Mauvais propriétaire du fichier
>>>>>>> 85231e3ac39 (🔐 SÉCURITÉ: Configuration sudo utilisateur spécifique (FIX critical))

**Solution:**
```bash
sudo chown root:root /etc/sudoers.d/odoo-saas
sudo chown root:root /etc/sudoers.d/README
```

<<<<<<< HEAD
<<<<<<< HEAD
### Erreur: "sudo: parse error in /etc/sudoers.d/odoo-saas near line X"

**Cause:** Erreur de syntaxe dans le fichier

**Solution:**
```bash
# Corriger avec visudo (éditeur sécurisé)
sudo visudo -f /etc/sudoers.d/odoo-saas

# Vérifier la syntaxe
sudo visudo -c
```

### Odoo affiche "User: unknown | Sudo: FAILED"

**Cause:** L'utilisateur dans sudoers ne correspond pas à l'utilisateur qui exécute Odoo

**Solution:**
```bash
# 1. Identifier l'utilisateur réel
./addons/onedesk_core/scripts/identify_odoo_user.sh

# 2. Mettre à jour sudoers avec le bon utilisateur
sudo visudo -f /etc/sudoers.d/odoo-saas

# 3. Redémarrer Odoo
sudo systemctl restart odoo
```

## 📦 Déploiement Multi-Environnement

### Environnement de DÉVELOPPEMENT

```bash
# Utiliser 'user' ou 'root' pour les tests
user ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh
```

### Environnement de TEST

```bash
# Identifier l'utilisateur
./identify_odoo_user.sh

# Configurer avec l'utilisateur exact (ex: odoo)
odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/test_client_domain_local.sh
```

### Environnement de PRODUCTION

**⚠️ CRITIQUE: NE PAS utiliser 'ALL' ou 'user' en production**

```bash
# 1. SSH sur le VPS
ssh user@production-vps.example.com

# 2. Identifier l'utilisateur Odoo
./identify_odoo_user.sh

# 3. Créer le fichier avec l'utilisateur correct
sudo visudo -f /etc/sudoers.d/odoo-saas

# 4. Ajouter UNIQUEMENT les lignes pour l'utilisateur identifié
odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh
# ... (autres commandes)

# 5. Vérifier et tester
sudo visudo -c
sudo -u odoo sudo -n whoami
```

## 🔄 Maintenance

### Ajouter un nouveau script

```bash
# Éditer avec visudo (sécurisé)
sudo visudo -f /etc/sudoers.d/odoo-saas

# Ajouter la ligne (avec le bon utilisateur)
odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/nouveau_script.sh

# Vérifier
sudo visudo -c
```

### Retirer un script

```bash
sudo visudo -f /etc/sudoers.d/odoo-saas

# Supprimer ou commenter la ligne
# odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/ancien_script.sh
```

### Changer l'utilisateur Odoo

Si vous changez l'utilisateur qui exécute Odoo:

```bash
# 1. Éditer le fichier
sudo visudo -f /etc/sudoers.d/odoo-saas

# 2. Remplacer tous les 'odoo' par le nouvel utilisateur
# Utiliser :%s/^odoo /nouvel_user /g dans visudo

# 3. Vérifier
sudo visudo -c

# 4. Redémarrer Odoo
sudo systemctl restart odoo
```

## 📚 Ressources et Références

### Documentation Sudo
- `man sudoers` - Documentation complète
- `man visudo` - Éditeur sécurisé sudoers
- [Sudoers Manual](https://www.sudo.ws/docs/man/1.8.17/sudoers.man/)

### Bonnes Pratiques
- Toujours utiliser `visudo` pour éditer sudoers
- Toujours spécifier des chemins absolus
- Limiter aux utilisateurs et commandes strictement nécessaires
- Tester après chaque modification
- Documenter chaque règle

## 📝 Notes Importantes

- ✅ Ce fichier est **spécifique à chaque serveur**
- ✅ **NE PAS** committer dans git (contient config système)
- ✅ Inclure dans scripts de déploiement (Ansible, Terraform, etc.)
- ✅ Documenter dans wiki/README du projet
- ⚠️ **NE JAMAIS** utiliser `ALL` en production
- ⚠️ Adapter l'utilisateur selon votre installation
- ⚠️ Tester sur environnement de test avant production
=======
## Déploiement
=======
### Erreur: "sudo: parse error in /etc/sudoers.d/odoo-saas near line X"
>>>>>>> 85231e3ac39 (🔐 SÉCURITÉ: Configuration sudo utilisateur spécifique (FIX critical))

**Cause:** Erreur de syntaxe dans le fichier

**Solution:**
```bash
# Corriger avec visudo (éditeur sécurisé)
sudo visudo -f /etc/sudoers.d/odoo-saas

# Vérifier la syntaxe
sudo visudo -c
```

### Odoo affiche "User: unknown | Sudo: FAILED"

**Cause:** L'utilisateur dans sudoers ne correspond pas à l'utilisateur qui exécute Odoo

**Solution:**
```bash
# 1. Identifier l'utilisateur réel
./addons/onedesk_core/scripts/identify_odoo_user.sh

# 2. Mettre à jour sudoers avec le bon utilisateur
sudo visudo -f /etc/sudoers.d/odoo-saas

# 3. Redémarrer Odoo
sudo systemctl restart odoo
```

## 📦 Déploiement Multi-Environnement

### Environnement de DÉVELOPPEMENT

```bash
# Utiliser 'user' ou 'root' pour les tests
user ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh
```

### Environnement de TEST

```bash
# Identifier l'utilisateur
./identify_odoo_user.sh

# Configurer avec l'utilisateur exact (ex: odoo)
odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/test_client_domain_local.sh
```

### Environnement de PRODUCTION

**⚠️ CRITIQUE: NE PAS utiliser 'ALL' ou 'user' en production**

```bash
# 1. SSH sur le VPS
ssh user@production-vps.example.com

# 2. Identifier l'utilisateur Odoo
./identify_odoo_user.sh

# 3. Créer le fichier avec l'utilisateur correct
sudo visudo -f /etc/sudoers.d/odoo-saas

# 4. Ajouter UNIQUEMENT les lignes pour l'utilisateur identifié
odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/setup_client_domain.sh
# ... (autres commandes)

# 5. Vérifier et tester
sudo visudo -c
sudo -u odoo sudo -n whoami
```

## 🔄 Maintenance

### Ajouter un nouveau script

```bash
# Éditer avec visudo (sécurisé)
sudo visudo -f /etc/sudoers.d/odoo-saas

# Ajouter la ligne (avec le bon utilisateur)
odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/nouveau_script.sh

# Vérifier
sudo visudo -c
```

### Retirer un script

```bash
sudo visudo -f /etc/sudoers.d/odoo-saas

# Supprimer ou commenter la ligne
# odoo ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/ancien_script.sh
```

### Changer l'utilisateur Odoo

Si vous changez l'utilisateur qui exécute Odoo:

```bash
# 1. Éditer le fichier
sudo visudo -f /etc/sudoers.d/odoo-saas

# 2. Remplacer tous les 'odoo' par le nouvel utilisateur
# Utiliser :%s/^odoo /nouvel_user /g dans visudo

# 3. Vérifier
sudo visudo -c

# 4. Redémarrer Odoo
sudo systemctl restart odoo
```

## 📚 Ressources et Références

### Documentation Sudo
- `man sudoers` - Documentation complète
- `man visudo` - Éditeur sécurisé sudoers
- [Sudoers Manual](https://www.sudo.ws/docs/man/1.8.17/sudoers.man/)

### Bonnes Pratiques
- Toujours utiliser `visudo` pour éditer sudoers
- Toujours spécifier des chemins absolus
- Limiter aux utilisateurs et commandes strictement nécessaires
- Tester après chaque modification
- Documenter chaque règle

## 📝 Notes Importantes

- ✅ Ce fichier est **spécifique à chaque serveur**
<<<<<<< HEAD
- ✅ **Ne PAS** le committer dans git
- ✅ Documenter dans README ou wiki
- ✅ Inclure dans scripts de déploiement/ansible
>>>>>>> 376f841fdca (📝 DOC: Configuration Sudo pour scripts domaines)
=======
- ✅ **NE PAS** committer dans git (contient config système)
- ✅ Inclure dans scripts de déploiement (Ansible, Terraform, etc.)
- ✅ Documenter dans wiki/README du projet
- ⚠️ **NE JAMAIS** utiliser `ALL` en production
- ⚠️ Adapter l'utilisateur selon votre installation
- ⚠️ Tester sur environnement de test avant production
>>>>>>> 85231e3ac39 (🔐 SÉCURITÉ: Configuration sudo utilisateur spécifique (FIX critical))
