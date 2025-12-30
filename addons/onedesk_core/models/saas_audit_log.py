# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class SaasAuditLog(models.Model):
    """
    Journal d'audit pour toutes les actions critiques SaaS

    SÉCURITÉ: Traçabilité complète des opérations sensibles
    Conforme RGPD avec rétention de 1 an minimum pour audit
    """
    _name = 'saas.audit_log'
    _description = 'Journal d\'Audit SaaS'
    _order = 'timestamp desc'
    _rec_name = 'action'

    # Identification de l'action
    action = fields.Selection([
        # Provisioning
        ('provision', 'Provisioning Base'),
        ('provision_success', 'Provisioning Réussi'),
        ('provision_error', 'Erreur Provisioning'),

        # État de la base
        ('suspend', 'Suspension Base'),
        ('terminate', 'Terminaison Base'),
        ('reactivate', 'Réactivation Base'),

        # Modifications
        ('change_plan', 'Changement de Plan'),
        ('update_quotas', 'Mise à jour Quotas'),
        ('update_domain', 'Mise à jour Domaine'),

        # Sécurité
        ('password_reset', 'Réinitialisation Mot de Passe'),
        ('access_granted', 'Accès Accordé'),
        ('access_denied', 'Accès Refusé'),
        ('rate_limit_hit', 'Rate Limit Atteint'),

        # Système
        ('backup_created', 'Backup Créé'),
        ('backup_restored', 'Backup Restauré'),
        ('migration', 'Migration Base'),
    ], string='Action', required=True, index=True)

    action_category = fields.Selection([
        ('security', 'Sécurité'),
        ('provisioning', 'Provisioning'),
        ('administration', 'Administration'),
        ('system', 'Système'),
    ], string='Catégorie', compute='_compute_action_category', store=True, index=True)

    # Contexte
    timestamp = fields.Datetime('Horodatage', default=fields.Datetime.now, required=True, index=True,
                                 help="Date et heure exacte de l'action")

    # Acteur
    user_id = fields.Many2one('res.users', 'Utilisateur', index=True,
                               help="Utilisateur ayant effectué l'action")
    user_name = fields.Char('Nom Utilisateur', help="Nom de l'utilisateur au moment de l'action")
    user_email = fields.Char('Email Utilisateur')

    # Cible
    client_id = fields.Many2one('saas.client', 'Client SaaS', ondelete='set null', index=True,
                                 help="Client concerné par l'action")
    client_name = fields.Char('Nom Client', help="Nom du client au moment de l'action")
    database_name = fields.Char('Nom Base', index=True)

    # Détails techniques
    ip_address = fields.Char('Adresse IP', index=True,
                              help="IP source de la requête")
    user_agent = fields.Char('User Agent',
                              help="Navigateur/Client HTTP utilisé")

    # Résultat
    status = fields.Selection([
        ('success', 'Succès'),
        ('error', 'Erreur'),
        ('warning', 'Avertissement'),
    ], string='Statut', default='success', required=True, index=True)

    error_message = fields.Text('Message d\'Erreur',
                                 help="Détails de l'erreur si applicable")

    # Données additionnelles
    old_values = fields.Text('Anciennes Valeurs (JSON)',
                              help="Valeurs avant modification (format JSON)")
    new_values = fields.Text('Nouvelles Valeurs (JSON)',
                              help="Valeurs après modification (format JSON)")
    metadata = fields.Text('Métadonnées (JSON)',
                            help="Informations contextuelles additionnelles")

    # Niveau de sévérité
    severity = fields.Selection([
        ('info', 'Information'),
        ('warning', 'Avertissement'),
        ('critical', 'Critique'),
    ], string='Sévérité', compute='_compute_severity', store=True, index=True)

    # Archive et rétention
    is_archived = fields.Boolean('Archivé', default=False,
                                   help="Enregistrement archivé après rétention")
    retention_date = fields.Date('Date Rétention', compute='_compute_retention_date', store=True,
                                   help="Date après laquelle l'enregistrement peut être archivé")

    @api.depends('action')
    def _compute_action_category(self):
        """Catégorise automatiquement l'action"""
        for record in self:
            if record.action in ['access_granted', 'access_denied', 'password_reset', 'rate_limit_hit']:
                record.action_category = 'security'
            elif record.action in ['provision', 'provision_success', 'provision_error']:
                record.action_category = 'provisioning'
            elif record.action in ['suspend', 'terminate', 'reactivate', 'change_plan', 'update_quotas', 'update_domain']:
                record.action_category = 'administration'
            else:
                record.action_category = 'system'

    @api.depends('action', 'status')
    def _compute_severity(self):
        """Détermine automatiquement la sévérité"""
        for record in self:
            if record.status == 'error':
                record.severity = 'critical'
            elif record.action in ['terminate', 'suspend', 'access_denied', 'rate_limit_hit']:
                record.severity = 'warning'
            elif record.action in ['provision_error']:
                record.severity = 'critical'
            else:
                record.severity = 'info'

    @api.depends('timestamp')
    def _compute_retention_date(self):
        """
        Calcule la date de rétention (RGPD: 1 an minimum pour audit)
        Les logs critiques sont conservés 3 ans
        """
        for record in self:
            if not record.timestamp:
                record.retention_date = False
                continue

            # Logs critiques: 3 ans
            if record.severity == 'critical' or record.action_category == 'security':
                retention_years = 3
            else:
                # Logs normaux: 1 an
                retention_years = 1

            record.retention_date = (record.timestamp + timedelta(days=365 * retention_years)).date()

    @api.model
    def log_action(self, action, client_id=None, status='success', error_message=None,
                   old_values=None, new_values=None, metadata=None):
        """
        Enregistre une action dans le journal d'audit

        Args:
            action (str): Type d'action (voir sélection 'action')
            client_id (int): ID du client concerné
            status (str): 'success', 'error', 'warning'
            error_message (str): Message d'erreur si applicable
            old_values (dict): Valeurs avant modification
            new_values (dict): Valeurs après modification
            metadata (dict): Métadonnées contextuelles

        Returns:
            saas.audit_log: Record créé
        """
        import json
        from odoo.http import request

        # Récupérer l'utilisateur actuel
        user = self.env.user
        user_name = user.name
        user_email = user.email

        # Récupérer l'IP et User-Agent si disponibles
        ip_address = None
        user_agent = None

        if request and hasattr(request, 'httprequest'):
            # IP réelle (supporte proxy/load balancer)
            ip_address = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR')
            if ip_address:
                ip_address = ip_address.split(',')[0].strip()
            else:
                ip_address = request.httprequest.environ.get('REMOTE_ADDR')

            user_agent = request.httprequest.environ.get('HTTP_USER_AGENT', '')[:255]

        # Récupérer les infos du client si fourni
        client_name = None
        database_name = None

        if client_id:
            client = self.env['saas.client'].browse(client_id)
            if client.exists():
                client_name = client.name
                database_name = client.database_name

        # Convertir les dictionnaires en JSON
        old_values_json = json.dumps(old_values) if old_values else None
        new_values_json = json.dumps(new_values) if new_values else None
        metadata_json = json.dumps(metadata) if metadata else None

        # Créer l'enregistrement d'audit
        audit_log = self.create({
            'action': action,
            'timestamp': fields.Datetime.now(),
            'user_id': user.id,
            'user_name': user_name,
            'user_email': user_email,
            'client_id': client_id,
            'client_name': client_name,
            'database_name': database_name,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'status': status,
            'error_message': error_message,
            'old_values': old_values_json,
            'new_values': new_values_json,
            'metadata': metadata_json,
        })

        # Log selon la sévérité
        if audit_log.severity == 'critical':
            _logger.error(f"[SAAS AUDIT CRITICAL] {action} - Client: {client_name} - User: {user_name} - Status: {status}")
        elif audit_log.severity == 'warning':
            _logger.warning(f"[SAAS AUDIT WARNING] {action} - Client: {client_name} - User: {user_name}")
        else:
            _logger.info(f"[SAAS AUDIT] {action} - Client: {client_name} - User: {user_name}")

        return audit_log

    @api.model
    def cleanup_old_logs(self):
        """
        Archive les logs ayant dépassé leur date de rétention
        Appelé par un cron job mensuel

        Les logs ne sont PAS supprimés mais archivés pour conformité
        """
        today = fields.Date.today()

        # Trouver les logs à archiver
        old_logs = self.search([
            ('is_archived', '=', False),
            ('retention_date', '<', today),
        ])

        count = len(old_logs)
        if count > 0:
            old_logs.write({'is_archived': True})
            _logger.info(f"[SAAS AUDIT] {count} logs archivés (rétention expirée)")

        return {'archived': count}

    @api.model
    def get_statistics(self, days=30):
        """
        Retourne des statistiques d'audit pour les X derniers jours

        Args:
            days (int): Nombre de jours à analyser (défaut: 30)

        Returns:
            dict: Statistiques par action, catégorie, sévérité
        """
        cutoff_date = fields.Datetime.now() - timedelta(days=days)

        domain = [('timestamp', '>=', cutoff_date)]

        total = self.search_count(domain)

        # Par statut
        by_status = {}
        for status in ['success', 'error', 'warning']:
            by_status[status] = self.search_count(domain + [('status', '=', status)])

        # Par sévérité
        by_severity = {}
        for severity in ['info', 'warning', 'critical']:
            by_severity[severity] = self.search_count(domain + [('severity', '=', severity)])

        # Par catégorie
        by_category = {}
        for category in ['security', 'provisioning', 'administration', 'system']:
            by_category[category] = self.search_count(domain + [('action_category', '=', category)])

        # Top 5 actions
        top_actions = self.read_group(
            domain,
            ['action'],
            ['action'],
            limit=5,
            orderby='action_count desc'
        )

        return {
            'total': total,
            'by_status': by_status,
            'by_severity': by_severity,
            'by_category': by_category,
            'top_actions': top_actions,
            'period_days': days,
        }
