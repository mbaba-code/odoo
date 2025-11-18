import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class CalendarEventOverride(models.Model):
    """Add company_id field to calendar.event for multi-tenant isolation"""
    _inherit = 'calendar.event'

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company,
        index=True,
        help="Company that owns this calendar event"
    )
