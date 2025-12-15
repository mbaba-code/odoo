# OneDesk Core - Changelog

Documentation des versions et modifications fonctionnelles du module **OneDesk Core**.

---

## Version 19.0.1.0.1 (2025-12-12)

### 🎯 Fonctionnalité majeure: Groupe Premium Manager

**Objectif**: Créer un groupe "Premium Manager" qui donne accès complet à Odoo (CRM, Website, Comptabilité, Settings) tout en maintenant l'isolation multi-tenant par `company_id`.

#### Architecture

```
Super Admin (base.group_system)
    ↓ Voit TOUT (toutes companies)

Premium Manager (company_id=1)
    ↓ Voit UNIQUEMENT company_id=1
    ├── CRM de company_id=1
    ├── Website de company_id=1
    ├── Comptabilité de company_id=1
    └── Contacts de company_id=1

Premium Manager (company_id=2)
    ↓ Voit UNIQUEMENT company_id=2
    └── ...
```

#### Fichiers créés/modifiés

**1. Groupe avec implied_ids** (`data/onedesk_groups.xml`)
```xml
<record id="group_onedesk_premium_manager" model="res.groups">
    <field name="name">OneDesk / Premium Manager</field>
    <field name="comment">Gestionnaire Premium OneDesk - Accès complet à Odoo avec isolation multi-tenant</field>
</record>
```

**Note**: Les `implied_ids` sont ajoutés via migration pour éviter les erreurs de Foreign Key.

**2. Migration pour implied_ids** (`migrations/19.0.1.0.1/post-migrate.py`)
- Détecte le groupe Premium Manager existant
- Ajoute automatiquement les `implied_ids`:
  - `base.group_erp_manager` (Settings)
  - `sales_team.group_sale_manager` (CRM)
  - `website.group_website_designer` (Website)
  - `account.group_account_manager` (Comptabilité)
  - `base.group_partner_manager` (Contacts)

**3. Auto-configuration utilisateur** (`models/res_users.py`)

**Fonctionnalité**: Quand un utilisateur reçoit le groupe Premium Manager:
- ✅ Les groupes implied sont ajoutés automatiquement (via Odoo)
- ✅ L'utilisateur est restreint à SA company uniquement (`company_ids`)
- ✅ Un website est créé automatiquement pour sa company s'il n'existe pas

```python
def write(self, vals):
    # Évite la récursion infinie avec contexte
    if self.env.context.get('skip_premium_auto_config'):
        return super().write(vals)

    res = super().write(vals)

    if 'group_ids' in vals:
        for user in self:
            self._auto_configure_premium_manager(user)

    return res
```

**4. Menu Website intelligent** (`views/website_menu_override.xml`)

**Problème résolu**: Le menu Website par défaut essaie d'ouvrir "My Website" (ID: 1) qui peut appartenir à une autre company → erreur "Forbidden".

**Solution**: Server Action qui:
- Détecte automatiquement le website de la company de l'utilisateur
- Crée le website s'il n'existe pas
- Redirige vers `/website/force/{website_id}`

**5. Règles de sécurité multi-tenant** (`data/onedesk_security.xml`)

**Règle GLOBALE** (ligne 831):
```xml
<record id="rule_global_website_multitenant" model="ir.rule">
    <field name="name">GLOBAL Multi-tenant: Websites restricted by company_ids</field>
    <field name="model_id" ref="website.model_website"/>
    <field name="domain_force">['|', ('company_id', '=', False), ('company_id', 'in', user.company_ids.ids)]</field>
    <field name="groups" eval="[(4, ref('base.group_user'))]"/>
    <field name="global">True</field>
</record>
```

**Règles Premium Manager**:
- `rule_premium_manager_website` - Websites de sa company
- `rule_premium_manager_res_company` - UNIQUEMENT sa company
- `rule_premium_manager_res_users` - Users de sa company
- `rule_premium_manager_res_partner` - Contacts de sa company + partenaire de la company
- `rule_premium_manager_crm_lead` - CRM Leads de sa company
- `rule_premium_manager_account_move` - Factures de sa company
- `rule_premium_manager_account_payment` - Paiements de sa company
- `rule_premium_manager_account_journal` - Journaux de sa company
- `rule_premium_manager_sale_order` - Commandes de sa company
- `rule_premium_manager_product` - Produits de sa company
- `rule_premium_manager_website_page` - Pages website de sa company
- `rule_premium_manager_website_menu` - Menus website de sa company
- `rule_premium_manager_ir_sequence` - Séquences de sa company

