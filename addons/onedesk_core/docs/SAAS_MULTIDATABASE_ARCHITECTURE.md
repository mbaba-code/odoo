# Architecture SaaS Multi-Database OneDesk Premium/Enterprise

## 📋 Executive Summary

Migration d'une architecture **multi-company** (une base, plusieurs companies isolées) vers une architecture **multi-database SaaS** (une base par client Premium) pour OneDesk Premium/Enterprise.

### Pourquoi cette migration ?

| Critère | Multi-Company (Actuel) | Multi-Database (Cible) |
|---------|------------------------|------------------------|
| **Isolation** | Logique (record rules SQL) | Physique (bases PostgreSQL séparées) |
| **Sécurité** | Forte (rules au niveau SQL) | **Maximale** (isolation totale) |
| **Performance** | Partagée entre tous les clients | **Dédiée** par client |
| **Customisation** | Limitée (modules communs) | **Totale** (modules/code indépendants) |
| **Admin client** | Sous-admin avec restrictions | **Admin système total** de SA base |
| **Backup** | Backup global (tous clients) | **Backup sélectif** par client |
| **Scaling** | Vertical uniquement | **Horizontal** (sharding possible) |
| **Compliance** | Risque théorique de fuite | **Garantie absolue** (RGPD, SOC2) |

### Vision Cible

```
┌─────────────────────────────────────────────────────────────────┐
│                    ONEDESK SAAS PLATFORM                        │
└─────────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            │                                   │
            ▼                                   ▼
┌─────────────────────┐            ┌─────────────────────────┐
│  BASE MAÎTRE        │            │  BASES CLIENTS          │
│  onedesk_core       │            │  onedesk_client_XXX     │
├─────────────────────┤            ├─────────────────────────┤
│ - Gestion clients   │───────────▶│ Client A: onedesk_cli_1 │
│ - Abonnements       │            │ Client B: onedesk_cli_2 │
│ - Facturation       │            │ Client C: onedesk_cli_3 │
│ - Provisioning      │            │ ...                     │
│ - Monitoring        │            │ Client Z: onedesk_cli_N │
│ - Métriques         │            └─────────────────────────┘
└─────────────────────┘                       │
                                              ▼
                              ┌─────────────────────────────┐
                              │  Accès via sous-domaines    │
                              ├─────────────────────────────┤
                              │ clienta.onedesk.com         │
                              │ clientb.onedesk.com         │
                              │ clientc.onedesk.com         │
                              └─────────────────────────────┘
```

---

## 📊 Analyse de l'Architecture Actuelle (Multi-Company)

### Vue d'ensemble

**Fichier de référence**: `/addons/onedesk_core/docs/PREMIUM_MANAGER_ARCHITECTURE.md`

L'architecture actuelle utilise le modèle **multi-company** d'Odoo :

```
┌──────────────────────────────────────────────────────────┐
│             BASE UNIQUE: onedesk_production              │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Company A (ID=1)          Company B (ID=2)             │
│  ├─ Users (company_id=1)   ├─ Users (company_id=2)     │
│  ├─ Partners (company_id=1)├─ Partners (company_id=2)   │
│  ├─ Invoices (company_id=1)├─ Invoices (company_id=2)   │
│  ├─ CRM (company_id=1)     ├─ CRM (company_id=2)        │
│  └─ Website (company_id=1) └─ Website (company_id=2)    │
│                                                          │
│  Isolation: Record Rules SQL (company_id filtering)     │
└──────────────────────────────────────────────────────────┘
```

### Composants clés actuels

#### 1. **Groupe Premium Manager** (`data/onedesk_groups.xml`)
- Rôle: Sous-administrateur avec accès complet Odoo
- Groupes hérités: `base.group_system`, `base.group_erp_manager`, `sales_team.group_sale_manager`, etc.
- **Limitation**: Malgré `group_system`, accès restreint à SA company uniquement

#### 2. **Auto-configuration** (`models/res_users.py`)
- Méthode: `_auto_configure_premium_manager()`
- Actions:
  - Ajoute automatiquement les groupes manquants
  - Restreint `company_ids` à UNE seule company
  - Aligne `partner_id.company_id` avec `user.company_id`
  - Crée automatiquement un website pour la company

#### 3. **Record Rules Multi-Tenant** (`data/onedesk_security.xml`, `data/onedesk_security_premium.xml`)

**Principe**: Filtrage SQL au niveau des record rules

```xml
<!-- Exemple: Partners -->
<field name="domain_force">
  ['|', ('company_id', '=', False), ('company_id', '=', user.company_id.id)]
</field>
```

**Modèles couverts** (22 record rules):
- `res.partner` (contacts)
- `res.users` (utilisateurs)
- `res.company` (companies)
- `website.website`, `website.page`, `website.menu`
- `crm.lead` (CRM)
- `account.move`, `account.payment`, `account.journal` (comptabilité)
- `sale.order` (ventes)
- `product.template` (produits)
- Tous les modèles OneDesk (property, unit, tenant, etc.)

**Garantie de sécurité**:
- ✅ Filtrage au niveau SQL (impossible à bypass côté client)
- ✅ Même avec `base.group_system`, pas de bypass (conditions supprimées)
- ✅ Isolation stricte entre companies

#### 4. **Migration Automatique** (`migrations/19.0.1.0.2/post-migrate.py`)

Corrige automatiquement les données existantes :
- Aligne `partner_id.company_id` avec `user.company_id`
- Met les partners système (`Administrator`, `OdooBot`) en global (`company_id=False`)
- Restreint Premium Managers à UNE company

### Forces de l'architecture actuelle

✅ **Sécurité robuste** via record rules SQL
✅ **Auto-configuration** complète et automatique
✅ **Migration automatique** des données existantes
✅ **Gestion centralisée** dans une seule base
✅ **Performance** correcte pour ~100-500 clients

### Limites de l'architecture actuelle

