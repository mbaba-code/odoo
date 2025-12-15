# 🐛 Solution: Erreur d'Accès res.partner

## ❌ Le Problème

```
Erreur d'accès

Désolé, Administrator (id=2) n'a pas d'accès 'créer' à :
- Contact, merveillesbaba@gmail.com (res.partner: 1755)

La faute aux règles suivantes :
- res.partner company
```

---

## 🔍 Diagnostic

L'erreur persiste car **les modifications du code ne sont PAS automatiquement appliquées dans Odoo**. Il faut mettre à jour le module!

### Causes Possibles

1. **Module non mis à jour** (le plus probable)
   - Les nouvelles règles ne sont pas chargées en base
   - Odoo utilise encore les anciennes règles

2. **Company_id différent**
   - Le contact appartient à une company X
   - L'admin appartient à une company Y
   - Les règles bloquent l'accès

3. **Règles conflictuelles**
   - Plusieurs règles s'appliquent
   - Une règle plus restrictive bloque

---

## ✅ SOLUTION 1: Mettre à Jour le Module (OBLIGATOIRE)

### Option A: Interface Web (Recommandé)

1. **Allez dans: Apps** (Applications)
   ![Apps Menu](https://i.imgur.com/example.png)

2. **Recherchez: "OneDesk Core"**
   - Utilisez la barre de recherche

3. **Cliquez sur: ⋮** (trois points verticaux)
   - Sélectionnez: **"Mettre à jour"**

4. **Confirmez la mise à jour**
   - Attendez que le processus se termine
   - Rechargez la page (F5)

### Option B: Ligne de Commande

```bash
cd /home/user/odoo

# 1. Arrêter Odoo
sudo systemctl stop odoo

# 2. Mettre à jour le module
./odoo-bin -u onedesk_core -d VOTRE_BASE_DE_DONNEES --stop-after-init

# 3. Redémarrer Odoo
sudo systemctl start odoo
```

**Remplacez `VOTRE_BASE_DE_DONNEES` par le nom de votre base Odoo**

---

## 🔧 SOLUTION 2: Diagnostic Approfondi

Si après mise à jour l'erreur persiste, exécutez le script de diagnostic:

```bash
cd /home/user/odoo

# Option 1: Shell Odoo interactif
./odoo-bin shell -d VOTRE_BASE

# Puis copiez-collez le script depuis: diagnose_partner_access.py
```

### Commandes de Diagnostic Manuelles

```python
# Dans le shell Odoo:

# 1. Vérifier le contact
contact = env['res.partner'].sudo().browse(1755)
print(f"Contact company: {contact.company_id.name if contact.company_id else 'PARTAGÉ'}")

# 2. Vérifier l'admin
admin = env['res.users'].browse(2)
print(f"Admin company: {admin.company_id.name}")

# 3. Comparer
if contact.company_id and contact.company_id != admin.company_id:
    print("⚠️  PROBLÈME: Company différente!")
```

---

## 🛠️ SOLUTION 3: Corrections Spécifiques

### Cas 1: Contact avec company_id différent

```python
# Shell Odoo:

# Solution A: Mettre le contact en mode PARTAGÉ (recommandé)
contact = env['res.partner'].sudo().browse(1755)
contact.write({'company_id': False})
print("✅ Contact mis en mode partagé")

# Solution B: Changer la company du contact
contact = env['res.partner'].sudo().browse(1755)
admin = env['res.users'].browse(2)
contact.write({'company_id': admin.company_id.id})
print("✅ Contact déplacé vers la company de l'admin")
```

### Cas 2: Admin sans droits suffisants

```python
# Shell Odoo:

# Ajouter l'admin au groupe System (TOUS les droits)
admin = env['res.users'].browse(2)
admin.write({'groups_id': [(4, env.ref('base.group_system').id)]})
print("✅ Admin ajouté au groupe System")
```

### Cas 3: Règles pas à jour

```python
# Shell Odoo:

# Vérifier la règle
rule = env['ir.rule'].search([('name', '=', 'Property Manager - Company Partners')], limit=1)
print(f"Règle actuelle: {rule.domain_force}")

# Si la règle ne contient pas '|', elle n'est pas à jour!
# → Retour SOLUTION 1: Mettre à jour le module
```

---

## 📋 Vérification Post-Correction

### 1. Vérifier les Règles dans l'Interface

```
Paramètres → Technique → Sécurité → Règles d'enregistrement
```

Cherchez: **"Property Manager - Company Partners"**

**Domain Force doit contenir:**
```python
['|', ('company_id', '=', False), ('company_id', '=', user.company_id.id)]
```

### 2. Tester la Création de Contact

1. Allez dans: **Contacts**
2. Cliquez: **Créer**
3. Remplissez:
   - Nom: Test Contact
   - Email: test@example.com
   - **NE PAS remplir company** (laisser vide = partagé)
4. Cliquez: **Enregistrer**

**Résultat attendu:** ✅ Le contact est créé sans erreur

---

## 🎯 Résumé des Étapes

```
┌─────────────────────────────────────────────┐
│ 1. MISE À JOUR MODULE (OBLIGATOIRE)        │
│    Apps → OneDesk Core → Mettre à jour     │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 2. TESTER                                   │
│    Créer un contact sans company_id         │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 3. SI ERREUR PERSISTE                       │
│    Exécuter: diagnose_partner_access.py     │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 4. APPLIQUER CORRECTIONS SPÉCIFIQUES        │
│    Selon diagnostic (voir SOLUTION 3)       │
└─────────────────────────────────────────────┘
```

---

## 📞 Support

Si le problème persiste après toutes ces étapes:

1. **Collecter les logs:**
   ```bash
   tail -f /var/log/odoo/odoo-server.log
   ```

2. **Exécuter le diagnostic complet:**
   ```bash
   ./odoo-bin shell -d VOTRE_BASE < diagnose_partner_access.py > diagnostic.txt
   ```

3. **Partager:**
   - Le fichier `diagnostic.txt`
   - Les dernières lignes du log Odoo
   - La capture d'écran de l'erreur

---

## 🔑 Points Clés

✅ **Les modifications du code ne sont PAS automatiques**
- Toujours mettre à jour le module après un git pull

✅ **Les contacts peuvent être PARTAGÉS**
- `company_id = False` → visible par tous

✅ **L'isolation multi-tenant fonctionne**
- Les contacts avec `company_id` sont isolés
- Chaque client voit uniquement ses contacts

✅ **Les règles s'appliquent en cascade**
- Plusieurs règles peuvent s'appliquer
- La plus restrictive gagne

---

## 📚 Fichiers Modifiés

```
✅ addons/onedesk_core/data/onedesk_security.xml
   - Règles Property Manager, Staff, Viewer

✅ addons/onedesk_core/data/onedesk_security_premium.xml
   - Règles Premium Manager

✅ addons/onedesk_core/data/onedesk_groups.xml
   - Groupe Premium Manager

✅ addons/onedesk_core/__manifest__.py
   - Chargement des nouveaux fichiers
```

**Commit:** `3e29413b` - 🐛 FIX: Correction règles d'accès res.partner trop restrictives

---

## ✅ Après Correction

Une fois le module mis à jour, vous pourrez:

1. ✅ Créer des contacts sans company_id (partagés)
2. ✅ Créer des contacts avec votre company_id
3. ✅ Accéder aux contacts partagés
4. ❌ NE PAS voir les contacts d'autres companies (isolation maintenue)

**L'isolation multi-tenant reste intacte! 🔒**
