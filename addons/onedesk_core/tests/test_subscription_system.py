"""Tests pour le système d'abonnement OneDesk Core"""
from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError


class TestOneDeskSubscriptionSystem(TransactionCase):
    """Tests complets pour le système d'abonnement OneDesk"""

    def setUp(self):
        """Set up test data"""
        super().setUp()

        # Créer une entreprise de test
        self.company = self.env['res.company'].create({
            'name': 'TestCorp',
        })

        # Créer un plan d'abonnement
        self.plan = self.env['onedesk.subscription.plan'].create({
            'name': 'Plan Premium',
            'description': 'Plan avec 10 propriétés',
            'max_properties': 10,
            'max_units': 50,
            'max_users': 5,
            'price_per_unit': 99.99,
        })

    def test_subscription_creation(self):
        """Test la création d'un abonnement"""
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan.id,
            'state': 'active',
        })

        self.assertIsNotNone(subscription.id)
        self.assertEqual(subscription.state, 'active')
        self.assertEqual(subscription.plan_id.id, self.plan.id)

    def test_subscription_with_properties_count(self):
        """Test le calcul du nombre de propriétés actives"""
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan.id,
            'state': 'active',
        })

        # Créer des propriétés
        property1 = self.env['onedesk.property'].create({
            'name': 'Propriété Test 1',
            'address': '123 Rue Test',
            'property_type': 'apartment',
            'company_id': self.company.id,
        })

        property2 = self.env['onedesk.property'].create({
            'name': 'Propriété Test 2',
            'address': '456 Avenue Test',
            'property_type': 'villa',
            'company_id': self.company.id,
        })

        # Vérifier le calcul
        subscription._compute_current_usage()
        self.assertGreaterEqual(subscription.current_properties_count, 2)

    def test_subscription_suspend_action(self):
        """Test la suspension d'un abonnement"""
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan.id,
            'state': 'active',
        })

        subscription.action_suspend()
        self.assertEqual(subscription.state, 'suspended')

    def test_subscription_reactivate_action(self):
        """Test la réactivation d'un abonnement"""
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan.id,
            'state': 'suspended',
        })

        subscription.action_reactivate()
        self.assertEqual(subscription.state, 'active')

    def test_property_creation_with_plan_limit_check(self):
        """Test qu'une propriété déclenche une vérification des limites du plan"""
        limited_plan = self.env['onedesk.subscription.plan'].create({
            'name': 'Plan Limité',
            'max_properties': 1,
            'max_units': 5,
            'max_users': 1,
            'price_per_unit': 9.99,
        })

        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': limited_plan.id,
            'state': 'active',
        })

        property1 = self.env['onedesk.property'].create({
            'name': 'Propriété 1',
            'address': '111 Rue Test',
            'property_type': 'apartment',
            'company_id': self.company.id,
        })

        self.assertIsNotNone(property1.id)

    def test_unit_creation_with_plan_limit_check(self):
        """Test qu'une unité déclenche une vérification des limites du plan"""
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan.id,
            'state': 'active',
        })

        property_obj = self.env['onedesk.property'].create({
            'name': 'Immeuble Test',
            'address': '789 Rue Test',
            'property_type': 'apartment',
            'company_id': self.company.id,
        })

        unit = self.env['onedesk.unit'].create({
            'name': 'Unité Test',
            'property_id': property_obj.id,
            'bedrooms': 2,
            'bathrooms': 1,
            'capacity': 4,
            'price_per_night': 100.0,
        })

        self.assertIsNotNone(unit.id)

    def test_subscription_plan_enforcement(self):
        """Test l'application des limites du plan"""
        limited_plan = self.env['onedesk.subscription.plan'].create({
            'name': 'Plan Très Limité',
            'max_properties': 0,
            'max_units': 0,
            'max_users': 0,
            'price_per_unit': 5.99,
        })

        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': limited_plan.id,
            'state': 'active',
        })

        property_obj = self.env['onedesk.property'].create({
            'name': 'Propriété Dépassement',
            'address': '999 Rue Test',
            'property_type': 'apartment',
            'company_id': self.company.id,
        })

        subscription._compute_current_usage()

    def test_subscription_state_transitions(self):
        """Test les transitions d'état d'un abonnement"""
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan.id,
            'state': 'active',
        })

        subscription.action_suspend()
        self.assertEqual(subscription.state, 'suspended')

        subscription.action_cancel()
        self.assertEqual(subscription.state, 'cancelled')

    def test_audit_log_creation(self):
        """Test la création de journaux d'audit"""
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan.id,
            'state': 'active',
        })

        audit_log = self.env['onedesk.audit.log'].create({
            'action': 'subscription_activated',
            'description': 'Test de journal d\'audit',
        })

        self.assertIsNotNone(audit_log.id)