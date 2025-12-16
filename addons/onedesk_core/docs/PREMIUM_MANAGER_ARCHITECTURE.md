# PREMIUM MANAGER - Architecture et Fonctionnalités

## 📋 Vue d'ensemble

Le **Premium Manager** est un rôle de sous-administrateur dans OneDesk qui donne un accès administratif complet à Odoo (CRM, Site web, Comptabilité, Paramètres, Contacts) tout en maintenant une **isolation multi-tenant stricte par company_id**.

### Principe clé
- ✅ **Accès admin complet** pour SA company (installation apps, configuration technique)
- 🔒 **Isolation stricte** : Ne voit QUE les données de SA company
- 🚫 **Aucune fuite** de données entre companies (multi-tenant SaaS)

---

## 📁 Fichiers du Système Premium Manager

### 1. Définition du Groupe
**Fichier**: `data/onedesk_groups.xml`

**Fonctionnalité**: Définit le groupe Premium Manager et ses permissions héritées

**Code clé**:
```xml
<record id="group_onedesk_premium_manager" model="res.groups">
    <field name="name">OneDesk / Premium Manager</field>
    <field name="implied_ids" eval="[(4, ref('group_onedesk_property_manager')),
                                      (4, ref('base.group_system')),
                                      (4, ref('base.group_erp_manager')),
                                      (4, ref('sales_team.group_sale_manager')),
                                      (4, ref('website.group_website_designer')),
                                      (4, ref('account.group_account_manager')),
                                      (4, ref('base.group_partner_manager'))]"/>
</record>
```

**Groupes hérités**:
- `base.group_system` → **ADMIN**: Installation d'apps, accès technique complet
- `base.group_erp_manager` → Paramètres ERP
- `sales_team.group_sale_manager` → Gestion CRM/Ventes
- `website.group_website_designer` → Édition site web
- `account.group_account_manager` → Comptabilité complète
- `base.group_partner_manager` → Gestion contacts

---

### 2. Configuration Automatique des Utilisateurs
**Fichier**: `models/res_users.py`

**Fonctionnalité**: Auto-configuration automatique quand on assigne le groupe Premium Manager

**Méthodes importantes**:

#### `create()` - Création utilisateur
```python
@api.model_create_multi
def create(self, vals_list):
    users = super(ResUsers, self).create(vals_list)
    for user in users:
        # Fix partner company_id immédiatement
        if user.partner_id and user.company_id:
            if user.partner_id.company_id != user.company_id:
                user.partner_id.sudo().write({'company_id': user.company_id.id})

        # Auto-configure Premium Manager si nécessaire
        self._auto_configure_premium_manager(user)
    return users
```

**Rôle**: S'assure que le partner de l'utilisateur a la même company_id que l'utilisateur

#### `write()` - Modification utilisateur
```python
def write(self, vals):
    if self.env.context.get('skip_premium_auto_config'):
        return super(ResUsers, self).write(vals)

    res = super(ResUsers, self).write(vals)

    if 'group_ids' in vals or 'groups_id' in vals:
        for user in self:
            self._auto_configure_premium_manager(user)
    return res
```

**Rôle**: Déclenche l'auto-configuration quand on modifie les groupes

#### `_auto_configure_premium_manager()` - Configuration automatique
**Étapes**:
1. **Ajoute les groupes manquants** (si le groupe Premium Manager est assigné)
2. **Assure restriction company**: `company_ids = [(6, 0, [company_id])]`
3. **Aligne partner.company_id** avec user.company_id
4. **Crée website automatiquement** pour la company si nécessaire

