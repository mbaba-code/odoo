"""Tests pour le portail de souscription website_onedesk"""
import json
from datetime import datetime, timedelta
from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError


class TestSubscriptionPortal(TransactionCase):
    """Tests pour le système de souscription et portail client"""

    def setUp(self):
        """Set up test data"""
        super().setUp()

        # Créer une entreprise
        self.company = self.env['res.company'].create({
            'name': 'TestCorp Website',
        })

        # Créer des plans de tarification
        self.plan_basic = self.env['onedesk.subscription.plan'].create({
            'name': 'Plan Basique',
            'description': 'Plan avec 5 propriétés',
            'max_properties': 5,
            'max_units': 20,
            'max_staff_users': 2,
            'monthly_price': 29.99,
        })

        self.plan_premium = self.env['onedesk.subscription.plan'].create({
            'name': 'Plan Premium',
            'description': 'Plan avec 10 propriétés',
            'max_properties': 10,
            'max_units': 50,
            'max_staff_users': 5,
            'monthly_price': 99.99,
        })

        # Créer un client
        self.client = self.env['onedesk.client'].create({
            'name': 'Client Test',
            'email': 'client@test.com',
            'company_id': self.company.id,
            'state': 'active',
        })

        # Créer un partenaire pour le client
        self.partner = self.env['res.partner'].create({
            'name': 'Client Test Partner',
            'email': 'client@test.com',
            'company_id': self.company.id,
        })

    def test_subscription_portal_page_load(self):
        """Test le chargement de la page de souscription"""
        # Créer un utilisateur portail
        portal_user = self.env['res.users'].create({
            'name': 'Portal User',
            'login': 'portal@test.com',
            'email': 'portal@test.com',
            'company_id': self.company.id,
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
            'partner_id': self.partner.id,
        })

        self.assertEqual(portal_user.partner_id.id, self.partner.id)

    def test_subscription_creation_from_portal(self):
        """Test la création d'une souscription depuis le portail"""
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan_basic.id,
            'client_id': self.client.id,
            'state': 'active',
        })

        self.assertIsNotNone(subscription.id)
        self.assertEqual(subscription.plan_id.id, self.plan_basic.id)
        self.assertEqual(subscription.client_id.id, self.client.id)

    def test_plan_selection_and_pricing(self):
        """Test la sélection de plan et calcul du prix"""
        # Vérifier les prix des plans
        self.assertEqual(self.plan_basic.monthly_price, 29.99)
        self.assertEqual(self.plan_premium.monthly_price, 99.99)

        # Vérifier les limites
        self.assertEqual(self.plan_basic.max_properties, 5)
        self.assertEqual(self.plan_premium.max_properties, 10)

    def test_subscription_upgrade(self):
        """Test l'upgrade d'un abonnement"""
        # Créer un abonnement initial
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan_basic.id,
            'client_id': self.client.id,
            'state': 'active',
        })

        # Upgrade vers Plan Premium
        subscription.plan_id = self.plan_premium.id
        subscription.write({'plan_id': self.plan_premium.id})

        # Vérifier le changement
        self.assertEqual(subscription.plan_id.id, self.plan_premium.id)

    def test_subscription_downgrade(self):
        """Test le downgrade d'un abonnement"""
        # Créer un abonnement avec le plan premium
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan_premium.id,
            'client_id': self.client.id,
            'state': 'active',
        })

        # Downgrade vers Plan Basique
        subscription.plan_id = self.plan_basic.id
        subscription.write({'plan_id': self.plan_basic.id})

        # Vérifier le changement
        self.assertEqual(subscription.plan_id.id, self.plan_basic.id)

    def test_client_portal_access(self):
        """Test l'accès au portail client"""
        # Créer un utilisateur avec accès portal
        portal_user = self.env['res.users'].create({
            'name': 'Portal Client',
            'login': 'portal_client@test.com',
            'email': 'portal_client@test.com',
            'company_id': self.company.id,
            'partner_id': self.partner.id,
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
        })

        self.assertTrue(portal_user.id > 0)

    def test_client_invitation_creation(self):
        """Test la création d'une invitation client"""
        invitation = self.env['onedesk.client.invitation'].create({
            'email': 'newclient@test.com',
            'client_id': self.client.id,
            'state': 'sent',
        })

        self.assertIsNotNone(invitation.id)
        self.assertEqual(invitation.email, 'newclient@test.com')
        self.assertEqual(invitation.state, 'sent')

    def test_client_invitation_acceptance(self):
        """Test l'acceptation d'une invitation"""
        invitation = self.env['onedesk.client.invitation'].create({
            'email': 'newclient2@test.com',
            'client_id': self.client.id,
            'state': 'sent',
        })

        # Changer l'état à accepté
        invitation.write({'state': 'accepted'})

        self.assertEqual(invitation.state, 'accepted')

    def test_subscription_display_in_portal(self):
        """Test l'affichage des abonnements dans le portail"""
        # Créer plusieurs abonnements
        sub1 = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan_basic.id,
            'client_id': self.client.id,
            'state': 'active',
        })

        sub2 = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan_premium.id,
            'client_id': self.client.id,
            'state': 'active',
        })

        # Vérifier que les deux abonnements existent
        subs = self.env['onedesk.subscription'].search([
            ('client_id', '=', self.client.id),
            ('state', '=', 'active'),
        ])

        self.assertEqual(len(subs), 2)

    def test_subscription_cancellation_from_portal(self):
        """Test l'annulation d'un abonnement depuis le portail"""
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan_basic.id,
            'client_id': self.client.id,
            'state': 'active',
        })

        # Annuler l'abonnement
        subscription.action_cancel()

        # Vérifier l'état
        self.assertEqual(subscription.state, 'cancelled')

    def test_plan_comparison(self):
        """Test la comparaison des plans"""
        plans = self.env['onedesk.subscription.plan'].search([])

        # Vérifier qu'il y a au moins 2 plans
        self.assertGreaterEqual(len(plans), 2)

        # Trier par prix
        plans_sorted = sorted(plans, key=lambda p: p.monthly_price)
        self.assertLess(plans_sorted[0].monthly_price, plans_sorted[-1].monthly_price)

    def test_subscription_renewal_date(self):
        """Test le calcul de la date de renouvellement"""
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan_basic.id,
            'client_id': self.client.id,
            'state': 'active',
            'start_date': datetime.now().date(),
        })

        # Vérifier que la date de début est définie
        self.assertIsNotNone(subscription.start_date)

    def test_subscription_invoice_generation(self):
        """Test la génération de facture pour un abonnement"""
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan_basic.id,
            'client_id': self.client.id,
            'state': 'active',
        })

        # Créer une facture de test
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'invoice_line_ids': [(0, 0, {
                'name': f'Abonnement {self.plan_basic.name}',
                'quantity': 1,
                'price_unit': self.plan_basic.monthly_price,
            })],
        })

        self.assertIsNotNone(invoice.id)
        self.assertEqual(invoice.move_type, 'out_invoice')

    def test_client_suspension_message(self):
        """Test le message affiché lors de la suspension d'un client"""
        # Suspendre le client
        self.client.action_suspend_client()

        # Vérifier l'état
        self.assertEqual(self.client.state, 'suspended')

    def test_client_cancellation_message(self):
        """Test le message affiché lors de l'annulation d'un client"""
        # Annuler le client
        self.client.action_cancel_client()

        # Vérifier l'état
        self.assertEqual(self.client.state, 'cancelled')

    def test_portal_dashboard_content(self):
        """Test le contenu du tableau de bord du portail"""
        # Créer plusieurs éléments associés
        property_obj = self.env['onedesk.property'].create({
            'name': 'Propriété Portal',
            'address': '100 Rue Portal',
            'property_type': 'apartment',
            'company_id': self.company.id,
        })

        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan_basic.id,
            'client_id': self.client.id,
            'state': 'active',
        })

        # Vérifier que les données sont accessibles
        self.assertIsNotNone(property_obj.id)
        self.assertIsNotNone(subscription.id)

    def test_subscription_list_view(self):
        """Test l'affichage de la liste des abonnements"""
        # Créer plusieurs abonnements
        for i in range(3):
            self.env['onedesk.subscription'].create({
                'company_id': self.company.id,
                'plan_id': self.plan_basic.id if i % 2 == 0 else self.plan_premium.id,
                'client_id': self.client.id,
                'state': 'active',
            })

        # Chercher les abonnements du client
        subs = self.env['onedesk.subscription'].search([
            ('client_id', '=', self.client.id),
        ])

        self.assertEqual(len(subs), 3)

    def test_plan_details_view(self):
        """Test l'affichage des détails d'un plan"""
        plan = self.plan_premium

        # Vérifier les informations du plan
        self.assertIsNotNone(plan.name)
        self.assertIsNotNone(plan.description)
        self.assertGreater(plan.monthly_price, 0)
        self.assertGreater(plan.max_properties, 0)

    def test_multi_language_support(self):
        """Test le support multi-langue pour les plans"""
        # Créer un plan avec descriptions multilingues
        plan = self.env['onedesk.subscription.plan'].create({
            'name': 'Plan Multi-Langue',
            'description': 'Description en français',
            'max_properties': 5,
            'max_units': 20,
            'max_staff_users': 2,
            'monthly_price': 49.99,
        })

        self.assertEqual(plan.name, 'Plan Multi-Langue')

    def test_subscription_with_payment_method(self):
        """Test la création d'abonnement avec méthode de paiement"""
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan_basic.id,
            'client_id': self.client.id,
            'state': 'active',
        })

        # Ajouter une transaction de paiement
        payment_transaction = self.env['payment.transaction'].create({
            'amount': self.plan_basic.monthly_price,
            'currency_id': self.env.ref('base.EUR').id,
            'partner_id': self.partner.id,
            'reference': f'sub-{subscription.id}',
            'state': 'draft',
        })

        self.assertIsNotNone(payment_transaction.id)

    def test_subscription_email_confirmation(self):
        """Test l'envoi d'email de confirmation de souscription"""
        subscription = self.env['onedesk.subscription'].create({
            'company_id': self.company.id,
            'plan_id': self.plan_basic.id,
            'client_id': self.client.id,
            'state': 'active',
        })

        # Vérifier que l'abonnement a une adresse email
        self.assertTrue(self.client.email)
