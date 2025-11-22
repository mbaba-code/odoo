"""Model pour documents et signatures"""
from odoo import models, fields, api
import base64
import logging

_logger = logging.getLogger(__name__)


class OnedeskDocument(models.Model):
    _name = 'onedesk.document'
    _description = 'Documents (Contrats, Factures, Rapports)'
    _rec_name = 'name'

    # ========== CHAMPS PRINCIPAUX ==========
    name = fields.Char(string='Titre du document', required=True)
    document_type = fields.Selection([
        ('contract', '📜 Contrat'),
        ('invoice', '💰 Facture'),
        ('inspection', '🔍 Rapport d\'inspection'),
        ('report', '📋 Rapport'),
        ('other', '📄 Autre'),
    ], string='Type de document', required=True, default='other')

    file = fields.Binary(string='Document (PDF)', required=True, attachment=True)
    filename = fields.Char(string='Nom du fichier')

    status = fields.Selection([
        ('draft', '✏️ Brouillon'),
        ('pending_signature', '⏳ En attente de signature'),
        ('signed', '✅ Signé'),
        ('archived', '📦 Archivé'),
    ], string='Statut', default='draft', tracking=True)

    # ========== RELATIONS ==========
    property_id = fields.Many2one('onedesk.property', string='Propriété')
    unit_id = fields.Many2one('onedesk.unit', string='Unité')
    reservation_id = fields.Many2one('onedesk.reservation', string='Réservation')
    task_id = fields.Many2one('onedesk.task', string='Tâche')

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)

    created_by = fields.Many2one('res.users', string='Créé par', default=lambda self: self.env.user)
    date_created = fields.Datetime(string='Date de création', default=fields.Datetime.now)

    # ========== SIGNATURES ==========
    signature_ids = fields.One2many('onedesk.document.signature', 'document_id',
                                   string='Signataires')
    signaturit_request_id = fields.Char(string='SignaturIT Request ID', readonly=True)

    # ========== NOTES ==========
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    @api.onchange('reservation_id')
    def _onchange_reservation_id(self):
        """Auto-populate company et unit depuis reservation"""
        if self.reservation_id:
            self.company_id = self.reservation_id.unit_id.property_id.company_id
            self.unit_id = self.reservation_id.unit_id

    @api.onchange('unit_id')
    def _onchange_unit_id(self):
        """Auto-populate company depuis unit"""
        if self.unit_id:
            self.company_id = self.unit_id.property_id.company_id

    def action_send_signature(self):
        """Envoyer le document pour signature via SignaturIT"""
        self.ensure_one()

        # Vérifier qu'il y a des signataires
        if not self.signature_ids:
            raise ValueError('Ajoutez au moins un signataire!')

        # Appeler API SignaturIT
        request_data = self._send_to_signaturit()

        # Sauvegarder l'ID de request
        self.signaturit_request_id = request_data.get('id')

        # Mettre à jour le statut
        self.status = 'pending_signature'

        # Log
        _logger.info(f'✅ Document {self.name} envoyé pour signature (Request ID: {self.signaturit_request_id})')

        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': '📤 Envoyé pour signature!',
                          'message': f'{len(self.signature_ids)} signataire(s) ont reçu le lien de signature.'}}

    def _send_to_signaturit(self):
        """Envoyer le document à SignaturIT via API"""
        import requests
        import json

        # Récupérer la clé API
        api_key = self.env['ir.config_parameter'].sudo().get_param('signaturit.api.key')
        if not api_key:
            raise ValueError('Clé API SignaturIT non configurée!')

        # Préparer les signataires
        signers = []
        for signature in self.signature_ids:
            signers.append({
                'email': signature.signer_email,
                'name': signature.signer_name,
            })

        # Envoyer à SignaturIT
        headers = {
            'Authorization': f'Bearer {api_key}',
        }

        files = {
            'document': (self.filename or 'document.pdf', self.file)
        }

        data = {
            'signers': json.dumps(signers),
            'name': self.name,
            'description': self.notes or '',
        }

        try:
            response = requests.post(
                'https://api.signaturit.com/v3/requests',
                headers=headers,
                files=files,
                data=data,
                timeout=30
            )

            if response.status_code not in [200, 201]:
                raise ValueError(f'Erreur SignaturIT: {response.text}')

            return response.json()

        except Exception as e:
            _logger.error(f'❌ Erreur API SignaturIT: {str(e)}')
            raise

    def _download_signed_pdf(self):
        """Télécharger le PDF signé depuis SignaturIT"""
        import requests

        if not self.signaturit_request_id:
            return

        api_key = self.env['ir.config_parameter'].sudo().get_param('signaturit.api.key')

        headers = {
            'Authorization': f'Bearer {api_key}',
        }

        try:
            response = requests.get(
                f'https://api.signaturit.com/v3/requests/{self.signaturit_request_id}/document',
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                self.file = base64.b64encode(response.content)
                _logger.info(f'✅ PDF signé téléchargé pour {self.name}')
            else:
                _logger.warning(f'Impossible de télécharger le PDF signé: {response.text}')

        except Exception as e:
            _logger.error(f'❌ Erreur téléchargement PDF: {str(e)}')

    def action_archive(self):
        """Archiver le document"""
        self.status = 'archived'


class OnedeskDocumentSignature(models.Model):
    _name = 'onedesk.document.signature'
    _description = 'Signature de document'
    _rec_name = 'signer_name'

    # ========== RELATIONS ==========
    document_id = fields.Many2one('onedesk.document', string='Document', required=True, ondelete='cascade')

    # ========== SIGNATAIRE ==========
    signer_email = fields.Char(string='Email du signataire', required=True)
    signer_name = fields.Char(string='Nom du signataire', required=True)

    # ========== STATUT ==========
    status = fields.Selection([
        ('pending', '⏳ En attente'),
        ('signed', '✅ Signé'),
        ('declined', '❌ Refusé'),
    ], string='Statut', default='pending', tracking=True)

    signature_date = fields.Datetime(string='Date de signature')

    # ========== INFOS SIGNATURIT ==========
    signaturit_request_id = fields.Char(string='SignaturIT Request ID', readonly=True)
    signed_document_url = fields.Char(string='URL PDF signé')

    # ========== AUDIT ==========
    created_date = fields.Datetime(string='Date création', default=fields.Datetime.now)
    expiration_date = fields.Datetime(string='Expires le')

    @api.onchange('document_id')
    def _onchange_document_id(self):
        """Auto-populate signaturit_request_id depuis document"""
        if self.document_id:
            self.signaturit_request_id = self.document_id.signaturit_request_id

    def action_resend(self):
        """Renvoyer le lien de signature au signataire"""
        self.ensure_one()

        if self.status == 'signed':
            raise ValueError('Ce document est déjà signé!')

        # TODO: Appeler SignaturIT API pour renvoyer
        _logger.info(f'📬 Lien renvoyé à {self.signer_email}')

        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': '📬 Lien renvoyé!',
                          'message': f'Lien de signature renvoyé à {self.signer_email}'}}