**Code clé**:
```python
def _auto_configure_premium_manager(self, user):
    # 1. Ajouter groupes requis
    required_groups_xml_ids = [
        'base.group_system',
        'base.group_erp_manager',
        'sales_team.group_sale_manager',
        'website.group_website_designer',
        'account.group_account_manager',
        'base.group_partner_manager',
    ]

    # 2. Restreindre à UNE company
    if set(user.company_ids.ids) != {user.company_id.id}:
        user.sudo().write({'company_ids': [(6, 0, [user.company_id.id])]})

    # 3. Aligner partner company_id
    if user.partner_id.company_id != user.company_id:
        user.partner_id.sudo().write({'company_id': user.company_id.id})

    # 4. Créer website pour la company
    if not existing_website:
        new_website = self.env['website'].sudo().create({
            'name': f'Site {user.company_id.name}',
            'company_id': user.company_id.id,
            'domain': f'company-{user.company_id.id}.local',
        })
```

---

### 3. Règles de Sécurité Multi-Tenant (Core)
**Fichier**: `data/onedesk_security.xml`

**Fonctionnalité**: Règles de sécurité de base pour tous les modèles OneDesk

**Règles Premium Manager**:

#### Partners/Contacts
```xml
<record id="rule_premium_manager_res_partner" model="ir.rule">
    <field name="name">Premium Manager - Contacts Own Company</field>
    <field name="model_id" ref="base.model_res_partner"/>
    <field name="domain_force">['|', ('company_id', '=', False), ('company_id', '=', user.company_id.id)]</field>
    <field name="groups" eval="[(4, ref('group_onedesk_premium_manager'))]"/>
    <field name="perm_read">True</field>
    <field name="perm_write">True</field>
    <field name="perm_create">True</field>
</record>
```

**Effet**:
- Voit les partners avec `company_id = False` (système: Administrator, OdooBot)
- Voit les partners avec `company_id = user.company_id.id` (SA company)
- **Ne voit PAS** les partners d'autres companies

#### Websites
```xml
<record id="rule_global_website_multitenant" model="ir.rule">
    <field name="name">GLOBAL Multi-tenant: Websites restricted by company_ids</field>
    <field name="model_id" ref="website.model_website"/>
    <field name="domain_force">['|', ('company_id', '=', False), ('company_id', 'in', user.company_ids.ids)]</field>
    <field name="groups" eval="[(4, ref('base.group_user'))]"/>
    <field name="global">True</field>
</record>
```

**Effet**: Règle GLOBALE qui filtre les websites pour TOUS les utilisateurs (sauf System Admin)

#### Companies
```xml
<record id="rule_premium_manager_res_company" model="ir.rule">
    <field name="name">Premium Manager - Own Company ONLY</field>
    <field name="model_id" ref="base.model_res_company"/>
    <field name="domain_force">[('id', '=', user.company_id.id)]</field>
</record>
```

**Effet**: Voit uniquement SA company (pas les autres)

#### Users
```xml
<record id="rule_premium_manager_res_users" model="ir.rule">
    <field name="name">Premium Manager - Users Own Company</field>
    <field name="model_id" ref="base.model_res_users"/>
    <field name="domain_force">['|', ('company_id', '=', False), ('company_id', '=', user.company_id.id)]</field>
</record>
```

**Effet**:
- Voit les utilisateurs système (company_id=False)
- Voit uniquement les utilisateurs de SA company

---

### 4. Règles de Sécurité Premium (Odoo Standard)
**Fichier**: `data/onedesk_security_premium.xml`

**Fonctionnalité**: Règles de sécurité pour les modules Odoo standard (CRM, Comptabilité, Website, Sale)

**CRITICAL**: Toutes les règles ont été modifiées pour **TOUJOURS** filtrer par company_id, même avec `base.group_system`

#### CRM Leads
```xml
<record id="rule_premium_manager_crm_lead" model="ir.rule">
    <field name="name">Premium Manager - CRM Leads Own Company</field>
    <field name="model_id" ref="crm.model_crm_lead"/>
    <field name="domain_force">['|', ('company_id', '=', False), ('company_id', '=', user.company_id.id)]</field>
</record>
```

