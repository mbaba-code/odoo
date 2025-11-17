# Stratégie de Test - OneDesk Module

## Vue d'ensemble

Ce document décrit la stratégie de test complète pour les modules OneDesk (onedesk_core et website_onedesk).

## Structure des tests

```
addons/
├── onedesk_core/
│   └── tests/
│       ├── __init__.py
│       ├── README.md
│       ├── test_reservation.py      (12 tests)
│       ├── test_unit.py             (8 tests)
│       ├── test_property.py         (8 tests)
│       └── test_integration.py      (10 tests)
└── website_onedesk/
    └── tests/
        ├── __init__.py
        ├── README.md
        ├── test_booking_controller.py (9 tests)
        └── test_availability.py      (10 tests)
```

## Résumé des tests

### onedesk_core (38 tests)

#### test_reservation.py (12 tests)
- ✓ Création de réservation
- ✓ Calcul des nuits
- ✓ Détection chevauchement
- ✓ Réservations annulées
- ✓ Vérification disponibilité
- ✓ Email de confirmation
- ✓ Transitions de statut
- ✓ Notes spéciales
- ✓ Notes internes
- ✓ Partenaires multiples
- ✓ Données complètes
- ✓ Cas limites

#### test_unit.py (8 tests)
- ✓ Création d'unité
- ✓ Équipements/commodités
- ✓ Calcul de tarif
- ✓ Gestion d'images
- ✓ Unités multiples
- ✓ Statut actif/inactif
- ✓ Description et détails
- ✓ Types d'unités

#### test_property.py (8 tests)
- ✓ Création de propriété
- ✓ Unités associées
- ✓ Galerie d'images
- ✓ Données de localisation
- ✓ Commodités
- ✓ Types de propriétés
- ✓ Statut
- ✓ IDs d'intégration

#### test_integration.py (10 tests)
- ✓ Workflow complet réservation
- ✓ Réservations multiples (unités différentes)
- ✓ Propriété avec données complètes
- ✓ Intégration email
- ✓ Recherche et filtrage
- ✓ Vérification disponibilité
- ✓ Réservations clients multiples
- ✓ Transitions de statut
- ✓ Gestion d'images
- ✓ Cas limites

### website_onedesk (19 tests)

#### test_booking_controller.py (9 tests)
- ✓ Booking avec données valides
- ✓ Champ manquant
- ✓ Unité invalide
- ✓ Email de confirmation
- ✓ Validation des dates
- ✓ Chevauchement empêché
- ✓ Notes du client
- ✓ Demandes spéciales
- ✓ Validation formulaire

#### test_availability.py (10 tests)
- ✓ Unité vide
- ✓ Avec réservation
- ✓ Avant réservation
- ✓ Après réservation
- ✓ Chevauchement partiel
- ✓ Réservation annulée
- ✓ Unités indépendantes
- ✓ Checkout/check-in même jour
- ✓ Réservations long terme
- ✓ Gestion erreurs

## Niveaux de test

### 1. Tests Unitaires (24)
Testent les modèles individuels en isolation:
- Création d'objets
- Validation des champs
- Calculs et formules
- Contraintes de base de données

**Fichiers**: test_reservation.py, test_unit.py, test_property.py

### 2. Tests d'Intégration (15)
Testent l'interaction entre modèles:
- Workflows multiples modèles
- Relation parent-enfant
- Cascades de suppression
- Dépendances métier

**Fichiers**: test_integration.py, test_booking_controller.py, test_availability.py

### 3. Tests Fonctionnels (19)
Testent les fonctionnalités métier:
- Disponibilité des unités
- Chevauchement de réservations
- Workflow de booking
- Calcul des tarifs

**Fichiers**: test_availability.py, test_booking_controller.py

## Couverture par domaine

### Réservations (15 tests)
- Création ✓
- Validation ✓
- Chevauchement ✓
- Statut workflow ✓
- Disponibilité ✓
- Email ✓
- Cas limites ✓

### Unités (11 tests)
- Création ✓
- Commodités ✓
- Tarification ✓
- Images ✓
- Disponibilité ✓
- Propriétés ✓
- Cas limites ✓

### Propriétés (12 tests)
- Création ✓
- Unités ✓
- Images ✓
- Localisation ✓
- Intégration ✓
- Recherche ✓
- Types ✓

