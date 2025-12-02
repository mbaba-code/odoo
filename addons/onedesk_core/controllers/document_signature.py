"""
Controller pour la signature publique de documents
Permet aux signataires (internes et externes) de signer des documents
via un lien sécurisé avec token d'accès
"""
from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessError
import logging
import base64

_logger = logging.getLogger(__name__)


class DocumentSignatureController(http.Controller):
    """Contrôleur pour la signature publique de documents"""

    @http.route('/onedesk/document/<int:document_id>/pdf', type='http', auth='public', methods=['GET'])
    def document_pdf(self, document_id, access_token=None, download=None, **kwargs):
        """
        Servir le PDF du document en mode public avec vérification du token

        Args:
            document_id (int): ID du document
            access_token (str): Token d'accès pour sécuriser l'accès
            download (str): Si présent, force le téléchargement au lieu de la visualisation

        Returns:
            PDF file response ou erreur 404
        """
        try:
            # Vérifier que le token est fourni
            if not access_token:
                _logger.warning(f"Tentative d'accès au PDF {document_id} sans token")
                return request.not_found()

            # Rechercher une signature valide avec ce token pour ce document
            Signature = request.env['onedesk.document.signature'].sudo()
            signature = Signature.search([
                ('document_id', '=', document_id),
                ('access_token', '=', access_token)
            ], limit=1)

            if not signature:
                _logger.warning(f"Token invalide pour accès PDF document {document_id}")
                return request.not_found()

            # Récupérer le document
            document = signature.document_id

            if not document or not document.file:
                _logger.warning(f"Document {document_id} ou fichier PDF non trouvé")
                return request.not_found()

            # Décoder le PDF et le retourner
            pdf_data = base64.b64decode(document.file)
            filename = document.filename or f'document_{document_id}.pdf'

            # Déterminer si on force le téléchargement ou la visualisation inline
            disposition = 'attachment' if download else 'inline'

            # Retourner le PDF
            headers = [
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'{disposition}; filename="{filename}"'),
                ('Content-Length', len(pdf_data))
            ]

            action = "téléchargé" if download else "visualisé"
            _logger.info(f"PDF {action} avec succès pour document {document_id} (token valide)")
            return request.make_response(pdf_data, headers=headers)

        except Exception as e:
            _logger.error(f"Erreur lors du service du PDF {document_id}: {e}", exc_info=True)
            return request.not_found()

    @http.route('/onedesk/document/<int:document_id>/signed_pdf', type='http', auth='public', methods=['GET'])
    def signed_document_pdf(self, document_id, access_token=None, download=None, **kwargs):
        """
        Servir le PDF SIGNÉ du document en mode public avec vérification du token

        Args:
            document_id (int): ID du document
            access_token (str): Token d'accès pour sécuriser l'accès
            download (str): Si présent, force le téléchargement au lieu de la visualisation

        Returns:
            PDF signed file response ou erreur 404
        """
        try:
            # Vérifier que le token est fourni
            if not access_token:
                _logger.warning(f"Tentative d'accès au PDF signé {document_id} sans token")
                return request.not_found()

            # Rechercher une signature valide avec ce token pour ce document
            Signature = request.env['onedesk.document.signature'].sudo()
            signature = Signature.search([
                ('document_id', '=', document_id),
                ('access_token', '=', access_token)
            ], limit=1)

            if not signature:
                _logger.warning(f"Token invalide pour accès PDF signé document {document_id}")
                return request.not_found()

            # Récupérer le document
            document = signature.document_id

            if not document or not document.signed_file:
                _logger.warning(f"Document {document_id} ou fichier PDF signé non trouvé")
                return request.not_found()

            # Décoder le PDF signé et le retourner
            pdf_data = base64.b64decode(document.signed_file)
            filename = document.signed_filename or f'document_{document_id}_signed.pdf'

            # Déterminer si on force le téléchargement ou la visualisation inline
            disposition = 'attachment' if download else 'inline'

            # Retourner le PDF signé
            headers = [
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'{disposition}; filename="{filename}"'),
                ('Content-Length', len(pdf_data))
            ]

            action = "téléchargé" if download else "visualisé"
            _logger.info(f"PDF signé {action} avec succès pour document {document_id} (token valide)")
            return request.make_response(pdf_data, headers=headers)

        except Exception as e:
            _logger.error(f"Erreur lors du service du PDF signé {document_id}: {e}", exc_info=True)
            return request.not_found()

    @http.route('/onedesk/document/<int:document_id>/sign', type='http', auth='public', website=True)
    def document_sign(self, document_id, access_token=None, **kwargs):
        """
        Page publique pour signer un document

        Args:
            document_id (int): ID du document
            access_token (str): Token d'accès unique pour sécuriser l'accès

        Returns:
            Rendered template: Page de signature ou page d'erreur
        """
        try:
            # Rechercher le document
            Document = request.env['onedesk.document'].sudo()
            document = Document.search([('id', '=', document_id)], limit=1)

            if not document:
                _logger.warning(f"Document {document_id} non trouvé")
                return request.render('onedesk_core.public_signature_error', {
                    'error_message': "Document non trouvé."
                })

            # Vérifier que le token est fourni
            if not access_token:
                _logger.warning(f"Accès au document {document_id} sans token")
                return request.render('onedesk_core.public_signature_error', {
                    'error_message': "Token d'accès manquant. Veuillez utiliser le lien fourni dans votre email."
                })

            # Rechercher la signature correspondante avec le token
            Signature = request.env['onedesk.document.signature'].sudo()
            signature = Signature.search([
                ('document_id', '=', document_id),
                ('access_token', '=', access_token)
            ], limit=1)

            if not signature:
                _logger.warning(f"Token invalide pour document {document_id}: {access_token[:8]}...")
                return request.render('onedesk_core.public_signature_error', {
                    'error_message': "Token d'accès invalide ou expiré."
                })

            # Tout est OK - afficher la page de signature
            _logger.info(f"Affichage page signature pour {signature.signer_email} - document {document.name}")

            return request.render('onedesk_core.public_signature_page', {
                'document': document,
                'signature': signature,
            })

        except Exception as e:
            _logger.error(f"Erreur lors de l'affichage de la page de signature: {e}", exc_info=True)
            return request.render('onedesk_core.public_signature_error', {
                'error_message': "Une erreur s'est produite. Veuillez réessayer plus tard."
            })

    @http.route('/onedesk/document/<int:document_id>/sign/action', type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def document_sign_action(self, document_id, signature_id, access_token, action, **kwargs):
        """
        Traitement de l'action de signature (signer ou refuser)

        Args:
            document_id (int): ID du document
            signature_id (int): ID de la signature
            access_token (str): Token d'accès
            action (str): Action à effectuer ('sign' ou 'decline')

        Returns:
            Rendered template: Page de confirmation ou erreur
        """
        try:
            # Vérifications de sécurité
            Document = request.env['onedesk.document'].sudo()
            document = Document.search([('id', '=', document_id)], limit=1)

            if not document:
                return request.render('onedesk_core.public_signature_error', {
                    'error_message': "Document non trouvé."
                })

            Signature = request.env['onedesk.document.signature'].sudo()
            signature = Signature.search([
                ('id', '=', int(signature_id)),
                ('document_id', '=', document_id),
                ('access_token', '=', access_token)
            ], limit=1)

            if not signature:
                return request.render('onedesk_core.public_signature_error', {
                    'error_message': "Signature non trouvée ou token invalide."
                })

            # Vérifier que la signature n'a pas déjà été traitée
            if signature.status != 'pending':
                _logger.warning(f"Tentative de signature d'un document déjà traité (statut: {signature.status})")
                return request.render('onedesk_core.public_signature_error', {
                    'error_message': f"Ce document a déjà été {signature.status}."
                })

            # Traiter l'action
            if action == 'sign':
                # Capturer la signature électronique (image base64)
                signature_data = kwargs.get('signature_data', '')

                if signature_data:
                    # Extraire les données base64 (enlever le préfixe data:image/png;base64,)
                    if ',' in signature_data:
                        signature_data = signature_data.split(',')[1]

                    # Vérifier que la signature n'est pas vide (minimum 100 chars base64)
                    if len(signature_data) < 100:
                        _logger.error(f"❌ Signature trop courte ({len(signature_data)} chars), probablement vide ou corrompue")
                        return request.render('onedesk_core.public_signature_form', {
                            'document': document,
                            'signature': signature,
                            'error_message': "La signature semble vide ou invalide. Veuillez dessiner votre signature."
                        })

                    # Stocker la signature base64 DIRECTEMENT (Odoo Binary attend du base64, pas des bytes)
                    # PAS besoin de décoder/réencoder, le champ Binary le gère automatiquement
                    _logger.info(f"📸 Signature capturée: {len(signature_data)} caractères base64")

                    # Capturer la position de la signature choisie par le signataire
                    try:
                        sig_page = int(kwargs.get('signature_page', -1))
                        sig_x = float(kwargs.get('signature_x', 0))
                        sig_y = float(kwargs.get('signature_y', 0))
                        _logger.info(f"📍 Position signature: page={sig_page}, x={sig_x}, y={sig_y}")
                    except (ValueError, TypeError) as e:
                        _logger.warning(f"⚠️ Erreur parsing position signature: {e}, utilisation des valeurs par défaut")
                        sig_page = -1
                        sig_x = 0
                        sig_y = 0

                    # Signer le document avec l'image de signature ET la position
                    signature.write({
                        'status': 'signed',
                        'signature_date': fields.Datetime.now(),
                        'signature_image': signature_data,  # String base64, pas bytes!
                        'signature_image_filename': f'signature_{signature.signer_name}.png',
                        'signature_page': sig_page,
                        'signature_x': sig_x,
                        'signature_y': sig_y
                    })

                    _logger.info(f"✅ Signature électronique capturée pour {signature.signer_email}")

                    # Générer le PDF signé avec TOUTES les signatures (y compris la nouvelle)
                    signed_pdf = document.generate_signed_pdf_with_all_signatures()
                    if signed_pdf:
                        # Stocker le PDF signé dans le document
                        document.write({
                            'signed_file': signed_pdf,
                            'signed_filename': f'{document.name}_signed.pdf'
                        })
                        _logger.info(f"📄 PDF signé généré avec toutes les signatures pour {document.name}")
                    else:
                        _logger.error(f"❌ ERREUR: generate_signed_pdf_with_all_signatures() a retourné None. Vérifier les logs ci-dessus pour la cause.")
                else:
                    # Pas de signature fournie, juste marquer comme signé
                    signature.write({
                        'status': 'signed',
                        'signature_date': fields.Datetime.now()
                    })
                    _logger.warning(f"⚠️ Signature sans image pour {signature.signer_email}")

                # Log l'action
                signature.message_post(
                    body=f"✅ Document signé par {signature.signer_name} ({signature.signer_email}) le {fields.Datetime.now()}",
                    message_type='comment'
                )

                _logger.info(f"✅ Document {document.name} signé par {signature.signer_email}")

                # Vérifier si tous les signataires ont signé
                all_signatures = Signature.search([('document_id', '=', document_id)])
                if all(s.status == 'signed' for s in all_signatures):
                    # Marquer le document comme signé et lui attribuer une catégorie
                    # pour qu'il soit visible dans "Stock Document"
                    document_update = {'status': 'signed'}

                    # Si le document n'a pas de catégorie, lui en attribuer une par défaut
                    if not document.document_category:
                        document_update['document_category'] = 'other'
                        _logger.info(f"📦 Document {document.name} classé dans 'Autre' après signature complète")

                    document.write(document_update)
                    _logger.info(f"📄 Document {document.name} entièrement signé et stocké!")

                # ========== ENVOI EMAIL DE CONFIRMATION ==========
                try:
                    # Chercher le template d'email de confirmation
                    email_template = request.env.ref(
                        'onedesk_core.email_template_signature_confirmation',
                        raise_if_not_found=False
                    ).sudo()

                    if email_template:
                        # Rendre et envoyer l'email
                        subject = email_template._render_field('subject', signature.ids, compute_lang=True)[signature.id]
                        body_html = email_template._render_field('body_html', signature.ids, compute_lang=True)[signature.id]
                        email_from = email_template.email_from or 'noreply@onedesk.io'

                        mail_values = {
                            'subject': subject,
                            'body_html': body_html,
                            'email_to': signature.signer_email,
                            'email_from': email_from,
                            'model': 'onedesk.document.signature',
                            'res_id': signature.id,
                        }

                        mail = request.env['mail.mail'].sudo().create(mail_values)

                        # Attacher le PDF SIGNÉ (avec signature incrustée) à l'email
                        attachments_created = []
                        if document.signed_file:
                            # Utiliser le PDF signé généré
                            pdf_attachment = request.env['ir.attachment'].sudo().create({
                                'name': document.signed_filename or f'{document.name}_signed.pdf',
                                'type': 'binary',
                                'datas': document.signed_file,
                                'res_model': 'mail.mail',
                                'res_id': mail.id,
                                'mimetype': 'application/pdf',
                            })
                            attachments_created.append(f"PDF Signé ({pdf_attachment.id})")
                            _logger.info(f"📎 PDF SIGNÉ (avec signature incrustée) attaché à l'email (ID: {pdf_attachment.id})")
                        elif document.file:
                            # Fallback sur PDF original si pas de PDF signé
                            pdf_attachment = request.env['ir.attachment'].sudo().create({
                                'name': document.filename or f'{document.name}.pdf',
                                'type': 'binary',
                                'datas': document.file,
                                'res_model': 'mail.mail',
                                'res_id': mail.id,
                                'mimetype': 'application/pdf',
                            })
                            attachments_created.append(f"PDF Original ({pdf_attachment.id})")
                            _logger.info(f"📎 PDF original attaché à l'email (ID: {pdf_attachment.id})")

                        mail.sudo().send()
                        _logger.info(f"📧 Email de confirmation envoyé à {signature.signer_email} avec {len(attachments_created)} pièces jointes: {', '.join(attachments_created)}")
                    else:
                        _logger.warning("⚠️ Template email de confirmation non trouvé")

                except Exception as e:
                    _logger.error(f"❌ Erreur envoi email confirmation: {e}", exc_info=True)
                    # On ne bloque pas le processus si l'email échoue

                # Afficher la page de succès
                return request.render('onedesk_core.public_signature_success', {
                    'document': document,
                    'signature': signature,
                })

            elif action == 'decline':
                # Refuser de signer
                signature.write({
                    'status': 'declined',
                })

                # Log l'action
                signature.message_post(
                    body=f"❌ Signature refusée par {signature.signer_name} ({signature.signer_email})",
                    message_type='comment'
                )

                _logger.info(f"❌ Document {document.name} refusé par {signature.signer_email}")

                # Afficher la page de refus
                return request.render('onedesk_core.public_signature_declined', {
                    'document': document,
                    'signature': signature,
                })

            else:
                _logger.error(f"Action inconnue: {action}")
                return request.render('onedesk_core.public_signature_error', {
                    'error_message': "Action invalide."
                })

        except Exception as e:
            _logger.error(f"Erreur lors du traitement de l'action de signature: {e}", exc_info=True)
            return request.render('onedesk_core.public_signature_error', {
                'error_message': "Une erreur s'est produite lors du traitement de votre demande."
            })
