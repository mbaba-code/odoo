# Tests pour website_onedesk

Ce dossier contient la suite de tests pour le module `website_onedesk`.

## Structure des tests

### test_booking_controller.py
Tests pour le contrôleur de booking:
- Création de réservations via le contrôleur
- Validation des données de booking
- Gestion des unités invalides
- Envoi de confirmation email
- Validation des dates
- Prévention des réservations chevauchantes
- Notes du client
- Demandes spéciales

### test_availability.py
Tests pour la vérification de disponibilité:
- Disponibilité pour unités vides
- Détection des réservations existantes
- Disponibilité avant/après des réservations
- Chevauchements partiels
- Réservations annulées ne bloquant pas
- Indépendance per unité
- Checkout/check-in même jour
- Réservations long terme

## Exécution des tests

### Exécuter tous les tests du module
```bash
python manage.py test --addon website_onedesk
```

### Exécuter un fichier de test spécifique
```bash
python manage.py test --addon website_onedesk --test-file test_booking_controller
```

### Exécuter une classe de test spécifique
```bash
python manage.py test --addon website_onedesk.tests.test_booking_controller.TestBookingController
```

### Exécuter une méthode de test spécifique
```bash
python manage.py test --addon website_onedesk.tests.test_availability.TestAvailabilityCheck.test_unit_availability_empty
```

## Couverture de test

Total: **20+ tests** couvrant:
- ✅ Validation du formulaire de booking
- ✅ Gestion des erreurs
- ✅ Logique de disponibilité
- ✅ Envoi d'emails
- ✅ Cas limites (chevauchements, dates invalides)
- ✅ Indépendance des unités

## Dépendances

Les tests nécessitent:
- Odoo 19+
- Module onedesk_core
- Modules: website, mail
- Base de données de test

## Test Data Setup

Chaque test crée:
- 1 Propriété de test
- 1 Unité de test
- 1+ Clients/Partenaires de test
- Réservations de test selon les besoins

## Cas de test principaux

### Booking Controller
1. **test_booking_with_valid_data** - Réservation valide
2. **test_booking_with_missing_field** - Champ manquant
3. **test_booking_with_invalid_unit** - Unité invalide
4. **test_booking_confirmation_email** - Email confirmé
5. **test_booking_overlapping_dates** - Dates qui se chevauchent
6. **test_booking_guest_notes** - Notes du client
7. **test_booking_special_requests** - Demandes spéciales

### Availability Check
1. **test_unit_availability_empty** - Unité vide
2. **test_unit_availability_with_booking** - Avec réservation existante
3. **test_unit_availability_before_booking** - Avant une réservation
4. **test_unit_availability_after_booking** - Après une réservation
5. **test_unit_availability_partial_overlap** - Chevauchement partiel
6. **test_cancelled_reservation_not_blocking** - Réservation annulée
7. **test_multiple_units_independent_availability** - Unités multiples
8. **test_long_term_availability** - Réservations long terme

## Scénarios Edge Cases

✓ Chevauchement exact des dates
✓ Réservation d'un jour
✓ Réservations très longues (30+ jours)
✓ Checkout/check-in le même jour
✓ Réservations multiples pour un même client
✓ Réservations sur unités différentes
✓ Réservations annulées

## Notes importantes

- Les tests simulent des demandes HTTP de booking
- Les dates utilisent `datetime.now() + timedelta` (relatives)
- Chaque test est isolé et indépendant
- Utilisation de `TransactionCase` pour le rollback automatique
- Les validations métier sont testées (chevauchements, etc.)

## Améliorations futures

- [ ] Tests de contrôleur HTTP (POST /onedesk/booking)
- [ ] Tests de validation du formulaire website
- [ ] Tests de sécurité CSRF
- [ ] Tests de pagination sur listing
- [ ] Tests de filtrage avancé
- [ ] Tests de performance (bulk bookings)
- [ ] Tests avec différentes devises/taxes

## Dépannage

### Erreur: "Unit not found"
Vérifier que la propriété et l'unité sont créées dans setUp()

### Erreur: "Overlapping reservations"
Cela est attendu pour les tests de chevauchement - voir la validation

### Erreur: "CSRF token"
Les tests simulent les données, pas les requêtes HTTP réelles
