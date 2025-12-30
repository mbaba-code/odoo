# OneDesk SaaS Multi-Tenant - Documentation Complète

**Version**: 19.0.2.0.0
**Date**: 2025-12-23
**Auteur**: Merveilles Baba

---

## 📋 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Fonctionnalités Principales](#fonctionnalités-principales)
3. [Architecture & Sécurité](#architecture--sécurité)
4. [Guide d'Utilisation](#guide-dutilisation)
5. [Configuration Technique](#configuration-technique)
6. [Compatibilité Odoo 19](#compatibilité-odoo-19)
7. [Dépannage](#dépannage)

---

## Vue d'ensemble

Le module **OneDesk Core** intègre un système complet de gestion SaaS multi-tenant permettant de:
- Provisionner automatiquement des bases de données clients isolées
- Gérer les abonnements et plans (Starter, Pro, Enterprise)
- Configurer des domaines personnalisés avec SSL automatique
- Suspendre/réactiver les accès clients
- Monitorer les métriques et performances

### Modèles Principaux

| Modèle | Description |
|--------|-------------|
| `saas.client` | Gestion des clients SaaS et provisioning |
| `saas.plan` | Plans d'abonnement (Starter, Pro, Enterprise) |
| `saas.domain.request` | Demandes de domaine personnalisé |
| `saas.database` | Surveillance des bases de données |
| `saas.metric` | Métriques et KPIs |
| `saas.alert` | Alertes système |

---

## Fonctionnalités Principales

### 1. 🚀 Provisioning Automatique

**Workflow complet** :
1. Création d'un client SaaS
2. Génération automatique du nom de base (`onedesk_client_X_slug`)
3. Initialisation Odoo avec modules selon le plan
4. Création de deux comptes admin :
   - **Admin Client** : Credentials uniques envoyés par email
   - **Super Admin OneDesk** : Credentials fixes pour tous les clients
     - Login: `onedesk.admin@basatechno.fr`
     - Password: `OneDesk@Admin2025!` (configurable)

**Fichier** : `addons/onedesk_core/models/saas_client.py`

```python
def action_provision_database(self):
    """
    1. _initialize_odoo_database() - Crée base PostgreSQL + init Odoo
    2. _create_client_admin() - Crée admins (client + super admin)
    3. _configure_client_company() - Configure company
    4. _send_welcome_email() - Envoie credentials client
    """
```

### 2. ⏸️ Suspension/Réactivation Réelle

**Fonctionnement** :
- `action_suspend()` : Désactive TOUS les utilisateurs (sauf super admin OneDesk)
- `action_activate()` : Réactive tous les utilisateurs
- `action_terminate()` : Marque comme terminé (backup recommandé)

**Code** : `saas_client.py:584-679`

```python
def action_suspend(self):
    # Se connecte à la base client
    registry = Registry(self.database_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        # Désactive tous sauf super admin OneDesk
        users = env['res.users'].search([
            ('login', '!=', super_admin_login),
            ('id', '!=', SUPERUSER_ID),
        ])
        users.write({'active': False})
```

### 3. 🌐 Domaines Personnalisés avec SSL

**Workflow Client** :
1. Client va dans **OneDesk → Paramètres → Domaine Personnalisé**
2. Entre son domaine (ex: `monentreprise.com`)
3. Configure CNAME chez son registrar : `monentreprise.com → basatechno.fr`
4. Clique sur **"Vérifier DNS"** (validation automatique)
5. Soumet la demande

**Workflow Admin SaaS** :
1. Reçoit notification dans **SaaS Manager → Configuration → Demandes de Domaine**
2. Vérifie la demande (vue Kanban par état)
3. Clique sur **"Approuver"**
4. Le système configure automatiquement :
   - Nginx virtual host
   - Certificat SSL Let's Encrypt
   - Redirection HTTP → HTTPS

**Fichiers** :
- Modèle : `addons/onedesk_core/models/saas_domain_request.py`
- Vues : `addons/onedesk_core/views/saas_domain_request_views.xml`
- Script : `addons/onedesk_core/scripts/setup_client_domain.sh`

### 4. 💾 Backup Complet PostgreSQL

**Fonctionnalité** :
- Téléchargement dump PostgreSQL complet (structure + données)
- Format custom compressé (`pg_dump -F c`)
- Authentification sécurisée via `.pgpass` temporaire

**Code** : `saas_client.py:action_download_backup()`

### 5. 🔐 Sécurité Multi-Tenant

**Isolation des Menus** :

| Menu | Visible Dans | Groupe Requis |
|------|--------------|---------------|
| SaaS Manager | Base principale UNIQUEMENT | `group_saas_manager` |
| OneDesk (clients) | Toutes les bases | `group_onedesk_property_manager` |
| Domaine Personnalisé | Toutes les bases | Auto |

**Groupe SaaS Manager** :
- Créé dans `data/onedesk_groups.xml`
- Hérite de `base.group_system`
- Assigné UNIQUEMENT aux admins de la base principale
- Les clients ne verront JAMAIS le menu SaaS Manager

---

## Architecture & Sécurité

### Structure des Bases

```
┌─────────────────────────────────────┐
│  BASE PRINCIPALE (odoo_prod)        │
│  - Module onedesk_core complet      │
│  - Menu "SaaS Manager" visible      │
│  - Gestion de tous les clients      │
└─────────────────────────────────────┘
              │
              │ Provisioning
              ▼
┌─────────────────────────────────────┐
│  BASE CLIENT 1 (onedesk_client_1)   │
│  - Module onedesk_core (sans SaaS)  │
│  - Menu "SaaS Manager" CACHÉ        │
│  - Isolation stricte par company_id │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│  BASE CLIENT 2 (onedesk_client_2)   │
│  - Module onedesk_core (sans SaaS)  │
│  - Menu "SaaS Manager" CACHÉ        │
│  - Isolation stricte par company_id │
└─────────────────────────────────────┘
```

### Comptes Admin

**Base Principale** :
- Admin principal avec groupe `group_saas_manager`
- Voit et gère tous les clients SaaS

**Bases Clients** :
- **Admin Client** : Login unique, password généré aléatoirement
- **Super Admin OneDesk** : Credentials fixes (tous les clients)
  - Permet connexion sans chercher le mot de passe
  - Utile pour support et débogage

### Règles de Sécurité

**Fichier** : `security/ir.model.access.csv`

```csv
id,name,model_id,group_id,perm_read,perm_write,perm_create,perm_unlink
access_saas_client_admin,SaaS Client Admin,model_saas_client,group_saas_manager,1,1,1,1
access_saas_domain_request_manager,SaaS Domain Manager,model_saas_domain_request,group_saas_manager,1,1,1,1
access_saas_domain_request_client,SaaS Domain Client,model_saas_domain_request,group_onedesk_property_manager,1,1,1,0
```

---

## Guide d'Utilisation

### Pour l'Admin SaaS (Base Principale)

#### Créer un Nouveau Client

1. **SaaS Manager → Clients → Créer**
2. Remplir :
   - Nom du client
   - Email de contact
   - Plan (Starter/Pro/Enterprise)
   - Domaine personnalisé (optionnel)
3. Cliquer **"Provisionner"**
4. Attendre (~30-60 secondes)
5. Vérifier l'état : `active`
6. Credentials envoyés par email au client

#### Suspendre un Client

1. **SaaS Manager → Clients → [Client]**
2. Cliquer **"Suspendre"**
3. ✅ Tous les utilisateurs de la base client sont désactivés
4. Le client ne peut plus se connecter

#### Approuver un Domaine Personnalisé

1. **SaaS Manager → Configuration → Demandes de Domaine**
2. Vue Kanban : voir demandes en "pending"
3. Vérifier que DNS est valide
4. Cliquer **"Approuver"**
5. ✅ Nginx + SSL configurés automatiquement

#### Se Connecter à une Base Client

1. **SaaS Manager → Clients → [Client]**
2. Cliquer **"🔐 Connexion Admin"**
3. Copier les credentials affichés :
   - Login: `onedesk.admin@basatechno.fr`
   - Password: `OneDesk@Admin2025!`
4. Ouvrir l'URL du client
5. Se connecter avec ces credentials

### Pour le Client (Base Client)

#### Configurer un Domaine Personnalisé

1. **OneDesk → Paramètres → Domaine Personnalisé**
2. Cliquer **"Créer"**
3. Entrer le domaine : `monentreprise.com`
4. Configurer CNAME chez le registrar :
   ```
   Type: CNAME
   Nom: monentreprise.com
   Cible: basatechno.fr
   ```
5. Attendre propagation DNS (~5-60 min)
6. Cliquer **"Vérifier DNS"**
7. Si valide ✅, cliquer **"Soumettre la demande"**
8. Attendre approbation de l'admin SaaS
9. Une fois approuvé, accéder via `https://monentreprise.com`

---

## Configuration Technique

### Variables de Configuration

**Fichier** : `/etc/odoo/odoo.conf`

```ini
[options]
# Super Admin OneDesk (credentials fixes pour toutes les bases clients)
saas_super_admin_login = onedesk.admin@basatechno.fr
saas_super_admin_password = OneDesk@Admin2025!

# Domaine principal (pour CNAME)
# onedesk.saas_main_domain = basatechno.fr  # Via ir.config_parameter
```

### Paramètres Système

**Settings → Technical → Parameters → System Parameters** :

| Clé | Valeur | Description |
|-----|--------|-------------|
| `onedesk.saas_main_domain` | `basatechno.fr` | Domaine principal pour CNAME |

### Scripts Bash

**Fichier** : `addons/onedesk_core/scripts/setup_client_domain.sh`

**Fonctionnement** :
1. Crée config Nginx HTTP
2. Teste la config (`nginx -t`)
3. Reload Nginx
4. Lance Certbot pour SSL
5. Configure auto-renewal (cron)

**Permissions Sudo** :

```bash
# /etc/sudoers.d/odoo
odoo ALL=(ALL) NOPASSWD: /usr/bin/nginx
odoo ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
odoo ALL=(ALL) NOPASSWD: /usr/bin/certbot
```

### Cron Jobs

**Fichier** : `data/saas_cron.xml`

| Cron | Fréquence | Action |
|------|-----------|--------|
| Collect Metrics | 1h | Collecte métriques bases clients |
| Check Alerts | 30min | Vérifie alertes (espace disque, etc) |

---

## Compatibilité Odoo 19

### Changements Majeurs Appliqués

| Ancien (≤ Odoo 18) | Nouveau (Odoo 19) | Fichier |
|-------------------|-------------------|---------|
| `view_mode="tree,form"` | `view_mode="list,form"` | Toutes les actions |
| `<t t-name="kanban-box">` | `<t t-name="card">` | Vues kanban |
| `groups_ids` (create) | `groups_ids` (write séparé) | saas_client.py:462 |
| `category_id` (res.groups) | ❌ Supprimé | onedesk_groups.xml |
| `<separator/>` (search) | ❌ Supprimé | Vues search |
| `expand="0"` (group) | ❌ Supprimé | Vues search |

### Corrections Spécifiques

**1. Création Utilisateur avec Groupes**

❌ **Ancien (ne marche pas)** :
```python
user = env['res.users'].create({
    'name': 'Admin',
    'group_ids': [(6, 0, [group_id])],  # ❌ Erreur Odoo 19
})
```

✅ **Nouveau (Odoo 19)** :
```python
# Étape 1: Créer sans groupes
user = env['res.users'].create({
    'name': 'Admin',
})

# Étape 2: Ajouter groupes via write()
user.write({
    'group_ids': [(6, 0, [group_id])],  # ✅ OK
})
```

**2. Vues Kanban OWL**

❌ **Ancien** :
```xml
<templates>
    <t t-name="kanban-box">
        ...
    </t>
</templates>
```

✅ **Nouveau** :
```xml
<templates>
    <t t-name="card">
        ...
    </t>
</templates>
```

**3. Actions avec Vues List**

❌ **Ancien** :
```xml
<field name="view_mode">tree,form</field>
```

✅ **Nouveau** :
```xml
<field name="view_mode">list,form</field>
```

---

## Dépannage

### Problème : Erreur "Invalid field 'groups_ids'"

**Cause** : Tentative de définir `groups_ids` lors du `create()` d'un utilisateur

**Solution** : Créer l'utilisateur d'abord, puis ajouter les groupes via `write()`

**Fichier** : `saas_client.py:453-467`

---

### Problème : Nginx "invalid variable name"

**Cause** : Configuration nginx cassée ou lien symbolique pointant vers un fichier supprimé

**Solution** :
```bash
# Tester nginx
sudo nginx -t

# Si erreur, trouver le fichier problématique
ls -la /etc/nginx/sites-enabled/

# Supprimer lien cassé
sudo rm /etc/nginx/sites-enabled/FICHIER_PROBLEMATIQUE

# Retester
sudo nginx -t
```

---

### Problème : Menu "SaaS Manager" visible dans base client

**Cause** : Le groupe `group_saas_manager` n'est pas correctement configuré

**Vérification** :
```python
# Dans base cliente, vérifier que le menu est caché
self.env.ref('onedesk_core.menu_saas_root').groups_id
# Doit retourner: onedesk_core.group_saas_manager

# Vérifier que l'utilisateur N'A PAS ce groupe
self.env.user.groups_id
```

---

### Problème : Provisioning échoue "relation ir_module_module does not exist"

**Cause** : `exp_create_database()` n'a pas complété l'initialisation Odoo

**Solution** : Vérifier les logs Odoo pour voir l'erreur exacte lors de l'initialisation

---

### Problème : DNS invalide pour domaine personnalisé

**Cause** : CNAME pas encore propagé ou mal configuré

**Vérification** :
```bash
# Tester résolution DNS
nslookup monentreprise.com

# Tester avec Google DNS
nslookup monentreprise.com 8.8.8.8

# Vérifier CNAME
dig monentreprise.com CNAME
```

**Propagation** : Peut prendre 5-60 minutes (voire plus selon le TTL)

---

## Commits Importants

| Commit | Description |
|--------|-------------|
| `46d64fb3` | 🔒 SECURITY: Cacher SaaS Manager aux clients + Vraie suspension |
| `1023ab72` | ✨ FEAT: Système de demande de domaine avec vérification DNS |
| `1deda750` | 🔧 FIX: group_ids (pas groups_ids) |
| `a916395f` | 🔧 FIX: Retirer category_id (incompatible Odoo 19) |
| `2f8a7744` | 🔧 FIX: Vue search simplifiée |
| `83e8849b` | 🔧 FIX: Action domaine + Menu OneDesk |
| `fd33c41e` | 🔧 FIX: tree → list (Odoo 19) |
| `7d1842e6` | 🔧 FIX: Kanban template kanban-box → card |

---

## Prochaines Étapes Recommandées

1. **Tests Complets** :
   - ✅ Provisionner un nouveau client
   - ✅ Tester suspension/réactivation
   - ✅ Demander un domaine personnalisé
   - ✅ Approuver et vérifier config nginx/SSL
   - ✅ Télécharger un backup

2. **Améliorations Futures** :
   - [ ] Interface de monitoring en temps réel (WebSocket)
   - [ ] Notifications email pour alertes système
   - [ ] Facturation automatique intégrée
   - [ ] API REST pour provisioning externe
   - [ ] Dashboard client avec métriques d'utilisation

3. **Documentation Utilisateur** :
   - [ ] Vidéo tutoriel provisioning
   - [ ] Guide client configuration domaine
   - [ ] FAQ support technique

---

## Support & Contact

**Développeur** : Merveilles Baba
**Email** : support@basatechno.fr
**Version** : 19.0.2.0.0
**Dernière mise à jour** : 2025-12-23

---

**Fin de la documentation** 🎉
