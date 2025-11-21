# Guide de Test pour OneDesk Core et Website OneDesk

Ce document explique comment exécuter les tests complets pour les modules OneDesk.

## Architecture des Tests

### 1. OneDesk Core (`onedesk_core/tests/`)

#### test_subscription_system.py
Tests complets du système d'abonnement OneDesk, couvrant:

**Tests de Création:**
- `test_subscription_creation()` - Création basique d'un abonnement
- `test_subscription_with_properties_count()` - Vérification du calcul des propriétés
- `test_property_creation_with_plan_limit_check()` - Création avec vérification des limites
- `test_unit_creation_with_plan_limit_check()` - Création d'unité avec vérification

**Tests de Gestion d'État:**
- `test_subscription_suspend_action()` - Suspension et révocation de groupes
- `test_subscription_reactivate_action()` - Réactivation et restauration d'accès
- `test_subscription_state_transitions()` - Transitions d'état complètes
- `test_subscription_plan_enforcement()` - Application des limites du plan

**Tests de Contrôle d'Accès:**
- `test_client_suspension_revokes_access()` - Suspension de client révoque accès
- `test_access_rules_master_admin()` - Accès Master Admin
- `test_access_rules_property_manager()` - Accès Property Manager

**Tests de Logs et Synchronisation:**
- `test_audit_log_creation()` - Création de journaux d'audit
- `test_bidirectional_sync_subscription_to_client()` - Synchronisation bidirectionnelle

### 2. Website OneDesk (`website_onedesk/tests/`)

#### test_subscription_portal.py
Tests du portail client et système de souscription, couvrant:

**Tests de Portail:**
- `test_subscription_portal_page_load()` - Chargement de la page
- `test_client_portal_access()` - Accès utilisateur portal
- `test_portal_dashboard_content()` - Contenu du tableau de bord
- `test_subscription_list_view()` - Affichage liste abonnements
- `test_plan_details_view()` - Détails du plan

**Tests de Souscription:**
- `test_subscription_creation_from_portal()` - Création depuis le portail
- `test_plan_selection_and_pricing()` - Sélection et tarification
- `test_subscription_upgrade()` - Upgrade de plan
- `test_subscription_downgrade()` - Downgrade de plan
- `test_subscription_renewal_date()` - Calcul date renouvellement
- `test_subscription_cancellation_from_portal()` - Annulation depuis portail

**Tests de Paiement et Facturation:**
- `test_subscription_invoice_generation()` - Génération de facture
- `test_subscription_with_payment_method()` - Méthode de paiement
- `test_subscription_email_confirmation()` - Email de confirmation

**Tests de Gestion Client:**
- `test_client_invitation_creation()` - Création d'invitation
- `test_client_invitation_acceptance()` - Acceptation d'invitation
- `test_client_suspension_message()` - Message suspension
- `test_client_cancellation_message()` - Message annulation

**Tests Additionnels:**
- `test_plan_comparison()` - Comparaison des plans
- `test_multi_language_support()` - Support multilingue

## Comment Exécuter les Tests

### Prérequis
```bash
# Installer les dépendances de test
pip install freezegun num2words vobject

# S'assurer que PostgreSQL est en cours d'exécution
service postgresql start
```

### Exécuter tous les tests OneDesk
```bash
# Exécuter tous les tests du module onedesk_core
python3 odoo-bin --test-tags=onedesk_core -d base2 --stop-after-init

# Exécuter tous les tests du module website_onedesk
python3 odoo-bin --test-tags=website_onedesk -d base2 --stop-after-init
```

### Exécuter des tests spécifiques
```bash
# Tests de souscription seulement
python3 odoo-bin --test-file=addons/onedesk_core/tests/test_subscription_system.py -d base2 --stop-after-init

# Tests de portail seulement
python3 odoo-bin --test-file=addons/website_onedesk/tests/test_subscription_portal.py -d base2 --stop-after-init
```

### Exécuter une classe de test spécifique
```bash
# Tester un cas spécifique
python3 odoo-bin --test-tags=TestOneDeskSubscriptionSystem.test_subscription_creation -d base2 --stop-after-init
```

## Structure des Tests

Chaque test hérite de `TransactionCase`:
- Chaque test est isolé dans une transaction
- Les données créées sont automatiquement annulées après le test
- Les tests peuvent être exécutés indépendamment

### Exemple de Test

```python
def test_subscription_creation(self):
    """Test la création d'un abonnement"""
    subscription = self.env['onedesk.subscription'].create({
        'company_id': self.company.id,
        'plan_id': self.plan.id,
        'state': 'active',
    })

    # Assertions
    self.assertIsNotNone(subscription.id)
    self.assertEqual(subscription.state, 'active')
    self.assertEqual(subscription.plan_id.id, self.plan.id)
```

## Assertions Courantes

```python
# Vérifier l'existence
self.assertIsNotNone(obj.id)

# Vérifier l'égalité
self.assertEqual(obj.state, 'active')
self.assertEqual(obj.plan_id.id, plan.id)

# Vérifier les nombres
self.assertEqual(len(records), 2)
self.assertGreater(count, 0)
self.assertLess(price, 100)

# Vérifier l'appartenance
self.assertIn(value, [1, 2, 3])
self.assertNotIn(value, [1, 2, 3])
```

## Résultats Attendus

Tous les tests doivent passer avec des messages de succès :

```
Ran XX tests in X.XXXs

OK
```

## Dépannage

### Erreur: "No module named 'freezegun'"
```bash
pip install freezegun
```

### Erreur: "No module named 'num2words'"
```bash
pip install num2words
```

### Erreur: Database not found
```bash
# S'assurer que PostgreSQL est en cours d'exécution
service postgresql start
```

### Erreur: Connection refused
```bash
# Attendre que PostgreSQL démarre
sleep 3
```

## Couverture de Code

Les tests couvrent:
- ✅ Création de modèles
- ✅ Gestion d'état
- ✅ Règles d'accès
- ✅ Limites de plan
- ✅ Synchronisation bidirectionnelle
- ✅ Logs d'audit
- ✅ Transitions d'état
- ✅ Suspensions/Annulations
- ✅ Portail client
- ✅ Invitations
- ✅ Paiements/Facturation

## Bonnes Pratiques pour Ajouter des Tests

1. **Utiliser des noms clairs** : `test_<feature>_<scenario>()`
2. **Un test = une fonctionnalité** : Tester une seule chose par test
3. **Utiliser setUp()** : Pour les données réutilisables
4. **Assertions explicites** : Messages clairs en cas d'erreur
5. **Documenter** : Docstrings pour chaque test

```python
def test_new_feature(self):
    """Test la nouvelle fonctionnalité"""
    # Arrange: Préparer les données
    obj = self.env['model'].create({...})

    # Act: Exécuter l'action
    result = obj.method()

    # Assert: Vérifier les résultats
    self.assertEqual(result, expected)
```

## Intégration CI/CD

Pour intégrer les tests dans un pipeline CI/CD:

```bash
#!/bin/bash
# test.sh

# Lancer PostgreSQL
service postgresql start
sleep 3

# Exécuter les tests
python3 odoo-bin --test-tags=onedesk_core,website_onedesk -d base2 --stop-after-init

# Capturer le code de sortie
exit $?
```

## Ressources

- [Documentation Odoo Testing](https://www.odoo.com/documentation/19.0/fr/developer/reference/backend/testing.html)
- [TransactionCase Reference](https://www.odoo.com/documentation/19.0/fr/developer/reference/backend/api/models.html)
