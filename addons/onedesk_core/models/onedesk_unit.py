from odoo import models, fields, api
from datetime import datetime, timedelta

class OnedeskUnit(models.Model):
    _name = 'onedesk.unit'
    _description = 'Unité de propriété'

    name = fields.Char(string="Nom de l'unité", required=True)
    property_id = fields.Many2one('onedesk.property', string="Propriété")

    # Tarification flexible
    price_per_night = fields.Float(string="Prix par nuit (défaut)", required=True, default=100.0)
    seasonal_price_ids = fields.One2many('onedesk.seasonal_price', 'unit_id', string='Tarifs saisonniers')

    available = fields.Boolean(string="Disponible", default=True)

    def get_price_for_dates(self, date_start, date_end):
        """
        Retourne le prix moyen pour une période donnée
        Cherche les tarifs saisonniers et calcule une moyenne pondérée

        Args:
            date_start: date début (date object)
            date_end: date fin (date object)

        Returns:
            float: prix moyen par nuit
        """
        self.ensure_one()

        if not isinstance(date_start, (str, datetime)):
            return self.price_per_night

        # Convertir en date si nécessaire
        if isinstance(date_start, str):
            date_start = datetime.strptime(date_start, '%Y-%m-%d').date()
        elif isinstance(date_start, datetime):
            date_start = date_start.date()

        if isinstance(date_end, str):
            date_end = datetime.strptime(date_end, '%Y-%m-%d').date()
        elif isinstance(date_end, datetime):
            date_end = date_end.date()

        # Nombre total de nuits
        total_nights = (date_end - date_start).days
        if total_nights <= 0:
            return self.price_per_night

        # Cherche les tarifs saisonniers qui chevauchent cette période
        seasonal_prices = self.seasonal_price_ids.filtered(
            lambda p: p.active and p.date_start <= date_end and p.date_end >= date_start
        )

        if not seasonal_prices:
            # Aucun tarif saisonnier → prix par défaut
            return self.price_per_night

        # Calcule la moyenne pondérée des prix
        price_sum = 0.0
        nights_covered = 0

        current_date = date_start
        while current_date < date_end:
            # Cherche quel tarif saisonnier s'applique à cette date
            applicable_price = self.price_per_night
            for sp in seasonal_prices:
                if sp.date_start <= current_date < sp.date_end:
                    applicable_price = sp.price_per_night
                    break

            price_sum += applicable_price
            nights_covered += 1
            current_date += timedelta(days=1)

        return price_sum / nights_covered if nights_covered > 0 else self.price_per_night

    def get_total_price_for_dates(self, date_start, date_end):
        """Calcule le prix TOTAL pour une période"""
        nights = (date_end - date_start).days
        avg_price = self.get_price_for_dates(date_start, date_end)
        return avg_price * nights
