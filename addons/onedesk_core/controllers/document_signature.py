"""
Controller pour la signature publique de documents
Permet aux signataires (internes et externes) de signer des documents
via un lien sécurisé avec token d'accès
"""
from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessError
import logging

_logger = logging.getLogger(__name__)


class DocumentSignatureController(http.Controller):
    """Contrôleur pour la signature publique de documents"""

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

                    # Décoder base64 et stocker
                    import base64
                    signature_image_binary = base64.b64decode(signature_data)

                    # Signer le document avec l'image de signature
                    signature.write({
                        'status': 'signed',
                        'signature_date': fields.Datetime.now(),
                        'signature_image': signature_image_binary,
                        'signature_image_filename': f'signature_{signature.signer_name}.png'
                    })

                    _logger.info(f"✅ Signature électronique capturée pour {signature.signer_email}")
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
                    document.write({'status': 'signed'})
                    _logger.info(f"📄 Document {document.name} entièrement signé!")

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
                        mail.sudo().send()
                        _logger.info(f"📧 Email de confirmation envoyé à {signature.signer_email}")
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
