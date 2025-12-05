# Configuration API Sirene - Guide Sécurisé

## 🔒 Méthode Sécurisée (RECOMMANDÉE)

Votre clé API est maintenant stockée dans les **paramètres système Odoo** au lieu d'être en dur dans le code. C'est la meilleure pratique !

### ✅ Avantages :
- ✅ Pas de clé API dans le code source
- ✅ Pas de clé dans Git/GitHub
- ✅ Configuration facile via l'interface Odoo
- ✅ Une seule clé pour toute l'installation

---

## ⚠️ IMPORTANT : Mode SIMPLE OBLIGATOIRE

**L'API Sirene Public fonctionne uniquement en mode "SIMPLE"**

- ✅ Mode SIMPLE = FONCTIONNE
- ❌ Mode Backend-to-Backend = NE FONCTIONNE JAMAIS

**Header d'authentification :**
```
X-INSEE-Api-Key-Integration: VOTRE_CLE_API
```

⚠️ **PAS** `Authorization: Bearer` (provoque erreur 401)

---

## 📋 Configuration en 3 étapes

### **Étape 1 : Obtenir votre clé API gratuite**

1. Allez sur https://portail-api.insee.fr/
2. Créez un compte (gratuit)
3. Créez une application en mode **"SIMPLE"** (obligatoire!)
4. Souscrivez au plan "Public" de l'API Sirene
5. Copiez votre clé API (ex: `699b7729-261f-4f02-9b77-29261faf02a2`)

### **Étape 2 : Configurer dans Odoo**

**Option A : Via l'interface (MODE DEBUG activé)**

1. Activez le mode développeur :
   - Paramètres → Activer le mode développeur

2. Allez dans :
   ```
   Paramètres → Technique → Paramètres Système
   ```

3. Cliquez sur **"Créer"**

4. Remplissez :
   - **Clé** : `onedesk.sirene_api_key`
   - **Valeur** : Collez votre clé API (ex: `Bearer_xxxxxxxxxxxxx`)

5. Sauvegardez

**Option B : Via ligne de commande Python (depuis le shell Odoo)**

```python
# Ouvrir le shell Odoo
# Puis exécuter :

self.env['ir.config_parameter'].sudo().set_param('onedesk.sirene_api_key', 'VOTRE_CLE_API_ICI')
```

### **Étape 3 : Tester l'import**

1. Allez dans : **Équipe → 🚀 Import Conciergeries**
2. Configurez vos critères de recherche
3. Cliquez sur **"🚀 LANCER L'IMPORT"**

Si tout fonctionne, vous verrez dans les logs :
```
Appel API Sirene avec clé authentifiée...
API Sirene: X résultats trouvés
```

---

## 🔍 Vérification du mode actif

### **MODE DÉMO** (aucune clé configurée)
```
Mode DÉMO activé - Aucune clé API Sirene configurée
→ Importe 3 contacts fictifs
```

### **MODE PRODUCTION** (clé API configurée)
```
Appel API Sirene avec clé authentifiée...
API Sirene: 127 résultats trouvés
→ Importe de vraies conciergeries françaises
```

---

## ❌ Erreurs possibles et solutions

### **Erreur 401 - Unauthorized**
```
Clé API Sirene invalide
```
**Solution** : Vérifiez que votre clé est correcte et commence bien par "Bearer_"

### **Erreur 429 - Too Many Requests**
```
Limite de requêtes API atteinte
```
**Solution** : Attendez quelques minutes. L'API gratuite a des limites de taux.

### **Erreur de connexion**
```
Erreur de connexion à l'API Sirene
```
**Solution** : Vérifiez votre connexion Internet

---

## 🔐 Sécurité

### ✅ Ce qui est SÉCURISÉ :
- Clé stockée dans la base de données Odoo
- Accessible uniquement aux administrateurs système
- Pas dans le code source
- Pas dans Git/GitHub

### ❌ Ce qui est DANGEREUX (à éviter) :
- ❌ Mettre la clé en dur dans le code Python
- ❌ Commiter la clé dans Git
- ❌ Partager la clé publiquement

---

## 📊 Limites de l'API gratuite

L'API Sirene gratuite de l'INSEE a des limites :
- **30 requêtes par minute**
- **1000 requêtes par jour**
- **50 000 requêtes par mois**

Pour la plupart des usages, c'est largement suffisant !

---

## 🆘 Support

Si vous avez des problèmes :
1. Vérifiez les logs Odoo pour voir les messages d'erreur détaillés
2. Vérifiez que votre clé API est valide sur api.insee.fr
3. Testez d'abord en mode DÉMO (sans clé) pour vérifier que le reste fonctionne

---

## 🎯 Pour désactiver l'API et revenir en mode DÉMO

Supprimez simplement le paramètre système :
```
Paramètres → Technique → Paramètres Système
→ Chercher "onedesk.sirene_api_key"
→ Supprimer
```

Le système repassera automatiquement en mode DÉMO.