#### Accounting (Factures/Paiements)
```xml
<record id="rule_premium_manager_account_move" model="ir.rule">
    <field name="name">Premium Manager - Account Moves Own Company</field>
    <field name="model_id" ref="account.model_account_move"/>
    <field name="domain_force">['|', ('company_id', '=', False), ('company_id', '=', user.company_id.id)]</field>
</record>

<record id="rule_premium_manager_account_payment" model="ir.rule">
    <field name="name">Premium Manager - Payments Own Company</field>
    <field name="model_id" ref="account.model_account_payment"/>
    <field name="domain_force">['|', ('company_id', '=', False), ('company_id', '=', user.company_id.id)]</field>
</record>
```

#### Website
```xml
<record id="rule_premium_manager_website" model="ir.rule">
    <field name="name">Premium Manager - Websites Own Company ONLY</field>
    <field name="model_id" ref="website.model_website"/>
    <field name="domain_force">['|', ('company_id', '=', False), ('company_id', '=', user.company_id.id)]</field>
</record>

<record id="rule_premium_manager_website_page" model="ir.rule">
    <field name="name">Premium Manager - Website Pages Own Company</field>
    <field name="model_id" ref="website.model_website_page"/>
    <field name="domain_force">['|', ('website_id.company_id', '=', False), ('website_id.company_id', '=', user.company_id.id)]</field>
</record>
```

#### Sale Orders
```xml
<record id="rule_premium_manager_sale_order" model="ir.rule">
    <field name="name">Premium Manager - Sale Orders Own Company</field>
    <field name="model_id" ref="sale.model_sale_order"/>
    <field name="domain_force">['|', ('company_id', '=', False), ('company_id', '=', user.company_id.id)]</field>
</record>
```

#### Products
```xml
<record id="rule_premium_manager_product_template" model="ir.rule">
    <field name="name">Premium Manager - Products Own Company</field>
    <field name="model_id" ref="product.model_product_template"/>
    <field name="domain_force">['|', ('company_id', '=', False), ('company_id', '=', user.company_id.id)]</field>
</record>
```

#### **CRITICAL - Partners (doublon corrigé)**
```xml
<record id="rule_partner_company" model="ir.rule">
    <field name="name">Premium Manager - Contacts Own Company ONLY</field>
    <field name="model_id" ref="base.model_res_partner"/>
    <field name="domain_force">['|', ('company_id','=',False), ('company_id','=',user.company_id.id)]</field>
</record>
```

**IMPORTANT**: Cette règle n'a PLUS la condition `if not user.has_group('base.group_system')` qui permettait de contourner le filtrage.

#### **CRITICAL - Companies (doublon corrigé)**
```xml
<record id="rule_premium_manager_res_company" model="ir.rule">
    <field name="name">Premium Manager - Own Company ONLY</field>
    <field name="model_id" ref="base.model_res_company"/>
    <field name="domain_force">[('id', '=', user.company_id.id)]</field>
</record>
```

**IMPORTANT**: Plus de condition `if not user.has_group('base.group_system')`

#### **CRITICAL - Users (doublon corrigé)**
```xml
<record id="rule_premium_manager_res_users" model="ir.rule">
    <field name="name">Premium Manager - Users Own Company ONLY</field>
    <field name="model_id" ref="base.model_res_users"/>
    <field name="domain_force">[('company_id', '=', user.company_id.id)]</field>
</record>
```

**IMPORTANT**: Plus de condition `if not user.has_group('base.group_system')`

---

### 5. Droits d'Accès au Niveau Modèle
**Fichier**: `security/ir.model.access.csv`

**Fonctionnalité**: Permissions CRUD (Create, Read, Update, Delete) au niveau modèle

**Format CSV**:
```
id,name,model_id,group_id,perm_read,perm_write,perm_create,perm_unlink
```

**Ligne Premium Manager pour res.partner**:
```csv
access_premium_res_partner,Premium Manager - res.partner,base.model_res_partner,group_onedesk_premium_manager,1,1,1,1
```

