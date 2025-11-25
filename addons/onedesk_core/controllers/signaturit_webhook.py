"""Webhook pour les événements SignaturIT avec validation HMAC"""
from odoo import http
from odoo.http import request
import logging
import json
import hmac
import hashlib

_logger = logging.getLogger(__name__)


class SignaturitWebhook(http.Controller):

    def _verify_signaturit_signature(self):
        """
        SECURITY: Vérifier la signature HMAC de SignaturIT

        SignaturIT envoie une signature HMAC dans le header X-Signaturit-Signature
        pour garantir que la requête provient bien de SignaturIT.

        Returns:
            bool: True si la signature est valide, False sinon
        """
        try:
            # Récupérer la signature depuis le header
            received_signature = request.httprequest.headers.get('X-Signaturit-Signature')

            if not received_signature:
                _logger.warning('⚠️ Webhook SignaturIT sans signature HMAC')
                return False

            # Récupérer le secret webhook depuis la configuration
            webhook_secret = request.env['ir.config_parameter'].sudo().get_param(
                'signaturit.webhook.secret'
            )

            if not webhook_secret:
                _logger.error('❌ Secret webhook SignaturIT non configuré!')
                return False

            # Récupérer le payload brut
            payload = request.httprequest.get_data()

            # Calculer la signature attendue
            expected_signature = hmac.new(
                webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()

            # Comparer de manière sécurisée (timing-attack safe)
            is_valid = hmac.compare_digest(received_signature, expected_signature)

            if not is_valid:
                _logger.error('❌ Signature HMAC invalide - possible attaque!')

            return is_valid

        except Exception as e:
            _logger.error(f'❌ Erreur lors de la vérification HMAC: {str(e)}')
            return False

    @http.route('/signaturit/webhook', auth='public', type='json', csrf=False, methods=['POST'])
    def signaturit_webhook(self, **kwargs):
        """
        Traiter les événements SignaturIT avec validation de sécurité

        SECURITY IMPROVEMENTS:
        - Validation HMAC de la signature
        - Auth 'public' au lieu de 'none' pour logging
        - Logs détaillés pour audit

        Events:
        - request_signed: Tous les signataires ont signé
        - request_signer_signed: Un signataire a signé
        - request_declined: Un signataire a refusé
        """
        try:
            # SECURITY: Vérifier la signature HMAC avant tout traitement
            if not self._verify_signaturit_signature():
                _logger.error('❌ Tentative d\'accès webhook avec signature invalide')
                return {
                    'status': 'error',
                    'message': 'Invalid signature'
                }

            data = request.get_json_data()
            event = data.get('event')
            request_data = data.get('request', {})
            request_id = request_data.get('id')

            _logger.info(f'📬 Webhook SignaturIT validé: {event} - Request ID: {request_id}')

            if not request_id:
                _logger.warning('⚠️ Webhook sans request ID')
                return {'status': 'error', 'message': 'No request ID'}

            # Chercher le document avec cet ID
            document = request.env['onedesk.document'].sudo().search(
                [('signaturit_request_id', '=', request_id)]
            )

            if not document:
                _logger.warning(f'Document non trouvé pour request ID: {request_id}')
                return {'status': 'error', 'message': 'Document not found'}

            # Traiter l'événement
            if event == 'request_signed':
                # Tous ont signé!
                _logger.info(f'✅ Tous les signataires ont signé le document {document.name}')
                document._handle_all_signed()

            elif event == 'request_signer_signed':
                # Un signataire a signé
                signer_data = data.get('signer', {})
                signer_email = signer_data.get('email')
                _logger.info(f'✅ {signer_email} a signé le document {document.name}')
                document._handle_signer_signed(signer_email)

            elif event == 'request_declined':
                # Un signataire a refusé
                signer_data = data.get('signer', {})
                signer_email = signer_data.get('email')
                _logger.warning(f'❌ {signer_email} a refusé de signer {document.name}')
                document._handle_signer_declined(signer_email)

            return {'status': 'ok'}

        except Exception as e:
            _logger.error(f'❌ Erreur webhook SignaturIT: {str(e)}')
            return {'status': 'error', 'message': str(e)}
