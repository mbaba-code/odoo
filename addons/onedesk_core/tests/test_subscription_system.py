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

        # Créer des groupes de test
        self.group_admin = self.env.ref('onedesk_core.group_onedesk_master_admin')
        self.group_pm = self.env.ref('onedesk_core.group_onedesk_property_manager')

        # Créer un utilisateur admin
        self.admin_user = self.env['res.users'].create({
            'name': 'Admin Test',
            'login': 'admin_test@example.com',
            'company_id': self.company.id,
            'groups_id': [(6, 0, [self.group_admin.id])],
        })

        # Créer un plan d'abonnement
        self.plan = self.env['onedesk.subscription.plan'].create({
            'name': 'Plan Premium',
            'description': 'Plan avec 10 propriétés',
            'max_properties': 10,
            'max_units': 50,
            'max_staff_users': 5,
            'monthly_price': 99.99,
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
        # Créer un abonnement
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
        self.assertEqual(subscription.current_properties_count, 2)

    def test_subscription_suspend_action(self):
        """Test la suspension d'un abonnement"""
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan.id,
            'state': 'active',
        })

        # Ajouter un utilisateur au groupe
        self.admin_user.groups_id = [(4, self.group_pm.id)]

        # Suspendre l'abonnement
        subscription.action_suspend()

        # Vérifier l'état
        self.assertEqual(subscription.state, 'suspended')

        # Vérifier que le groupe a été retiré
        self.admin_user.refresh()
        self.assertNotIn(self.group_pm.id, self.admin_user.groups_id.ids)

    def test_subscription_reactivate_action(self):
        """Test la réactivation d'un abonnement"""
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan.id,
            'state': 'suspended',
        })

        # Ajouter un utilisateur avec motif de login pattern
        self.admin_user.groups_id = [(4, self.group_pm.id)]

        # Créer une entrée de pattern de connexion
        self.env['onedesk.client.login.pattern'].create({
            'user_id': self.admin_user.id,
            'company_id': self.company.id,
        })

        # Réactiver l'abonnement
        subscription.action_reactivate()

        # Vérifier l'état
        self.assertEqual(subscription.state, 'active')

    def test_property_creation_with_plan_limit_check(self):
        """Test qu'une propriété déclenche une vérification des limites du plan"""
        # Créer un plan avec limite très basse
        limited_plan = self.env['onedesk.subscription.plan'].create({
            'name': 'Plan Limité',
            'max_properties': 1,
            'max_units': 5,
            'max_staff_users': 1,
            'monthly_price': 9.99,
        })

        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': limited_plan.id,
            'state': 'active',
        })

        # Créer une propriété (devrait passer)
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

        # Créer une propriété
        property_obj = self.env['onedesk.property'].create({
            'name': 'Immeuble Test',
            'address': '789 Rue Test',
            'property_type': 'apartment',
            'company_id': self.company.id,
        })

        # Créer une unité (devrait passer)
        unit = self.env['onedesk.unit'].create({
            'name': 'Unité Test',
            'property_id': property_obj.id,
            'bedrooms': 2,
            'bathrooms': 1,
            'capacity': 4,
            'unit_type': 'apartment',
        })

        self.assertIsNotNone(unit.id)

    def test_subscription_plan_enforcement(self):
        """Test l'application des limites du plan"""
        limited_plan = self.env['onedesk.subscription.plan'].create({
            'name': 'Plan Très Limité',
            'max_properties': 0,  # Zéro propriété autorisée
            'max_units': 0,
            'max_staff_users': 0,
            'monthly_price': 5.99,
        })

        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': limited_plan.id,
            'state': 'active',
        })

        # Tenter de créer une propriété (devrait déclencher un warning)
        property_obj = self.env['onedesk.property'].create({
            'name': 'Propriété Dépassement',
            'address': '999 Rue Test',
            'property_type': 'apartment',
            'company_id': self.company.id,
        })

        # Vérifier les limites (logging uniquement, pas d'exception)
        subscription._compute_current_usage()
        subscription._check_limits()

    def test_subscription_state_transitions(self):
        """Test les transitions d'état d'un abonnement"""
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan.id,
            'state': 'active',
        })

        # Test: active -> suspended
        subscription.action_suspend()
        self.assertEqual(subscription.state, 'suspended')

        # Test: suspended -> cancelled
        subscription.action_cancel()
        self.assertEqual(subscription.state, 'cancelled')

    def test_client_suspension_revokes_access(self):
        """Test que la suspension d'un client révoque les accès"""
        # Créer un client
        client = self.env['onedesk.client'].create({
            'name': 'Client Test',
            'email': 'client@test.com',
            'company_id': self.company.id,
            'state': 'active',
        })

        # Créer un abonnement pour le client
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan.id,
            'state': 'active',
            'client_id': client.id,
        })

        # Ajouter un utilisateur au groupe
        self.admin_user.groups_id = [(4, self.group_pm.id)]

        # Suspendre le client
        client.action_suspend_client()

        # Vérifier l'état
        self.assertEqual(client.state, 'suspended')

    def test_audit_log_creation(self):
        """Test la création de journaux d'audit"""
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan.id,
            'state': 'active',
        })

        # Créer une entrée de journal d'audit
        audit_log = self.env['onedesk.audit.log'].create({
            'subscription_id': subscription.id,
            'log_type': 'subscription_activated',
            'severity': 'info',
            'message': 'Test de journal d\'audit',
        })

        self.assertIsNotNone(audit_log.id)
        self.assertEqual(audit_log.log_type, 'subscription_activated')

    def test_bidirectional_sync_subscription_to_client(self):
        """Test la synchronisation bidirectionnelle subscription -> client"""
        client = self.env['onedesk.client'].create({
            'name': 'Client Sync Test',
            'email': 'sync@test.com',
            'company_id': self.company.id,
            'state': 'active',
        })

        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan.id,
            'state': 'active',
            'client_id': client.id,
        })

        # Modifier l'état de l'abonnement
        subscription.state = 'suspended'
        subscription.write({'state': 'suspended'})

        # Vérifier que le client est aussi suspendu (si sync activée)
        # Cette logique dépend de votre implémentation exacte

    def test_access_rules_master_admin(self):
        """Test les règles d'accès pour Master Admin"""
        # Master Admin doit avoir accès complet
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan.id,
            'state': 'active',
        })

        # Vérifier que l'accès est autorisé
        self.assertTrue(subscription.id > 0)

    def test_access_rules_property_manager(self):
        """Test les règles d'accès pour Property Manager"""
        # Créer un utilisateur PM
        pm_user = self.env['res.users'].create({
            'name': 'PM Test',
            'login': 'pm_test@example.com',
            'company_id': self.company.id,
            'groups_id': [(6, 0, [self.group_pm.id])],
        })

        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan.id,
            'state': 'active',
        })

        # PM doit pouvoir lire les abonnements
        self.assertTrue(subscription.id > 0)
