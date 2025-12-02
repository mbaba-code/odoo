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
from markupsafe import escape
import base64
import logging
import uuid
import io
from datetime import datetime

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

    signed_file = fields.Binary(string='Document Signé (PDF)', attachment=True,
                               help='Le PDF du document avec toutes les signatures apposées')
    signed_filename = fields.Char(string='Nom fichier signé')

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

    # ========== MODE DE SIGNATURE (Simple/Multiple) ==========
    signature_mode = fields.Selection([
        ('single_signer_multiple', '👤 Une personne - Plusieurs signatures'),
        ('multiple_signers', '👥 Plusieurs personnes - Plusieurs signatures chacun'),
    ], string='Mode de signature', default='single_signer_multiple',
       help="Une personne - Plusieurs signatures: 1 email, la personne peut cliquer plusieurs fois sur le PDF\n"
            "Plusieurs personnes - Plusieurs signatures: Chaque personne reçoit 1 email et peut cliquer plusieurs fois. Email envoyé quand TOUS ont signé.")

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

    @api.onchange('file')
    def _onchange_file(self):
        """Auto-populate filename quand le fichier est upload"""
        if self.file and not self.filename:
            # Générer un nom de fichier basé sur le nom du document
            sanitized_name = self.name.replace(' ', '_').replace('/', '_').lower()
            self.filename = f"{sanitized_name}.pdf"
            _logger.info(f'📄 Filename auto-rempli: {self.filename}')

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

    def action_download(self):
        """Télécharger le fichier PDF du document (priorité au PDF signé si disponible)"""
        self.ensure_one()

        # Priorité 1: Si le document a été signé, télécharger le PDF signé
        if self.signed_file:
            filename = self.signed_filename or f"{self.name}_signed.pdf"
            field_name = 'signed_file'
            _logger.info(f'📥 Téléchargement du PDF SIGNÉ {filename} pour {self.name}')
        # Priorité 2: Sinon, télécharger le PDF original
        elif self.file:
            filename = self.filename or f"{self.name}.pdf"
            field_name = 'file'
            _logger.info(f'📥 Téléchargement du PDF ORIGINAL {filename} pour {self.name}')
        else:
            raise ValueError('❌ Ce document n\'a pas de fichier PDF à télécharger!')

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/onedesk.document/{self.id}/{field_name}?download=true&filename={filename}',
            'target': 'new',
        }

    def action_archive(self):
        """Archiver le document"""
        self.ensure_one()
        self.write({
            'status': 'archived',
            'archive_date': fields.Datetime.now(),
        })
        _logger.info(f'📦 Document {self.name} archivé à {self.archive_date}')

    def generate_signed_pdf_with_all_signatures(self):
        """
        Génère un PDF avec TOUTES les signatures incrustées sur le document original

        Returns:
            bytes: Le PDF signé en base64 avec toutes les signatures
        """
        self.ensure_one()

        _logger.info(f"🔵 Génération PDF avec toutes les signatures pour {self.name}")

        if not self.file:
            _logger.error(f"❌ Impossible de générer PDF signé: pas de fichier original")
            return None

        # Récupérer toutes les signatures qui ont été validées
        # En mode single_signer_multiple: multiple_signatures (JSON) est rempli
        # En mode multiple_signers: signature_image est rempli
        signatures = self.env['onedesk.document.signature'].search([
            ('document_id', '=', self.id),
            ('status', '=', 'signed'),
            '|',  # OR
            ('signature_image', '!=', False),
            ('multiple_signatures', '!=', False)
        ])

        if not signatures:
            _logger.warning(f"⚠️ Aucune signature trouvée pour {self.name}, retour du PDF original")
            return self.file

        _logger.info(f"📝 {len(signatures)} signature(s) à intégrer")

        try:
            from pypdf import PdfReader, PdfWriter
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import ImageReader
            from PIL import Image

            # Décoder le PDF original
            original_pdf_data = base64.b64decode(self.file)
            original_pdf = PdfReader(io.BytesIO(original_pdf_data))

            # Créer un writer pour le PDF final
            output = PdfWriter()

            # Traiter chaque page
            for page_num in range(len(original_pdf.pages)):
                page = original_pdf.pages[page_num]
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)

                # Trouver toutes les signatures pour cette page
                page_signatures = [sig for sig in signatures
                                 if (sig.signature_page == page_num or
                                     (sig.signature_page == -1 and page_num == len(original_pdf.pages) - 1))]

                if page_signatures:
                    # Créer un overlay avec toutes les signatures pour cette page
                    packet = io.BytesIO()
                    can = canvas.Canvas(packet, pagesize=(page_width, page_height))

                    for sig in page_signatures:
                        try:
                            # Vérifier si mode signatures multiples (JSON)
                            signatures_to_add = []

                            if sig.multiple_signatures:
                                # Mode: Une personne, plusieurs signatures
                                import json
                                try:
                                    multi_sigs = json.loads(sig.multiple_signatures)
                                    for ms in multi_sigs:
                                        if ms.get('page') == page_num:
                                            signatures_to_add.append({
                                                'image_base64': ms.get('image'),
                                                'x': ms.get('x', 0),
                                                'y': ms.get('y', 0),
                                                'name': sig.signer_name,
                                                'date': sig.signature_date
                                            })
                                except json.JSONDecodeError as e:
                                    _logger.error(f"❌ Erreur parsing multiple_signatures JSON: {e}")
                                    continue
                            else:
                                # Mode: Une signature simple
                                if sig.signature_image:
                                    signatures_to_add.append({
                                        'image_base64': sig.signature_image,
                                        'x': sig.signature_x if sig.signature_x > 0 else page_width - 200,
                                        'y': sig.signature_y if sig.signature_y > 0 else 50,
                                        'name': sig.signer_name,
                                        'date': sig.signature_date
                                    })

                            # Dessiner toutes les signatures pour cette signature record
                            for sig_data in signatures_to_add:
                                try:
                                    # Décoder l'image de signature
                                    signature_img_data = base64.b64decode(sig_data['image_base64'])
                                    signature_img = Image.open(io.BytesIO(signature_img_data))

                                    if signature_img.mode not in ('RGB', 'RGBA'):
                                        signature_img = signature_img.convert('RGBA')

                                    # Sauvegarder temporairement l'image
                                    temp_sig = io.BytesIO()
                                    signature_img.save(temp_sig, format='PNG')
                                    temp_sig.seek(0)

                                    # Dimensions et position
                                    sig_width = 150
                                    sig_height = 50
                                    sig_x = sig_data['x']
                                    sig_y = sig_data['y']

                                    # Dessiner la signature
                                    img_reader = ImageReader(temp_sig)
                                    can.drawImage(img_reader, sig_x, sig_y, width=sig_width, height=sig_height, mask='auto')

                                    # Ajouter texte
                                    can.setFont("Helvetica", 8)
                                    try:
                                        can.drawString(sig_x, sig_y - 12, f"Signé par: {sig_data['name']}")
                                        can.drawString(sig_x, sig_y - 24, f"Date: {sig_data['date'].strftime('%d/%m/%Y %H:%M') if sig_data['date'] else 'N/A'}")
                                    except:
                                        signer_ascii = sig_data['name'].encode('ascii', 'ignore').decode('ascii')
                                        can.drawString(sig_x, sig_y - 12, f"Signe par: {signer_ascii}")
                                        can.drawString(sig_x, sig_y - 24, f"Date: {sig_data['date'].strftime('%d/%m/%Y %H:%M') if sig_data['date'] else 'N/A'}")

                                    _logger.info(f"  ✓ Signature de {sig_data['name']} ajoutée à page {page_num} ({sig_x}, {sig_y})")

                                except Exception as e:
                                    _logger.error(f"❌ Erreur ajout signature individuelle: {e}")
                                    continue

                        except Exception as e:
                            _logger.error(f"❌ Erreur traitement signature {sig.signer_name}: {e}")
                            continue

                    can.save()

                    # Merger l'overlay avec la page
                    packet.seek(0)
                    overlay = PdfReader(packet)
                    page.merge_page(overlay.pages[0])

                output.add_page(page)

            # Écrire le PDF final
            final_pdf = io.BytesIO()
            output.write(final_pdf)
            final_pdf.seek(0)

            # Encoder en base64
            pdf_bytes = final_pdf.read()
            signed_pdf_b64 = base64.b64encode(pdf_bytes)

            _logger.info(f"✅ PDF signé généré avec {len(signatures)} signature(s)")
            _logger.info(f"   - Taille PDF: {len(pdf_bytes)} bytes")
            _logger.info(f"   - Nombre de pages: {len(output.pages)}")

            return signed_pdf_b64

        except Exception as e:
            _logger.error(f"❌ Erreur génération PDF avec toutes signatures: {e}", exc_info=True)
            return None


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

    # ========== SÉCURITÉ - Accès Public ==========
    access_token = fields.Char(
        string='Token d\'accès',
        default=lambda self: str(uuid.uuid4()),
        required=True,
        readonly=True,
        copy=False,
        help="Token unique pour permettre l'accès public sécurisé au document à signer"
    )

    # ========== SIGNATURE ÉLECTRONIQUE ==========
    signature_image = fields.Binary(
        string='Image de signature',
        attachment=True,
        help="Image de la signature manuscrite du signataire"
    )
    signature_image_filename = fields.Char(
        string='Nom fichier signature',
        default='signature.png'
    )

    # ========== POSITION DE LA SIGNATURE ==========
    signature_page = fields.Integer(
        string='Page de signature',
        default=-1,
        help="Numéro de la page où placer la signature (-1 = dernière page)"
    )
    signature_x = fields.Float(
        string='Position X',
        default=0,
        help="Position horizontale de la signature (0 = auto, en bas à droite)"
    )
    signature_y = fields.Float(
        string='Position Y',
        default=0,
        help="Position verticale de la signature (0 = auto, en bas à droite)"
    )

    # ========== SIGNATURES MULTIPLES (Mode single_signer_multiple) ==========
    multiple_signatures = fields.Text(
        string='Positions signatures multiples (JSON)',
        help="Stocke plusieurs positions de signature au format JSON: [{page, x, y, image_base64}, ...]"
    )

    def generate_signed_pdf(self):
        """
        Génère un PDF avec la signature incrustée sur le document original

        Returns:
            bytes: Le PDF signé en base64
        """
        self.ensure_one()

        _logger.info(f"🔵 Début génération PDF signé pour {self.signer_name}")
        _logger.info(f"   - document_id: {self.document_id}")
        _logger.info(f"   - document_id.file existe: {bool(self.document_id.file)}")
        _logger.info(f"   - signature_image existe: {bool(self.signature_image)}")
        _logger.info(f"   - Position: page={self.signature_page}, x={self.signature_x}, y={self.signature_y}")

        if not self.document_id.file or not self.signature_image:
            _logger.error(f"❌ Impossible de générer PDF signé: document={bool(self.document_id.file)}, signature={bool(self.signature_image)}")
            return None

        try:
            from pypdf import PdfReader, PdfWriter
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import ImageReader
            from PIL import Image

            # Décoder le PDF original
            original_pdf_data = base64.b64decode(self.document_id.file)
            original_pdf = PdfReader(io.BytesIO(original_pdf_data))

            # Décoder l'image de signature
            # Les champs Binary dans Odoo sont stockés en base64
            if not self.signature_image:
                _logger.error(f"❌ Champ signature_image est vide")
                return None

            # Vérifier la longueur du base64 avant décodage
            if len(self.signature_image) < 100:
                _logger.error(f"❌ signature_image trop court ({len(self.signature_image)} chars), données corrompues")
                return None

            try:
                signature_img_data = base64.b64decode(self.signature_image)
                _logger.info(f"✓ Décodage base64 OK: {len(signature_img_data)} bytes PNG")
            except Exception as e:
                _logger.error(f"❌ Erreur décodage base64 signature: {e}")
                _logger.error(f"   Début de signature_image: {self.signature_image[:50]}...")
                return None

            # Vérifier que les bytes PNG sont valides
            if not signature_img_data or len(signature_img_data) < 100:
                _logger.error(f"❌ Données PNG invalides après décodage (taille: {len(signature_img_data) if signature_img_data else 0} bytes)")
                return None

            # Ouvrir l'image
            try:
                signature_img = Image.open(io.BytesIO(signature_img_data))
                # Convertir en RGBA si nécessaire
                if signature_img.mode not in ('RGB', 'RGBA'):
                    signature_img = signature_img.convert('RGBA')
            except Exception as e:
                _logger.error(f"Erreur ouverture image signature: {e}")
                return None

            # Déterminer la page de signature
            target_page_num = self.signature_page if self.signature_page >= 0 else len(original_pdf.pages) - 1
            if target_page_num >= len(original_pdf.pages):
                target_page_num = len(original_pdf.pages) - 1

            target_page = original_pdf.pages[target_page_num]
            page_width = float(target_page.mediabox.width)
            page_height = float(target_page.mediabox.height)

            # Créer un PDF overlay avec la signature
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=(page_width, page_height))

            # Sauvegarder temporairement l'image de signature en PNG
            temp_sig = io.BytesIO()
            signature_img.save(temp_sig, format='PNG')
            temp_sig.seek(0)

            # Dimensions de la signature
            sig_width = 150
            sig_height = 50

            # Position de la signature
            if self.signature_x > 0 and self.signature_y > 0:
                # Position personnalisée définie
                sig_x = self.signature_x
                sig_y = self.signature_y
                _logger.info(f"Position signature personnalisée: ({sig_x}, {sig_y}) page {target_page_num}")
            else:
                # Position par défaut (en bas à droite)
                sig_x = page_width - sig_width - 50
                sig_y = 50
                _logger.info(f"Position signature par défaut: ({sig_x}, {sig_y}) page {target_page_num}")

            # Dessiner la signature sur le canvas en utilisant ImageReader
            img_reader = ImageReader(temp_sig)
            can.drawImage(img_reader, sig_x, sig_y, width=sig_width, height=sig_height,
                         mask='auto')

            # Ajouter texte "Signé électroniquement"
            can.setFont("Helvetica", 8)
            try:
                # Essayer d'écrire le texte avec le nom (peut contenir des accents)
                can.drawString(sig_x, sig_y - 12, f"Signé par: {self.signer_name}")
                can.drawString(sig_x, sig_y - 24, f"Date: {self.signature_date.strftime('%d/%m/%Y %H:%M') if self.signature_date else 'N/A'}")
            except Exception as e:
                # Fallback sans accents si problème d'encoding
                _logger.warning(f"Erreur ajout texte signature (probablement encoding): {e}")
                # Essayer avec une version ASCII simplifiée
                signer_ascii = self.signer_name.encode('ascii', 'ignore').decode('ascii')
                can.drawString(sig_x, sig_y - 12, f"Signe par: {signer_ascii}")
                can.drawString(sig_x, sig_y - 24, f"Date: {self.signature_date.strftime('%d/%m/%Y %H:%M') if self.signature_date else 'N/A'}")

            can.save()

            # Merger le canvas avec le PDF original
            packet.seek(0)
            overlay = PdfReader(packet)

            # Créer le PDF final
            output = PdfWriter()

            # Copier toutes les pages
            for page_num in range(len(original_pdf.pages)):
                page = original_pdf.pages[page_num]

                # Ajouter la signature sur la page cible
                if page_num == target_page_num:
                    page.merge_page(overlay.pages[0])

                output.add_page(page)

            # Écrire le PDF final
            final_pdf = io.BytesIO()
            output.write(final_pdf)
            final_pdf.seek(0)

            # Encoder en base64
            pdf_bytes = final_pdf.read()
            signed_pdf_b64 = base64.b64encode(pdf_bytes)

            _logger.info(f"✅ PDF signé généré avec succès pour {self.signer_name}")
            _logger.info(f"   - Taille PDF: {len(pdf_bytes)} bytes")
            _logger.info(f"   - Nombre de pages: {len(output.pages)}")
            _logger.info(f"   - Signature placée sur page {target_page_num}")
            return signed_pdf_b64

        except Exception as e:
            _logger.error(f"❌ Erreur génération PDF signé: {e}", exc_info=True)
            return None

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
            if signature.signer_email and signature.document_id:
                try:
                    company = signature.document_id.company_id or self.env.company

                    # Cherche le template (sans lever d’erreur)
                    template = self.env.ref(
                        'onedesk_core.email_template_signature_request',
                        raise_if_not_found=False
                    )

                    if template:
                        _logger.info(f"📧 Envoi email signature via template (rendu manuel) pour {signature.signer_email}")

                        # ============ Rendu manuel (ÉVITE send_mail) ============
                        subject = template._render_field(
                            'subject', signature.ids, compute_lang=True
                        )[signature.id]

                        body_html = template._render_field(
                            'body_html', signature.ids, compute_lang=True
                        )[signature.id]

                        email_from = template.email_from or company.email or 'noreply@localhost'

                        mail_values = {
                            'subject': subject,
                            'body_html': body_html,
                            'email_to': signature.signer_email,
                            'email_from': email_from,
                        }

                        mail = self.env['mail.mail'].sudo().create(mail_values)
                        mail.sudo().send()

                        _logger.info(
                            f"✅ Email envoyé (mail_id={mail.id}) à {signature.signer_email}"
                        )

                    else:
                    # ========= Fallback si pas de template =========
                        _logger.warning(
                            "⚠️ Template email_template_signature_request introuvable ! Envoi fallback direct."
                        )
                        self._send_signature_email_direct(signature, company)

                # Log Odoo
                    signature.message_post(
                        body=f"📧 Email de demande de signature envoyé à {signature.signer_email}",
                        message_type='comment'
                    )

                except Exception as e:
                    error_msg = str(e)
                    _logger.error(f"❌ Erreur envoi email signature: {error_msg}", exc_info=True)
                    signature.message_post(
                        body=f"⚠️ Erreur envoi email signature: {error_msg}",
                        message_type='comment'
                    )   

        return signatures

     

    def _send_signature_email_direct(self, signature, company):
        """
        Envoyer un email direct de demande de signature (fallback)

        SECURITY: Tous les contenus HTML sont échappés pour prévenir XSS
        """
        doc_type_dict = dict(signature.document_id._fields['document_type'].selection)
        doc_type_label = doc_type_dict.get(signature.document_id.document_type, signature.document_id.document_type)

        # SECURITY: Échapper tous les contenus pour prévenir XSS
        signer_name = escape(signature.signer_name)
        document_name = escape(signature.document_id.name)
        doc_type_escaped = escape(doc_type_label)
        requester_name = escape(self.env.user.name)
        company_name = escape(company.name)

        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>📄 Demande de Signature</h2>
            <p>Bonjour {signer_name},</p>

            <p>Un document vous attend pour signature:</p>
            <div style="background-color: #f5f5f5; padding: 15px; margin: 20px 0; border-left: 4px solid #1f77d2;">
                <p><strong>Document:</strong> {document_name}</p>
                <p><strong>Type:</strong> {doc_type_escaped}</p>
                <p><strong>Demandé par:</strong> {requester_name}</p>
            </div>

            <p>Veuillez consulter le document en pièce jointe ou accéder à votre portail Odoo pour signer.</p>

            <p style="color: #666; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 20px;">
                <small>© {company_name} - Plateforme de gestion immobilière</small>
            </p>
        </div>
        """

        mail_values = {
            'subject': f"📄 Signature requise: {document_name}",
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
