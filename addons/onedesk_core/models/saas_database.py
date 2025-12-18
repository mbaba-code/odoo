# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SaasDatabase(models.Model):
    _name = 'saas.database'
    _description = 'Instance Base de Données Client'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Nom de la Base', required=True, readonly=True)
    client_id = fields.Many2one('saas.client', 'Client', required=True, ondelete='cascade')
    plan_id = fields.Many2one('saas.plan', 'Plan', related='client_id.plan_id', store=True)

    state = fields.Selection([
        ('active', 'Active'),
        ('suspended', 'Suspendue'),
        ('terminated', 'Terminée'),
    ], string='État', default='active', required=True, tracking=True)

    # Informations techniques
    postgresql_size_bytes = fields.Integer('Taille PostgreSQL (bytes)', readonly=True)
    postgresql_size_mb = fields.Float('Taille PostgreSQL (MB)', compute='_compute_postgresql_size_mb', store=True)
    filestore_size_bytes = fields.Integer('Taille Filestore (bytes)', readonly=True)
    filestore_size_mb = fields.Float('Taille Filestore (MB)', compute='_compute_filestore_size_mb', store=True)

    total_size_gb = fields.Float('Taille Totale (GB)', compute='_compute_total_size_gb', store=True)

    # Statistiques
    nb_tables = fields.Integer('Nombre de Tables', readonly=True)
    nb_records_total = fields.Integer('Nombre Total d\'Enregistrements', readonly=True)

    # Dernière activité
    last_backup_date = fields.Datetime('Dernier Backup', readonly=True)
    last_update_date = fields.Datetime('Dernière Mise à Jour', readonly=True)
    last_connection_date = fields.Datetime('Dernière Connexion', readonly=True)

    # Métriques
    metric_ids = fields.One2many('saas.metric', 'database_id', 'Métriques')

    @api.depends('postgresql_size_bytes')
    def _compute_postgresql_size_mb(self):
        for db in self:
            db.postgresql_size_mb = (db.postgresql_size_bytes or 0) / (1024**2)

    @api.depends('filestore_size_bytes')
    def _compute_filestore_size_mb(self):
        for db in self:
            db.filestore_size_mb = (db.filestore_size_bytes or 0) / (1024**2)

    @api.depends('postgresql_size_bytes', 'filestore_size_bytes')
    def _compute_total_size_gb(self):
        for db in self:
            total_bytes = (db.postgresql_size_bytes or 0) + (db.filestore_size_bytes or 0)
            db.total_size_gb = total_bytes / (1024**3)
