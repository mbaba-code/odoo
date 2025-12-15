# 🔒 FIX : Isolation Multi-Tenant Premium Manager

## 📋 Problème Identifié

Les utilisateurs Premium Manager avaient accès à **TOUS les modules** Odoo, mais sans isolation multi-tenant correcte :

### ❌ **Avant la correction :**

| Ressource | Visibilité | Problème |
|-----------|-----------|----------|
| **website.website** | TOUS les sites | 🔴 Critique - Pas de filtre |
| **Settings/Paramètres** | Partagés entre companies | 🔴 Fuite de données |
| **res.company** | Toutes les companies | 🔴 Violation isolation |
| **res.users** | Tous les utilisateurs | 🔴 Violation privacy |
| **ir.sequence** | Toutes les séquences | 🟡 Confusion numérotation |
| **mail.template** | Tous les templates | 🟡 Templates partagés |

**Conséquence :** Un client Premium pouvait voir/modifier les sites web, paramètres et utilisateurs d'AUTRES clients !

---

## ✅ Solution Appliquée

### **6 Nouvelles Record Rules Ajoutées**

Fichier : `addons/onedesk_core/data/onedesk_security_premium.xml`

#### 1️⃣ **website.website** (ROOT FIX - LE PLUS CRITIQUE)

```xml
<record id="rule_premium_manager_website" model="ir.rule">
    <field name="name">Premium Manager - Websites Own Company ONLY</field>
    <field name="model_id" ref="website.model_website"/>
    <field name="domain_force">[('company_id', '=', user.company_id.id)]</field>
    <field name="groups" eval="[(4, ref('group_onedesk_premium_manager'))]"/>
    <field name="perm_read">True</field>
    <field name="perm_write">True</field>
    <field name="perm_create">True</field>
    <field name="perm_unlink">False</field>
</record>
```

**Impact :** Chaque Premium Manager voit UNIQUEMENT le site web de sa company.

---

#### 2️⃣ **res.company** (Isolation Company)

```xml
<record id="rule_premium_manager_res_company" model="ir.rule">
    <field name="name">Premium Manager - Own Company ONLY</field>
    <field name="model_id" ref="base.model_res_company"/>
    <field name="domain_force">[('id', '=', user.company_id.id)]</field>
</record>
```

**Impact :** L'utilisateur ne voit QUE sa propre company dans les sélecteurs.

---

#### 3️⃣ **res.users** (Isolation Utilisateurs)

```xml
<record id="rule_premium_manager_res_users" model="ir.rule">
    <field name="name">Premium Manager - Users Own Company</field>
    <field name="model_id" ref="base.model_res_users"/>
    <field name="domain_force">[('company_id', '=', user.company_id.id)]</field>
</record>
```

**Impact :** Chaque Premium Manager voit uniquement les utilisateurs de sa company.

---

#### 4️⃣ **ir.sequence** (Séquences de Numérotation)

```xml
<record id="rule_premium_manager_ir_sequence" model="ir.rule">
    <field name="name">Premium Manager - Sequences Own Company</field>
    <field name="model_id" ref="base.model_ir_sequence"/>
    <field name="domain_force">['|', ('company_id', '=', False), ('company_id', '=', user.company_id.id)]</field>
</record>
```

**Impact :** Chaque company a ses propres séquences (factures, commandes, etc.)

---

#### 5️⃣ **mail.template** (Templates Email)

```xml
<record id="rule_premium_manager_mail_template" model="ir.rule">
    <field name="name">Premium Manager - Email Templates Own Company</field>
    <field name="model_id" ref="mail.model_mail_template"/>
    <field name="domain_force">['|', ('company_id', '=', False), ('company_id', '=', user.company_id.id)]</field>
</record>
```

**Impact :** Templates email personnalisés par company.

---

#### 6️⃣ **ir.actions.report** (Rapports)

```xml
<record id="rule_premium_manager_ir_act_report_xml" model="ir.rule">
    <field name="name">Premium Manager - Reports Own Company</field>
    <field name="model_id" ref="base.model_ir_actions_report"/>
    <field name="domain_force">['|', ('company_id', '=', False), ('company_id', '=', user.company_id.id)]</field>
    <field name="perm_read">True</field>
    <field name="perm_write">False</field>
</record>
```

**Impact :** Rapports isolés par company (lecture seule pour Premium).

---

## 🚀 Application de la Correction

### **Étape 1 : Update du Module**

```bash
# Option 1 : Via interface Odoo
Apps → Rechercher "OneDesk Core" → Mettre à jour

# Option 2 : Ligne de commande (RECOMMANDÉ)
sudo systemctl stop odoo
./odoo-bin -u onedesk_core -d VOTRE_BASE --stop-after-init
sudo systemctl start odoo
```

### **Étape 2 : Vérification Shell (Optionnel)**

```bash
./odoo-bin shell -d VOTRE_BASE
```