**Signification**:
- `perm_read=1`: Peut lire les partners
- `perm_write=1`: Peut modifier les partners
- `perm_create=1`: Peut créer des partners
- `perm_unlink=1`: Peut supprimer des partners

**NOTE**: Les record rules filtrent ENSUITE quels partners sont visibles (seulement sa company)

---

### 6. Alignement Partner Company_id
**Fichier**: `models/res_partner_override.py`

**Fonctionnalité**: Force tous les partners normaux à avoir un company_id, sauf les partners système

**Code clé**:
```python
SYSTEM_PARTNERS = [
    'Administrator',
    'OdooBot',
    'Public user',
    'Portal',
]

def write(self, vals):
    if 'company_id' in vals and vals['company_id'] is False:
        system_partners = self.filtered(lambda p: p.name in SYSTEM_PARTNERS)

        if system_partners:
            # OK pour les partners système → company_id=False
            pass
        else:
            # Partners normaux DOIVENT avoir une company
            current_user = self.env.user
            if current_user and current_user.company_id:
                vals['company_id'] = current_user.company_id.id

    return super().write(vals)
```

**Rôle**:
- Empêche les partners normaux d'être "globaux" (company_id=False)
- Permet aux partners système d'être globaux
- Assure que chaque contact appartient à UNE company

---

### 7. Migration Automatique
**Fichier**: `migrations/19.0.1.0.2/post-migrate.py`

**Fonctionnalité**: Correction automatique de TOUTES les données existantes lors de l'upgrade du module

**Étapes de la migration**:

#### 1. Corriger partners des utilisateurs
```python
all_users = env['res.users'].search([
    ('partner_id', '!=', False),
    ('company_id', '!=', False),
])

for user in all_users:
    if user.partner_id.company_id != user.company_id:
        user.partner_id.write({'company_id': user.company_id.id})
```

#### 2. Mettre partners système en global
```python
system_partner_names = ['Administrator', 'OdooBot', 'Public user', 'Portal']
for partner_name in system_partner_names:
    partner = env['res.partner'].search([('name', '=', partner_name)], limit=1)
    if partner and partner.company_id:
        partner.write({'company_id': False})
```

#### 3. Restreindre Premium Managers à UNE company
```python
premium_group = env.ref('onedesk_core.group_onedesk_premium_manager')
premium_users = env['res.users'].search([
    ('group_ids', 'in', [premium_group.id])
])

for user in premium_users:
    if user.company_id and set(user.company_ids.ids) != {user.company_id.id}:
        user.write({'company_ids': [(6, 0, [user.company_id.id])]})
```

**Rôle**: Fonctionne pour 1 utilisateur ou 1 million d'utilisateurs, automatiquement

---

### 8. Menu Website Intelligent
**Fichier**: `views/website_menu_override.xml`

**Fonctionnalité**: Menu "Mon Site Web" qui détecte automatiquement le website de la company de l'utilisateur

**Action Serveur**:
```xml
<record id="action_open_user_website" model="ir.actions.server">
    <field name="name">Mon Site Web</field>
    <field name="model_id" ref="website.model_website"/>
    <field name="state">code</field>
    <field name="code">
# Trouver le website de la company de l'utilisateur
user_website = env['website'].search([
    ('company_id', '=', env.user.company_id.id)
], limit=1)

if not user_website:
    # Créer automatiquement si n'existe pas
    unique_domain = f'company-{env.user.company_id.id}.local'
    user_website = env['website'].create({
        'name': f'Site {env.user.company_id.name}',
        'company_id': env.user.company_id.id,
        'domain': unique_domain,
    })

action = {
    'type': 'ir.actions.act_url',
    'url': f'/website/force/{user_website.id}',
    'target': 'self',
}
    </field>
</record>
```

**Menu**:
```xml
<menuitem id="menu_website_override"
    name="Mon Site Web"
    action="action_open_user_website"
    parent="website.menu_website_configuration"
    sequence="1"/>
```

