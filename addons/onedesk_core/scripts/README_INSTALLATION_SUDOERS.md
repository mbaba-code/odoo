# 🚀 Installation Rapide Sudoers - Copier/Coller

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 1d21623536f (👥 UPDATE: Utilisateurs spécifiques sudoers (odoo, baba_odoo, babamerveilles))
## 👥 Utilisateurs Configurés

### Production (VPS)
- ✅ **odoo** - Utilisateur système qui exécute Odoo
- ✅ **baba_odoo** - Utilisateur admin

### Dev/Test
- ✅ **odoo** - Utilisateur système qui exécute Odoo
- ✅ **baba_odoo** - Utilisateur admin
- ✅ **babamerveilles** - Développeur MacBook

---

<<<<<<< HEAD
=======
>>>>>>> bf69dd4e6a9 (🚀 SCRIPTS: Installation automatique sudoers (PROD + DEV))
=======
>>>>>>> 1d21623536f (👥 UPDATE: Utilisateurs spécifiques sudoers (odoo, baba_odoo, babamerveilles))
## Pour PRODUCTION (VPS Production)

**1️⃣ Copier-coller cette commande complète :**

```bash
cd /home/user/odoo && \
chmod +x addons/onedesk_core/scripts/install_sudoers_production.sh && \
sudo addons/onedesk_core/scripts/install_sudoers_production.sh
```

Le script va :
<<<<<<< HEAD
<<<<<<< HEAD
- ✅ Configurer utilisateurs **odoo** et **baba_odoo**
=======
- ✅ Détecter automatiquement l'utilisateur Odoo
>>>>>>> bf69dd4e6a9 (🚀 SCRIPTS: Installation automatique sudoers (PROD + DEV))
=======
- ✅ Configurer utilisateurs **odoo** et **baba_odoo**
>>>>>>> 1d21623536f (👥 UPDATE: Utilisateurs spécifiques sudoers (odoo, baba_odoo, babamerveilles))
- ✅ Créer la configuration sécurisée
- ✅ Configurer les permissions strictes
- ✅ Vérifier la syntaxe
- ✅ Tester la configuration
<<<<<<< HEAD
<<<<<<< HEAD
- ✅ Proposer de créer l'utilisateur baba_odoo si n'existe pas
=======
>>>>>>> bf69dd4e6a9 (🚀 SCRIPTS: Installation automatique sudoers (PROD + DEV))
=======
- ✅ Proposer de créer l'utilisateur baba_odoo si n'existe pas
>>>>>>> 1d21623536f (👥 UPDATE: Utilisateurs spécifiques sudoers (odoo, baba_odoo, babamerveilles))

---

## Pour DEV/TEST (Environnement de développement)

**1️⃣ Copier-coller cette commande complète :**

```bash
cd /home/user/odoo && \
chmod +x addons/onedesk_core/scripts/install_sudoers_dev.sh && \
sudo addons/onedesk_core/scripts/install_sudoers_dev.sh
```

Le script va :
<<<<<<< HEAD
<<<<<<< HEAD
- ✅ Configurer utilisateurs **odoo**, **baba_odoo** et **babamerveilles**
- ✅ Permettre les tests depuis n'importe quel utilisateur
- ✅ Configuration adaptée pour MacBook et serveur test
=======
- ✅ Configurer permissions pour utilisateur dev + odoo
- ✅ Permettre les tests sans restrictions
>>>>>>> bf69dd4e6a9 (🚀 SCRIPTS: Installation automatique sudoers (PROD + DEV))
=======
- ✅ Configurer utilisateurs **odoo**, **baba_odoo** et **babamerveilles**
- ✅ Permettre les tests depuis n'importe quel utilisateur
- ✅ Configuration adaptée pour MacBook et serveur test
>>>>>>> 1d21623536f (👥 UPDATE: Utilisateurs spécifiques sudoers (odoo, baba_odoo, babamerveilles))
- ⚠️ Configuration NON recommandée pour production