**6. Droits d'accès** (`security/ir.model.access.csv`)

Ajout de 17 lignes pour donner accès CRUD aux modèles:
- `website`, `website.page`, `website.menu`
- `crm.lead`
- `account.move`, `account.payment`, `account.journal`
- `sale.order`
- `product.product`, `product.template`
- `res.users`, `res.partner`, `res.company`
- `ir.sequence`

#### Problèmes rencontrés et solutions

**Problème 1**: Boucle infinie de récursion dans `res_users.write()`
```python
# AVANT (ERREUR)
user.write({'group_ids': [(4, gid)]})  # Re-déclenche write() → boucle infinie

# APRÈS (CORRIGÉ)
user.with_context(skip_premium_auto_config=True).write({'group_ids': [(4, gid)]})
```

**Problème 2**: Foreign Key constraint lors de l'upgrade
```
ERROR: update or delete on table "res_groups" violates foreign key constraint "ir_model_access_group_id_fkey"
```

**Solution**: Utiliser une migration au lieu de recréer le groupe via XML.

**Problème 3**: Nom de champ Odoo 19
```python
# Odoo 18 et avant
user.write({'groups_id': [(4, gid)]})

# Odoo 19 (CORRECT)
user.write({'group_ids': [(4, gid)]})
```

**Problème 4**: L'utilisateur voit TOUS les websites au lieu de voir uniquement le sien

**Cause**: Les groupes hérités (Website Designer, etc.) ont des règles plus permissives qui écrasent la règle restrictive.

**Solution**: Règle GLOBALE avec `global=True` qui s'applique à TOUS les utilisateurs et force la restriction par `company_ids`.

**Problème 5**: Access Error sur le partenaire de la company

**Cause**: Chaque company a un partenaire associé (`company_id.partner_id`) qui peut avoir un `company_id` différent.

**Solution**: Ajouter une condition dans la règle res.partner:
```python
['|', '|', ('company_id', '=', False), ('company_id', '=', user.company_id.id), ('id', '=', user.company_id.partner_id.id)]
```

#### Test de validation

Pour valider que le groupe fonctionne correctement:

1. **Créer un utilisateur test**:
   - Nom: "Test Premium"
   - Company: Créer une nouvelle company "Test Company"
   - Assigner UNIQUEMENT le groupe "OneDesk / Premium Manager"

2. **Vérifications**:
   - ✅ Les modules CRM, Website, Settings, Accounting, Contacts apparaissent automatiquement
   - ✅ Un website est créé automatiquement pour "Test Company"
   - ✅ L'utilisateur ne voit QUE les données de "Test Company"
   - ✅ L'utilisateur ne voit PAS les websites/données des autres companies
   - ✅ Si on retire le groupe Premium Manager, tous les modules disparaissent

3. **Test multi-tenant**:
   - Créer 2 utilisateurs avec 2 companies différentes
   - Vérifier qu'ils ne voient PAS les données l'un de l'autre
   - Le Super Admin doit voir TOUT

#### Migration depuis version précédente

Si vous upgrader depuis une version sans Premium Manager:

```bash
./odoo-bin -u onedesk_core -d votre_database --stop-after-init
```

La migration `19.0.1.0.1/post-migrate.py` va automatiquement:
1. Trouver le groupe Premium Manager existant (si créé manuellement)
2. Ajouter les `implied_ids` manquants
3. Configurer les utilisateurs Premium Manager existants

---

## Version 1.0.0 (Date antérieure)

### Fonctionnalités initiales

- Gestion des propriétés (onedesk_property)
- Gestion des unités (onedesk_unit)
- Gestion des réservations (onedesk_reservation)
- Gestion des tâches (onedesk_task)
- Système d'intégration (onedesk_integration)
- Multi-tenant avec plans et clients (onedesk_plan, onedesk_client)
- Dashboard (onedesk_dashboard)
- Gestion des documents et signatures
- Import de contacts
- Paiements et retry automatique

---

## Dépendances

- `base`: Module de base Odoo
- `contacts`: Gestion des contacts
- `mail`: Messagerie
- `account`: Comptabilité
- `calendar`: Calendrier
- `payment`: Paiements
- `account_payment`: Paiements comptables
- `website`: Site web
- `crm`: CRM (Requis pour Premium Manager)
- `sale`: Ventes (Requis pour Premium Manager)

---

## Mainteneurs

- **Auteur**: Merveilles
- **License**: LGPL-3
- **Catégorie**: Services