❌ **Isolation logique** uniquement (risque théorique de bug dans les rules)
❌ **Performance partagée** (un client lourd impacte tous les autres)
❌ **Customisation limitée** (impossible d'avoir modules différents par client)
❌ **Backup global** (impossible de restaurer un seul client)
❌ **Scaling horizontal** impossible (une seule base)
❌ **Admin client limité** (pas de vrai `admin` système)
❌ **Compliance complexe** (RGPD: données dans une seule base)

---

## 🎯 Architecture Cible: Multi-Database SaaS

### Principe fondamental

**UN CLIENT PREMIUM = UNE BASE POSTGRESQL DÉDIÉE**

```
PostgreSQL Cluster (unique serveur)
├─ onedesk_core              ← Base MAÎTRE (gestion SaaS)
├─ onedesk_client_1          ← Client Premium A
├─ onedesk_client_2          ← Client Premium B
├─ onedesk_client_3          ← Client Premium C
└─ onedesk_client_N          ← Client Premium N
```

### Rôles et responsabilités

#### **Base Maître: `onedesk_core`**

**Rôle**: Pilotage complet de la plateforme SaaS

**Responsabilités**:
1. **Gestion des clients Premium**
   - CRUD clients (create, read, update, delete)
   - Informations: nom, email, plan, statut, date création, etc.

2. **Gestion des abonnements**
   - Plans: Starter, Pro, Enterprise
   - Facturation récurrente (mensuelle, annuelle)
   - États: trial, active, suspended, cancelled
   - Limites: nombre d'utilisateurs, stockage, API calls, etc.

3. **Provisioning automatique**
   - Création de la base PostgreSQL client
   - Initialisation Odoo (modules, données de base)
   - Création utilisateur admin client
   - Configuration DNS/sous-domaine
   - Liaison avec la base maître

4. **Monitoring & Métriques**
   - Santé des bases clients (uptime, erreurs)
   - Métriques d'utilisation (users actifs, stockage, requêtes/min)
   - Alertes (quota dépassé, erreurs critiques)

5. **Facturation & Paiements**
   - Génération automatique des factures
   - Intégration Stripe/PayPal
   - Gestion des impayés
   - Upgrade/downgrade de plans

6. **Administration globale**
   - Vue d'ensemble de tous les clients
   - Opérations de maintenance (backup, restore, migration)
   - Logs centralisés
   - Analytics globaux

**Modules installés**:
- `onedesk_saas_manager` (nouveau module à créer)
- `account`, `sale`, `payment` (pour la facturation)
- `website` (portail client)
- Modules monitoring

**Utilisateurs**:
- **SuperAdmin OneDesk**: Nous (équipe OneDesk)
- **Opérateurs**: Support technique
- **Clients**: Accès portail pour voir leurs abonnements/factures

**Base de données**:
```sql
-- Tables principales
- saas_client (clients Premium)
- saas_subscription (abonnements)
- saas_plan (plans: Starter, Pro, Enterprise)
- saas_database (instances bases clients)
- saas_metric (métriques d'utilisation)
- saas_alert (alertes)
```

---

#### **Bases Clients: `onedesk_client_XXX`**

**Rôle**: Instance Odoo complète et **indépendante** pour chaque client Premium

**Responsabilités**:
1. **Données métier du client**
   - Properties, Units, Tenants
   - CRM, Ventes, Comptabilité
   - Website, Blog, eCommerce
   - Documents, Tâches, Calendrier

2. **Gestion des utilisateurs du client**
   - Admin client = `base.group_system` complet
   - Utilisateurs du client (employés, managers)
   - Portail (tenants, propriétaires)

3. **Customisation totale**
   - Installation de modules spécifiques
   - Code personnalisé
   - Thèmes/templates website personnalisés
   - Intégrations tierces

**Modules installés**:
- `onedesk_core` (version client, sans le SaaS manager)
- Tous les modules standard Odoo choisis par le client
- Modules custom du client

**Utilisateurs**:
- **Admin Client**: Le client Premium (admin système total)
- **Property Managers**: Employés du client
- **Users**: Autres rôles définis par le client
- **Portal**: Tenants, propriétaires (accès portail)

**Isolation**:
- ✅ Base PostgreSQL séparée
- ✅ Schéma de données indépendant
- ✅ Modules indépendants
- ✅ Code Python indépendant
- ✅ Stockage fichiers séparé (`/filestore/onedesk_client_XXX/`)

**Accès**:
- Via sous-domaine: `https://clienta.onedesk.com`
- Ou via dbfilter: `https://app.onedesk.com?db=onedesk_client_1`

---

### Schéma d'architecture détaillé

```
┌────────────────────────────────────────────────────────────────┐
│                        INTERNET / CLIENTS                      │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    NGINX REVERSE PROXY                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Routing par sous-domaine (dbfilter dynamique):          │  │
│  │  - app.onedesk.com       → onedesk_core (base maître)    │  │
│  │  - clienta.onedesk.com   → onedesk_client_1              │  │
│  │  - clientb.onedesk.com   → onedesk_client_2              │  │
│  │  - clientc.onedesk.com   → onedesk_client_3              │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    ODOO APPLICATION SERVER                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Configuration:                                          │  │
│  │  - dbfilter = %d (dynamique selon Host header)          │  │
│  │  - list_db = False (sécurité)                           │  │
│  │  - workers = 8-16 (selon CPU)                           │  │
│  │  - max_cron_threads = 2                                 │  │
│  │  - limit_time_cpu = 300 (5 min max)                     │  │
│  │  - limit_time_real = 600 (10 min max)                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    PGBOUNCER (Connection Pooling)              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Configuration:                                          │  │
│  │  - pool_mode = transaction                              │  │
│  │  - max_client_conn = 1000                               │  │
│  │  - default_pool_size = 25 par base                      │  │
│  │  - reserve_pool_size = 5 par base                       │  │
│  │  - max_db_connections = 100 (limite PostgreSQL)         │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│              POSTGRESQL CLUSTER (Single Server)                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Bases:                                                  │  │
│  │  - postgres (base système PostgreSQL)                   │  │
│  │  - onedesk_core (base maître)                           │  │
│  │  - onedesk_client_1 (Client A)                          │  │
│  │  - onedesk_client_2 (Client B)                          │  │
│  │  - onedesk_client_3 (Client C)                          │  │
│  │  - ...                                                   │  │
│  │  - onedesk_client_N (Client N)                          │  │
│  │                                                          │  │
│  │  Configuration:                                          │  │
│  │  - max_connections = 200                                │  │
│  │  - shared_buffers = 4GB (25% RAM)                       │  │
│  │  - effective_cache_size = 12GB (75% RAM)                │  │
│  │  - work_mem = 50MB                                      │  │
│  │  - maintenance_work_mem = 1GB                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    STOCKAGE FICHIERS                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  /opt/odoo/filestore/                                    │  │
│  │  ├─ onedesk_core/              (base maître)            │  │
│  │  ├─ onedesk_client_1/          (Client A)               │  │
│  │  ├─ onedesk_client_2/          (Client B)               │  │
│  │  ├─ onedesk_client_3/          (Client C)               │  │
│  │  └─ onedesk_client_N/          (Client N)               │  │
│  │                                                          │  │
│  │  Alternative: S3-compatible storage (Minio, AWS S3)     │  │
│  │  - Bucket par client: onedesk-client-1, onedesk-client-2│  │
│  │  - Isolation totale                                     │  │
│  │  - Backup automatique                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Provisioning Automatique d'un Nouveau Client

### Vue d'ensemble du processus

```
┌─────────────────────────────────────────────────────────────────┐
│  TRIGGER: Création d'un client Premium dans onedesk_core       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │  1. VALIDATION DES DONNÉES             │
        │  - Nom client unique                   │
        │  - Email valide                        │
        │  - Plan choisi (Starter/Pro/Enterprise)│
        │  - Génération db_name unique           │
        └────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │  2. CRÉATION BASE POSTGRESQL           │
        │  - CREATE DATABASE onedesk_client_XXX  │
        │  - Owner: odoo (user PostgreSQL)       │
        │  - Encoding: UTF8                      │
        │  - Collation: fr_FR.UTF-8 ou en_US.UTF8│
        └────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │  3. INITIALISATION ODOO                │
        │  - odoo-bin -d onedesk_client_XXX      │
        │    --init=base,web,onedesk_core,...    │
        │  - Installation modules de base        │
        │  - Création données démo (optionnel)   │
        │  - Configuration initiale              │
        └────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │  4. CRÉATION UTILISATEUR ADMIN CLIENT  │
        │  - Login: email du client              │
        │  - Password: généré aléatoirement      │
        │  - Groupe: base.group_system (ADMIN)   │
        │  - Email de bienvenue avec credentials │
        └────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │  5. CONFIGURATION COMPANY              │
        │  - Renommer company par défaut         │
        │  - Logo client                         │
        │  - Informations fiscales               │
        │  - Devise, langue, timezone            │
        └────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │  6. LIAISON AVEC BASE MAÎTRE           │
        │  - Enregistrement dans saas_database   │
        │  - État: active                        │
        │  - Quotas initiaux (selon plan)        │
        │  - Métriques à 0                       │
        └────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │  7. CONFIGURATION DNS / SOUS-DOMAINE   │
        │  - Ajout enregistrement DNS:           │
        │    clientname.onedesk.com → Server IP  │
        │  - Ou: configuration dbfilter dynamique│
        │  - Certificat SSL (Let's Encrypt)      │
        └────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │  8. TESTS POST-PROVISIONING            │
        │  - Connexion à la base OK              │
        │  - Login admin client OK               │
        │  - Modules chargés OK                  │
        │  - Website accessible OK               │
        └────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │  9. NOTIFICATION CLIENT                │
        │  - Email de bienvenue                  │
        │  - Lien d'accès: clientname.onedesk.com│
        │  - Credentials admin                   │
        │  - Guide de démarrage                  │
        └────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │  ✅ CLIENT OPÉRATIONNEL                │
        │  Base créée, accessible, admin connecté│
        └────────────────────────────────────────┘
```

### Code de provisioning (Python)

**Fichier**: `models/saas_client.py` (dans module `onedesk_saas_manager`)

```python
import secrets
import string
import psycopg2
from odoo import models, fields, api
from odoo.exceptions import UserError

class SaasClient(models.Model):
    _name = 'saas.client'
    _description = 'Client SaaS Premium'

    name = fields.Char('Nom Client', required=True)
    email = fields.Char('Email Admin', required=True)
    company_name = fields.Char('Nom Société', required=True)

    # Base de données
    database_name = fields.Char('Nom Base de Données', readonly=True)
    database_state = fields.Selection([
        ('draft', 'Brouillon'),
        ('provisioning', 'En cours de création'),
        ('active', 'Active'),
        ('suspended', 'Suspendue'),
        ('terminated', 'Terminée'),
    ], default='draft', required=True)

    # Abonnement
    plan_id = fields.Many2one('saas.plan', 'Plan', required=True)
    subscription_state = fields.Selection([
        ('trial', 'Essai gratuit'),
        ('active', 'Actif'),
        ('past_due', 'Impayé'),
        ('cancelled', 'Résilié'),
    ], default='trial', required=True)

    # Credentials admin client
    admin_login = fields.Char('Login Admin', readonly=True)
    admin_password_temp = fields.Char('Mot de passe temporaire', readonly=True)

    # Accès
    subdomain = fields.Char('Sous-domaine', required=True)
    url = fields.Char('URL d\'accès', compute='_compute_url', store=True)

    # Dates
    created_date = fields.Datetime('Date création', default=fields.Datetime.now)
    trial_end_date = fields.Date('Fin période d\'essai')

    # Métriques
    nb_users = fields.Integer('Nombre d\'utilisateurs', default=0)
    storage_used = fields.Float('Stockage utilisé (GB)', default=0)
    last_login = fields.Datetime('Dernière connexion')

    @api.depends('subdomain')
    def _compute_url(self):
        for rec in self:
            rec.url = f'https://{rec.subdomain}.onedesk.com' if rec.subdomain else False

    @api.model
    def create(self, vals):
        # Génération nom de base unique
        if not vals.get('database_name'):
            vals['database_name'] = self._generate_database_name(vals.get('name', 'client'))

        # Génération subdomain si manquant
        if not vals.get('subdomain'):
            vals['subdomain'] = self._slugify(vals.get('name', 'client'))

        client = super().create(vals)

        # Lancement provisioning automatique
        client._provision_client_database()

        return client

    def _generate_database_name(self, client_name):
        """Génère un nom de base unique: onedesk_client_XXX"""
        slug = self._slugify(client_name)
        # Trouver un ID unique
        existing_count = self.search_count([])
        db_name = f'onedesk_client_{existing_count + 1}_{slug}'
        return db_name[:63]  # Limite PostgreSQL

    def _slugify(self, text):
        """Convertit texte en slug (URL-safe)"""
        import re
        text = text.lower()
        text = re.sub(r'[^a-z0-9]+', '_', text)
        return text.strip('_')

    def _provision_client_database(self):
        """Provisioning complet de la base client"""
        self.ensure_one()

        if self.database_state != 'draft':
            raise UserError("Le provisioning a déjà été lancé pour ce client")

        try:
            # État: provisioning
            self.write({'database_state': 'provisioning'})

            # 1. Créer la base PostgreSQL
            self._create_postgresql_database()

            # 2. Initialiser Odoo
            self._initialize_odoo_database()

            # 3. Créer l'admin client
            admin_password = self._create_client_admin()

            # 4. Configurer la company
            self._configure_client_company()

            # 5. Enregistrer dans saas_database
            self._register_database()

            # 6. Envoyer email bienvenue
            self._send_welcome_email(admin_password)

            # État: active
            self.write({
                'database_state': 'active',
                'subscription_state': 'trial',
            })

        except Exception as e:
            self.write({'database_state': 'draft'})
            raise UserError(f"Erreur lors du provisioning: {str(e)}")

    def _create_postgresql_database(self):
        """Crée la base PostgreSQL"""
        self.ensure_one()

        # Connexion à PostgreSQL en tant que superuser
        conn = psycopg2.connect(
            host=self.env['ir.config_parameter'].sudo().get_param('db_host', 'localhost'),
            port=self.env['ir.config_parameter'].sudo().get_param('db_port', '5432'),
            user=self.env['ir.config_parameter'].sudo().get_param('db_user', 'odoo'),
            password=self.env['ir.config_parameter'].sudo().get_param('db_password'),
            database='postgres',
        )
        conn.autocommit = True
        cursor = conn.cursor()

        try:
            # Vérifier si la base existe déjà
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (self.database_name,)
            )
            if cursor.fetchone():
                raise UserError(f"La base {self.database_name} existe déjà")

            # Créer la base
            cursor.execute(f'CREATE DATABASE "{self.database_name}" ENCODING \'UTF8\'')

        finally:
            cursor.close()
            conn.close()

    def _initialize_odoo_database(self):
        """Initialise la base Odoo avec les modules de base"""
        self.ensure_one()

        import odoo
        from odoo.modules.registry import Registry

        # Modules à installer
        modules_to_install = [
            'base',
            'web',
            'mail',
            'contacts',
            'account',
            'sale',
            'crm',
            'website',
            'onedesk_core',  # Notre module (version client)
        ]

        # Initialisation de la base
        odoo.service.db.exp_create_database(
            self.database_name,
            demo=False,  # Pas de données démo
            lang='fr_FR',
            user_password='admin_temp_password',
            login='admin',
            country_code='FR',
        )

        # Installation des modules
        registry = Registry.new(self.database_name, update_module=True)
        with registry.cursor() as cr:
            env = api.Environment(cr, odoo.SUPERUSER_ID, {})

            # Installer les modules
            modules = env['ir.module.module'].search([
                ('name', 'in', modules_to_install),
                ('state', '=', 'uninstalled'),
            ])
            if modules:
                modules.button_immediate_install()

    def _create_client_admin(self):
        """Crée l'utilisateur admin client et retourne le password"""
        self.ensure_one()

        import odoo
        from odoo.modules.registry import Registry

        # Générer un mot de passe sécurisé
        alphabet = string.ascii_letters + string.digits
        admin_password = ''.join(secrets.choice(alphabet) for i in range(16))

        # Créer l'utilisateur dans la base client
        registry = Registry(self.database_name)
        with registry.cursor() as cr:
            env = api.Environment(cr, odoo.SUPERUSER_ID, {})

            # Rechercher ou créer l'utilisateur admin
            admin_user = env['res.users'].search([('login', '=', self.email)], limit=1)

            if admin_user:
                # Mettre à jour le mot de passe
                admin_user.write({'password': admin_password})
            else:
                # Créer nouvel admin
                admin_user = env['res.users'].create({
                    'name': self.name,
                    'login': self.email,
                    'email': self.email,
                    'password': admin_password,
                    'groups_id': [(6, 0, [
                        env.ref('base.group_system').id,
                        env.ref('base.group_erp_manager').id,
                    ])],
                })

            cr.commit()

        # Sauvegarder les credentials (temporairement)
        self.write({
            'admin_login': self.email,
            'admin_password_temp': admin_password,
        })

        return admin_password

    def _configure_client_company(self):
        """Configure la company par défaut de la base client"""
        self.ensure_one()

        import odoo
        from odoo.modules.registry import Registry

        registry = Registry(self.database_name)
        with registry.cursor() as cr:
            env = api.Environment(cr, odoo.SUPERUSER_ID, {})

            # Récupérer la company principale
            main_company = env['res.company'].search([], limit=1)

            if main_company:
                main_company.write({
                    'name': self.company_name,
                    'email': self.email,
                })

            cr.commit()

    def _register_database(self):
        """Enregistre la base dans saas.database"""
        self.ensure_one()

        self.env['saas.database'].create({
            'client_id': self.id,
            'name': self.database_name,
            'state': 'active',
            'plan_id': self.plan_id.id,
        })

    def _send_welcome_email(self, admin_password):
        """Envoie l'email de bienvenue avec les credentials"""
        self.ensure_one()

        template = self.env.ref('onedesk_saas_manager.email_template_client_welcome')
        template.with_context({
            'client_name': self.name,
            'url': self.url,
            'login': self.admin_login,
            'password': admin_password,
        }).send_mail(self.id, force_send=True)
```

---

## 🔐 Gestion des Accès

### 1. Configuration dbfilter dynamique

**Fichier**: `/etc/odoo/odoo.conf`

```ini
[options]
# Database filtering dynamique par sous-domaine
dbfilter = %d

# Empêcher le listing des bases (sécurité)
list_db = False

# Proxy mode (pour récupérer le bon Host header)
proxy_mode = True
```

**Comment ça marche**:

```
Requête: https://clienta.onedesk.com/web/login
         ↓
Host header: clienta.onedesk.com
         ↓
dbfilter=%d remplace %d par le premier segment: "clienta"
         ↓
Odoo cherche une base nommée "clienta" → NOT FOUND
```

**PROBLÈME**: Le sous-domaine ne correspond pas au nom de base (`onedesk_client_1`)

**SOLUTION**: Mapping personnalisé via module Python

**Fichier**: `models/ir_http.py` (dans `onedesk_saas_manager`)

```python
from odoo import models
from odoo.http import request

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_db_from_request(cls, httprequest):
        """Override pour mapper sous-domaine → nom de base"""

        # Récupérer le Host header
        host = httprequest.environ.get('HTTP_HOST', '').split(':')[0]

        # Extraire le sous-domaine
        # Exemple: clienta.onedesk.com → clienta
        parts = host.split('.')
        if len(parts) >= 3:
            subdomain = parts[0]

            # Mapping subdomain → database_name
            # Option 1: Chercher dans Redis/Memcached (cache)
            # Option 2: Chercher dans PostgreSQL (base maître)

            # Pour cet exemple, on utilise PostgreSQL
            import psycopg2
            conn = psycopg2.connect(
                host='localhost',
                port='5432',
                user='odoo',
                password='odoo_password',
                database='onedesk_core',
            )
            cursor = conn.cursor()

            try:
                cursor.execute(
                    "SELECT database_name FROM saas_client WHERE subdomain = %s AND database_state = 'active'",
                    (subdomain,)
                )
                result = cursor.fetchone()

                if result:
                    return result[0]  # database_name

            finally:
                cursor.close()
                conn.close()

        # Fallback sur le comportement par défaut
        return super()._get_db_from_request(httprequest)
```

**Alternative plus performante: Redis Cache**

```python
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Lors du provisioning, créer le mapping dans Redis
redis_client.set(f'subdomain:{subdomain}', database_name)

# Dans _get_db_from_request:
database_name = redis_client.get(f'subdomain:{subdomain}')
if database_name:
    return database_name.decode('utf-8')
```

---

### 2. Configuration NGINX

**Fichier**: `/etc/nginx/sites-available/onedesk-saas`

```nginx
# Upstream Odoo
upstream odoo {
    server 127.0.0.1:8069;
}

# Upstream Odoo Longpolling
upstream odoochat {
    server 127.0.0.1:8072;
}

# Redirect HTTP → HTTPS
server {
    listen 80;
    server_name *.onedesk.com onedesk.com;
    return 301 https://$host$request_uri;
}

# HTTPS - Wildcard pour tous les sous-domaines
server {
    listen 443 ssl http2;
    server_name *.onedesk.com onedesk.com;

    # SSL Configuration (Let's Encrypt wildcard)
    ssl_certificate /etc/letsencrypt/live/onedesk.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/onedesk.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Headers de sécurité
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logs par sous-domaine
    access_log /var/log/nginx/onedesk-access.log;
    error_log /var/log/nginx/onedesk-error.log;

    # Client body size (uploads)
    client_max_body_size 100M;

    # Proxy settings
    proxy_read_timeout 720s;
    proxy_connect_timeout 720s;
    proxy_send_timeout 720s;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Gzip compression
    gzip on;
    gzip_types text/css text/plain text/xml application/xml application/json application/javascript;

    # Static files
    location ~* /web/static/ {
        proxy_cache_valid 200 90m;
        proxy_buffering on;
        expires 864000;
        proxy_pass http://odoo;
    }

    # Longpolling
    location /longpolling {
        proxy_pass http://odoochat;
    }

    # Main Odoo
    location / {
        proxy_redirect off;
        proxy_pass http://odoo;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "OK\n";
        add_header Content-Type text/plain;
    }
}
```

**Obtenir certificat SSL wildcard (Let's Encrypt)**:

```bash
# Installation certbot avec DNS challenge
sudo apt-get install certbot python3-certbot-dns-cloudflare

# Configuration Cloudflare (si DNS sur Cloudflare)
cat > /root/.secrets/cloudflare.ini <<EOF
dns_cloudflare_api_token = YOUR_CLOUDFLARE_API_TOKEN
EOF

chmod 600 /root/.secrets/cloudflare.ini

# Obtenir certificat wildcard
sudo certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials /root/.secrets/cloudflare.ini \
  -d onedesk.com \
  -d *.onedesk.com

# Renouvellement automatique
sudo certbot renew --dry-run
```

---

### 3. Sécurisation PostgreSQL

**Fichier**: `/etc/postgresql/14/main/pg_hba.conf`

```conf
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# Local connections
local   all             postgres                                peer
local   all             odoo                                    md5

# Host connections (from Odoo server)
host    all             odoo            127.0.0.1/32            md5
host    all             odoo            ::1/128                 md5

# Deny all other connections
host    all             all             0.0.0.0/0               reject
```

**Permissions PostgreSQL**:

```sql
-- Créer utilisateur Odoo (si pas déjà fait)
CREATE USER odoo WITH PASSWORD 'strong_secure_password';

-- Permissions pour créer des bases
ALTER USER odoo CREATEDB;

-- Par défaut, odoo est propriétaire de toutes les bases onedesk_*
-- Chaque base est isolée (odoo ne peut accéder qu'aux bases dont il est owner)

-- Pour sécuriser davantage: créer un user par base client (optionnel, complexe)
-- CREATE USER client_1 WITH PASSWORD 'random_password';
-- GRANT ALL PRIVILEGES ON DATABASE onedesk_client_1 TO client_1;
```

**Configuration PostgreSQL** (`/etc/postgresql/14/main/postgresql.conf`):

```conf
# Connexions
max_connections = 200

# Mémoire
shared_buffers = 4GB                    # 25% RAM
effective_cache_size = 12GB             # 75% RAM
maintenance_work_mem = 1GB
work_mem = 50MB

# WAL
wal_buffers = 16MB
checkpoint_completion_target = 0.9
max_wal_size = 2GB
min_wal_size = 1GB

# Logs
logging_collector = on
log_directory = 'pg_log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_min_duration_statement = 1000       # Log queries > 1s

# Performance
random_page_cost = 1.1                  # SSD
effective_io_concurrency = 200

# Autovacuum
autovacuum = on
autovacuum_max_workers = 4
autovacuum_naptime = 10min
```

---

### 4. Configuration PgBouncer

**Fichier**: `/etc/pgbouncer/pgbouncer.ini`

```ini
[databases]
; Wildcard pour toutes les bases
* = host=127.0.0.1 port=5432 dbname=onedesk_core

[pgbouncer]
; Listening
listen_addr = 127.0.0.1
listen_port = 6432

; Authentication
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

; Pooling
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
reserve_pool_size = 5
max_db_connections = 100
max_user_connections = 100

; Timeouts
server_idle_timeout = 600
server_lifetime = 3600
server_connect_timeout = 15
query_timeout = 0

; Logs
log_connections = 1
log_disconnections = 1
log_pooler_errors = 1
```

**Fichier**: `/etc/pgbouncer/userlist.txt`

```
"odoo" "md5_hash_of_password"
```

**Générer le hash**:

```bash
echo -n "passwordodoo" | md5sum | awk '{print "md5"$1}'
```

**Odoo configuration** (`/etc/odoo/odoo.conf`):

```ini
[options]
db_host = 127.0.0.1
db_port = 6432  # PgBouncer port (instead of 5432)
db_user = odoo
db_password = odoo_password
```

---

## 📦 Migration depuis l'Existant (Multi-Company → Multi-Database)

### Vue d'ensemble du processus

```
┌────────────────────────────────────────────────────────────────┐
│  BASE ACTUELLE: onedesk_production (Multi-Company)             │
│  ├─ Company A (ID=1) → 50 users, 10000 contacts, 5000 invoices│
│  ├─ Company B (ID=2) → 30 users, 5000 contacts, 3000 invoices │
│  └─ Company C (ID=3) → 20 users, 3000 contacts, 2000 invoices │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │  MIGRATION SCRIPT                      │
        │  extract_company_to_database.py        │
        └────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  BASES CIBLES (Multi-Database)                                 │
│  ├─ onedesk_client_1 (Company A)                               │
│  ├─ onedesk_client_2 (Company B)                               │
│  └─ onedesk_client_3 (Company C)                               │
└────────────────────────────────────────────────────────────────┘
```

### Étapes de migration

#### **Étape 1: Analyse et préparation**

```python
# Script: migration/analyze_companies.py

import psycopg2

def analyze_company(company_id):
    """Analyse une company pour estimer la taille de la migration"""

    conn = psycopg2.connect(database='onedesk_production')
    cursor = conn.cursor()

    stats = {}

    # Tables à analyser
    tables = [
        ('res_users', 'company_id'),
        ('res_partner', 'company_id'),
        ('account_move', 'company_id'),
        ('sale_order', 'company_id'),
        ('crm_lead', 'company_id'),
        ('onedesk_property', 'company_id'),
        ('onedesk_unit', 'company_id'),
        ('onedesk_tenant', 'company_id'),
    ]

    for table, company_field in tables:
        cursor.execute(f'''
            SELECT COUNT(*)
            FROM {table}
            WHERE {company_field} = %s OR {company_field} IS NULL
        ''', (company_id,))

        stats[table] = cursor.fetchone()[0]

    # Estimer la taille
    cursor.execute('''
        SELECT pg_size_pretty(SUM(pg_total_relation_size(quote_ident(schemaname) || '.' || quote_ident(tablename))))
        FROM pg_tables
        WHERE schemaname = 'public'
    ''')

    stats['total_size'] = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return stats

# Exemple d'utilisation
stats = analyze_company(company_id=1)
print(f"Users: {stats['res_users']}")
print(f"Partners: {stats['res_partner']}")
print(f"Invoices: {stats['account_move']}")
print(f"Taille estimée: {stats['total_size']}")
```

#### **Étape 2: Extraction d'une company**

**Script**: `migration/extract_company.py`

```python
#!/usr/bin/env python3
"""
Script de migration: Extrait une company d'une base multi-company
et la transforme en base dédiée
"""

import argparse
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def extract_company_to_database(source_db, company_id, target_db):
    """
    Extrait une company de source_db et crée une nouvelle base target_db

    Args:
        source_db: Nom de la base source (ex: onedesk_production)
        company_id: ID de la company à extraire
        target_db: Nom de la nouvelle base (ex: onedesk_client_1)
    """

    print(f"🔄 Migration de Company {company_id} de {source_db} vers {target_db}")

    # Étape 1: Créer la base cible
    print("📦 Étape 1/6: Création de la base cible...")
    create_target_database(target_db)

    # Étape 2: Copier le schéma complet
    print("📐 Étape 2/6: Copie du schéma (structure des tables)...")
    copy_database_schema(source_db, target_db)

    # Étape 3: Copier les données système (users, groups, etc.)
    print("👥 Étape 3/6: Copie des données système...")
    copy_system_data(source_db, target_db)

    # Étape 4: Copier les données de la company
    print("📊 Étape 4/6: Copie des données de la company...")
    copy_company_data(source_db, target_db, company_id)

    # Étape 5: Nettoyer et transformer
    print("🧹 Étape 5/6: Nettoyage et transformation...")
    cleanup_and_transform(target_db, company_id)

    # Étape 6: Vérifications finales
    print("✅ Étape 6/6: Vérifications finales...")
    verify_migration(target_db, company_id)

    print(f"✅ Migration terminée! Base {target_db} opérationnelle.")


def create_target_database(target_db):
    """Crée la base PostgreSQL cible"""
    conn = psycopg2.connect(database='postgres', user='odoo')
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    # Vérifier si existe déjà
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
    if cursor.fetchone():
        raise Exception(f"La base {target_db} existe déjà!")

    # Créer la base
    cursor.execute(f'CREATE DATABASE "{target_db}" ENCODING \'UTF8\' TEMPLATE template0')

    cursor.close()
    conn.close()


def copy_database_schema(source_db, target_db):
    """Copie le schéma complet (structure) de source vers target"""
    import subprocess

    # Dump du schéma uniquement (--schema-only)
    dump_cmd = f'pg_dump -U odoo -d {source_db} --schema-only --no-owner --no-privileges -f /tmp/schema.sql'
    subprocess.run(dump_cmd, shell=True, check=True)

    # Restaurer le schéma
    restore_cmd = f'psql -U odoo -d {target_db} -f /tmp/schema.sql'
    subprocess.run(restore_cmd, shell=True, check=True)


def copy_system_data(source_db, target_db):
    """Copie les données système (indépendantes de la company)"""

    # Tables système à copier intégralement
    system_tables = [
        'ir_module_module',
        'ir_module_module_dependency',
        'ir_model',
        'ir_model_fields',
        'ir_model_access',
        'ir_rule',
        'ir_ui_view',
        'ir_ui_menu',
        'ir_actions_*',
        'res_groups',
        'res_country',
        'res_country_state',
        'res_currency',
        'res_lang',
    ]

    source_conn = psycopg2.connect(database=source_db)
    target_conn = psycopg2.connect(database=target_db)

    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()

    for table in system_tables:
        print(f"  Copie {table}...")

        # Copier les données
        source_cursor.execute(f"SELECT * FROM {table}")
        rows = source_cursor.fetchall()

        if rows:
            # Obtenir les colonnes
            colnames = [desc[0] for desc in source_cursor.description]
            cols = ', '.join(colnames)
            placeholders = ', '.join(['%s'] * len(colnames))

            # Insérer dans la cible
            insert_query = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
            target_cursor.executemany(insert_query, rows)

    target_conn.commit()
    source_cursor.close()
    target_cursor.close()
    source_conn.close()
    target_conn.close()


def copy_company_data(source_db, target_db, company_id):
    """Copie les données de la company spécifique"""

    # Tables avec company_id à filtrer
    company_tables = [
        'res_users',
        'res_partner',
        'res_company',
        'account_move',
        'account_payment',
        'account_journal',
        'sale_order',
        'sale_order_line',
        'crm_lead',
        'product_template',
        'product_product',
        'website_website',
        'website_page',
        'website_menu',
        'onedesk_property',
        'onedesk_unit',
        'onedesk_tenant',
        'onedesk_lease',
        'onedesk_maintenance_request',
        'onedesk_document',
    ]

    source_conn = psycopg2.connect(database=source_db)
    target_conn = psycopg2.connect(database=target_db)

    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()

    for table in company_tables:
        print(f"  Copie {table} (company_id={company_id})...")

        # Copier les données de cette company
        source_cursor.execute(f'''
            SELECT * FROM {table}
            WHERE company_id = %s OR company_id IS NULL
        ''', (company_id,))

        rows = source_cursor.fetchall()

        if rows:
            colnames = [desc[0] for desc in source_cursor.description]
            cols = ', '.join(colnames)
            placeholders = ', '.join(['%s'] * len(colnames))

            insert_query = f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            target_cursor.executemany(insert_query, rows)

    target_conn.commit()
    source_cursor.close()
    target_cursor.close()
    source_conn.close()
    target_conn.close()


def cleanup_and_transform(target_db, company_id):
    """Nettoie et transforme la base cible"""

    conn = psycopg2.connect(database=target_db)
    cursor = conn.cursor()

    # 1. Faire de la company extraite LA company principale (ID=1)
    print("  Transformation de la company en company principale...")

    cursor.execute("SELECT id FROM res_company WHERE id = %s", (company_id,))
    if cursor.fetchone():
        # Si company_id != 1, remapper tout
        if company_id != 1:
            # Supprimer l'ancienne company ID=1 si elle existe
            cursor.execute("DELETE FROM res_company WHERE id = 1")

            # Remapper la company vers ID=1
            cursor.execute("UPDATE res_company SET id = 1 WHERE id = %s", (company_id,))

            # Remapper toutes les références company_id
            company_tables = [
                'res_users', 'res_partner', 'account_move', 'account_payment',
                'sale_order', 'crm_lead', 'onedesk_property', 'onedesk_unit',
                'onedesk_tenant', 'onedesk_lease',
            ]

            for table in company_tables:
                cursor.execute(f"UPDATE {table} SET company_id = 1 WHERE company_id = %s", (company_id,))

    # 2. Supprimer les autres companies
    print("  Suppression des autres companies...")
    cursor.execute("DELETE FROM res_company WHERE id != 1")

    # 3. Nettoyer les record rules multi-tenant (plus nécessaires)
    print("  Suppression des record rules multi-tenant...")
    cursor.execute("""
        DELETE FROM ir_rule
        WHERE name LIKE '%Premium Manager%'
           OR name LIKE '%Multi-tenant%'
           OR name LIKE '%Own Company%'
    """)

    # 4. Mettre tous les company_id à NULL ou à 1 (selon le contexte)
    print("  Normalisation des company_id...")
    # Pour les partners système, mettre à NULL
    cursor.execute("""
        UPDATE res_partner SET company_id = NULL
        WHERE name IN ('Administrator', 'OdooBot', 'Public user', 'Portal')
    """)

    # 5. Réinitialiser les séquences
    print("  Réinitialisation des séquences...")
    cursor.execute("""
        SELECT setval(pg_get_serial_sequence('account_move', 'id'), COALESCE(MAX(id), 1))
        FROM account_move
    """)

    conn.commit()
    cursor.close()
    conn.close()


def verify_migration(target_db, company_id):
    """Vérifie que la migration s'est bien passée"""

    conn = psycopg2.connect(database=target_db)
    cursor = conn.cursor()

    checks = []

    # Vérifier qu'il n'y a qu'une seule company
    cursor.execute("SELECT COUNT(*) FROM res_company")
    company_count = cursor.fetchone()[0]
    checks.append(('Une seule company', company_count == 1))

    # Vérifier que la company principale a l'ID 1
    cursor.execute("SELECT id FROM res_company LIMIT 1")
    main_company_id = cursor.fetchone()[0]
    checks.append(('Company principale = ID 1', main_company_id == 1))

    # Vérifier qu'il y a au moins un utilisateur
    cursor.execute("SELECT COUNT(*) FROM res_users WHERE active = True")
    user_count = cursor.fetchone()[0]
    checks.append(('Utilisateurs actifs > 0', user_count > 0))

    # Vérifier qu'il y a des données métier
    cursor.execute("SELECT COUNT(*) FROM res_partner WHERE company_id = 1")
    partner_count = cursor.fetchone()[0]
    checks.append(('Partners de la company', partner_count > 0))

    # Afficher les résultats
    print("\n  Résultats des vérifications:")
    for check_name, check_result in checks:
        status = "✅" if check_result else "❌"
        print(f"    {status} {check_name}")

    cursor.close()
    conn.close()

    # Lever une exception si une vérification a échoué
    if not all(result for _, result in checks):
        raise Exception("Certaines vérifications ont échoué!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extrait une company vers une base dédiée')
    parser.add_argument('--source-db', required=True, help='Base source (ex: onedesk_production)')
    parser.add_argument('--company-id', type=int, required=True, help='ID de la company à extraire')
    parser.add_argument('--target-db', required=True, help='Base cible (ex: onedesk_client_1)')

    args = parser.parse_args()

    extract_company_to_database(
        source_db=args.source_db,
        company_id=args.company_id,
        target_db=args.target_db
    )
```

**Utilisation**:

```bash
# Migrer Company ID=2 vers une base dédiée
python3 migration/extract_company.py \
    --source-db onedesk_production \
    --company-id 2 \
    --target-db onedesk_client_2

# Résultat:
# - Base onedesk_client_2 créée
# - Données de Company ID=2 copiées
# - Company remappée en ID=1
# - Record rules multi-tenant supprimées
# - Base prête à l'emploi
```

---

#### **Étape 3: Migration des utilisateurs**

Lors de la migration, les utilisateurs de la company sont copiés mais leurs mots de passe restent identiques. Il faut :

1. **Option A**: Forcer un reset de mot de passe
```python
# Dans la base cible
users = env['res.users'].search([('id', '!=', SUPERUSER_ID)])
for user in users:
    user.action_reset_password()  # Enverra un email de reset
```

2. **Option B**: Créer un nouvel admin et supprimer les anciens
```python
# Créer nouvel admin
new_admin = env['res.users'].create({
    'name': 'Admin Client',
    'login': 'admin@client.com',
    'password': 'temp_password_123',
    'groups_id': [(6, 0, [env.ref('base.group_system').id])],
})

# Désactiver les anciens utilisateurs (pour vérification)
old_users = env['res.users'].search([
    ('id', '!=', SUPERUSER_ID),
    ('id', '!=', new_admin.id),
])
old_users.write({'active': False})
```

---

## 🔧 Exploitation & Maintenance

### 1. Sauvegardes (Backup)

#### **Backup par base (sélectif)**

**Script**: `scripts/backup_client_database.sh`

```bash
#!/bin/bash
# Backup d'une base client spécifique

set -e

# Configuration
DB_NAME=$1
BACKUP_DIR="/var/backups/onedesk/clients"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Validation
if [ -z "$DB_NAME" ]; then
    echo "Usage: $0 <database_name>"
    exit 1
fi

# Créer le répertoire de backup
mkdir -p "$BACKUP_DIR/$DB_NAME"

# Backup PostgreSQL (format custom, compressé)
BACKUP_FILE="$BACKUP_DIR/$DB_NAME/${DB_NAME}_${TIMESTAMP}.dump"

echo "🔄 Backup de $DB_NAME en cours..."
pg_dump -U odoo -Fc -d "$DB_NAME" -f "$BACKUP_FILE"

# Backup du filestore
FILESTORE_SRC="/opt/odoo/filestore/$DB_NAME"
FILESTORE_BACKUP="$BACKUP_DIR/$DB_NAME/${DB_NAME}_filestore_${TIMESTAMP}.tar.gz"

if [ -d "$FILESTORE_SRC" ]; then
    echo "📁 Backup du filestore en cours..."
    tar -czf "$FILESTORE_BACKUP" -C "/opt/odoo/filestore" "$DB_NAME"
fi

# Nettoyer les anciens backups (> RETENTION_DAYS jours)
echo "🧹 Nettoyage des anciens backups (> $RETENTION_DAYS jours)..."
find "$BACKUP_DIR/$DB_NAME" -type f -name "*.dump" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR/$DB_NAME" -type f -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "✅ Backup terminé: $BACKUP_FILE"
echo "📊 Taille: $(du -h $BACKUP_FILE | cut -f1)"
```

**Backup automatique de toutes les bases clients**:

**Script**: `scripts/backup_all_clients.sh`

```bash
#!/bin/bash
# Backup de toutes les bases clients

# Récupérer la liste des bases clients depuis la base maître
DATABASES=$(psql -U odoo -d onedesk_core -t -c "
    SELECT database_name
    FROM saas_database
    WHERE state = 'active'
")

# Backup de chaque base
for DB in $DATABASES; do
    echo "🔄 Backup de $DB..."
    /opt/scripts/backup_client_database.sh "$DB"
done

echo "✅ Backup de toutes les bases terminé"
```

**Cron** (`/etc/cron.d/onedesk-backups`):

```cron
# Backup quotidien à 2h du matin
0 2 * * * root /opt/scripts/backup_all_clients.sh >> /var/log/onedesk/backup.log 2>&1
```

---

#### **Restauration d'une base**

**Script**: `scripts/restore_client_database.sh`

```bash
#!/bin/bash
# Restauration d'une base client

set -e

DB_NAME=$1
BACKUP_FILE=$2

if [ -z "$DB_NAME" ] || [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <database_name> <backup_file>"
    exit 1
fi

# Confirmation
read -p "⚠️  Restaurer $DB_NAME depuis $BACKUP_FILE ? (yes/no) " -r
if [[ ! $REPLY =~ ^yes$ ]]; then
    echo "Annulé"
    exit 1
fi

# Déconnecter tous les utilisateurs de la base
echo "🔌 Déconnexion des utilisateurs..."
psql -U odoo -d postgres -c "
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid()
"

# Supprimer la base existante
echo "🗑️  Suppression de la base existante..."
dropdb -U odoo "$DB_NAME"

# Créer une nouvelle base vide
echo "📦 Création de la nouvelle base..."
createdb -U odoo "$DB_NAME"

# Restaurer le dump
echo "📥 Restauration des données..."
pg_restore -U odoo -d "$DB_NAME" "$BACKUP_FILE"

# Restaurer le filestore (si existe)
FILESTORE_BACKUP="${BACKUP_FILE%.dump}_filestore.tar.gz"
if [ -f "$FILESTORE_BACKUP" ]; then
    echo "📁 Restauration du filestore..."
    rm -rf "/opt/odoo/filestore/$DB_NAME"
    tar -xzf "$FILESTORE_BACKUP" -C "/opt/odoo/filestore/"
fi

echo "✅ Restauration terminée!"
```

---

### 2. Mises à jour Odoo

#### **Mise à jour d'une base client**

**Script**: `scripts/upgrade_client_database.sh`

```bash
#!/bin/bash
# Mise à jour d'une base client (upgrade modules)

DB_NAME=$1

if [ -z "$DB_NAME" ]; then
    echo "Usage: $0 <database_name>"
    exit 1
fi

# Backup avant mise à jour
echo "🔄 Backup avant mise à jour..."
/opt/scripts/backup_client_database.sh "$DB_NAME"

# Mise à jour des modules
echo "📦 Mise à jour des modules..."
/opt/odoo/odoo-bin -d "$DB_NAME" -u all --stop-after-init

echo "✅ Mise à jour terminée"
```

#### **Mise à jour globale (toutes les bases)**

Attention: à faire progressivement, pas toutes en même temps!

```bash
#!/bin/bash
# Mise à jour progressive de toutes les bases clients

DATABASES=$(psql -U odoo -d onedesk_core -t -c "
    SELECT database_name
    FROM saas_database
    WHERE state = 'active'
    ORDER BY created_date DESC
")

for DB in $DATABASES; do
    echo "🔄 Mise à jour de $DB..."
    /opt/scripts/upgrade_client_database.sh "$DB"

    # Pause de 5 minutes entre chaque base
    echo "⏸️  Pause de 5 minutes..."
    sleep 300
done
```

---

### 3. Monitoring

#### **Métriques à surveiller**

**Modèle**: `saas.metric` (dans `onedesk_saas_manager`)

```python
class SaasMetric(models.Model):
    _name = 'saas.metric'
    _description = 'Métrique client SaaS'

    client_id = fields.Many2one('saas.client', 'Client', required=True, ondelete='cascade')
    database_id = fields.Many2one('saas.database', 'Base de données', required=True, ondelete='cascade')

    # Métriques
    metric_type = fields.Selection([
        ('users_active', 'Utilisateurs actifs'),
        ('storage_used', 'Stockage utilisé'),
        ('requests_per_minute', 'Requêtes/minute'),
        ('response_time_avg', 'Temps de réponse moyen'),
        ('errors_count', 'Nombre d\'erreurs'),
        ('cpu_usage', 'Usage CPU'),
        ('memory_usage', 'Usage mémoire'),
    ], required=True)

    value = fields.Float('Valeur', required=True)
    unit = fields.Char('Unité')  # GB, ms, %, etc.

    recorded_at = fields.Datetime('Enregistré le', default=fields.Datetime.now)
```

**Collecte des métriques** (Cron toutes les 5 minutes):

```python
def _collect_client_metrics(self):
    """Collecte les métriques pour tous les clients actifs"""

    active_databases = self.env['saas.database'].search([('state', '=', 'active')])

    for database in active_databases:
        # Connexion à la base client
        registry = Registry(database.name)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})

            # Métrique: Utilisateurs actifs
            active_users = env['res.users'].search_count([('active', '=', True)])
            self.env['saas.metric'].create({
                'client_id': database.client_id.id,
                'database_id': database.id,
                'metric_type': 'users_active',
                'value': active_users,
                'unit': 'users',
            })

            # Métrique: Stockage utilisé
            cr.execute("SELECT pg_database_size(current_database())")
            db_size_bytes = cr.fetchone()[0]
            db_size_gb = db_size_bytes / (1024**3)

            self.env['saas.metric'].create({
                'client_id': database.client_id.id,
                'database_id': database.id,
                'metric_type': 'storage_used',
                'value': db_size_gb,
                'unit': 'GB',
            })
```

---

#### **Dashboard de monitoring**

Vue pour afficher les métriques de tous les clients :

```xml
<record id="view_saas_dashboard" model="ir.ui.view">
    <field name="name">SaaS Dashboard</field>
    <field name="model">saas.client</field>
    <field name="arch" type="xml">
        <dashboard>
            <view type="graph"/>
            <group>
                <aggregate name="total_clients" field="id" group_operator="count"/>
                <aggregate name="total_users" field="nb_users" group_operator="sum"/>
                <aggregate name="total_storage" field="storage_used" group_operator="sum"/>
            </group>
            <view type="pivot"/>
        </dashboard>
    </field>
</record>
```

---

### 4. Alertes automatiques

**Modèle**: `saas.alert`

```python
class SaasAlert(models.Model):
    _name = 'saas.alert'
    _description = 'Alerte SaaS'

    client_id = fields.Many2one('saas.client', 'Client', required=True)
    alert_type = fields.Selection([
        ('quota_exceeded', 'Quota dépassé'),
        ('payment_failed', 'Paiement échoué'),
        ('high_error_rate', 'Taux d\'erreur élevé'),
        ('slow_response', 'Temps de réponse lent'),
        ('downtime', 'Indisponibilité'),
    ], required=True)

    severity = fields.Selection([
        ('info', 'Info'),
        ('warning', 'Avertissement'),
        ('critical', 'Critique'),
    ], required=True)

    message = fields.Text('Message', required=True)
    resolved = fields.Boolean('Résolu', default=False)

    created_at = fields.Datetime('Créé le', default=fields.Datetime.now)
    resolved_at = fields.Datetime('Résolu le')


def _check_quotas_and_alert(self):
    """Vérifie les quotas et crée des alertes si dépassement"""

    clients = self.env['saas.client'].search([('database_state', '=', 'active')])

    for client in clients:
        plan = client.plan_id

        # Vérifier les utilisateurs
        if client.nb_users > plan.max_users:
            self.env['saas.alert'].create({
                'client_id': client.id,
                'alert_type': 'quota_exceeded',
                'severity': 'warning',
                'message': f'Quota utilisateurs dépassé: {client.nb_users}/{plan.max_users}',
            })

        # Vérifier le stockage
        if client.storage_used > plan.max_storage_gb:
            self.env['saas.alert'].create({
                'client_id': client.id,
                'alert_type': 'quota_exceeded',
                'severity': 'critical',
                'message': f'Quota stockage dépassé: {client.storage_used:.2f}GB/{plan.max_storage_gb}GB',
            })
```

---

## 🎯 Bonnes Pratiques SaaS

### 1. Limites de connexions

**Par plan**:

| Plan | Max Users | Max Storage | Max API Calls/jour | Support |
|------|-----------|-------------|---------------------|---------|
| **Starter** | 5 | 10 GB | 10,000 | Email |
| **Pro** | 25 | 50 GB | 50,000 | Email + Chat |
| **Enterprise** | Illimité | 500 GB | 500,000 | Dédié 24/7 |

**Modèle**: `saas.plan`

```python
class SaasPlan(models.Model):
    _name = 'saas.plan'
    _description = 'Plan SaaS'

    name = fields.Char('Nom', required=True)  # Starter, Pro, Enterprise

    # Limites
    max_users = fields.Integer('Max utilisateurs', default=5)
    max_storage_gb = fields.Float('Max stockage (GB)', default=10)
    max_api_calls_per_day = fields.Integer('Max API calls/jour', default=10000)

    # Prix
    price_monthly = fields.Float('Prix mensuel (€)', required=True)
    price_yearly = fields.Float('Prix annuel (€)', required=True)

    # Features
    has_custom_domain = fields.Boolean('Domaine personnalisé', default=False)
    has_white_label = fields.Boolean('White label', default=False)
    has_api_access = fields.Boolean('Accès API', default=False)
    support_level = fields.Selection([
        ('email', 'Email'),
        ('chat', 'Email + Chat'),
        ('dedicated', 'Dédié 24/7'),
    ], default='email')
```

**Enforcement des limites**:

```python
@api.model
def create(self, vals):
    """Override create pour vérifier les quotas"""

    # Vérifier quota utilisateurs
    current_user_count = self.search_count([('active', '=', True)])
    max_users = self.env.company.saas_plan_id.max_users

    if current_user_count >= max_users:
        raise UserError(f'Quota utilisateurs atteint ({max_users}). Merci de upgrader votre plan.')

    return super().create(vals)
```

---

### 2. Isolation et sécurité

✅ **Base PostgreSQL séparée** = Isolation physique complète
✅ **Filestore séparé** = Pas de fuite de fichiers
✅ **Certificat SSL par sous-domaine** = HTTPS garanti
✅ **Password policies** = Complexité minimale
✅ **2FA optionnel** = Authentification à deux facteurs
✅ **Logs séparés** = Audit trail par client
✅ **Backup chiffré** = AES-256 encryption

---

### 3. Montée en charge (Scaling)

#### **Scaling Vertical** (augmenter les ressources du serveur)

```
Serveur actuel:
- 16 CPU cores
- 64 GB RAM
- 1 TB SSD

Serveur upgradé:
- 32 CPU cores
- 128 GB RAM
- 2 TB NVMe SSD
```

#### **Scaling Horizontal** (ajouter des serveurs)

```
┌─────────────────────────────────────────────────────────────┐
│                    LOAD BALANCER (HAProxy)                  │
└─────────────────────────────────────────────────────────────┘
              │                           │
              ▼                           ▼
┌──────────────────────┐      ┌──────────────────────┐
│  ODOO SERVER 1       │      │  ODOO SERVER 2       │
│  - Clients 1-50      │      │  - Clients 51-100    │
└──────────────────────┘      └──────────────────────┘
              │                           │
              ▼                           ▼
┌─────────────────────────────────────────────────────────────┐
│              POSTGRESQL PRIMARY (Read/Write)                │
│              - onedesk_core (master database)               │
│              - onedesk_client_1 ... onedesk_client_100      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              POSTGRESQL REPLICA (Read Only)                 │
│              - Backup temps réel                            │
│              - Reporting queries                            │
└─────────────────────────────────────────────────────────────┘
```

**Sharding** (si > 500 clients):

```
PostgreSQL Cluster 1: Clients 1-250 (onedesk_client_1 to onedesk_client_250)
PostgreSQL Cluster 2: Clients 251-500 (onedesk_client_251 to onedesk_client_500)
PostgreSQL Cluster 3: Clients 501-750 (onedesk_client_501 to onedesk_client_750)
```

---

### 4. Gestion Premium vs Standard

**Stratégie**:

| Type Client | Architecture | Raison |
|-------------|--------------|--------|
| **Standard** (Free/Basic) | Multi-company (base unique) | Coût faible, ressources partagées |
| **Premium** (Pro/Enterprise) | Multi-database (base dédiée) | Performance, isolation, customisation |

**Migration automatique** Standard → Premium:

```python
def upgrade_to_premium(self):
    """Migre un client Standard vers Premium (base dédiée)"""

    if self.client_type != 'standard':
        raise UserError('Ce client est déjà Premium')

    # Lancer la migration
    new_db_name = self._generate_database_name(self.name)

    # Utiliser le script d'extraction
    extract_company_to_database(
        source_db='onedesk_standard',  # Base multi-company
        company_id=self.company_id.id,
        target_db=new_db_name,
    )

    # Mettre à jour le client
    self.write({
        'client_type': 'premium',
        'database_name': new_db_name,
        'database_state': 'active',
    })
```

---

## 📋 Récapitulatif de l'Architecture

### Fichiers créés

```
addons/onedesk_saas_manager/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── saas_client.py              # Gestion clients Premium
│   ├── saas_plan.py                # Plans (Starter, Pro, Enterprise)
│   ├── saas_subscription.py        # Abonnements et facturation
│   ├── saas_database.py            # Instances bases clients
│   ├── saas_metric.py              # Métriques d'utilisation
│   ├── saas_alert.py               # Alertes
│   └── ir_http.py                  # Mapping subdomain → database
├── data/
│   ├── saas_plans.xml              # Données plans (Starter, Pro, etc.)
│   └── saas_cron.xml               # Tâches planifiées (métriques, backups)
├── security/
│   └── ir.model.access.csv
├── views/
│   ├── saas_client_views.xml
│   ├── saas_dashboard_views.xml
│   └── saas_menu.xml
└── templates/
    └── email_client_welcome.xml

scripts/
├── backup_client_database.sh       # Backup d'une base client
├── backup_all_clients.sh           # Backup de toutes les bases
├── restore_client_database.sh      # Restauration d'une base
└── upgrade_client_database.sh      # Mise à jour d'une base

migration/
├── analyze_companies.py            # Analyse taille migration
└── extract_company.py              # Migration multi-company → multi-database

docs/
├── PREMIUM_MANAGER_ARCHITECTURE.md # Architecture actuelle (multi-company)
└── SAAS_MULTIDATABASE_ARCHITECTURE.md # Architecture cible (multi-database)
```

---

## ✅ Plan de Déploiement en Production

### Phase 1: Préparation (Semaine 1-2)

- [ ] Créer le module `onedesk_saas_manager`
- [ ] Implémenter les modèles (client, plan, subscription, database, metric, alert)
- [ ] Créer les vues et menus
- [ ] Tester le provisioning automatique sur environnement de dev
- [ ] Créer les scripts de backup/restore
- [ ] Documenter les procédures

### Phase 2: Infrastructure (Semaine 3-4)

- [ ] Configurer NGINX avec wildcard SSL
- [ ] Configurer PgBouncer
- [ ] Optimiser PostgreSQL (shared_buffers, work_mem, etc.)
- [ ] Mettre en place monitoring (Prometheus, Grafana)
- [ ] Tester la charge (stress testing)

### Phase 3: Migration Progressive (Semaine 5-8)

- [ ] Migrer 1 client test (non-production)
- [ ] Valider la migration (données, accès, performance)
- [ ] Migrer 3-5 clients pilotes (avec accord client)
- [ ] Feedback et ajustements
- [ ] Migrer tous les clients Premium (par vagues de 10)

### Phase 4: Production (Semaine 9+)

- [ ] Nouveaux clients Premium → provisioning automatique
- [ ] Monitoring quotidien des métriques
- [ ] Backup automatique (quotidien)
- [ ] Support dédié pour clients Premium
- [ ] Amélioration continue

---

## 📞 Support & Contact

**Équipe OneDesk DevOps**: [devops@onedesk.com](mailto:devops@onedesk.com)
**Documentation**: https://docs.onedesk.com/saas-architecture
**Status Page**: https://status.onedesk.com

---

**Version**: 1.0.0
**Date**: 2025-12-18
**Auteur**: Claude AI (OneDesk SaaS Architect)
