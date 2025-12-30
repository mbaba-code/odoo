# 🔐 Déploiement SÉCURISÉ en Production - SaaS Domaines

## ⚠️ CHECKLIST SÉCURITÉ CRITIQUE

Avant de déployer en production, **VÉRIFIER IMPÉRATIVEMENT** :

- [ ] ❌ **PAS de `ALL ALL` dans sudoers**
- [ ] ✅ Utilisateur Odoo spécifique identifié
- [ ] ✅ Sudoers configuré avec utilisateur exact
- [ ] ✅ Fichier sudoers testé avant déploiement
- [ ] ✅ Permissions 0440 sur /etc/sudoers.d/odoo-saas
- [ ] ✅ Propriétaire root:root
- [ ] ✅ Nginx installé et configuré
- [ ] ✅ Certbot installé
- [ ] ✅ Scripts testés manuellement

## 🚀 Guide de Déploiement Rapide

### Étape 1: SSH sur le VPS de Production

```bash
ssh user@votre-vps-production.com
cd /home/user/odoo
```

### Étape 2: Identifier l'Utilisateur Odoo

```bash
# Exécuter le script d'identification
./addons/onedesk_core/scripts/identify_odoo_user.sh

# OU vérifier manuellement
ps aux | grep odoo-bin | grep -v grep
systemctl status odoo
```

**Notez le nom de l'utilisateur** (exemple: `odoo`, `www-data`, `openerp`)

### Étape 3: Créer le Fichier Sudoers SÉCURISÉ

**⚠️ ATTENTION: Remplacer TOUTES les occurrences de `odoo` par votre utilisateur réel**

```bash
# Méthode 1: Avec visudo (recommandé - plus sûr)
sudo visudo -f /etc/sudoers.d/odoo-saas

# Copier-coller le contenu ci-dessous en remplaçant 'odoo' par votre utilisateur:
```

**Contenu du fichier sudoers (PRODUCTION):**

```bash
# Odoo SaaS - Configuration SÉCURISÉE Production
# Remplacer 'odoo' par votre utilisateur Odoo réel

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
```

**Méthode 2: En une seule commande (avancé)**

```bash
# ATTENTION: Modifier 'odoo' AVANT d'exécuter!
ODOO_USER="odoo"  # ← CHANGER ICI

sudo tee /etc/sudoers.d/odoo-saas > /dev/null <<EOF
# Odoo SaaS - Configuration SÉCURISÉE Production
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
```

### Étape 4: Définir les Permissions CRITIQUES

```bash
# Permissions strictes (lecture seule pour root)
sudo chmod 0440 /etc/sudoers.d/odoo-saas

# Propriétaire root obligatoire
sudo chown root:root /etc/sudoers.d/odoo-saas

# Vérifier
ls -la /etc/sudoers.d/odoo-saas
# Devrait afficher: -r--r----- 1 root root
```

### Étape 5: VÉRIFIER la Syntaxe

```bash
# Vérification critique (ne pas sauter!)
sudo visudo -c -f /etc/sudoers.d/odoo-saas

# Devrait afficher: "parsed OK"
# Si erreur → CORRIGER AVANT de continuer
```

### Étape 6: Tester Sudo

```bash
# Test 1: Sudo basique
sudo -u odoo sudo -n whoami
# Attendu: root (sans demander password)

# Test 2: Script simulation
sudo -u odoo sudo -n /home/user/odoo/addons/onedesk_core/scripts/simulate_domain_setup.sh test.exemple.com testdb
# Attendu: Configuration simulée réussie
```

### Étape 7: Vérifier les Prérequis Nginx & Certbot

```bash
# Nginx installé?
which nginx
nginx -v

# Certbot installé?
which certbot
certbot --version

# Si non installés:
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx -y
```

### Étape 8: Redémarrer Odoo

```bash
sudo systemctl restart odoo
sudo systemctl status odoo
```

### Étape 9: Test Depuis Interface Odoo

1. Se connecter à Odoo production
2. Ouvrir **SaaS Manager → Clients**
3. Créer ou sélectionner un client test
4. Cliquer **"🔍 DEBUG: Tester Sudo"**
5. **Vérifier:** Affiche "✅ Sudo fonctionne: OUI"

Si affiche "❌ Sudo: FAILED" → Voir Troubleshooting

### Étape 10: Test Domaine Complet (Optionnel)

**⚠️ Attention:** Ce test créera vraiment une config Nginx + SSL

```bash
# Depuis l'interface Odoo:
1. Entrer un domaine test: test-client.votre-domaine.com
2. Cliquer "🔧 PROD: Configurer + SSL"
3. Vérifier les logs dans /var/log/onedesk/domain_setup.log
```

## 🔍 Vérifications Post-Déploiement

### Vérifier Sudoers

```bash
# Contenu du fichier
cat /etc/sudoers.d/odoo-saas

# DOIT contenir utilisateur spécifique (odoo, www-data, etc.)
# NE DOIT PAS contenir "ALL ALL"
```

### Vérifier Logs

```bash
# Créer le dossier de logs si nécessaire
sudo mkdir -p /var/log/onedesk
sudo chown odoo:odoo /var/log/onedesk

# Surveiller les logs
tail -f /var/log/onedesk/domain_setup.log
```

