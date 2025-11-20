from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class OnedeskoSubscriptionPlan(models.Model):
    """
    Modèle de plan d'abonnement flexible pour OneDesk
    Supportez la facturation par unité ou par pourcentage sur 3 ans
    """
    _name = 'onedesk.subscription.plan'
    _description = 'Subscription Plan for OneDesk'
    _order = 'sequence, id'

    name = fields.Char(string="Nom du plan", required=True)
    description = fields.Text(string="Description")
    sequence = fields.Integer(string="Ordre d'affichage", default=10)
    active = fields.Boolean(string="Actif", default=True)

    # Billing Model
    billing_model = fields.Selection([
        ('per_unit', 'Par unité'),
        ('commission', 'Commission (%)'),
    ], string="Modèle de facturation", required=True, default='per_unit')

    # Per-Unit Pricing
    price_per_unit = fields.Float(
        string="Prix par unité/mois",
        help="Prix mensuel par unité de location"
    )

    # Commission Model
    commission_percentage = fields.Float(
        string="Commission (%)",
        help="Pourcentage de commission sur les réservations"
    )
    commission_period = fields.Selection([
        ('monthly', 'Mensuel'),
        ('quarterly', 'Trimestriel'),
        ('yearly', 'Annuel'),
    ], string="Période de facturation", default='monthly')

    # Setup & Support
    setup_fee = fields.Float(string="Frais de setup", default=0.0)
    includes_support = fields.Boolean(string="Support inclus", default=True)
    support_hours = fields.Selection([
        ('none', 'Aucun'),
        ('business', 'Heures de bureau'),
        ('24_7', '24/7'),
    ], string="Heures de support", default='business')

    # Features
    max_properties = fields.Integer(
        string="Max de propriétés",
        default=-1,  # -1 = illimité
        help="-1 pour illimité"
    )
    max_units = fields.Integer(
        string="Max d'unités",
        default=-1,
        help="-1 pour illimité"
    )
    max_users = fields.Integer(
        string="Max d'utilisateurs",
        default=1,
        help="Nombre de comptes utilisateurs inclus"
    )

    include_channel_manager = fields.Boolean(
        string="Gestionnaire multi-canaux inclus",
        default=False
    )
    include_accounting = fields.Boolean(
        string="Module comptable inclus",
        default=False
    )
    include_advanced_analytics = fields.Boolean(
        string="Analytique avancée incluse",
        default=False
    )

    # Contract
    minimum_commitment_months = fields.Integer(
        string="Engagement minimum (mois)",
        default=12
    )
    can_downgrade = fields.Boolean(
        string="Permettre la rétrogradation",
        default=True
    )

    subscription_ids = fields.One2many(
        'onedesk.subscription',
        'plan_id',
        string="Abonnements"
    )

    def get_display_name(self):
        """Affichage personnalisé du plan"""
        billing_label = dict(self._fields['billing_model'].selection).get(self.billing_model, '')
        return f"{self.name} ({billing_label})"

    @api.constrains('price_per_unit', 'commission_percentage')
    def _check_plan_values(self):
        """Valider les valeurs du plan"""
        for record in self:
            if record.price_per_unit < 0:
                raise ValidationError("Le prix par unité doit être positif")
            if record.commission_percentage < 0 or record.commission_percentage > 100:
                raise ValidationError("La commission doit être entre 0 et 100%")