**Rôle**:
- Remplace le menu "Websites" global
- Ouvre automatiquement SON website
- Crée le website si nécessaire

---

## 🏗️ Architecture Complète

```
┌─────────────────────────────────────────────────────────────┐
│                    PREMIUM MANAGER ROLE                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  1. GROUP DEFINITION                    │
        │  data/onedesk_groups.xml                │
        │  ✓ Définit groupe Premium Manager      │
        │  ✓ implied_ids = groupes hérités       │
        │    - base.group_system (ADMIN)          │
        │    - base.group_erp_manager             │
        │    - sales_team.group_sale_manager      │
        │    - website.group_website_designer     │
        │    - account.group_account_manager      │
        │    - base.group_partner_manager         │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  2. AUTO-CONFIGURATION                  │
        │  models/res_users.py                    │
        │  ✓ create() → Aligne partner company_id│
        │  ✓ write() → Déclenche auto-config     │
        │  ✓ _auto_configure_premium_manager()   │
        │    - Ajoute groupes manquants           │
        │    - Restreint à UNE company            │
        │    - Aligne partner.company_id          │
        │    - Crée website automatiquement       │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  3. PARTNER ALIGNMENT                   │
        │  models/res_partner_override.py         │
        │  ✓ Force company_id pour partners       │
        │  ✓ Autorise company_id=False pour       │
        │    partners système uniquement          │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  4. SECURITY RULES (Core)               │
        │  data/onedesk_security.xml              │
        │  ✓ res.partner → Own company + global   │
        │  ✓ res.company → Own company ONLY       │
        │  ✓ res.users → Own company users        │
        │  ✓ website.website → Own company        │
        │  ✓ OneDesk models (property, unit, etc) │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  5. SECURITY RULES (Premium)            │
        │  data/onedesk_security_premium.xml      │
        │  ✓ crm.lead → Own company               │
        │  ✓ account.move → Own company           │
        │  ✓ account.payment → Own company        │
        │  ✓ account.journal → Own company        │
        │  ✓ sale.order → Own company             │
        │  ✓ product.template → Own company       │
        │  ✓ website.page → Own company           │
        │  ✓ website.menu → Own company           │
        │  ✓ ir.sequence → Own company            │
        │  ⚠️ PAS de bypass avec base.group_system│
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  6. MODEL ACCESS RIGHTS                 │
        │  security/ir.model.access.csv           │
        │  ✓ CRUD permissions (Create, Read,      │
        │    Update, Delete) par modèle           │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  7. AUTOMATIC MIGRATION                 │
        │  migrations/19.0.1.0.2/post-migrate.py  │
        │  ✓ Corrige partners existants           │
        │  ✓ Met partners système en global       │
        │  ✓ Restreint Premium Managers           │
        │  ✓ Fonctionne pour 1M+ utilisateurs     │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  8. WEBSITE MENU                        │
        │  views/website_menu_override.xml        │
        │  ✓ Détecte website automatiquement      │
        │  ✓ Crée website si nécessaire           │
        │  ✓ Ouvre SON website uniquement         │
        └─────────────────────────────────────────┘
```

---

## 🔐 Flux de Sécurité Multi-Tenant

### Scénario: Premium Manager essaie d'accéder à un contact

