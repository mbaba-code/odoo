import json
import secrets
import string
from datetime import datetime, timedelta
from odoo import http, fields
from odoo.http import request


class OnedeskoSignupController(http.Controller):
    """
    Contrôleur pour le processus d'inscription OneDesk
    Gère la création automatique de Company, Contact et User
    """

    @http.route('/onedesk/signup', type='http', auth='public', csrf=False)
    def signup_form(self, **kwargs):
        """Afficher le formulaire d'inscription"""
        return request.render('onedesk_core.signup_form_template', {})

    @http.route('/onedesk/signup/process', type='json', auth='public', csrf=False)
    def signup_process(self, **data):
        """
        Traiter l'inscription du client
        POST data:
        {
            'company_name': 'Mon Entreprise',
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'email': 'jean@example.com',
            'phone': '+33612345678',
            'country_id': 'FR',
            'business_type': 'property_manager',
            'accept_tos': True,
            'accept_privacy': True
        }
        """
        try:
            # Valider les données
            self._validate_signup_data(data)

            # Créer la Company
            company = self._create_company(data)

            # Créer le Contact (res.partner)
            partner = self._create_partner(company, data)

            # Créer le Client OneDesk
            client = self._create_client(company, partner, data)

            # Créer l'utilisateur
            user = self._create_user(company, partner, data)

            # Assigner le groupe "Property Manager"
            self._assign_user_group(user)

            # Créer l'abonnement avec le plan d'essai
            subscription = self._create_subscription(client, data)

            # Envoyer l'email d'activation
            self._send_welcome_email(user, password=data.get('password'))

            # Enregistrer dans le log d'audit
            self._log_signup(client, user)

            return {
                'status': 'success',
                'message': 'Inscription réussie! Vérifiez votre email.',
                'client_id': client.id,
                'user_id': user.id,
                'redirect_url': '/web/login',
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
            }

    @staticmethod
    def _validate_signup_data(data):
        """Valider les données d'inscription"""
        required_fields = ['company_name', 'first_name', 'last_name', 'email', 'password']

        for field in required_fields:
            if not data.get(field):
                raise ValueError(f"Le champ '{field}' est requis")

        # Vérifier le format email
        if '@' not in data.get('email', ''):
            raise ValueError("Email invalide")

        # Vérifier les longueurs
        if len(data['password']) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")

        if len(data['company_name']) < 2:
            raise ValueError("Le nom de l'entreprise est trop court")

        # Vérifier que l'email n'existe pas déjà
        existing_user = request.env['res.users'].sudo().search([
            ('login', '=', data['email'])
        ], limit=1)

        if existing_user:
            raise ValueError("Cet email est déjà utilisé")

        # Vérifier l'acceptation des conditions
        if not data.get('accept_tos') or not data.get('accept_privacy'):
            raise ValueError("Vous devez accepter les conditions d'utilisation")

    @staticmethod
    def _create_company(data):
        """Créer une nouvelle Company (tenant)"""
        Company = request.env['res.company'].sudo()

        company = Company.create({
            'name': data['company_name'],
            'is_onedesk_client': True,
            'country_id': request.env['res.country'].sudo().search(
                [('code', '=', data.get('country_id', 'FR'))], limit=1
            ).id or False,
        })

        return company

    @staticmethod
    def _create_partner(company, data):
        """Créer le contact principal (res.partner)"""
        Partner = request.env['res.partner'].sudo()

        partner = Partner.create({
            'name': f"{data['first_name']} {data['last_name']}",
            'email': data['email'],
            'phone': data.get('phone', ''),
            'company_id': company.id,
            'type': 'contact',
        })

        return partner

    @staticmethod
    def _create_client(company, partner, data):
        """Créer le profil OneDesk Client"""
        Client = request.env['onedesk.client'].sudo()

        client = Client.create({
            'company_id': company.id,
            'owner_partner_id': partner.id,
            'business_type': data.get('business_type', 'individual'),
            'support_email': data['email'],
            'onboarding_step': 'welcome',
            'state': 'pending_setup',
            'accepted_tos': data.get('accept_tos', False),
            'tos_accepted_date': fields.Date.today() if data.get('accept_tos') else False,
            'accepted_privacy': data.get('accept_privacy', False),
            'privacy_accepted_date': fields.Date.today() if data.get('accept_privacy') else False,
        })

        return client

    @staticmethod
    def _create_user(company, partner, data):
        """Créer l'utilisateur Odoo"""
        User = request.env['res.users'].sudo()

        user = User.create({
            'name': f"{data['first_name']} {data['last_name']}",
            'login': data['email'],
            'email': data['email'],
            'password': data['password'],
            'company_id': company.id,
            'company_ids': [(6, 0, [company.id])],
            'partner_id': partner.id,
            'tz': data.get('timezone', 'Europe/Paris'),
            'lang': data.get('language', 'fr_FR'),
        })

        return user

    @staticmethod
    def _assign_user_group(user):
        """Assigner le groupe Property Manager"""
        try:
            group = request.env.ref('onedesk_core.group_onedesk_property_manager').sudo()
            user.sudo().write({'group_ids': [(4, group.id)]})
        except:
            pass  # Le groupe pourrait ne pas exister si le module n'est pas installé

    @staticmethod
    def _create_subscription(client, data):
        """Créer l'abonnement avec le plan d'essai"""
        Subscription = request.env['onedesk.subscription'].sudo()
        Plan = request.env['onedesk.subscription.plan'].sudo()

        # Récupérer le plan d'essai
        trial_plan = Plan.search([('id', '=', request.env.ref('onedesk_core.plan_free_trial').id)], limit=1)

        if not trial_plan:
            # Fallback: utiliser n'importe quel plan actif
            trial_plan = Plan.search([('active', '=', True)], limit=1)

        if trial_plan:
            subscription = Subscription.create({
                'company_id': client.company_id.id,
                'plan_id': trial_plan.id,
                'start_date': fields.Date.today(),
                'end_date': fields.Date.today() + timedelta(days=30),
                'state': 'active',
                'auto_renew': False,  # L'essai ne se renouvelle pas automatiquement
            })

            # Associer le client à l'abonnement
            client.subscription_id = subscription.id

            return subscription

        return None

    @staticmethod
    def _send_welcome_email(user, password=None):
        """Envoyer l'email de bienvenue"""
        try:
            # Utiliser le template d'email
            email_template = request.env.ref('onedesk_core.email_template_welcome').sudo()

            if email_template:
                email_template.send_mail(user.id, force_send=True)

        except Exception as e:
            # Log l'erreur mais ne pas bloquer le processus
            request.env['onedesk.system.log'].sudo().create({
                'level': 'warning',
                'module': 'signup',
                'message': f'Erreur lors de l\'envoi de l\'email de bienvenue: {str(e)}',
            })

    @staticmethod
    def _log_signup(client, user):
        """Enregistrer l'inscription dans le log d'audit"""
        try:
            request.env['onedesk.audit.log'].sudo().create({
                'log_type': 'client_created',
                'severity': 'info',
                'client_id': client.id,
                'user_id': user.id,
                'company_id': client.company_id.id,
                'description': f'Nouveau client créé via signup: {client.company_id.name}',
                'actor_name': 'System (Auto-signup)',
                'result': 'success',
            })
        except:
            pass  # Ne pas bloquer si le log échoue

    @http.route('/onedesk/verify-email/<token>', type='http', auth='public')
    def verify_email(self, token, **kwargs):
        """Vérifier l'email après inscription"""
        # À implémenter : vérification du token envoyé par email
        return request.render('onedesk_core.email_verified_template', {
            'message': 'Email vérifié! Vous pouvez maintenant vous connecter.',
        })

    @http.route('/onedesk/login', type='http', auth='public')
    def login(self, **kwargs):
        """Page de connexion personnalisée pour OneDesk"""
        return request.render('onedesk_core.login_template', {})

    @http.route('/onedesk/invite/accept/<token>', type='json', auth='public', csrf=False)
    def accept_invitation(self, token, **data):
        """Accepter une invitation d'utilisateur"""
        try:
            Invitation = request.env['onedesk.client.invitation'].sudo()

            # Trouver l'invitation
            invitation = Invitation.search([('invitation_token', '=', token)], limit=1)

            if not invitation:
                return {
                    'status': 'error',
                    'message': 'Invitation non trouvée ou expirée'
                }

            # Accepter et créer l'utilisateur
            user = invitation.action_accept_invitation(password=data.get('password'))

            return {
                'status': 'success',
                'message': 'Invitation acceptée! Vous pouvez maintenant vous connecter.',
                'user_id': user.id,
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
            }


