# Configuration SaaS Multi-Tenant

## 🎉 Détection Automatique de la Base Maître

**Bonne nouvelle !** Le système détecte automatiquement votre base de données maître (celle qui contient les modèles SaaS).

### Comment ça fonctionne ?

Le système cherche automatiquement quelle base contient la table `saas_client` :

1. **Cache** : Utilise le cache si déjà détecté (performance)
2. **Base actuelle** : Vérifie d'abord la base de la requête en cours
3. **Scan PostgreSQL** : Si nécessaire, scanne toutes les bases pour trouver celle avec `saas_client`

**Aucune configuration manuelle requise !** ✨

### Vérification de la détection

Au démarrage, vous verrez dans les logs :

```
[SAAS] Base maître détectée automatiquement: base3
```

Lors du blocage d'une base suspendue :
```
[SAAS] Accès refusé à onedesk_client_1_test - État: suspended
```

## Protection active

Une fois la base maître détectée :
- ✅ Le système bloque automatiquement l'accès aux bases suspendues/terminées
- ✅ Les clients ne peuvent plus se connecter si leur abonnement est annulé
- ✅ Protection complète du système SaaS sans configuration
- 🚀 Performance optimale grâce au cache

## Autres variables d'environnement optionnelles

```bash
# Credentials PostgreSQL (pour plus de sécurité)
export SAAS_DB_HOST=localhost
export SAAS_DB_PORT=5432
export SAAS_DB_USER=odoo
export SAAS_DB_PASSWORD=votre_password
```

Ces variables permettent de ne pas stocker les credentials dans la config Odoo accessible via l'API.
