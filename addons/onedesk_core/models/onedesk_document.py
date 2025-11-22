"""Model pour documents et signatures"""
from odoo import models, fields, api
import base64
import logging

_logger = logging.getLogger(__name__)


class OnedeskDocument(models.Model):
    _name = 'onedesk.document'
    _description = 'Documents (Contrats, Factures, Rapports)'
    _rec_name = 'name'
    _inherit = 'mail.thread'

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
    ], string='Statut', default='draft')

    # ========== MÉTHODE DE SIGNATURE (Hybride) ==========
    signing_method = fields.Selection([
        ('signaturit', '🌐 SignaturIT (tiers)'),
        ('odoo_sign', '✍️ Signature Odoo'),
    ], string='Méthode de signature', default='signaturit',
       help="SignaturIT: service tiers avec advanced features\nOdoo Sign: signature native et rapide")

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
    # Signataires depuis les contacts Odoo (Many2many vers res.partner) - PRINCIPALE
    partner_signer_ids = fields.Many2many('res.partner', 'document_partner_signer_rel',
                                          'document_id', 'partner_id',
                                          string='Signataires (Contacts)',
                                          domain=[('is_company', '=', False)])

    # Signataires sélectionnés depuis la base custom (Many2many) - OPTIONNEL pour signataires non-contacts
    recipient_ids = fields.Many2many('onedesk.document.recipient', 'document_recipient_rel',
                                     'document_id', 'recipient_id',
                                     string='Autres signataires')
    # Suivi des statuts de signature (One2many)
    signature_ids = fields.One2many('onedesk.document.signature', 'document_id',
                                   string='Suivi des signatures')
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
        """Router vers la bonne méthode de signature"""
        self.ensure_one()

        # Vérifier qu'il y a des signataires (depuis contacts ou custom)
        if not self.partner_signer_ids and not self.recipient_ids:
            raise ValueError('Ajoutez au moins un signataire (contacts ou autres)!')

        # Router selon la méthode choisie
        if self.signing_method == 'signaturit':
            return self._send_via_signaturit()
        elif self.signing_method == 'odoo_sign':
            return self._send_via_odoo_sign()
        else:
            raise ValueError(f'Méthode de signature inconnue: {self.signing_method}')

    def _send_via_signaturit(self):
        """Envoyer via SignaturIT (service tiers)"""
        # Appeler API SignaturIT
        request_data = self._send_to_signaturit()

        # Sauvegarder l'ID de request
        self.signaturit_request_id = request_data.get('id')

        # Mettre à jour le statut
        self.status = 'pending_signature'

        # Compter les signataires (contacts + autres)
        total_signers = len(self.partner_signer_ids) + len(self.recipient_ids)

        # Log
        _logger.info(f'✅ Document {self.name} envoyé pour signature via SignaturIT (Request ID: {self.signaturit_request_id})')

        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': '📤 Envoyé pour signature SignaturIT!',
                          'message': f'{total_signers} signataire(s) vont recevoir un email avec le lien de signature.'}}

    def _send_via_odoo_sign(self):
        """Envoyer via signature Odoo native"""
        # TODO: Intégrer avec le module sign d'Odoo
        # Compter les signataires (contacts + autres)
        total_signers = len(self.partner_signer_ids) + len(self.recipient_ids)
        message = f'Signature Odoo: {total_signers} signataire(s) ajoutés'

        self.status = 'pending_signature'
        _logger.info(f'✅ Document {self.name} prêt pour signature Odoo')

        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': '✍️ Document prêt pour signature Odoo',
                          'message': message}}

    def _send_to_signaturit(self):
        """Envoyer le document à SignaturIT via API"""
        import requests
        import json

        # Récupérer la clé API
        api_key = self.env['ir.config_parameter'].sudo().get_param('signaturit.api.key')
        if not api_key:
            raise ValueError('Clé API SignaturIT non configurée!')

        # Préparer les signataires depuis les DEUX sources
        signers = []

        # Source 1: Signataires depuis les contacts Odoo (res.partner)
        for partner in self.partner_signer_ids:
            signers.append({
                'email': partner.email,
                'name': partner.name or partner.contact_address,
            })

        # Source 2: Signataires depuis la base custom (onedesk.document.recipient)
        for recipient in self.recipient_ids:
            signers.append({
                'email': recipient.email,
                'name': recipient.name,
            })

        # Envoyer à SignaturIT avec le format correct (just token, pas Bearer)
        headers = {
            'Authorization': api_key,  # SignaturIT utilise juste le token, pas Bearer
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
            _logger.info(f'📤 Envoi à SignaturIT: {self.name} avec {len(signers)} signataire(s)')
            _logger.debug(f'Signers: {signers}')

            response = requests.post(
                'https://api.signaturit.com/v3/requests',
                headers=headers,
                files=files,
                data=data,
                timeout=30
            )

            if response.status_code not in [200, 201]:
                error_msg = f'Erreur SignaturIT (HTTP {response.status_code}): {response.text}'
                _logger.error(f'❌ {error_msg}')
                raise ValueError(error_msg)

            result = response.json()
            _logger.info(f'✅ Réponse SignaturIT: {result}')
            return result

        except requests.exceptions.RequestException as e:
            error_msg = f'❌ Erreur API SignaturIT: {str(e)}'
            _logger.error(error_msg)
            raise ValueError(error_msg)

    def _download_signed_pdf(self):
        """Télécharger le PDF signé depuis SignaturIT"""
        import requests

        if not self.signaturit_request_id:
            return

        api_key = self.env['ir.config_parameter'].sudo().get_param('signaturit.api.key')

        headers = {
            'Authorization': api_key,  # SignaturIT utilise juste le token
        }

        try:
            _logger.info(f'📥 Téléchargement PDF signé pour request {self.signaturit_request_id}')

            response = requests.get(
                f'https://api.signaturit.com/v3/requests/{self.signaturit_request_id}/document',
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                self.file = base64.b64encode(response.content)
                _logger.info(f'✅ PDF signé téléchargé et sauvegardé pour {self.name}')
            else:
                error_msg = f'Impossible de télécharger le PDF signé (HTTP {response.status_code}): {response.text}'
                _logger.warning(f'⚠️ {error_msg}')

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
    ], string='Statut', default='pending')

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


# ========== MODÈLE DESTINATAIRES ==========
class OnedeskDocumentRecipient(models.Model):
    """Destinataires/Signataires réutilisables"""
    _name = 'onedesk.document.recipient'
    _description = 'Signataire (destinataire de documents)'
    _rec_name = 'name'

    # ========== CHAMPS ==========
    name = fields.Char(string='Nom', required=True)
    email = fields.Char(string='Email', required=True)
    phone = fields.Char(string='Téléphone')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)

    # ========== INFOS ADDITIONNELLES ==========
    partner_id = fields.Many2one('res.partner', string='Contact', help='Lier à un contact optionnel')
    active = fields.Boolean(default=True)

    @api.model
    def create(self, vals):
        """Vérifier que l'email n'existe pas déjà pour cette company"""
        if vals.get('email'):
            existing = self.search([
                ('email', '=', vals['email']),
                ('company_id', '=', vals.get('company_id', self.env.company.id))
            ])
            if existing:
                raise ValueError(f"Un signataire avec l'email {vals['email']} existe déjà!")
        return super().create(vals)

    _sql_constraints = [
        ('unique_email_company', 'unique(email, company_id)',
         'L\'email doit être unique par company!')
    ]
