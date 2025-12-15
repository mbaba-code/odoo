# ✨ Configuration Automatique Premium Manager

## 🎯 Fonctionnalité

Désormais, quand tu **assignes le rôle Premium Manager** à un utilisateur dans l'interface Odoo, **TOUT SE CONFIGURE AUTOMATIQUEMENT** !

Plus besoin de shell, plus besoin de scripts manuels. Tout se passe dans Odoo ! 🚀

---

## ⚡ Ce qui se passe automatiquement

Quand tu coches **"OneDesk / Premium Manager"** pour un utilisateur :

### 1️⃣ **Vérification de la Company**
```
✅ Si l'utilisateur n'a PAS de company_id
   → Assignation automatique à une company par défaut
```

### 2️⃣ **Marquage Client OneDesk**
```
✅ La company est marquée comme "Client OneDesk"
   → is_onedesk_client = True
```

### 3️⃣ **Création Website Automatique**
```
✅ Si la company n'a PAS de website
   → Création d'un nouveau website "Site [Nom de la Company]"
   → Website lié à la company (isolation multi-tenant)
```

### 4️⃣ **Page d'Accueil par Défaut**
```
✅ Création d'une page d'accueil basique
   → Prête à être personnalisée
   → Publiée automatiquement
```

---

## 🚀 Usage dans Odoo

### **Créer un nouvel utilisateur Premium Manager**

1. **Aller dans Paramètres → Utilisateurs & Companies → Utilisateurs**

2. **Créer un nouvel utilisateur :**
   ```
   Nom : Jean Dupont
   Email : jean.dupont@example.com
   Company : MaSociété
   ```

3. **Assigner le groupe Premium Manager :**
   ```
   ☑ OneDesk / Premium Manager
   ```

4. **Enregistrer**
   ```
   → Le système configure TOUT automatiquement !
   ```

### **Logs de Configuration**

Tu peux vérifier dans les logs Odoo :

```
2025-12-11 11:30:00 INFO odoo.addons.onedesk_core.models.res_users:
   🔧 Setup Premium Manager pour Jean Dupont
   ✅ Company assignée: MaSociété
   ✅ Company MaSociété marquée comme client OneDesk
   ✅ Nouveau website créé: Site MaSociété (ID: 42)
   ✅ Page d'accueil créée
```

---

## 🧪 Test de la Configuration

### **1. Créer un utilisateur de test**

Via Odoo UI :
```
Paramètres → Utilisateurs → Créer

Nom : Test Premium
Email : test.premium@example.com
Company : Société Test
Groupes : ☑ OneDesk / Premium Manager
```

### **2. Vérifier que le website a été créé**

```
Website → Configuration → Websites
```

Tu devrais voir :
```
✅ Site Société Test (Company: Société Test)
```

### **3. Se connecter comme l'utilisateur Premium**

1. Se déconnecter de l'admin
2. Se connecter avec `test.premium@example.com`
3. Vérifier l'isolation :

```
Website → Configuration → Websites
   → Devrait voir UNIQUEMENT "Site Société Test"
   → PAS les websites des autres companies

Paramètres → Companies
   → Devrait voir UNIQUEMENT "Société Test"
   → PAS les autres companies

Paramètres → Utilisateurs
   → Devrait voir UNIQUEMENT les users de "Société Test"
```

---

## 🔧 Architecture Technique

### **Fichier : `addons/onedesk_core/models/res_users.py`**

```python
class ResUsers(models.Model):
    _inherit = 'res.users'

    def write(self, vals):
        """Détecte l'ajout du groupe Premium Manager"""
        res = super().write(vals)

        if 'group_ids' in vals or 'groups_id' in vals:
            for user in self:
                self._setup_premium_manager(user)

        return res

    def _setup_premium_manager(self, user):
        """Configure automatiquement le Premium Manager"""
        # 1. Vérifier qu'il a le groupe Premium
        is_premium = user.has_group('onedesk_core.group_onedesk_premium_manager')
        if not is_premium:
            return

        # 2. Assigner company si manquante
        if not user.company_id:
            user.company_id = default_company

        # 3. Marquer company comme OneDesk
        user.company_id.is_onedesk_client = True

        # 4. Créer website si nécessaire
        self._ensure_company_website(user.company_id)
```

### **Méthodes Principales**

| Méthode | Fonction |
|---------|----------|
| `_setup_premium_manager(user)` | Point d'entrée - configure tout |
| `_ensure_company_website(company)` | Crée le website si manquant |
| `_create_default_website_pages(website)` | Crée la page d'accueil |

---

## 🔒 Isolation Multi-Tenant

### **Record Rules Actives**

Les règles de sécurité s'appliquent automatiquement :

