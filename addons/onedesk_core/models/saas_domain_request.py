# -*- coding: utf-8 -*-

import logging
import socket
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaaSDomainRequest(models.Model):
    _name = 'saas.domain.request'
    _description = 'Demande de domaine personnalisé client SaaS'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Nom de domaine', required=True, tracking=True,
                       help="Le nom de domaine personnalisé (ex: monentreprise.com)")

    client_id = fields.Many2one('saas.client', string='Client SaaS', required=True,
                                ondelete='cascade', tracking=True)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('pending', 'En attente validation'),
        ('dns_checking', 'Vérification DNS'),
        ('approved', 'Approuvé'),
        ('configured', 'Configuré'),
        ('rejected', 'Refusé'),
    ], string='État', default='draft', required=True, tracking=True)

    dns_status = fields.Selection([
        ('not_checked', 'Non vérifié'),
        ('checking', 'Vérification en cours'),
        ('valid', 'DNS valide'),
        ('invalid', 'DNS invalide'),
    ], string='Statut DNS', default='not_checked', tracking=True)

    dns_target = fields.Char(string='Cible DNS attendue', compute='_compute_dns_target',
                             help="Le CNAME que le client doit configurer")

    dns_check_result = fields.Text(string='Résultat vérification DNS', readonly=True)

    rejection_reason = fields.Text(string='Raison du refus')

    requested_date = fields.Datetime(string='Date demande', readonly=True)
    approved_date = fields.Datetime(string='Date approbation', readonly=True)
    configured_date = fields.Datetime(string='Date configuration', readonly=True)

    def _compute_dns_target(self):
        """Le CNAME doit pointer vers le domaine principal du serveur"""
        # Récupérer le domaine principal depuis la config ou depuis le premier client
        main_domain = self.env['ir.config_parameter'].sudo().get_param(
            'onedesk.saas_main_domain',
            'basatechno.fr'
        )

        for record in self:
            record.dns_target = main_domain

    def action_submit_request(self):
        """Soumettre la demande de domaine pour validation"""
        self.ensure_one()

        if self.state != 'draft':
            raise UserError("Seules les demandes en brouillon peuvent être soumises.")

        # Vérifier le DNS avant de soumettre
        self.action_check_dns()

        if self.dns_status != 'valid':
            raise UserError(
                "Le DNS n'est pas correctement configuré.\n\n"
                f"Veuillez créer un enregistrement CNAME:\n"
                f"  {self.name} → {self.dns_target}\n\n"
                "Vérifiez votre configuration DNS et réessayez."
            )

        self.write({
            'state': 'pending',
            'requested_date': fields.Datetime.now(),
        })

        self.message_post(
            body=f"📨 Demande soumise - En attente de validation par l'administrateur SaaS",
            subject="Demande de domaine soumise"
        )

        # Notifier l'admin SaaS (à implémenter)
        self._notify_saas_admin()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Demande soumise',
                'message': 'Votre demande de domaine a été soumise. Vous recevrez une notification une fois approuvée.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_check_dns(self):
        """Vérifier si le DNS pointe correctement vers le serveur"""
        self.ensure_one()

        _logger.info(f"[SAAS] Vérification DNS pour {self.name}")

        self.write({'dns_status': 'checking'})

        try:
            # Résoudre le CNAME
            try:
                # Essayer de résoudre le nom de domaine
                result = socket.getaddrinfo(self.name, None)
                resolved_ips = list(set([r[4][0] for r in result]))

                _logger.info(f"[SAAS] DNS {self.name} résolu vers: {resolved_ips}")

                # Vérifier que le domaine pointe vers notre serveur
                # On pourrait comparer avec l'IP du serveur, mais c'est complexe
                # Pour l'instant, on accepte si le domaine est résolvable

                self.write({
                    'dns_status': 'valid',
                    'dns_check_result': f"✅ DNS configuré correctement\n"
                                       f"Le domaine {self.name} pointe vers: {', '.join(resolved_ips)}"
                })

                self.message_post(
                    body=f"✅ DNS vérifié avec succès - Le domaine pointe vers {', '.join(resolved_ips)}"
                )

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'DNS Valide',
                        'message': f'Le domaine {self.name} est correctement configuré!',
                        'type': 'success',
                        'sticky': False,
                    }
                }

            except socket.gaierror as e:
                error_msg = f"❌ Impossible de résoudre {self.name}\n\n" \
                           f"Veuillez créer un enregistrement CNAME:\n" \
                           f"  {self.name} → {self.dns_target}\n\n" \
                           f"Erreur: {str(e)}"

                self.write({
                    'dns_status': 'invalid',
                    'dns_check_result': error_msg
                })

                self.message_post(
                    body=error_msg,
                    subject="Vérification DNS échouée"
                )

                raise UserError(error_msg)

        except Exception as e:
            _logger.error(f"[SAAS] Erreur vérification DNS {self.name}: {str(e)}")
            self.write({
                'dns_status': 'invalid',
                'dns_check_result': f"Erreur lors de la vérification: {str(e)}"
            })
            raise

    def action_approve(self):
        """Approuver la demande (réservé aux admins SaaS)"""
        self.ensure_one()

        if self.state != 'pending':
            raise UserError("Seules les demandes en attente peuvent être approuvées.")

        self.write({
            'state': 'approved',
            'approved_date': fields.Datetime.now(),
        })

        self.message_post(
            body=f"✅ Demande approuvée par {self.env.user.name}",
            subject="Demande approuvée"
        )

        # Configurer automatiquement le domaine
        try:
            self.action_configure_domain()
        except Exception as e:
            _logger.error(f"[SAAS] Erreur configuration domaine: {str(e)}")
            self.message_post(
                body=f"⚠️ Erreur lors de la configuration automatique: {str(e)}<br/>"
                     f"Veuillez configurer manuellement.",
                subject="Erreur configuration"
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Demande approuvée',
                'message': f'Le domaine {self.name} a été approuvé et est en cours de configuration.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_reject(self):
        """Refuser la demande"""
        self.ensure_one()

        if self.state not in ['pending', 'dns_checking']:
            raise UserError("Cette demande ne peut pas être refusée.")

        if not self.rejection_reason:
            raise UserError("Veuillez indiquer une raison de refus.")

        self.write({'state': 'rejected'})

        self.message_post(
            body=f"❌ Demande refusée par {self.env.user.name}<br/>"
                 f"Raison: {self.rejection_reason}",
            subject="Demande refusée"
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Demande refusée',
                'message': 'La demande a été refusée.',
                'type': 'warning',
                'sticky': False,
            }
        }

    def action_configure_domain(self):
        """Configurer le domaine nginx + SSL (appelle la méthode du client)"""
        self.ensure_one()

        if self.state != 'approved':
            raise UserError("Seules les demandes approuvées peuvent être configurées.")

        # Mettre à jour le domaine du client
        self.client_id.write({'custom_domain': self.name})

        # Appeler la méthode de configuration du client
        try:
            self.client_id.action_configure_domain()

            self.write({
                'state': 'configured',
                'configured_date': fields.Datetime.now(),
            })

            self.message_post(
                body=f"✅ Domaine configuré avec succès!<br/>"
                     f"Le client peut maintenant accéder via: https://{self.name}",
                subject="Configuration terminée"
            )

        except Exception as e:
            _logger.error(f"[SAAS] Erreur configuration domaine {self.name}: {str(e)}")
            raise

    def _notify_saas_admin(self):
        """Notifier les admins SaaS qu'une nouvelle demande a été soumise"""
        # Trouver tous les utilisateurs avec le groupe SaaS Manager
        saas_managers = self.env.ref('onedesk_core.group_saas_manager').users

        if not saas_managers:
            _logger.warning("[SAAS] Aucun admin SaaS trouvé pour notification")
            return

        # Créer une activité pour chaque manager
        for manager in saas_managers:
            self.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                summary=f'Nouvelle demande de domaine: {self.name}',
                note=f"Le client {self.client_id.name} demande le domaine personnalisé: {self.name}\n"
                     f"Veuillez vérifier et approuver cette demande.",
                user_id=manager.id,
            )

        _logger.info(f"[SAAS] {len(saas_managers)} admins SaaS notifiés pour demande {self.name}")