### Vérifier Scripts

```bash
# Les scripts doivent être exécutables
ls -la /home/user/odoo/addons/onedesk_core/scripts/*.sh

# Si besoin:
chmod +x /home/user/odoo/addons/onedesk_core/scripts/*.sh
```

## 🚨 Troubleshooting Production

### Erreur: "sudo: a password is required"

```bash
# Vérifier l'utilisateur dans sudoers correspond à l'utilisateur Odoo
./addons/onedesk_core/scripts/identify_odoo_user.sh
cat /etc/sudoers.d/odoo-saas | grep -v "^#" | grep -v "^$"

# Les deux doivent correspondre!
```

### Erreur: Odoo affiche "Sudo: FAILED"

```bash
# 1. Vérifier depuis le shell
sudo -u odoo sudo -n whoami

# 2. Vérifier les permissions du fichier
ls -la /etc/sudoers.d/odoo-saas
# Doit être: -r--r----- 1 root root

# 3. Vérifier la syntaxe
sudo visudo -c -f /etc/sudoers.d/odoo-saas

# 4. Redémarrer Odoo
sudo systemctl restart odoo
```

### Erreur: "nginx: command not found"

```bash
# Installer Nginx
sudo apt update
sudo apt install nginx -y

# Vérifier
which nginx
nginx -v
```

### Erreur: Certificat SSL échoue

```bash
# Vérifier Certbot
which certbot
certbot --version

# Installer si nécessaire
sudo apt install certbot python3-certbot-nginx -y

# Tester manuellement
sudo certbot --nginx -d test.votredomaine.com --dry-run
```

## 🔒 Checklist Sécurité Finale

Avant de valider le déploiement:

```bash
# 1. Vérifier qu'il n'y a PAS de "ALL ALL" dangereux
grep "^ALL ALL" /etc/sudoers.d/odoo-saas
# Ne devrait RIEN retourner !

# 2. Vérifier utilisateur spécifique
grep "^odoo\|^www-data\|^openerp" /etc/sudoers.d/odoo-saas
# Devrait lister les permissions

# 3. Vérifier permissions fichier
stat -c '%a %U:%G' /etc/sudoers.d/odoo-saas
# Devrait afficher: 440 root:root

# 4. Test final sudo
sudo -u odoo sudo -n whoami
# Devrait afficher: root
```

## 📊 Différences Dev vs Prod

| Aspect | DEV/TEST | PRODUCTION |
|--------|----------|------------|
| **Utilisateur sudoers** | `user` (permissif) | `odoo` (spécifique) |
| **Règle ALL** | ⚠️ Acceptable | ❌ INTERDIT |
| **Scripts Nginx** | Simulation mode | Vraie config |
| **SSL/Certbot** | Simulation | Vrais certificats |
| **Logs** | Optionnels | **Obligatoires** |
| **Monitoring** | Non requis | **Requis** |

## 📝 Template de Déploiement Ansible (Bonus)

```yaml
---
- name: Configuration Sudoers Sécurisée pour Odoo SaaS
  hosts: production
  become: yes
  vars:
    odoo_user: "odoo"  # À adapter
    odoo_path: "/home/user/odoo"

  tasks:
    - name: Créer fichier sudoers sécurisé
      template:
        src: templates/odoo-saas.sudoers.j2
        dest: /etc/sudoers.d/odoo-saas
        owner: root
        group: root
        mode: '0440'
        validate: 'visudo -c -f %s'

    - name: Créer dossier logs
      file:
        path: /var/log/onedesk
        state: directory
        owner: "{{ odoo_user }}"
        group: "{{ odoo_user }}"
        mode: '0755'

    - name: Rendre scripts exécutables
      file:
        path: "{{ odoo_path }}/addons/onedesk_core/scripts/{{ item }}"
        mode: '0755'
      loop:
        - setup_client_domain.sh
        - test_client_domain_local.sh
        - simulate_domain_setup.sh
        - identify_odoo_user.sh

    - name: Vérifier Nginx installé
      package:
        name: nginx
        state: present

    - name: Vérifier Certbot installé
      package:
        name:
          - certbot
          - python3-certbot-nginx
        state: present
```

## 🎯 Résumé - Points Clés

1. ✅ **TOUJOURS** utiliser utilisateur spécifique (`odoo`, jamais `ALL`)
2. ✅ **TOUJOURS** tester avec `visudo -c` avant validation
3. ✅ **TOUJOURS** permissions 440 root:root
4. ✅ **TOUJOURS** tester depuis CLI ET interface Odoo
5. ❌ **JAMAIS** `ALL ALL=(ALL)` en production
6. ❌ **JAMAIS** permissions permissives (777, 644, etc.)
7. ❌ **JAMAIS** déployer sans tests préalables

## 📞 Support

En cas de problème:
1. Consulter `/var/log/onedesk/domain_setup.log`
2. Exécuter `identify_odoo_user.sh`
3. Vérifier `sudo visudo -c`
4. Consulter `SUDOERS_CONFIG.md` pour détails

---

**Dernière mise à jour:** 2025-12-21
**Version:** 1.0 - Configuration Sécurisée
