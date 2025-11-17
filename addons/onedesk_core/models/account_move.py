from odoo import models, fields


class AccountMove(models.Model):
    """Étendre account.move pour supporter OneDesk"""
    _inherit = 'account.move'

    # OneDesk Subscription relationship
    onedesk_subscription_id = fields.Many2one(
        'onedesk.subscription',
        string="Abonnement OneDesk",
        help="Abonnement associé à cette facture",
        ondelete='set null'
    )
