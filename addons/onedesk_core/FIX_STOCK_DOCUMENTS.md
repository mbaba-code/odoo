# 🔧 Fix Stock de Documents - Guide Étape par Étape

## ❌ Le Problème
Le menu **📦 Stock de documents** affiche une liste vide, même si les documents sont visibles dans le menu **✍️ Envoyer pour signature**.

## ✅ La Solution (4 étapes simples)

### **Étape 1: Mettre à jour le module (CRITIQUE)**
```
1. Allez à: Applications
2. Cherchez: "onedesk_core"
3. Cliquez sur le module "onedesk_core"
4. Cliquez sur le bouton "Mettre à jour"
5. Attendez 30-60 secondes jusqu'à ce que la mise à jour soit complète
```

### **Étape 2: Rafraîchir le navigateur**
```
Windows/Linux: Ctrl+F5
Mac: Cmd+Shift+R
```

### **Étape 3: Retester le menu Stock**
```
1. Allez à: 📄 Documents → 📦 Stock de documents
2. Vous devriez maintenant voir une liste de documents
3. Si la liste est vide, continuez à l'Étape 4
```

### **Étape 4: Si ça ne marche pas encore...**

#### Option A: Redémarrer le serveur Odoo
```bash
# Arrêtez le serveur
Ctrl+C

# Attendez 2-3 secondes

# Redémarrez le serveur
odoo -c /home/user/odoo.conf
```

#### Option B: Forcer la réinstallation du module
```
1. Applications → Modules installés
2. Cherchez "onedesk_core"
3. Cliquez sur le menu ⋮ (trois points)
4. Cliquez "Désinstaller"
5. Attendez que ce soit terminé
6. Allez à Applications → Tous → Cherchez "onedesk_core"
7. Cliquez "Installer"
8. Attendez 60-90 secondes
9. Retestez le menu Stock
```

---

## 🔍 Vérification: Est-ce que ça marche?

### ✅ Vous verrez...
- Une liste de documents dans le menu Stock
- Chaque document avec son nom, type, catégorie, localisation, etc.
- Possibilité de cliquer sur un document pour le modifier

### ❌ Si ça ne marche toujours pas...
Vérifiez que:
1. **Au moins un document existe**: Allez à "✍️ Envoyer pour signature" et vérifiez qu'il y a des documents
2. **Le module a bien été mis à jour**: Cherchez "onedesk_core" et vérifiez la version
3. **Pas d'erreurs dans les logs**: Consultez `/tmp/odoo.log` pour voir s'il y a des messages d'erreur

---

## 📝 Ce qui a été corrigé

**Commit 8fa6c790**: Création de vues séparées pour le menu Stock
- ✅ Nouvelle liste dédiée au stockage (affiche catégorie, localisation)
- ✅ Nouveau kanban groupé par catégorie (pas par statut)
- ✅ Utilise le formulaire de stockage (pas le formulaire de signature)

**Commit 0f181f97**: Domaine explicite pour Stock
- ✅ Domain = [] (affiche TOUS les documents, aucun filtrage)

**Commit faf639c8**: Context pour éviter les filtres cachés
- ✅ Désactive les filtres de recherche par défaut

---

## 💡 Explication du problème

Avant le fix, les menus "Envoyer" et "Stock" partageaient les MÊMES listes et kanban. Cela causait une confusion de routage vers la bonne vue formulaire.

Maintenant:
- **Envoyer**: Utilise `view_document_list` et `view_document_kanban` → `view_document_form_send`
- **Stock**: Utilise `view_document_list_stock` et `view_document_kanban_stock` → `view_document_form_stock`

Chaque menu a sa propre expérience utilisateur optimisée. ✅

---

## ⚡ TL;DR - Résumé Rapide

```
1. Applications → Cherchez "onedesk_core" → Mettre à jour ⏳
2. Ctrl+F5 pour rafraîchir le navigateur 🔄
3. Allez à 📦 Stock de documents → Vous devriez voir les documents ✅
```

Si ça ne marche pas après ces 2 étapes, redémarrez le serveur Odoo.