### Booking Website (9 tests)
- Validation formulaire ✓
- Création réservation ✓
- Erreurs ✓
- Email confirmation ✓
- Cas limites ✓

### Disponibilité (10 tests)
- Calcul ✓
- Chevauchement ✓
- Périodes ✓
- Annulation ✓
- Cas limites ✓
- Long terme ✓
- Multiples unités ✓

## Exécution des tests

### Tous les tests
```bash
python manage.py test --addon onedesk_core,website_onedesk
```

### Par module
```bash
python manage.py test --addon onedesk_core
python manage.py test --addon website_onedesk
```

### Par suite
```bash
python manage.py test --addon onedesk_core.tests.test_reservation
python manage.py test --addon website_onedesk.tests.test_availability
```

### Test spécifique
```bash
python manage.py test --addon onedesk_core.tests.test_reservation.TestOneDeskReservation.test_reservation_creation
```

### Avec coverage
```bash
coverage run --source addons manage.py test
coverage report
coverage html
```

## Outils utilisés

- **Test Framework**: Odoo TransactionCase
- **Assertions**: unittest.TestCase
- **Date Handling**: datetime, timedelta
- **Mocking**: Simulations de demandes HTTP

## Données de test

### Setup par test
```python
def setUp(self):
    # Crée propriété, unité, client
    # Isolation complète entre tests
    # Rollback automatique après chaque test
```

### Données persistantes
- Aucune - tests isolés
- Utilise TransactionCase (rollback)
- Base de données fraîche pour chaque test

## Assertions principales

- `assertIsNotNone()` - Objet créé
- `assertEqual()` - Valeur correcte
- `assertTrue()/False()` - Conditions
- `assertRaises()` - Exceptions
- `assertGreater()` - Comparaisons

## Cas de test critiques

### Sécurité
- ✓ Validation des dates
- ✓ Prévention chevauchement
- ✓ Gestion d'erreurs

### Métier
- ✓ Calcul nuits
- ✓ Tarification
- ✓ Statuts workflow
- ✓ Email confirmation

### Intégration
- ✓ Réservation ↔ Unité
- ✓ Unité ↔ Propriété
- ✓ Client ↔ Réservation
- ✓ Website ↔ Backend

## Résultats attendus

- ✅ **57 tests au total**
- ✅ **100% des tests passent**
- ✅ **Couverture complète** des modèles
- ✅ **Cas limites** couverts
- ✅ **Intégrations** testées
- ✅ **Erreurs** gérées

## Maintenance

### Ajouter un test
1. Créer méthode `test_*()` dans la classe appropriée
2. Utiliser setUp() pour les données
3. Documenter l'intention du test
4. Utiliser assertions explicites

### Modifier un test
1. Vérifier qu'il ne devient pas trop complexe
2. Garder les tests indépendants
3. Mettre à jour la documentation
4. Tester localement avant commit

### Supprimer un test
1. Vérifier qu'il ne teste plus un cas pertinent
2. Commenter pour expliquer la suppression
3. Vérifier que la couverture ne baisse pas
4. Documenter dans le changelog

## Bonnes pratiques

✓ Un test = une fonctionnalité
✓ Tests indépendants
✓ Noms de test clairs
✓ Setup/teardown complet
✓ Assertions explicites
✓ Pas de dépendances hardcoded
✓ Dates relatives (not hardcoded)
✓ Documentation inline

## Problèmes connus

### À tester
- [ ] Tests HTTP complets
- [ ] Tests de performance
- [ ] Tests de permission/sécurité
- [ ] Tests de fuseaux horaires
- [ ] Tests de migrations
- [ ] Tests de rapports

### À améliorer
- Ajouter des fixtures réutilisables
- Ajouter des factories pour les données
- Ajouter des tests de performance
- Augmenter la couverture

## Objectifs de couverture

- **Couverture code**: 85%+
- **Couverture tests**: 100% des workflows critiques
- **Temps exécution**: < 60s pour tous les tests
- **Pass rate**: 100%

## Ressources

- [Docs Odoo Testing](https://www.odoo.com/documentation/master/developer/reference/backend/testing.html)
- [TransactionCase](https://www.odoo.com/documentation/master/developer/reference/backend/orm.html)
- [Assertions](https://docs.python.org/3/library/unittest.html#test-cases)
