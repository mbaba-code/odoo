"""Controller simple pour la signature de documents"""
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class DocumentSignatureController(http.Controller):

    @http.route('/onedesk/document/<int:document_id>/sign', type='http', auth='public', website=True)
    def document_sign(self, document_id, **kwargs):
        """
        Page simple pour signer un document
        Redirige vers le backend Odoo pour l'instant
        """
        # Chercher le document
        document = request.env['onedesk.document'].sudo().search([
            ('id', '=', document_id)
        ], limit=1)

        if not document:
            return request.render('website.404')

        # Pour l'instant, on redirige vers le backend Odoo
        # où l'utilisateur peut voir le document et le signer
        return request.redirect(f'/web#id={document_id}&model=onedesk.document&view_type=form')