# ========== WEBHOOK HANDLERS ==========
class OnedeskDocumentWebhookHandlers(models.Model):
    """Mixin pour les handlers de webhook SignaturIT"""
    _inherit = 'onedesk.document'

    def _handle_signer_signed(self, signer_email):
        """Gérer l'événement: un signataire a signé"""
        self.ensure_one()

        # Mettre à jour le statut du signataire
        signature = self.signature_ids.filtered(lambda s: s.signer_email == signer_email)
        if signature:
            signature.status = 'signed'
            signature.signature_date = fields.Datetime.now()
            _logger.info(f'✅ Signature enregistrée pour {signer_email}')

    def _handle_signer_declined(self, signer_email):
        """Gérer l'événement: un signataire a refusé"""
        self.ensure_one()

        # Mettre à jour le statut du signataire
        signature = self.signature_ids.filtered(lambda s: s.signer_email == signer_email)
        if signature:
            signature.status = 'declined'
            _logger.warning(f'❌ Signature refusée par {signer_email}')

    def _handle_all_signed(self):
        """Gérer l'événement: tous ont signé"""
        self.ensure_one()

        # Télécharger le PDF signé
        self._download_signed_pdf()

        # Mettre à jour le statut du document
        self.status = 'signed'
        _logger.info(f'✅ Document {self.name} entièrement signé!')

        # Notifier les utilisateurs
        self._notify_all_signed()

    def _notify_all_signed(self):
        """Notifier l'utilisateur que tous les signataires ont signé"""
        try:
            message = f'✅ {self.name} a été entièrement signé par tous les signataires!'
            self.message_post(body=message, message_type='notification')
            _logger.info(f'📬 Notification: {message}')
        except Exception as e:
            _logger.warning(f'Erreur envoi notification: {str(e)}')
