from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import secrets
import string


class OnedeskoClient(models.Model):
    """
    Modèle de client OneDesk multi-tenant
    Gère le profil, les paramètres et l'accès d'une Company cliente
    """
    _name = 'onedesk.client'
    _description = 'OneDesk Client Account'
    _order = 'create_date desc'

    # Relations
    company_id = fields.Many2one(
        'res.company',
        string="Société Odoo",
        required=True,
        ondelete='cascade',
        unique=True
    )
    owner_partner_id = fields.Many2one(
        'res.partner',
        string="Propriétaire/Contact principal",
        required=True,
        ondelete='restrict'
    )
    subscription_id = fields.Many2one(
        'onedesk.subscription',
        string="Abonnement actif",
        help="Lien vers l'abonnement actuel"
    )

    # Identification
    client_name = fields.Char(related='company_id.name', string="Nom du client", readonly=True)
    client_code = fields.Char(
        string="Code client",
        readonly=True,
        copy=False
    )
    registration_date = fields.Date(
        string="Date d'inscription",
        default=fields.Date.today,
        readonly=True
    )

    # Status
    state = fields.Selection([
        ('pending_setup', 'En attente de configuration'),
        ('active', 'Actif'),
        ('suspended', 'Suspendu'),
        ('cancelled', 'Annulé'),
    ], string="État", default='pending_setup', required=True)

    # Business Info
    business_type = fields.Selection([
        ('property_manager', 'Gestionnaire immobilier'),
        ('agency', 'Agence'),
        ('individual', 'Particulier'),
        ('company', 'PME'),
    ], string="Type d'entreprise")

    industry = fields.Char(string="Secteur d'activité")
    country_id = fields.Many2one(
        'res.country',
        string="Pays",
        related='owner_partner_id.country_id',
        readonly=True
    )
    website = fields.Char(string="Site web")
    business_phone = fields.Char(string="Téléphone entreprise")

    # Contact Settings
    primary_email = fields.Char(
        string="Email principal",
        related='owner_partner_id.email',
        readonly=True
    )
    support_email = fields.Char(
        string="Email support",
        help="Email pour les notifications de support"
    )
    phone = fields.Char(
        string="Téléphone",
        related='owner_partner_id.phone',
        readonly=True
    )

    # Onboarding
    onboarding_step = fields.Selection([
        ('welcome', 'Accueil'),
        ('account_setup', 'Configuration du compte'),
        ('property_setup', 'Configuration propriétés'),
        ('payment_setup', 'Configuration paiement'),
        ('integration', 'Intégrations externes'),
        ('completed', 'Complété'),
    ], string="Étape d'onboarding", default='welcome')

    onboarding_progress = fields.Float(
        string="Progression (%)",
        compute='_compute_onboarding_progress',
        readonly=True
    )

    onboarding_completed_date = fields.Date(
        string="Onboarding complété le"
    )

    # Settings
    timezone = fields.Selection(
        selection='_get_timezones',
        string="Fuseau horaire",
        default='Europe/Paris'
    )
    language = fields.Selection(
        selection='_get_languages',
        string="Langue",
        default='fr_FR'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.ref('base.EUR')
    )

    # Notification Preferences
    notify_daily_summary = fields.Boolean(string="Résumé quotidien", default=True)
    notify_booking_confirmation = fields.Boolean(string="Confirmation de réservation", default=True)
    notify_payment_received = fields.Boolean(string="Paiement reçu", default=True)
    notify_system_alerts = fields.Boolean(string="Alertes système", default=True)

    # Compliance
    accepted_tos = fields.Boolean(string="Conditions acceptées")
    tos_accepted_date = fields.Date(string="Date d'acceptation des conditions", readonly=True)
    accepted_privacy = fields.Boolean(string="Politique de confidentialité acceptée")
    privacy_accepted_date = fields.Date(string="Date d'acceptation de la confidentialité", readonly=True)

    # Admin notes
    internal_notes = fields.Text(string="Notes internes")
    admin_notes = fields.Text(string="Notes d'administration")

    # Activity
    last_login = fields.Datetime(string="Dernière connexion")
    last_activity = fields.Datetime(string="Dernière activité")

    # Account limits & usage
    properties_count = fields.Integer(
        string="Nombre de propriétés",
        compute='_compute_usage_stats',
        readonly=True
    )
    units_count = fields.Integer(
        string="Nombre d'unités",
        compute='_compute_usage_stats',
        readonly=True
    )
    reservations_count = fields.Integer(
        string="Nombre de réservations",
        compute='_compute_usage_stats',
        readonly=True
    )

    @api.model
    def _get_timezones(self):
        """Retourner la liste des fuseaux horaires disponibles"""
        import pytz
        return [(tz, tz) for tz in pytz.common_timezones]

    @api.model
    def _get_languages(self):
        """Retourner la liste des langues disponibles"""
        return [
            ('fr_FR', 'Français'),
            ('en_US', 'English'),
            ('es_ES', 'Español'),
            ('it_IT', 'Italiano'),
            ('de_DE', 'Deutsch'),
            ('pt_BR', 'Português'),
        ]

    @api.model
    def create(self, vals_list):
        """Créer de nouveaux clients avec codes uniques, companies et utilisateurs automatiques"""
        for vals in vals_list:
            # 1. Générer un code client unique
            if not vals.get('client_code'):
                vals['client_code'] = self._generate_client_code()

            # 2. Si pas de company_id fournie, en créer une nouvelle automatiquement
            if not vals.get('company_id'):
                # Créer une nouvelle Company Odoo
                partner_name = ''
                if vals.get('owner_partner_id'):
                    partner = self.env['res.partner'].browse(vals['owner_partner_id'])
                    partner_name = partner.name if partner else ''

                # Utiliser client_code pour garantir l'unicité du nom de company
                company_name = f"{partner_name or 'Client'} - {vals.get('client_code')}"
                new_company = self.env['res.company'].create({
                    'name': company_name,
                    'is_onedesk_client': True,
                })
                vals['company_id'] = new_company.id

            # Marquer comme client OneDesk si nécessaire
            if vals.get('company_id'):
                company = self.env['res.company'].browse(vals['company_id'])
                if not company.is_onedesk_client:
                    company.is_onedesk_client = True

        clients = super().create(vals_list)

        # 3. Créer les utilisateurs (Property Manager, Staff, Viewer) après la création du client
        for client in clients:
            self._create_default_users(client)

        return clients

    def _create_default_users(self, client):
        """Créer les utilisateurs par défaut (Property Manager, Staff, Viewer) pour un client"""
        company = client.company_id
        client_name = client.client_name

        # Les groupes OneDesk pour les rôles
        manager_group = self.env.ref('onedesk_core.group_onedesk_property_manager')
        staff_group = self.env.ref('onedesk_core.group_onedesk_staff')
        viewer_group = self.env.ref('onedesk_core.group_onedesk_viewer')

        # 3.1. Créer le Property Manager
        pm_user = self.env['res.users'].create({
            'name': f'{client_name} - Property Manager',
            'login': f'pm_{client.client_code}@onedesk.local'.lower(),
            'email': client.owner_partner_id.email if client.owner_partner_id else f'pm_{client.client_code}@onedesk.local',
            'company_id': company.id,
            'company_ids': [(6, 0, [company.id])],
            'state': 'new',
        })
        # Ajouter le groupe après création
        pm_user.groups_id = [(4, manager_group.id)]

        # 3.2. Créer le Staff
        staff_user = self.env['res.users'].create({
            'name': f'{client_name} - Staff Member',
            'login': f'staff_{client.client_code}@onedesk.local'.lower(),
            'email': f'staff_{client.client_code}@onedesk.local',
            'company_id': company.id,
            'company_ids': [(6, 0, [company.id])],
            'state': 'new',
        })
        # Ajouter le groupe après création
        staff_user.groups_id = [(4, staff_group.id)]

        # 3.3. Créer le Viewer
        viewer_user = self.env['res.users'].create({
            'name': f'{client_name} - Viewer',
            'login': f'viewer_{client.client_code}@onedesk.local'.lower(),
            'email': f'viewer_{client.client_code}@onedesk.local',
            'company_id': company.id,
            'company_ids': [(6, 0, [company.id])],
            'state': 'new',
        })
        # Ajouter le groupe après création
        viewer_user.groups_id = [(4, viewer_group.id)]

    @staticmethod
    def _generate_client_code():
        """Générer un code client unique (exemple: OD-ABC123)"""
        chars = string.ascii_uppercase + string.digits
        random_part = ''.join(secrets.choice(chars) for _ in range(6))
        return f"OD-{random_part}"

    def _compute_onboarding_progress(self):
        """Calculer la progression de l'onboarding"""
        step_progress = {
            'welcome': 20,
            'account_setup': 40,
            'property_setup': 60,
            'payment_setup': 80,
            'integration': 90,
            'completed': 100,
        }
        for record in self:
            record.onboarding_progress = step_progress.get(record.onboarding_step, 0)

    def _compute_usage_stats(self):
        """Calculer les statistiques d'utilisation"""
        for record in self:
            # Initialization simple des compteurs
            # TODO: Implémenter les relations company_id pour les modèles property, unit, reservation
            record.properties_count = 0
            record.units_count = 0
            record.reservations_count = 0

    @api.onchange('accepted_tos')
    def _onchange_accepted_tos(self):
        """Mettre à jour la date d'acceptation automatiquement"""
        if self.accepted_tos and not self.tos_accepted_date:
            self.tos_accepted_date = fields.Date.today()

    @api.onchange('accepted_privacy')
    def _onchange_accepted_privacy(self):
        """Mettre à jour la date d'acceptation automatiquement"""
        if self.accepted_privacy and not self.privacy_accepted_date:
            self.privacy_accepted_date = fields.Date.today()

    def action_mark_tos_accepted(self):
        """Marquer les conditions d'utilisation comme acceptées"""
        self.accepted_tos = True
        self.tos_accepted_date = fields.Date.today()

    def action_mark_privacy_accepted(self):
        """Marquer la politique de confidentialité comme acceptée"""
        self.accepted_privacy = True
        self.privacy_accepted_date = fields.Date.today()

    def action_next_onboarding_step(self):
        """Passer à l'étape suivante de l'onboarding"""
        step_progression = {
            'welcome': 'account_setup',
            'account_setup': 'property_setup',
            'property_setup': 'payment_setup',
            'payment_setup': 'integration',
            'integration': 'completed',
            'completed': 'completed',
        }

        new_step = step_progression.get(self.onboarding_step)
        if new_step:
            self.onboarding_step = new_step

            # Marquer comme complété
            if new_step == 'completed':
                self.state = 'active'
                self.onboarding_completed_date = fields.Date.today()

    def action_activate_client(self):
        """Activer le client"""
        if not self.accepted_tos or not self.accepted_privacy:
            raise ValidationError("Le client doit accepter les conditions et la politique de confidentialité")

        self.state = 'active'
        self.action_next_onboarding_step()

    def action_suspend_client(self):
        """Suspendre le client"""
        # Suspendre l'abonnement associé
        if self.subscription_id:
            self.subscription_id.action_suspend()
        self.state = 'suspended'

    def action_cancel_client(self):
        """Annuler le client"""
        # Annuler l'abonnement associé
        if self.subscription_id:
            self.subscription_id.action_cancel()
        self.state = 'cancelled'

    def get_subscription_limits(self):
        """Obtenir les limites du plan d'abonnement"""
        if self.subscription_id:
            return self.subscription_id.get_effective_plan_values()
        return {}

    def update_last_activity(self):
        """Mettre à jour l'heure de dernière activité"""
        self.last_activity = fields.Datetime.now()

    @api.model
    def find_by_company(self, company_id):
        """Trouver le client par company_id"""
        return self.search([('company_id', '=', company_id)], limit=1)


