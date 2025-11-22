"""Webhook pour les événements SignaturIT"""
from odoo import http
from odoo.http import request
import logging
import json

_logger = logging.getLogger(__name__)


class SignaturitWebhook(http.Controller):

    @http.route('/signaturit/webhook', auth='none', type='json', csrf=False, methods=['POST'])
    def signaturit_webhook(self, **kwargs):
        """Traiter les événements SignaturIT

        Events:
        - request_signed: Tous les signataires ont signé
        - request_signer_signed: Un signataire a signé
        - request_declined: Un signataire a refusé
        """
        try:
            data = request.get_json_data()
            event = data.get('event')
            request_data = data.get('request', {})
            request_id = request_data.get('id')

            _logger.info(f'📬 Webhook SignaturIT: {event} - Request ID: {request_id}')

            if not request_id:
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
