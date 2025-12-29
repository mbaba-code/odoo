# Configuration SaaS Multi-Tenant

## Variable d'environnement requise

Pour que le système de suspension/terminaison des bases de données fonctionne correctement, vous devez configurer le nom de votre base de données maître (celle qui contient les modèles SaaS).

### Méthode 1 : Variable d'environnement (recommandé)

```bash
export SAAS_MASTER_DATABASE=votre_base_principale
```

Exemple pour votre configuration actuelle :
```bash
export SAAS_MASTER_DATABASE=base3
```

### Méthode 2 : Fichier de configuration Odoo

Ajoutez cette ligne dans votre fichier `odoo.conf` :

```ini
[options]
saas_master_database = base3
```

### Méthode 3 : Au démarrage d'Odoo

```bash
odoo-bin -c odoo.conf --saas-master-database=base3
```

## Pourquoi cette configuration est nécessaire ?

Le système SaaS doit vérifier l'état des bases de données clients (active/suspended/terminated) avant de permettre l'accès. Pour cela, il doit se connecter à la base maître qui contient la table `saas_client`.

Sans cette configuration :
- ✅ Le système fonctionne normalement
- ⚠️ Mais la vérification de suspension/terminaison est désactivée (pour éviter des erreurs)

Avec cette configuration :
- ✅ Le système bloque l'accès aux bases suspendues/terminées
- ✅ Les clients ne peuvent plus se connecter si leur abonnement est annulé
- ✅ Protection complète du système SaaS

## Vérification de la configuration

Vous pouvez vérifier que la configuration est correcte en regardant les logs Odoo :

```
[SAAS] Subdomain 'test' → Database: onedesk_client_1_test
[SAAS] Accès refusé à onedesk_client_1_test - État: suspended
```

Si vous voyez des erreurs comme :
```
[SAAS] Erreur vérification accès base: database "onedesk_core" does not exist
```

C'est que la base maître n'est pas correctement configurée.

## Autres variables d'environnement optionnelles

```bash
# Credentials PostgreSQL (pour plus de sécurité)
export SAAS_DB_HOST=localhost
export SAAS_DB_PORT=5432
export SAAS_DB_USER=odoo
export SAAS_DB_PASSWORD=votre_password
```

Ces variables permettent de ne pas stocker les credentials dans la config Odoo accessible via l'API.
