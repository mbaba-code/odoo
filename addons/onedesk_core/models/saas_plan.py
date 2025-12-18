# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SaasPlan(models.Model):
    _name = 'saas.plan'
    _description = 'Plan SaaS Premium'
    _order = 'sequence, id'

    name = fields.Char('Nom du Plan', required=True, translate=True)
    sequence = fields.Integer('Séquence', default=10)
    active = fields.Boolean('Actif', default=True)

    # Description
    description = fields.Html('Description', translate=True)

    # Limites techniques
    max_users = fields.Integer('Max Utilisateurs', default=5, required=True)
    max_storage_gb = fields.Float('Max Stockage (GB)', default=10.0, required=True)
    max_api_calls_per_day = fields.Integer('Max API Calls/Jour', default=10000, required=True)
    max_databases = fields.Integer('Max Bases de Données', default=1, help="Pour les plans Enterprise multi-instances")

    # Tarification
    price_monthly = fields.Float('Prix Mensuel (€)', required=True, digits=(10, 2))
    price_yearly = fields.Float('Prix Annuel (€)', required=True, digits=(10, 2))
    trial_days = fields.Integer('Jours d\'Essai Gratuit', default=14)

    # Fonctionnalités
    has_custom_domain = fields.Boolean('Domaine Personnalisé', default=False)
    has_white_label = fields.Boolean('White Label', default=False, help="Personnalisation complète de la marque")
    has_api_access = fields.Boolean('Accès API', default=False)
    has_advanced_analytics = fields.Boolean('Analytics Avancés', default=False)
    has_priority_support = fields.Boolean('Support Prioritaire', default=False)

    # Support
    support_level = fields.Selection([
        ('email', 'Email (24-48h)'),
        ('chat', 'Email + Chat (8-24h)'),
        ('phone', 'Email + Chat + Phone (4-8h)'),
        ('dedicated', 'Dédié 24/7 (< 1h)'),
    ], string='Niveau de Support', default='email', required=True)

    # Modules Odoo autorisés
    allowed_module_ids = fields.Many2many(
        'ir.module.module',
        'saas_plan_module_rel',
        'plan_id',
        'module_id',
        string='Modules Autorisés',
        help="Modules que les clients de ce plan peuvent installer"
    )

    # Statistiques
    client_count = fields.Integer('Nombre de Clients', compute='_compute_client_count', store=True)
    revenue_monthly = fields.Float('Revenu Mensuel', compute='_compute_revenue', store=True)
    revenue_yearly = fields.Float('Revenu Annuel', compute='_compute_revenue', store=True)

    # Clients
    client_ids = fields.One2many('saas.client', 'plan_id', string='Clients')

    @api.depends('client_ids', 'client_ids.subscription_state')
    def _compute_client_count(self):
        for plan in self:
            plan.client_count = len(plan.client_ids.filtered(lambda c: c.subscription_state == 'active'))

    @api.depends('client_ids', 'client_ids.subscription_billing', 'price_monthly', 'price_yearly')
    def _compute_revenue(self):
        for plan in self:
            monthly_clients = plan.client_ids.filtered(
                lambda c: c.subscription_state == 'active' and c.subscription_billing == 'monthly'
            )
            yearly_clients = plan.client_ids.filtered(
                lambda c: c.subscription_state == 'active' and c.subscription_billing == 'yearly'
            )

            plan.revenue_monthly = len(monthly_clients) * plan.price_monthly
            plan.revenue_yearly = len(yearly_clients) * plan.price_yearly

    @api.constrains('max_users', 'max_storage_gb', 'max_api_calls_per_day')
    def _check_limits(self):
        for plan in self:
            if plan.max_users < 1:
                raise models.ValidationError("Le nombre max d'utilisateurs doit être au moins 1")
            if plan.max_storage_gb < 1:
                raise models.ValidationError("Le stockage max doit être au moins 1 GB")
            if plan.max_api_calls_per_day < 100:
                raise models.ValidationError("Le nombre d'API calls doit être au moins 100/jour")

    def name_get(self):
        result = []
        for plan in self:
            name = f"{plan.name} ({plan.client_count} clients)"
            result.append((plan.id, name))
        return result
