# Tests pour onedesk_core

Ce dossier contient la suite de tests pour le module `onedesk_core`.

## Structure des tests

### test_reservation.py
Tests pour le modèle `onedesk.reservation`:
- Création de réservations
- Calcul du nombre de nuits
- Détection des chevauchements
- Vérification de disponibilité
- Envoi d'email de confirmation
- Transitions de statut

### test_unit.py
Tests pour le modèle `onedesk.unit`:
- Création d'unités
- Équipements et commodités
- Calcul des tarifs
- Gestion des images
- Statut actif/inactif

### test_property.py
Tests pour le modèle `onedesk.property`:
- Création de propriétés
- Gestion des unités associées
- Galerie d'images
- Types de propriétés
- IDs d'intégration externes

### test_integration.py
Tests d'intégration:
- Workflows complets de réservation
- Réservations multiples
- Vérification de disponibilité complexe
- Intégration email
- Recherche et filtrage

## Exécution des tests

### Exécuter tous les tests du module
```bash
python manage.py test --addon onedesk_core
```

### Exécuter un fichier de test spécifique
```bash
python manage.py test --addon onedesk_core --test-file test_reservation
```

### Exécuter une classe de test spécifique
```bash
python manage.py test --addon onedesk_core.tests.test_reservation.TestOneDeskReservation
```

### Exécuter une méthode de test spécifique
```bash
python manage.py test --addon onedesk_core.tests.test_reservation.TestOneDeskReservation.test_reservation_creation
```

### Avec Odoo CLI
```bash
odoo -d test_db -i onedesk_core --test-enable --stop-after-init
```

### Avec PyTest (si configuré)
```bash
pytest addons/onedesk_core/tests/
```

## Couverture de test

Total: **60+ tests** couvrant:
- ✅ Création de modèles
- ✅ Validation des données
- ✅ Contraintes de base de données
- ✅ Workflows métier
- ✅ Intégrations
- ✅ Gestion d'erreurs

## Dépendances

Les tests nécessitent:
- Odoo 19+
- Modules: sale, account, mail, website
- Base de données de test

## Notes

- Tous les tests utilisent `TransactionCase` (rollback automatique)
- Les données de test sont créées en setUp()
- Les tests sont indépendants et peuvent être exécutés dans n'importe quel ordre
- Les tests utilisent des dates relatives (datetime.now() + timedelta)

## Améliorations futures

- [ ] Tests de performance
- [ ] Tests d'API HTTP (booking endpoint)
- [ ] Tests de permissions et sécurité
- [ ] Tests avec différents scénarios de fuseaux horaires
- [ ] Tests de migration
- [ ] Tests de rapports et statistiques
