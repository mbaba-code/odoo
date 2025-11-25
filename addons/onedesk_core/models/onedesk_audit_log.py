from odoo import models, fields, api
from odoo.tools import safe_eval
import json


class OnedeskoAuditLog(models.Model):
    """
    Modèle de journal d'audit pour OneDesk
    Trace toutes les actions importantes du système pour le master admin
    """
    _name = 'onedesk.audit.log'
    _description = 'OneDesk Audit Log'
    _order = 'create_date desc'

    # Subject
    log_type = fields.Selection([
        ('client_created', 'Client créé'),
        ('client_modified', 'Client modifié'),
        ('client_activated', 'Client activé'),
        ('client_suspended', 'Client suspendu'),
        ('client_cancelled', 'Client annulé'),
        ('subscription_created', 'Abonnement créé'),
        ('subscription_modified', 'Abonnement modifié'),
        ('subscription_activated', 'Abonnement activé'),
        ('subscription_suspended', 'Abonnement suspendu'),
        ('subscription_cancelled', 'Abonnement annulé'),
        ('user_created', 'Utilisateur créé'),
        ('user_deleted', 'Utilisateur supprimé'),
        ('login', 'Connexion'),
        ('data_export', 'Exportation de données'),
        ('data_import', 'Importation de données'),
        ('system_config', 'Configuration système'),
        ('security_event', 'Événement de sécurité'),
        ('payment_processed', 'Paiement traité'),
        ('payment_validated', 'Paiement validé'),
        ('payment_failed', 'Paiement échoué'),
        ('invoice_generated', 'Facture générée'),
        ('backup_completed', 'Sauvegarde complétée'),
        ('backup_restored', 'Sauvegarde restaurée'),
        ('other', 'Autre'),
    ], string="Type d'événement", required=True)

    severity = fields.Selection([
        ('info', 'Info'),
        ('warning', 'Attention'),
        ('error', 'Erreur'),
        ('critical', 'Critique'),
    ], string="Sévérité", default='info', required=True)

    # Actor
    user_id = fields.Many2one(
        'res.users',
        string="Utilisateur",
        help="Utilisateur qui a effectué l'action"
    )
    actor_name = fields.Char(
        string="Nom de l'acteur",
        help="Nom sauvegardé de l'utilisateur (en cas de suppression)"
    )
    actor_email = fields.Char(
        string="Email de l'acteur"
    )

    # Subject
    client_id = fields.Many2one(
        'onedesk.client',
        string="Client concerné"
    )
    company_id = fields.Many2one(
        'res.company',
        string="Société concernée"
    )
    subscription_id = fields.Many2one(
        'onedesk.subscription',
        string="Abonnement concerné"
    )

    # Details
    description = fields.Text(string="Description")
    action_url = fields.Char(
        string="URL de l'action",
        help="Lien vers le record affecté"
    )

    # Changes
    changed_fields = fields.Char(
        string="Champs modifiés",
        help="Liste des champs modifiés (JSON)"
    )
    old_values = fields.Text(
        string="Anciennes valeurs",
        help="Valeurs anciennes (JSON)"
    )
    new_values = fields.Text(
        string="Nouvelles valeurs",
        help="Nouvelles valeurs (JSON)"
    )

    # Context
    ip_address = fields.Char(string="Adresse IP")
    user_agent = fields.Char(string="User-Agent", help="Navigateur/client utilisé")
    session_id = fields.Char(string="ID de session")

    # Response
    result = fields.Selection([
        ('success', 'Succès'),
        ('failed', 'Échouée'),
        ('unauthorized', 'Non autorisé'),
    ], string="Résultat", default='success')

    error_message = fields.Text(string="Message d'erreur")

    @api.model
    def create(self, vals_list):
        """Créer une entrée de log d'audit"""
        logs = super().create(vals_list)
        return logs

    @staticmethod
    def log_action(log_type, severity='info', **kwargs):
        """
        Enregistrer une action pour l'audit
        Exemple:
            OnedeskoAuditLog.log_action(
                'client_created',
                severity='info',
                client_id=client.id,
                user_id=request.env.user.id,
                description="Nouveau client créé via signup"
            )
        """
        return {
            'log_type': log_type,
            'severity': severity,
            **kwargs
        }

    def format_changed_fields(self, old_dict, new_dict):
        """Formatter les champs modifiés"""
        changed = {}
        for key, new_val in new_dict.items():
            old_val = old_dict.get(key)
            if old_val != new_val:
                changed[key] = {
                    'old': str(old_val),
                    'new': str(new_val),
                }
        return changed

    @api.model
    def archive_old_logs(self, days=365):
        """Archiver les logs anciens (pour maintenance)"""
        import datetime
        cutoff_date = fields.Datetime.now() - datetime.timedelta(days=days)
        old_logs = self.search([('create_date', '<', cutoff_date)])
        # Les logs pourraient être exportés vers archive avant suppression
        # old_logs.unlink()

    def get_client_timeline(self, client_id, limit=50):
        """Récupérer la chronologie des événements pour un client"""
        return self.search([
            ('client_id', '=', client_id)
        ], limit=limit)

    def get_user_activity(self, user_id, limit=50):
        """Récupérer l'activité d'un utilisateur"""
        return self.search([
            ('user_id', '=', user_id)
        ], limit=limit)

    def get_subscription_history(self, subscription_id):
        """Récupérer l'historique d'un abonnement"""
        return self.search([
            ('subscription_id', '=', subscription_id),
            ('log_type', 'ilike', 'subscription_%'),
        ])


class OnedeskoSystemLog(models.Model):
    """
    Logs système pour le monitoring et le debugging
    """
    _name = 'onedesk.system.log'
    _description = 'OneDesk System Log'
    _order = 'create_date desc'

    level = fields.Selection([
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ], string="Niveau", default='info')

    module = fields.Char(string="Module", help="Module/fonction d'origine")
    message = fields.Text(string="Message", required=True)
    stack_trace = fields.Text(string="Stack trace")

    @api.model
    def create(self, vals_list):
        """Créer un log système"""
        return super().create(vals_list)

    @staticmethod
    def log_error(message, module='onedesk', stack_trace=None):
        """Enregistrer une erreur"""
        return {
            'level': 'error',
            'module': module,
            'message': message,
            'stack_trace': stack_trace,
        }

    @staticmethod
    def log_info(message, module='onedesk'):
        """Enregistrer une info"""
        return {
            'level': 'info',
            'module': module,
            'message': message,
        }