```xml
<!-- website.website -->
<field name="domain_force">
    ['|', ('company_id', '=', False), ('company_id', '=', user.company_id.id)]
    if not user.has_group('base.group_system') else []
</field>

<!-- res.company -->
<field name="domain_force">
    [('id', '=', user.company_id.id)]
    if not user.has_group('base.group_system') else []
</field>

<!-- res.users -->
<field name="domain_force">
    [('company_id', '=', user.company_id.id)]
    if not user.has_group('base.group_system') else []
</field>
```

### **Exception pour Admins**

Les utilisateurs **System Admin** (base.group_system) :
- ✅ Voient TOUS les websites
- ✅ Voient TOUTES les companies
- ✅ Voient TOUS les utilisateurs

→ Isolation multi-tenant **désactivée** pour les admins

---

## 📊 Scénarios d'Usage

### **Scénario 1 : Nouveau Client OneDesk**

```
1. Admin crée une nouvelle company "ClientA"
2. Admin crée un utilisateur "manager@clienta.com"
3. Admin assigne le groupe Premium Manager
   → ✅ Website "Site ClientA" créé automatiquement
   → ✅ Isolation multi-tenant activée
4. manager@clienta.com se connecte
   → ✅ Voit UNIQUEMENT son site et ses données
```

### **Scénario 2 : Migration Utilisateur Existant**

```
1. Utilisateur "user@company.com" existe déjà
2. Admin assigne le groupe Premium Manager
   → ✅ Système vérifie si website existe
   → ✅ Crée le website si nécessaire
   → ✅ Applique l'isolation
```

### **Scénario 3 : Plusieurs Utilisateurs Même Company**

```
1. Company "ClientB" a 3 utilisateurs Premium
2. Un seul website "Site ClientB" est créé
3. Les 3 utilisateurs partagent le même website
4. Mais chacun voit uniquement les données de ClientB
```

---

## ⚠️ Notes Importantes

### **1. Module Website Requis**

Le module `website` doit être installé :
```
Apps → Rechercher "Website" → Installer
```

### **2. Permissions Requises**

L'utilisateur qui assigne le groupe Premium Manager doit avoir :
- ✅ Accès aux Paramètres
- ✅ Droits de modification des utilisateurs

### **3. Groupe System Admin**

Si tu veux qu'un utilisateur ait accès à **TOUT** (bypass multi-tenant) :
```
☑ Administration / System
```

**Attention :** Cela donne un accès **total** à toute la base Odoo !

---

## 🐛 Dépannage

### **Problème : Website pas créé**

**Vérifier dans les logs :**
```bash
tail -f /var/log/odoo/odoo.log | grep "Setup Premium Manager"
```

**Causes possibles :**
1. Module `website` non installé
2. Erreur de permissions
3. Company_id manquant

**Solution :**
```python
# Dans le shell Odoo
user = env['res.users'].browse(USER_ID)
user._setup_premium_manager(user)
env.cr.commit()
```

### **Problème : Utilisateur voit toutes les companies**

**Cause :** Utilisateur a le groupe System Admin

**Vérifier :**
```python
user.has_group('base.group_system')  # Devrait être False
```

**Solution :**
```
Paramètres → Utilisateurs → Retirer "Administration / System"
```

### **Problème : Erreur "group_ids not found"**

**Cause :** Nom du champ varie selon version Odoo

**Solution :** Le code gère automatiquement `group_ids` et `groups_id`

---

## ✅ Checklist de Déploiement

Avant de déployer en production :

- [ ] Module `onedesk_core` mis à jour
- [ ] Module `website` installé
- [ ] Test créé un utilisateur Premium Manager
- [ ] Vérification website créé automatiquement
- [ ] Test isolation multi-tenant fonctionne
- [ ] Logs ne montrent aucune erreur
- [ ] Admin peut toujours voir toutes les données
- [ ] Documentation fournie aux utilisateurs

---

## 📞 Support

En cas de problème :

1. **Vérifier les logs Odoo**
2. **Tester dans le shell** avec `_setup_premium_manager(user)`
3. **Vérifier les record rules** avec le script de diagnostic
4. **Redémarrer Odoo** si nécessaire

---

## 🎉 Avantages

| Avant | Après |
|-------|-------|
| ❌ Configuration manuelle shell | ✅ Automatique dans Odoo UI |
| ❌ Risque d'oubli d'étape | ✅ Tout est configuré systématiquement |
| ❌ Complexe pour non-tech | ✅ Simple : cocher une case |
| ❌ Scripts à maintenir | ✅ Code intégré au module |
| ❌ Documentation éparpillée | ✅ Tout dans l'interface Odoo |

---

**Commit :** `1e53904a` - ✨ AUTO-SETUP: Configuration automatique Premium Manager
**Date :** 2025-12-11
**Fichiers :** `addons/onedesk_core/models/res_users.py`, `__init__.py`