class OnedeskoSubscription(models.Model):
    """
    Modèle d'abonnement client
    Lie un plan à une Company
    """
    _name = 'onedesk.subscription'
    _description = 'Client Subscription to OneDesk'
    _order = 'start_date desc'

    # Identifiant unique
    subscription_id = fields.Char(string="ID Abonnement", readonly=True, copy=False)

    # Relations
    company_id = fields.Many2one(
        'res.company',
        string="Société client",
        required=True,
        default=lambda self: self.env.company,
        ondelete='cascade'
    )
    plan_id = fields.Many2one(
        'onedesk.subscription.plan',
        string="Plan d'abonnement",
        required=True,
        ondelete='restrict'
    )

    # Dates
    start_date = fields.Date(string="Date de début", required=True, default=fields.Date.today)
    end_date = fields.Date(string="Date de fin")
    cancellation_date = fields.Date(string="Date d'annulation")

    # Status
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('active', 'Actif'),
        ('suspended', 'Suspendu'),
        ('cancelled', 'Annulé'),
        ('expired', 'Expiré'),
    ], string="État", default='draft', required=True)

    # Customization
    custom_price_per_unit = fields.Float(
        string="Prix personnalisé par unité",
        help="Laisser vide pour utiliser le prix du plan"
    )
    custom_commission = fields.Float(
        string="Commission personnalisée (%)",
        help="Laisser vide pour utiliser la commission du plan"
    )
    discount_percentage = fields.Float(
        string="Remise globale (%)",
        default=0.0
    )

    # Requested Units from Form
    requested_units = fields.Integer(
        string="Unités demandées",
        help="Nombre d'unités (propriétés/chambres) demandé lors de la souscription via le formulaire web",
        default=0
    )

    notes = fields.Text(string="Notes commerciales")

    # Auto-renewal
    auto_renew = fields.Boolean(string="Renouvellement automatique", default=True)
    renewal_notice_days = fields.Integer(
        string="Jours avant renouvellement",
        default=30,
        help="Notification avant la fin du contrat"
    )

    # Billing
    billing_contact_id = fields.Many2one(
        'res.partner',
        string="Contact de facturation",
        help="Contact pour les factures"
    )
    invoice_ids = fields.One2many(
        'account.move',
        'onedesk_subscription_id',
        string="Factures"
    )

    # Activity
    last_invoice_date = fields.Date(string="Dernière facture")
    next_invoice_date = fields.Date(string="Prochaine facture", compute='_compute_next_invoice_date')

    # Usage
    current_units_count = fields.Integer(
        string="Unités actuelles",
        compute='_compute_current_usage',
        readonly=True
    )
    current_users_count = fields.Integer(
        string="Utilisateurs actuels",
        compute='_compute_current_usage',
        readonly=True
    )

    @api.model
    def create(self, vals_list):
        """Générer les ID d'abonnement uniques"""
        for vals in vals_list:
            if not vals.get('subscription_id'):
                vals['subscription_id'] = self.env['ir.sequence'].next_by_code('onedesk.subscription')
        return super().create(vals_list)

    @api.depends('plan_id.billing_model')
    def _compute_next_invoice_date(self):
        """Calculer la prochaine date de facture"""
        for record in self:
            if record.state == 'active' and record.last_invoice_date:
                plan = record.plan_id
                period_map = {
                    'monthly': 30,
                    'quarterly': 90,
                    'yearly': 365,
                }
                days = period_map.get(plan.commission_period, 30)
                record.next_invoice_date = fields.Date.add(record.last_invoice_date, days=days)
            else:
                record.next_invoice_date = False

    def _compute_current_usage(self):
        """Calculer l'utilisation actuelle (unités, utilisateurs)"""
        for record in self:
            # Compter les unités actuelles de cette entreprise
            units_count = self.env['onedesk.unit'].search_count([
                ('company_id', '=', record.company_id.id),
                ('active', '=', True)
            ])

            # Compter les utilisateurs actifs de cette entreprise
            users_count = self.env['res.users'].search_count([
                ('company_id', '=', record.company_id.id),
                ('active', '=', True)
            ])

            record.current_units_count = units_count
            record.current_users_count = users_count

    def action_activate(self):
        """Activer l'abonnement"""
        self.state = 'active'

        # Créer le client OneDesk s'il n'existe pas
        # Cela va déclencher automatiquement la création des 3 rôles (property-manager, staff, viewer)
        client = self.env['onedesk.client'].search([('company_id', '=', self.company_id.id)], limit=1)
        if not client:
            client = self.env['onedesk.client'].create({
                'company_id': self.company_id.id,
                'owner_partner_id': self.billing_contact_id.id,
                'subscription_id': self.id,
                'state': 'active',
            })
            _logger.info(f'✅ Created OneDesk client {client.id} for company {self.company_id.name} with 3 default roles')

        # Audit log pour l'activation
        self.env['onedesk.audit.log'].create({
            'log_type': 'subscription_activated',
            'severity': 'info',
            'subscription_id': self.id,
            'company_id': self.company_id.id,
            'description': f'Abonnement activé: {self.subscription_id}',
            'result': 'success',
        })

    def action_suspend(self):
        """Suspendre l'abonnement"""
        self.state = 'suspended'

        # Désactiver tous les utilisateurs de cette entreprise
        users = self.env['res.users'].search([('company_id', '=', self.company_id.id)])
        users.write({'active': False})
        _logger.info(f'⏸️ Suspended subscription and deactivated {len(users)} users for company {self.company_id.name}')

        # Audit log pour la suspension
        self.env['onedesk.audit.log'].create({
            'log_type': 'subscription_suspended',
            'severity': 'warning',
            'subscription_id': self.id,
            'company_id': self.company_id.id,
            'description': f'Abonnement suspendu: {self.subscription_id} - {len(users)} utilisateurs désactivés',
            'result': 'success',
        })

    def action_reactivate(self):
        """Réactiver un abonnement suspendu"""
        self.state = 'active'

        # Réactiver tous les utilisateurs de cette entreprise
        users = self.env['res.users'].search([('company_id', '=', self.company_id.id)])
        users.write({'active': True})
        _logger.info(f'✅ Reactivated subscription and enabled {len(users)} users for company {self.company_id.name}')

        # Audit log pour la réactivation
        self.env['onedesk.audit.log'].create({
            'log_type': 'subscription_activated',
            'severity': 'info',
            'subscription_id': self.id,
            'company_id': self.company_id.id,
            'description': f'Abonnement réactivé: {self.subscription_id} - {len(users)} utilisateurs réactivés',
            'result': 'success',
        })

    def action_cancel(self):
        """Annuler l'abonnement"""
        self.cancellation_date = fields.Date.today()
        self.state = 'cancelled'

        # Désactiver tous les utilisateurs de cette entreprise
        users = self.env['res.users'].search([('company_id', '=', self.company_id.id)])
        users.write({'active': False})
        _logger.info(f'❌ Cancelled subscription and deactivated {len(users)} users for company {self.company_id.name}')

        # Audit log pour l'annulation
        self.env['onedesk.audit.log'].create({
            'log_type': 'subscription_cancelled',
            'severity': 'critical',
            'subscription_id': self.id,
            'company_id': self.company_id.id,
            'description': f'Abonnement annulé: {self.subscription_id} - {len(users)} utilisateurs désactivés',
            'result': 'success',
        })

    def calculate_monthly_fee(self):
        """Calculer les frais mensuels basés sur l'utilisation"""
        self.ensure_one()

        if self.plan_id.billing_model == 'per_unit':
            price = self.custom_price_per_unit or self.plan_id.price_per_unit
            monthly_fee = self.current_units_count * price
        else:  # commission model
            monthly_fee = 0  # Calculé à partir des réservations

        # Appliquer la remise
        discount = monthly_fee * (self.discount_percentage / 100)
        return monthly_fee - discount

    def get_effective_plan_values(self):
        """Obtenir les valeurs effectives du plan (avec customisations)"""
        self.ensure_one()
        return {
            'price_per_unit': self.custom_price_per_unit or self.plan_id.price_per_unit,
            'commission_percentage': self.custom_commission or self.plan_id.commission_percentage,
            'discount_percentage': self.discount_percentage,
            'max_properties': self.plan_id.max_properties,
            'max_units': self.plan_id.max_units,
            'max_users': self.plan_id.max_users,
        }

    def _check_limits(self):
        """Vérifier si les limites d'utilisation sont respectées"""
        plan = self.plan_id

        if plan.max_properties != -1 and self.current_units_count > plan.max_properties:
            raise ValidationError(
                f"Vous avez dépassé le nombre maximum de propriétés ({plan.max_properties})"
            )

        if plan.max_units != -1 and self.current_units_count > plan.max_units:
            raise ValidationError(
                f"Vous avez dépassé le nombre maximum d'unités ({plan.max_units})"
            )

        if plan.max_users != -1 and self.current_users_count > plan.max_users:
            raise ValidationError(
                f"Vous avez dépassé le nombre maximum d'utilisateurs ({plan.max_users})"
            )
