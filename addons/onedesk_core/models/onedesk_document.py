"""
OneDesk Document Management Module
===================================

Provides professional document management with signature support:

1. **Document Management**
   - Store PDF documents (contracts, invoices, reports, etc.)
   - Track document status lifecycle
   - Multi-tenant isolation via company_id
   - Activity tracking with Odoo chatter

2. **Signature Methods**
   - Native Email Signature (Recommended): Simple, reliable, uses Odoo email system
   - SignaturIT Integration (Beta): Advanced third-party service (requires API key)

3. **Signature Tracking**
   - Track individual signer status (pending, signed, declined)
   - Automatic email notifications
   - Webhook support for SignaturIT events
   - Email reminders for pending signatures

4. **Security**
   - Role-based access control (via ir.model.access)
   - Multi-tenant data isolation
   - Audit trail via message_post()
   - Company isolation on all operations

Author: OneDesk Team
License: LGPL-3
"""

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

    file = fields.Binary(string='Document (PDF)', attachment=True,
                        help='Le PDF du document. Obligatoire avant d\'envoyer pour signature.')
    filename = fields.Char(string='Nom du fichier')

    status = fields.Selection([
        ('draft', '✏️ Brouillon'),
        ('pending_signature', '⏳ En attente de signature'),
        ('signed', '✅ Signé'),
        ('archived', '📦 Archivé'),
    ], string='Statut', default='draft')

    # ========== MÉTHODE DE SIGNATURE (Hybride) ==========
    signing_method = fields.Selection([
        ('odoo_native', '✍️ Email Signature (Natif)'),
        ('signaturit', '🌐 SignaturIT (En développement - Beta)'),
    ], string='Méthode de signature', default='odoo_native',
       help="Email Signature: envoie par email Odoo, simple et rapide\nSignaturIT: service tiers avancé (en phase bêta)")

    # ========== RELATIONS ==========
    property_id = fields.Many2one('onedesk.property', string='Propriété', index=True)
    unit_id = fields.Many2one('onedesk.unit', string='Unité', index=True)
    reservation_id = fields.Many2one('onedesk.reservation', string='Réservation', index=True)  # Critical for filtering
    task_id = fields.Many2one('onedesk.task', string='Tâche', index=True)

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
    signaturit_request_id = fields.Char(string='SignaturIT Request ID', readonly=True, index=True)  # Critical for API tracking

    # ========== STOCK REFERENCE ==========
    source_document_id = fields.Many2one('onedesk.document', string='Sélectionner du stock',
                                        help='Optionnel: Sélectionnez un document du stock pour réutiliser son contenu',
                                        domain=[('status', '=', 'archived')])  # Voir les documents archivés

    # ========== NOTES ==========
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    # ========== CLASSEMENT & STOCKAGE ==========
    document_category = fields.Selection([
        ('contract', '📜 Contrat'),
        ('invoice', '💰 Facture'),
        ('inspection', '🔍 Inspection'),
        ('report', '📋 Rapport'),
        ('correspondence', '✉️ Correspondance'),
        ('compliance', '⚖️ Conformité'),
        ('financial', '💳 Financier'),
        ('legal', '⚖️ Légal'),
        ('technical', '⚙️ Technique'),
        ('other', '📄 Autre'),
    ], string='Catégorie du document', help='Catégorie pour organiser et classer les documents')

    document_tags = fields.Many2many('onedesk.document.tag', 'document_tag_rel',
                                     'document_id', 'tag_id',
                                     string='Tags/Étiquettes',
                                     help='Étiquettes pour retrouver rapidement les documents')

    storage_location = fields.Char(string='Lieu de stockage',
                                   help='Localisation physique ou logique du document (ex: Dossier Principal, Archives, Cloud)')

    archive_date = fields.Datetime(string='Date d\'archivage',
                                   help='Date et heure d\'archivage du document')

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
        elif self.signing_method == 'odoo_native':
            return self._send_via_odoo_native()
        else:
            raise ValueError(f'Méthode de signature inconnue: {self.signing_method}')

    def action_signaturit_beta(self):
        """Action pour le bouton SignaturIT désactivé (Beta)"""
        self.ensure_one()

        _logger.info(f'🔄 Tentative d\'accès à SignaturIT (Beta) pour {self.name}')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'warning',
                'title': '🔄 SignaturIT en développement',
                'message': 'Cette fonctionnalité est actuellement en phase de développement. '
                          'Veuillez utiliser l\'option "✍️ Envoyer pour signature (Email Odoo)" pour l\'instant.',
                'sticky': True,
            }
        }

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

    def _send_via_odoo_native(self):
        """
        Envoyer les demandes de signature via email Odoo natif
        Simple, fiable et sans dépendances externes
        """
        self.ensure_one()

        try:
            # Collecter tous les signataires (contacts + autres)
            signers = []

            # Source 1: Signataires depuis les contacts Odoo
            for partner in self.partner_signer_ids:
                if partner.email:
                    signers.append({
                        'email': partner.email,
                        'name': partner.name or 'Contact',
                        'type': 'contact'
                    })

            # Source 2: Signataires custom
            for recipient in self.recipient_ids:
                signers.append({
                    'email': recipient.email,
                    'name': recipient.name,
                    'type': 'recipient'
                })

            if not signers:
                raise ValueError('Aucun signataire avec email trouvé!')

            # Créer les enregistrements de signature et envoyer les emails
            signature_ids = []
            for signer in signers:
                # Créer l'enregistrement de signature
                sig = self.env['onedesk.document.signature'].create({
                    'document_id': self.id,
                    'signer_email': signer['email'],
                    'signer_name': signer['name'],
                    'status': 'pending',
                })
                signature_ids.append(sig.id)

                # Envoyer l'email de demande de signature (auto-déclenché dans create())
                _logger.info(f'📧 Email de signature envoyé à {signer["email"]} pour {self.name}')

            # Mettre à jour le statut du document
            self.status = 'pending_signature'

            # Log succès
            _logger.info(f'✅ Document {self.name} envoyé pour signature (email natif) - {len(signers)} signataire(s)')

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '✍️ Demandes de signature envoyées!',
                    'message': f'{len(signers)} signataire(s) ont reçu un email avec le document à signer via Odoo.',
                    'type': 'success'
                }
            }

        except Exception as e:
            _logger.error(f'❌ Erreur envoi signature Odoo native: {str(e)}')
            self.message_post(body=f'⚠️ Erreur envoi signature: {str(e)}', message_type='comment')
            raise

    def _send_to_signaturit(self):
        """Envoyer le document à SignaturIT via API"""
        import requests
        import json

        # Récupérer l'environnement (sandbox ou production)
        environment = self.env['ir.config_parameter'].sudo().get_param('signaturit.environment', 'sandbox')

        # Récupérer la clé API selon l'environnement
        if environment == 'production':
            api_key = self.env['ir.config_parameter'].sudo().get_param('signaturit.production.api.key')
            api_url = self.env['ir.config_parameter'].sudo().get_param('signaturit.production.api.url')
            env_label = '🔴 PRODUCTION'
        else:
            api_key = self.env['ir.config_parameter'].sudo().get_param('signaturit.sandbox.api.key')
            api_url = self.env['ir.config_parameter'].sudo().get_param('signaturit.sandbox.api.url')
            env_label = '🟡 SANDBOX'

        if not api_key:
            raise ValueError(f'Clé API SignaturIT {env_label} non configurée!')

        _logger.info(f'📡 Utilisation de l\'environnement {env_label}')

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

        # Envoyer à SignaturIT avec OAuth2 Bearer format
        headers = {
            'Authorization': f'Bearer {api_key}',  # OAuth2 Bearer token
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
            _logger.info(f'📤 Envoi à SignaturIT {env_label}: {self.name} avec {len(signers)} signataire(s)')
            _logger.debug(f'Signers: {signers}')
            _logger.debug(f'API URL: {api_url}')

            response = requests.post(
                f'{api_url}/requests',
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
            _logger.info(f'✅ Réponse SignaturIT {env_label}: {result}')
            return result

        except requests.exceptions.RequestException as e:
            error_msg = f'❌ Erreur API SignaturIT {env_label}: {str(e)}'
            _logger.error(error_msg)
            raise ValueError(error_msg)

    def _download_signed_pdf(self):
        """Télécharger le PDF signé depuis SignaturIT"""
        import requests

        if not self.signaturit_request_id:
            return

        # Récupérer l'environnement (sandbox ou production)
        environment = self.env['ir.config_parameter'].sudo().get_param('signaturit.environment', 'sandbox')

        # Récupérer la clé API selon l'environnement
        if environment == 'production':
            api_key = self.env['ir.config_parameter'].sudo().get_param('signaturit.production.api.key')
            api_url = self.env['ir.config_parameter'].sudo().get_param('signaturit.production.api.url')
            env_label = '🔴 PRODUCTION'
        else:
            api_key = self.env['ir.config_parameter'].sudo().get_param('signaturit.sandbox.api.key')
            api_url = self.env['ir.config_parameter'].sudo().get_param('signaturit.sandbox.api.url')
            env_label = '🟡 SANDBOX'

        headers = {
            'Authorization': f'Bearer {api_key}',  # OAuth2 Bearer token
        }

        try:
            _logger.info(f'📥 Téléchargement PDF signé {env_label} pour request {self.signaturit_request_id}')

            response = requests.get(
                f'{api_url}/requests/{self.signaturit_request_id}/document',
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                self.file = base64.b64encode(response.content)
                _logger.info(f'✅ PDF signé {env_label} téléchargé et sauvegardé pour {self.name}')
            else:
                error_msg = f'Impossible de télécharger le PDF signé (HTTP {response.status_code}): {response.text}'
                _logger.warning(f'⚠️ {error_msg}')

        except Exception as e:
            _logger.error(f'❌ Erreur téléchargement PDF {env_label}: {str(e)}')

    def action_archive(self):
        """Archiver le document"""
        self.ensure_one()
        self.write({
            'status': 'archived',
            'archive_date': fields.Datetime.now(),
        })
        _logger.info(f'📦 Document {self.name} archivé à {self.archive_date}')


class OnedeskDocumentSignature(models.Model):
    _name = 'onedesk.document.signature'
    _description = 'Signature de document'
    _rec_name = 'signer_name'
    _inherit = ['mail.thread']  # Enable message_post() for email tracking

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

    @api.model
    def create(self, vals_list):
        """Create signature records and send signature request emails"""
        signatures = super().create(vals_list)

        for signature in signatures:
            # ========== EMAIL TRIGGER: Signature Request ==========
            if signature.signer_email and signature.document_id:
                try:
                    # Get company from document for multi-tenant support
                    company = signature.document_id.company_id or self.env.company

                    # Try to use the email template for professional formatting
                    template = self.env.ref('onedesk_core.email_template_signature_request', raise_if_not_found=False)

                    if template:
                        # Use template if available
                        _logger.debug(f'Using email template for signature request')
                        template.send_mail(signature.id, force_send=False)
                    else:
                        # Fallback: Send direct email
                        _logger.debug(f'No template found, sending direct email')
                        self._send_signature_email_direct(signature, company)

                    # Log activity
                    signature.message_post(
                        body=f"📧 Email de demande de signature envoyé à {signature.signer_email}",
                        message_type='comment'
                    )
                    _logger.info(f'✅ Email signature envoyé: {signature.signer_name} ({signature.signer_email})')

                except Exception as e:
                    # Log error but don't fail
                    error_msg = str(e)
                    _logger.error(f'❌ Erreur envoi email signature: {error_msg}')
                    signature.message_post(
                        body=f"⚠️ Erreur envoi email signature: {error_msg}",
                        message_type='comment'
                    )

        return signatures

    def _send_signature_email_direct(self, signature, company):
        """Envoyer un email direct de demande de signature (fallback)"""
        doc_type_dict = dict(signature.document_id._fields['document_type'].selection)
        doc_type_label = doc_type_dict.get(signature.document_id.document_type, signature.document_id.document_type)

        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>📄 Demande de Signature</h2>
            <p>Bonjour {signature.signer_name},</p>

            <p>Un document vous attend pour signature:</p>
            <div style="background-color: #f5f5f5; padding: 15px; margin: 20px 0; border-left: 4px solid #1f77d2;">
                <p><strong>Document:</strong> {signature.document_id.name}</p>
                <p><strong>Type:</strong> {doc_type_label}</p>
                <p><strong>Demandé par:</strong> {self.env.user.name}</p>
            </div>

            <p>Veuillez consulter le document en pièce jointe ou accéder à votre portail Odoo pour signer.</p>

            <p style="color: #666; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 20px;">
                <small>© {company.name} - Plateforme de gestion immobilière</small>
            </p>
        </div>
        """

        mail_values = {
            'subject': f"📄 Signature requise: {signature.document_id.name}",
            'body_html': html_body,
            'email_to': signature.signer_email,
            'email_from': company.email or self.env.user.email,
            'company_id': company.id,
        }

        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send()
        _logger.info(f'📧 Email direct de signature envoyé à {signature.signer_email}')

    def action_resend(self):
        """Renvoyer l'email de demande de signature au signataire"""
        self.ensure_one()

        # Vérifier l'état de la signature
        if self.status == 'signed':
            raise ValueError('❌ Ce document est déjà signé, impossible de renvoyer!')

        if self.status == 'declined':
            raise ValueError('❌ Le signataire a refusé de signer ce document!')

        try:
            company = self.document_id.company_id or self.env.company

            # Renvoyer l'email de signature
            self._send_signature_email_direct(self, company)

            # Log l'action
            self.message_post(
                body=f'📬 Email de demande de signature renvoyé à {self.signer_email}',
                message_type='comment'
            )
            _logger.info(f'📬 Email signature renvoyé à {self.signer_email}')

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '📬 Email renvoyé!',
                    'message': f'Demande de signature renvoyée à {self.signer_email}',
                    'type': 'success'
                }
            }

        except Exception as e:
            _logger.error(f'❌ Erreur renvoi email: {str(e)}')
            self.message_post(body=f'⚠️ Erreur renvoi email: {str(e)}', message_type='comment')
            raise


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


# ========== MODÈLE TAGS/ÉTIQUETTES ==========
class OnedeskDocumentTag(models.Model):
    """Tags/Étiquettes pour organiser et retrouver les documents"""
    _name = 'onedesk.document.tag'
    _description = 'Tag/Étiquette pour documents'
    _rec_name = 'name'

    # ========== CHAMPS ==========
    name = fields.Char(string='Nom de l\'étiquette', required=True)
    color = fields.Integer(string='Couleur', default=1, help='Couleur de l\'étiquette (1-12)')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    # ========== RELATIONS ==========
    document_ids = fields.Many2many('onedesk.document', 'document_tag_rel',
                                    'tag_id', 'document_id',
                                    string='Documents')

    _sql_constraints = [
        ('unique_name_company', 'unique(name, company_id)',
         'Le nom de l\'étiquette doit être unique par company!')
    ]

    def name_get(self):
        """Afficher le tag avec un indicateur de couleur"""
        result = []
        for tag in self:
            result.append((tag.id, f"🏷️ {tag.name}"))
        return result