```
┌──────────────────────────────────────────────────────────┐
│  Premium Manager (Company: "Premium Company A")          │
│  Essaie d'accéder: res.partner (Contacts)               │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │  1. MODEL ACCESS CHECK             │
        │  ir.model.access.csv               │
        │  ✓ Premium Manager a-t-il CRUD?    │
        │  → OUI (read, write, create, del)  │
        └────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │  2. RECORD RULES CHECK             │
        │  ir.rule (res.partner)             │
        │  Règles appliquées:                │
        │  - onedesk_security.xml            │
        │    rule_premium_manager_res_partner│
        │  - onedesk_security_premium.xml    │
        │    rule_partner_company            │
        └────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │  3. DOMAIN EVALUATION              │
        │  ['|',                             │
        │    ('company_id', '=', False),     │ ← Contacts système
        │    ('company_id', '=', 4)          │ ← Company ID = 4
        │  ]                                 │
        └────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │  4. SQL QUERY                      │
        │  SELECT * FROM res_partner         │
        │  WHERE company_id IS NULL          │
        │     OR company_id = 4              │
        └────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │  5. RÉSULTATS FILTRÉS              │
        │  ✅ Administrator (company_id=NULL)│
        │  ✅ OdooBot (company_id=NULL)      │
        │  ✅ Contact A (company_id=4)       │
        │  ✅ Contact B (company_id=4)       │
        │  ❌ Contact X (company_id=5)       │ ← Autre company
        │  ❌ Contact Y (company_id=6)       │ ← Autre company
        └────────────────────────────────────┘
```

---

## ✅ Garanties de Sécurité

### 1. Isolation par company_id
✅ **TOUJOURS** filtré par `company_id = user.company_id.id`
✅ Même avec `base.group_system`, pas de bypass
✅ Record rules au niveau SQL (impossible à contourner côté client)

### 2. Alignement Partner ↔ User
✅ `user.partner_id.company_id == user.company_id`
✅ Vérifié à la création (`create()`)
✅ Vérifié à la modification (`write()`)
✅ Corrigé automatiquement par migration

### 3. Restriction company_ids
✅ Premium Manager: `company_ids = [user.company_id.id]` (UNE company)
✅ Impossible d'accéder à plusieurs companies
✅ Auto-configuré par `_auto_configure_premium_manager()`

### 4. Partners Système Globaux
✅ Administrator, OdooBot, Public user, Portal → `company_id = False`
✅ Visibles par TOUS les utilisateurs
✅ Protégés par `res_partner_override.py`

### 5. Création Automatique Website
✅ Website créé automatiquement pour chaque company
✅ Domain unique: `company-{id}.local`
✅ Filtré par `company_id` (record rules)

---

## 🔧 Configuration d'un Nouveau Premium Manager

### Méthode 1: Interface Odoo (Recommandée)
1. Aller dans **Settings > Users & Companies > Users**
2. Créer ou modifier un utilisateur
3. Assigner le groupe **"OneDesk / Premium Manager"**
4. Définir la **Company** de l'utilisateur
5. **Sauvegarder** → Auto-configuration automatique!

### Méthode 2: Code Python
```python
# Créer utilisateur Premium Manager
user = env['res.users'].create({
    'name': 'John Doe',
    'login': 'john.doe@example.com',
    'email': 'john.doe@example.com',
    'company_id': my_company.id,
    'company_ids': [(6, 0, [my_company.id])],
    'groups_id': [(4, env.ref('onedesk_core.group_onedesk_premium_manager').id)],
})

# Auto-configuration se fait automatiquement:
# - Groupes ajoutés
# - Partner aligné
# - Website créé
```

### Ce qui se passe automatiquement:
1. ✅ Groupes manquants ajoutés (base.group_system, etc.)
2. ✅ `company_ids` restreint à `[company_id]`
3. ✅ `partner_id.company_id` aligné avec `company_id`
4. ✅ Website créé pour la company

---

## 🐛 Résolution de Problèmes

### Problème: Premium Manager voit des données d'autres companies

**Diagnostic**:
```python
# Vérifier les record rules appliquées
rules = env['ir.rule'].search([
    ('model_id.model', '=', 'res.partner'),
    ('groups', 'in', user.groups_id.ids)
])
for rule in rules:
    print(f"Rule: {rule.name}")
    print(f"Domain: {rule.domain_force}")
```

**Solution**: Vérifier que les rules n'ont PAS de condition `if not user.has_group('base.group_system')`

### Problème: Partner company_id ne correspond pas à user company_id