---

## 🔍 Vérification Après Installation

**Copier-coller pour tester :**

```bash
# Test 1: Sudo fonctionne?
sudo -n whoami

# Test 2: Vérifier le fichier créé
cat /etc/sudoers.d/odoo-saas

# Test 3: Vérifier permissions
ls -la /etc/sudoers.d/odoo-saas

# Test 4: Test depuis Odoo (après redémarrage)
sudo systemctl restart odoo
```

---

## 📱 Installation Manuelle (Alternative)

Si tu préfères voir le contenu avant d'exécuter :

### Pour PRODUCTION :

```bash
# 1. Télécharger et voir le script
cat /home/user/odoo/addons/onedesk_core/scripts/install_sudoers_production.sh

# 2. Exécuter
sudo /home/user/odoo/addons/onedesk_core/scripts/install_sudoers_production.sh
```

### Pour DEV/TEST :

```bash
# 1. Télécharger et voir le script
cat /home/user/odoo/addons/onedesk_core/scripts/install_sudoers_dev.sh

# 2. Exécuter
sudo /home/user/odoo/addons/onedesk_core/scripts/install_sudoers_dev.sh
```

---

## ⚡ Installation Ultra-Rapide (One-Liner)

### PRODUCTION (copier-coller une seule ligne) :
```bash
curl -fsSL https://raw.githubusercontent.com/votre-repo/odoo/main/addons/onedesk_core/scripts/install_sudoers_production.sh | sudo bash
```

### DEV (copier-coller une seule ligne) :
```bash
cd /home/user/odoo && sudo bash addons/onedesk_core/scripts/install_sudoers_dev.sh
```

---

## 🔧 Désinstallation

**Copier-coller pour supprimer :**

```bash
# Supprimer la configuration sudoers
sudo rm -f /etc/sudoers.d/odoo-saas

# Vérifier la suppression
ls -la /etc/sudoers.d/
```

---

## ❓ En Cas de Problème

### Erreur: "sudo: a password is required"

```bash
# Réinstaller avec le script
sudo /home/user/odoo/addons/onedesk_core/scripts/install_sudoers_production.sh

# Vérifier l'utilisateur Odoo
/home/user/odoo/addons/onedesk_core/scripts/identify_odoo_user.sh
```

### Erreur: "parse error in sudoers"

```bash
# Supprimer le fichier corrompu
sudo rm -f /etc/sudoers.d/odoo-saas

# Réinstaller
sudo /home/user/odoo/addons/onedesk_core/scripts/install_sudoers_production.sh
```

---

## 📚 Documentation Complète

- **Guide déploiement :** `/home/user/odoo/addons/onedesk_core/docs/DEPLOIEMENT_PRODUCTION_SECURISE.md`
- **Configuration sudo :** `/home/user/odoo/addons/onedesk_core/docs/SUDOERS_CONFIG.md`
- **Identifier utilisateur :** `/home/user/odoo/addons/onedesk_core/scripts/identify_odoo_user.sh`

---

## ✅ Checklist Rapide

Après installation, vérifier :

- [ ] `sudo -n whoami` → retourne "root"
- [ ] `/etc/sudoers.d/odoo-saas` existe
- [ ] Permissions : `ls -la /etc/sudoers.d/odoo-saas` → `-r--r----- 1 root root`
- [ ] Pas de "ALL ALL" dans le fichier (production)
- [ ] Utilisateur spécifique présent (ex: odoo)
- [ ] Test depuis Odoo : Bouton "DEBUG: Tester Sudo" → "✅ OUI"

---

**Date de création :** 2025-12-21
**Scripts disponibles :**
- ✅ `install_sudoers_production.sh` - Production sécurisée
- ✅ `install_sudoers_dev.sh` - Développement/Test
- ✅ `identify_odoo_user.sh` - Identification utilisateur
