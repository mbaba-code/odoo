# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SaasAlert(models.Model):
    _name = 'saas.alert'
    _description = 'Alerte SaaS'
    _inherit = ['mail.thread']
    _order = 'created_at desc'

    client_id = fields.Many2one('saas.client', 'Client', required=True, ondelete='cascade', tracking=True)

    alert_type = fields.Selection([
        ('quota_users_exceeded', 'Quota Utilisateurs Dépassé'),
        ('quota_storage_exceeded', 'Quota Stockage Dépassé'),
        ('quota_api_exceeded', 'Quota API Dépassé'),
        ('payment_failed', 'Paiement Échoué'),
        ('trial_ending_soon', 'Essai se Termine Bientôt'),
        ('trial_expired', 'Essai Expiré'),
        ('high_error_rate', 'Taux d\'Erreur Élevé'),
        ('slow_response', 'Temps de Réponse Lent'),
        ('downtime', 'Indisponibilité'),
        ('backup_failed', 'Échec de Sauvegarde'),
    ], string='Type d\'Alerte', required=True, tracking=True)

    severity = fields.Selection([
        ('info', 'Info'),
        ('warning', 'Avertissement'),
        ('error', 'Erreur'),
        ('critical', 'Critique'),
    ], string='Sévérité', required=True, default='warning', tracking=True)

    message = fields.Text('Message', required=True)
    details = fields.Html('Détails')

    resolved = fields.Boolean('Résolu', default=False, tracking=True)
    resolved_by = fields.Many2one('res.users', 'Résolu par', readonly=True)
    resolved_at = fields.Datetime('Résolu le', readonly=True)
    resolution_notes = fields.Text('Notes de Résolution')

    created_at = fields.Datetime('Créé le', default=fields.Datetime.now, readonly=True)

    # Notification
    notification_sent = fields.Boolean('Notification Envoyée', default=False)
    notification_sent_at = fields.Datetime('Notification Envoyée le')

    def action_resolve(self):
        """Marquer l'alerte comme résolue"""
        self.write({
            'resolved': True,
            'resolved_by': self.env.user.id,
            'resolved_at': fields.Datetime.now(),
        })
        self.message_post(body="Alerte résolue")

    def action_send_notification(self):
        """Envoyer une notification au client"""
        for alert in self:
            # TODO: Envoyer email au client
            alert.write({
                'notification_sent': True,
                'notification_sent_at': fields.Datetime.now(),
            })
            alert.message_post(body=f"Notification envoyée à {alert.client_id.email}")

    @api.model
    def cron_check_quotas(self):
        """Cron: Vérifier les quotas de tous les clients actifs"""
        clients = self.env['saas.client'].search([('database_state', '=', 'active')])

        for client in clients:
            self._check_client_quotas(client)

    def _check_client_quotas(self, client):
        """Vérifier les quotas d'un client et créer des alertes si nécessaire"""
        plan = client.plan_id

        # Vérifier quota utilisateurs
        if client.nb_users > plan.max_users:
            existing_alert = self.search([
                ('client_id', '=', client.id),
                ('alert_type', '=', 'quota_users_exceeded'),
                ('resolved', '=', False),
            ], limit=1)

            if not existing_alert:
                self.create({
                    'client_id': client.id,
                    'alert_type': 'quota_users_exceeded',
                    'severity': 'warning',
                    'message': f'Quota utilisateurs dépassé: {client.nb_users}/{plan.max_users}',
                    'details': f'<p>Le client a {client.nb_users} utilisateurs actifs, '
                               f'mais son plan "{plan.name}" autorise seulement {plan.max_users} utilisateurs.</p>'
                               f'<p>Action recommandée: Proposer un upgrade de plan.</p>',
                })

        # Vérifier quota stockage
        if client.storage_used_gb > plan.max_storage_gb:
            existing_alert = self.search([
                ('client_id', '=', client.id),
                ('alert_type', '=', 'quota_storage_exceeded'),
                ('resolved', '=', False),
            ], limit=1)

            if not existing_alert:
                self.create({
                    'client_id': client.id,
                    'alert_type': 'quota_storage_exceeded',
                    'severity': 'critical',
                    'message': f'Quota stockage dépassé: {client.storage_used_gb:.2f}GB/{plan.max_storage_gb}GB',
                    'details': f'<p>Le client utilise {client.storage_used_gb:.2f}GB de stockage, '
                               f'mais son plan "{plan.name}" autorise seulement {plan.max_storage_gb}GB.</p>'
                               f'<p>Action recommandée: Proposer un upgrade de plan immédiatement.</p>',
                })

        # Vérifier quota API
        if client.api_calls_today > plan.max_api_calls_per_day:
            existing_alert = self.search([
                ('client_id', '=', client.id),
                ('alert_type', '=', 'quota_api_exceeded'),
                ('resolved', '=', False),
            ], limit=1)

            if not existing_alert:
                self.create({
                    'client_id': client.id,
                    'alert_type': 'quota_api_exceeded',
                    'severity': 'error',
                    'message': f'Quota API dépassé: {client.api_calls_today}/{plan.max_api_calls_per_day}',
                })

    @api.model
    def cron_check_trial_expiration(self):
        """Cron: Vérifier les essais qui arrivent à expiration"""
        from datetime import timedelta

        # Essais qui se terminent dans 3 jours
        three_days = fields.Date.today() + timedelta(days=3)
        clients_ending_soon = self.env['saas.client'].search([
            ('subscription_state', '=', 'trial'),
            ('trial_end_date', '=', three_days),
        ])

        for client in clients_ending_soon:
            existing_alert = self.search([
                ('client_id', '=', client.id),
                ('alert_type', '=', 'trial_ending_soon'),
                ('resolved', '=', False),
            ], limit=1)

            if not existing_alert:
                self.create({
                    'client_id': client.id,
                    'alert_type': 'trial_ending_soon',
                    'severity': 'warning',
                    'message': f'Essai se termine dans 3 jours',
                    'details': f'<p>L\'essai gratuit du client se termine le {client.trial_end_date}.</p>'
                               f'<p>Action: Contacter le client pour conversion en abonnement payant.</p>',
                })

        # Essais expirés
        clients_expired = self.env['saas.client'].search([
            ('subscription_state', '=', 'trial'),
            ('trial_end_date', '<', fields.Date.today()),
        ])

        for client in clients_expired:
            existing_alert = self.search([
                ('client_id', '=', client.id),
                ('alert_type', '=', 'trial_expired'),
                ('resolved', '=', False),
            ], limit=1)

            if not existing_alert:
                self.create({
                    'client_id': client.id,
                    'alert_type': 'trial_expired',
                    'severity': 'critical',
                    'message': 'Essai expiré',
                    'details': f'<p>L\'essai gratuit du client a expiré le {client.trial_end_date}.</p>'
                               f'<p>Action: Suspendre l\'accès ou convertir en abonnement payant.</p>',
                })