```python
# Vérifier qu'un Premium Manager ne voit qu'un seul site
premium_user = env['res.users'].search([
    ('groups_id', 'in', [env.ref('onedesk_core.group_onedesk_premium_manager').id])
], limit=1)

# Se connecter comme Premium Manager
env = env(user=premium_user.id)

# Tester la visibilité
websites = env['website'].search([])
print(f"✅ Nombre de sites visibles: {len(websites)}")
print(f"   Company du site: {websites.mapped('company_id.name')}")
# Devrait afficher: 1 site, company de l'utilisateur

companies = env['res.company'].search([])
print(f"✅ Nombre de companies visibles: {len(companies)}")
# Devrait afficher: 1 company

users = env['res.users'].search([])
print(f"✅ Nombre d'utilisateurs visibles: {len(users)}")
# Devrait afficher: uniquement les users de la company
```

---

## 🧪 Scénario de Test

### **Test 1 : Isolation Website**

1. Créer 2 companies : "Company A" et "Company B"
2. Créer 2 utilisateurs Premium Manager, un par company
3. Se connecter comme Premium Manager A
4. Aller dans Website → Configuration → Websites
5. **Résultat attendu :** Ne voit QUE le site de Company A

### **Test 2 : Isolation Utilisateurs**

1. Se connecter comme Premium Manager A
2. Aller dans Paramètres → Utilisateurs & Companies → Utilisateurs
3. **Résultat attendu :** Ne voit QUE les utilisateurs de Company A

### **Test 3 : Isolation Settings**

1. Se connecter comme Premium Manager A
2. Aller dans Paramètres → Général
3. Modifier un paramètre (ex: devise, langue)
4. Se connecter comme Premium Manager B
5. **Résultat attendu :** Les paramètres de B sont différents de A

---

## ⚠️ Avertissements

### **BREAKING CHANGE**

Cette correction peut **bloquer certains utilisateurs** qui étaient habitués à voir toutes les données.

**Si un utilisateur Premium se plaint :**

1. Vérifier qu'il a bien `company_id` défini
2. Vérifier qu'il est dans le bon groupe Premium Manager
3. Si besoin d'accès multi-company, le mettre dans `base.group_system` (Super Admin)

### **Migration de Données**

Si vous avez des **websites sans company_id**, assignez-les :

```python
./odoo-bin shell -d VOTRE_BASE
```

```python
# Trouver les sites sans company
websites_without_company = env['website'].sudo().search([
    ('company_id', '=', False)
])

if websites_without_company:
    # Assigner à la company par défaut
    default_company = env['res.company'].search([], limit=1)
    websites_without_company.write({'company_id': default_company.id})
    env.cr.commit()
    print(f"✅ {len(websites_without_company)} site(s) assigné(s) à {default_company.name}")
else:
    print("✅ Tous les sites ont une company_id")
```

---

## 📊 Résumé de l'Impact

| Modèle | Avant | Après | Impact |
|--------|-------|-------|--------|
| **website.website** | Tous | 1 (sa company) | 🔒 Isolation complète |
| **res.company** | Toutes | 1 (la sienne) | 🔒 Privacy |
| **res.users** | Tous | Users de sa company | 🔒 Privacy |
| **ir.sequence** | Toutes | Sa company + shared | ✅ Numérotation isolée |
| **mail.template** | Tous | Sa company + shared | ✅ Templates isolés |
| **ir.actions.report** | Tous | Sa company + shared | ✅ Reports isolés |

---

## 🎯 Checklist Post-Déploiement

- [ ] Module onedesk_core mis à jour
- [ ] Redémarrage Odoo effectué
- [ ] Test isolation website (Premium voit 1 seul site)
- [ ] Test isolation users (Premium voit ses users uniquement)
- [ ] Test création contact (pas d'erreur res.partner)
- [ ] Test paramètres (settings isolés par company)
- [ ] Vérifier aucun utilisateur bloqué
- [ ] Migration websites sans company_id (si applicable)

---

## 📞 Support

Si après cette correction, un utilisateur Premium Manager ne peut plus accéder à certaines fonctionnalités :

1. **Vérifier `company_id` de l'utilisateur :**
   ```python
   user = env['res.users'].browse(USER_ID)
   print(f"Company: {user.company_id.name}")
   ```

2. **Vérifier les groupes :**
   ```python
   print(user.groups_id.mapped('name'))
   ```

3. **Solution temporaire (bypass toutes règles) :**
   ```python
   user.write({'groups_id': [(4, env.ref('base.group_system').id)]})
   env.cr.commit()
   ```

---

## ✅ Conclusion

Cette correction établit une **isolation multi-tenant stricte** pour le groupe Premium Manager, garantissant que chaque client ne voit QUE ses propres données (website, utilisateurs, paramètres, etc.).

**Commit :** `66bb3810` - 🔒 SECURITY: Isolation multi-tenant Premium Manager
**Fichier modifié :** `addons/onedesk_core/data/onedesk_security_premium.xml`
**Lignes ajoutées :** +76
**Date :** 2025-12-11