class OnedeskoPortalController(http.Controller):
    """
    Contrôleur pour le portail client OneDesk
    Dashboard, gestion de compte, etc.
    """

    @http.route('/onedesk/portal', type='http', auth='user')
    def portal_dashboard(self, **kwargs):
        """Dashboard principal du portail client"""
        user = request.env.user
        client = request.env['onedesk.client'].sudo().search([
            ('company_id', '=', user.company_id.id)
        ], limit=1)

        if not client:
            return request.render('onedesk_core.portal_error_template', {
                'message': 'Client non trouvé',
            })

        # Récupérer les statistiques
        properties_count = request.env['onedesk.property'].search_count([
            ('company_id', '=', user.company_id.id)
        ])

        reservations_count = request.env['onedesk.reservation'].search_count([
            ('unit_id.property_id.company_id', '=', user.company_id.id)
        ])

        return request.render('onedesk_core.portal_dashboard_template', {
            'client': client,
            'properties_count': properties_count,
            'reservations_count': reservations_count,
        })

    @http.route('/onedesk/portal/account', type='http', auth='user')
    def portal_account(self, **kwargs):
        """Gestion du compte client"""
        user = request.env.user
        client = request.env['onedesk.client'].sudo().search([
            ('company_id', '=', user.company_id.id)
        ], limit=1)

        return request.render('onedesk_core.portal_account_template', {
            'client': client,
            'user': user,
        })