**Diagnostic**:
```python
user = env['res.users'].browse(USER_ID)
print(f"User company: {user.company_id.name}")
print(f"Partner company: {user.partner_id.company_id.name if user.partner_id.company_id else 'None'}")
```

**Solution**:
```python
# Corriger manuellement
user.partner_id.write({'company_id': user.company_id.id})

# Ou relancer la migration
env['res.users']._auto_configure_premium_manager(user)
```

### Problème: Website non créé

**Diagnostic**:
```python
website = env['website'].search([('company_id', '=', user.company_id.id)])
print(f"Website exists: {bool(website)}")
```

**Solution**:
```python
# Créer manuellement
env['website'].create({
    'name': f'Site {user.company_id.name}',
    'company_id': user.company_id.id,
    'domain': f'company-{user.company_id.id}.local',
})
```

---

## 📊 Statistiques et Monitoring

### Compter les Premium Managers
```python
premium_group = env.ref('onedesk_core.group_onedesk_premium_manager')
count = env['res.users'].search_count([
    ('groups_id', 'in', [premium_group.id])
])
print(f"Premium Managers: {count}")
```

### Vérifier l'alignement des données
```python
# Partners mal alignés
misaligned = env['res.users'].search([
    ('partner_id', '!=', False),
    ('company_id', '!=', False),
]).filtered(lambda u: u.partner_id.company_id != u.company_id)

print(f"Users with misaligned partners: {len(misaligned)}")
```

### Vérifier les companies multiples
```python
premium_group = env.ref('onedesk_core.group_onedesk_premium_manager')
multi_company_users = env['res.users'].search([
    ('groups_id', 'in', [premium_group.id])
]).filtered(lambda u: len(u.company_ids) > 1)

print(f"Premium Managers with multiple companies: {len(multi_company_users)}")
```

---

## 📝 Notes Importantes

### ⚠️ CRITICAL: Ne JAMAIS modifier
- Les conditions `if not user.has_group('base.group_system')` ont été SUPPRIMÉES
- Ne PAS les rajouter, sinon bypass de la sécurité multi-tenant

### ✅ BEST PRACTICES
- Toujours utiliser `sudo()` pour les opérations d'auto-configuration
- Toujours utiliser `skip_premium_auto_config` context pour éviter récursion
- Toujours vérifier `partner_id.company_id` après modifications

### 🔐 SÉCURITÉ
- Record rules au niveau SQL = impossible à bypass côté client
- Multi-tenant isolation garantie même avec droits admin
- Aucune fuite de données entre companies

---

## 📚 Résumé des Fichiers

| Fichier | Rôle | Critique |
|---------|------|----------|
| `data/onedesk_groups.xml` | Définition groupe + implied_ids | ⭐⭐⭐ |
| `models/res_users.py` | Auto-configuration Premium Manager | ⭐⭐⭐⭐⭐ |
| `models/res_partner_override.py` | Alignement partner company_id | ⭐⭐⭐⭐ |
| `data/onedesk_security.xml` | Record rules core (partners, users, etc) | ⭐⭐⭐⭐⭐ |
| `data/onedesk_security_premium.xml` | Record rules Odoo standard (CRM, comptabilité, etc) | ⭐⭐⭐⭐⭐ |
| `security/ir.model.access.csv` | Permissions CRUD par modèle | ⭐⭐⭐ |
| `migrations/19.0.1.0.2/post-migrate.py` | Correction données existantes | ⭐⭐⭐⭐ |
| `views/website_menu_override.xml` | Menu website intelligent | ⭐⭐ |

---

## 🎯 Conclusion

Le système Premium Manager offre:
- ✅ **Accès administratif complet** via `base.group_system`
- 🔒 **Isolation multi-tenant stricte** via record rules
- 🤖 **Configuration 100% automatique** via `_auto_configure_premium_manager()`
- 🔄 **Migration automatique** pour corriger données existantes
- 🌐 **Gestion website automatique** avec détection et création

**Principe fondamental**: Premium Manager = Admin de SA company, rien que SA company.
