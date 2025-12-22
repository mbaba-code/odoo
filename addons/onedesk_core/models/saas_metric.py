# -*- coding: utf-8 -*-
from odoo import models, fields

class SaasMetric(models.Model):
    _name = 'saas.metric'
    _description = 'Métrique Client SaaS'
    _order = 'recorded_at desc'

    client_id = fields.Many2one('saas.client', 'Client', required=True, ondelete='cascade', index=True)
    database_id = fields.Many2one('saas.database', 'Base de données', required=True, ondelete='cascade')

    # Métrique
    metric_type = fields.Selection([
        ('users_active', 'Utilisateurs Actifs'),
        ('users_connected', 'Utilisateurs Connectés'),
        ('storage_used', 'Stockage Utilisé'),
        ('storage_filestore', 'Stockage Filestore'),
        ('storage_database', 'Stockage Base de Données'),
        ('requests_per_minute', 'Requêtes/minute'),
        ('response_time_avg', 'Temps de Réponse Moyen'),
        ('errors_count', 'Nombre d\'Erreurs'),
        ('cpu_usage', 'Usage CPU'),
        ('memory_usage', 'Usage Mémoire'),
        ('api_calls', 'Appels API'),
    ], string='Type de Métrique', required=True, index=True)

    value = fields.Float('Valeur', required=True)
    unit = fields.Char('Unité', help='users, GB, ms, %, etc.')

    recorded_at = fields.Datetime('Enregistré le', default=fields.Datetime.now, required=True, index=True)

    _sql_constraints = [
        ('check_value_positive', 'CHECK(value >= 0)', 'La valeur doit être positive'),
    ]
