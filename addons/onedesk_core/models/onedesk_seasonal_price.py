from odoo import models, fields, api
from datetime import datetime

class OnedeskSeasonalPrice(models.Model):
    _name = 'onedesk.seasonal_price'
    _description = 'Tarification saisonnière'
    _order = 'date_start desc'

    unit_id = fields.Many2one('onedesk.unit', string='Unité', required=True, ondelete='cascade')
    name = fields.Char(string='Nom', required=True, help="Ex: Été 2024, Noël")

    date_start = fields.Date(string='Date début', required=True)
    date_end = fields.Date(string='Date fin', required=True)
    price_per_night = fields.Float(string='Prix par nuit', required=True, help="€/nuit pour cette période")

    active = fields.Boolean(default=True)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        """Vérifie que date_start < date_end"""
        for record in self:
            if record.date_start >= record.date_end:
                raise ValueError("La date de début doit être avant la date de fin")

    def __str__(self):
        return f"{self.name}: {self.date_start} → {self.date_end} ({self.price_per_night}€/nuit)"