class OnedeskoClientInvitation(models.Model):
    """
    Modèle pour gérer les invitations de clients
    Utilisé pour l'onboarding et l'ajout d'utilisateurs
    """
    _name = 'onedesk.client.invitation'
    _description = 'Client Invitation'
    _order = 'create_date desc'

    client_id = fields.Many2one(
        'onedesk.client',
        string="Client",
        required=True,
        ondelete='cascade'
    )
    email = fields.Char(string="Email", required=True)
    invitation_token = fields.Char(
        string="Token d'invitation",
        readonly=True,
        copy=False
    )
    role = fields.Selection([
        ('owner', 'Propriétaire'),
        ('manager', 'Gestionnaire'),
        ('staff', 'Personnel'),
        ('viewer', 'Consultateur'),
    ], string="Rôle", default='manager')

    state = fields.Selection([
        ('pending', 'En attente'),
        ('accepted', 'Acceptée'),
        ('rejected', 'Rejetée'),
        ('expired', 'Expirée'),
    ], string="État", default='pending')

    sent_date = fields.Datetime(string="Date d'envoi")
    accepted_date = fields.Datetime(string="Date d'acceptation")
    expires_date = fields.Datetime(string="Date d'expiration")

    @api.model
    def create(self, vals_list):
        """Générer des tokens uniques pour les invitations"""
        for vals in vals_list:
            if not vals.get('invitation_token'):
                vals['invitation_token'] = self._generate_token()
            if not vals.get('expires_date'):
                import datetime
                vals['expires_date'] = fields.Datetime.now() + datetime.timedelta(days=7)

        return super().create(vals_list)

    @staticmethod
    def _generate_token():
        """Générer un token d'invitation sécurisé"""
        return secrets.token_urlsafe(32)

    def send_invitation_email(self):
        """Envoyer l'email d'invitation"""
        self.ensure_one()
        # À implémenter avec le système d'email
        self.sent_date = fields.Datetime.now()

    def action_accept_invitation(self, password=None):
        """Accepter l'invitation et créer un utilisateur"""
        self.ensure_one()

        if self.state != 'pending':
            raise ValidationError("Cette invitation n'est pas valide")

        # Vérifier l'expiration
        if fields.Datetime.now() > self.expires_date:
            self.state = 'expired'
            raise ValidationError("L'invitation a expiré")

        # Créer l'utilisateur
        user = self.env['res.users'].create({
            'name': self.email.split('@')[0],
            'email': self.email,
            'login': self.email,
            'company_id': self.client_id.company_id.id,
            'company_ids': [(4, self.client_id.company_id.id)],
            'groups_id': [(4, self._get_group_id())],
        })

        if password:
            user.password = password

        self.state = 'accepted'
        self.accepted_date = fields.Datetime.now()

        return user

    def _get_group_id(self):
        """Obtenir le groupe correspondant au rôle"""
        group_map = {
            'owner': 'onedesk_core.group_onedesk_property_manager',
            'manager': 'onedesk_core.group_onedesk_property_manager',
            'staff': 'onedesk_core.group_onedesk_staff',
            'viewer': 'onedesk_core.group_onedesk_viewer',
        }
        group_ref = group_map.get(self.role)
        if group_ref:
            return self.env.ref(group_ref).id
        return False
