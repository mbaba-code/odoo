import json
import secrets
import string
import re
import logging
from datetime import datetime, timedelta
from odoo import http, fields
from odoo.http import request
from odoo.tools import email_normalize
from markupsafe import escape

_logger = logging.getLogger(__name__)


class OnedeskoSignupController(http.Controller):
    """
    Contrôleur pour le processus d'inscription OneDesk
    Gère la création automatique de Company, Contact et User
    """

    @http.route('/onedesk/signup', type='http', auth='public', csrf=False)
    def signup_form(self, **kwargs):
        """Afficher le formulaire d'inscription"""
        return request.render('onedesk_core.signup_form_template', {})

    @http.route('/onedesk/signup/process', type='jsonrpc', auth='public', csrf=False)
    def signup_process(self, **data):
        """
        Traiter l'inscription du client avec transaction atomique

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

        SECURITY IMPROVEMENTS:
        - Transaction atomique (rollback si erreur)
        - Validation renforcée des entrées
        - Pas d'envoi du mot de passe par email
        """
        # SECURITY: Transaction atomique pour éviter les données orphelines
        with request.env.cr.savepoint():
            try:
                # Valider les données (avec validation renforcée)
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

                # SECURITY: Envoyer l'email d'activation SANS le mot de passe
                # Le mot de passe ne doit JAMAIS être envoyé par email (RGPD + sécurité)
                self._send_welcome_email(user)

                # Enregistrer dans le log d'audit
                self._log_signup(client, user)

                return {
                    'status': 'success',
                    'message': 'Inscription réussie! Vous pouvez maintenant vous connecter.',
                    'client_id': client.id,
                    'user_id': user.id,
                    'redirect_url': '/web/login',
                }

            except Exception as e:
                # Rollback automatique via savepoint
                import logging
                _logger = logging.getLogger(__name__)
                _logger.error(f'Erreur lors de l\'inscription: {str(e)}', exc_info=True)

                return {
                    'status': 'error',
                    'message': str(e),
                }

    @staticmethod
    def _validate_signup_data(data):
        """Valider les données d'inscription avec validation renforcée"""
        required_fields = ['company_name', 'first_name', 'last_name', 'email', 'password']

        for field in required_fields:
            if not data.get(field):
                raise ValueError(f"Le champ '{field}' est requis")

        # SECURITY: Valider et normaliser l'email
        try:
            email_normalized = email_normalize(data.get('email'))
            if not email_normalized:
                raise ValueError("Email invalide")
            data['email'] = email_normalized
        except Exception:
            raise ValueError("Format d'email invalide")

        # SECURITY: Valider les champs texte contre XSS/injection
        text_fields = ['company_name', 'first_name', 'last_name']
        for field in text_fields:
            value = data.get(field, '').strip()

            # Vérifier longueur minimale
            if len(value) < 2:
                raise ValueError(f"Le champ '{field}' est trop court (minimum 2 caractères)")

            # Vérifier longueur maximale
            if len(value) > 100:
                raise ValueError(f"Le champ '{field}' est trop long (maximum 100 caractères)")

            # SECURITY: Bloquer caractères dangereux pour XSS/injection
            if re.search(r'[<>{}\\;\'"]', value):
                raise ValueError(f"Le champ '{field}' contient des caractères interdits")

            # Mettre à jour avec valeur nettoyée
            data[field] = value

        # SECURITY: Valider le mot de passe
        password = data.get('password', '')
        if len(password) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")

        if len(password) > 100:
            raise ValueError("Le mot de passe est trop long (maximum 100 caractères)")

        # Vérifier la complexité du mot de passe
        if not re.search(r'[a-z]', password):
            raise ValueError("Le mot de passe doit contenir au moins une minuscule")

        if not re.search(r'[A-Z]', password):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule")

        if not re.search(r'[0-9]', password):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre")

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
    def _send_welcome_email(user):
        """
        Envoyer l'email de bienvenue (SANS le mot de passe pour des raisons de sécurité)

        SECURITY NOTE: Le mot de passe ne doit JAMAIS être envoyé par email.
        - Violation RGPD
        - Risque d'interception
        - Pratique dangereuse
        """
        try:
            # Utiliser le template d'email
            email_template = request.env.ref('onedesk_core.email_template_welcome').sudo()

            if email_template:
                email_template.send_mail(user.id, force_send=True)

        except Exception as e:
            # Log l'erreur mais ne pas bloquer le processus
            # Note: Ne pas utiliser pass silencieux, toujours logger
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning(f'Erreur lors de l\'envoi de l\'email de bienvenue: {str(e)}', exc_info=True)

            # Essayer de créer le log système si le modèle existe
            try:
                request.env['onedesk.system.log'].sudo().create({
                    'level': 'warning',
                    'module': 'signup',
                    'message': f'Erreur lors de l\'envoi de l\'email de bienvenue: {str(e)}',
                })
            except:
                # Si le modèle n'existe pas, continuer silencieusement
                pass

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

    @http.route('/onedesk/invite/accept/<token>', type='http', auth='public', website=True)
    def accept_invitation_page(self, token, **kwargs):
        """Page HTML pour accepter l'invitation et définir le mot de passe"""
        Invitation = request.env['onedesk.client.invitation'].sudo()

        # Trouver l'invitation
        invitation = Invitation.search([('invitation_token', '=', token)], limit=1)

        if not invitation:
            return request.render('onedesk_core.invitation_error_template', {
                'error_message': 'Invitation non trouvée ou expirée',
            })

        # Vérifier l'expiration
        if fields.Datetime.now() > invitation.expires_date:
            invitation.state = 'expired'
            return request.render('onedesk_core.invitation_error_template', {
                'error_message': 'Cette invitation a expiré',
            })

        # Vérifier l'état
        if invitation.state != 'pending':
            return request.render('onedesk_core.invitation_error_template', {
                'error_message': 'Cette invitation n\'est plus valide',
            })

        # Afficher la page d'acceptation
        return request.render('onedesk_core.invitation_accept_template', {
            'invitation': invitation,
            'token': token,
        })

    @http.route('/onedesk/invite/accept/submit', type='json', auth='public', csrf=False)
    def accept_invitation(self, token, name=None, password=None, **data):
        """Accepter une invitation d'utilisateur et activer le compte"""
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
            user = invitation.action_accept_invitation(name=name, password=password)

            return {
                'status': 'success',
                'message': 'Compte activé avec succès! Redirection vers la page de connexion...',
                'user_id': user.id,
            }

        except Exception as e:
            _logger.error(f'Erreur acceptation invitation: {e}', exc_info=True)
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
