from odoo import models, fields, api
from datetime import datetime

class OneDeskReservation(models.Model):
    _name = 'onedesk.reservation'
    _description = 'Reservation'

    # Champs de base
    name = fields.Char(string='Reservation Reference', required=True, copy=False, default='New')
    unit_id = fields.Many2one('onedesk.unit', string='Unit', required=True)
    start_date = fields.Datetime(string='Start Date', required=True)
    end_date = fields.Datetime(string='End Date', required=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)

    # Champs intégration
    external_id = fields.Char(string='ID Externe', index=True,
                              help="ID de la plateforme externe (Airbnb, Booking, etc.)")
    integration_id = fields.Many2one('onedesk.integration', string='Source plateforme',
                                     help="Intégration depuis laquelle cette réservation a été importée")

    # Lien vers l'événement du calendrier
    calendar_event_id = fields.Many2one('calendar.event', string='Calendar Event', readonly=True)

    # ========== TARIFICATION ==========
    price_per_night = fields.Float(string='Prix par nuit (appliqué)',
                                   help="Prix moyen par nuit selon tarif saisonnier",
                                   readonly=True, store=True)
    number_of_nights = fields.Integer(string='Nombre de nuits',
                                      compute='_compute_number_of_nights',
                                      store=True, readonly=True)
    total_price = fields.Float(string='Prix total',
                               compute='_compute_total_price',
                               store=True, readonly=True)

    # Payment
    payment_status = fields.Selection([
        ('pending', 'En attente'),
        ('completed', 'Payée'),
        ('cancelled', 'Annulée'),
    ], string='Statut paiement', default='pending', tracking=True)
    payment_link = fields.Char(string='Lien de paiement')

    @api.depends('start_date', 'end_date')
    def _compute_number_of_nights(self):
        """Calcule le nombre de nuits"""
        for record in self:
            if record.start_date and record.end_date:
                delta = record.end_date - record.start_date
                # Convertir timedelta en jours
                record.number_of_nights = delta.days
            else:
                record.number_of_nights = 0

    @api.depends('price_per_night', 'number_of_nights')
    def _compute_total_price(self):
        """Calcule le prix total"""
        for record in self:
            record.total_price = record.price_per_night * record.number_of_nights

    # Création automatique de l'événement + calcul prix
    @api.model
    def create(self, vals):
        # Calcule le prix automatiquement avant création
        if 'unit_id' in vals and 'start_date' in vals and 'end_date' in vals:
            unit = self.env['onedesk.unit'].browse(vals['unit_id'])
            if unit:
                # Convertir dates si nécessaire
                start_date = vals['start_date']
                end_date = vals['end_date']
                if isinstance(start_date, str):
                    start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00')).date()
                elif hasattr(start_date, 'date'):
                    start_date = start_date.date()

                if isinstance(end_date, str):
                    end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00')).date()
                elif hasattr(end_date, 'date'):
                    end_date = end_date.date()

                # Récupère le prix pour cette période
                vals['price_per_night'] = unit.get_price_for_dates(start_date, end_date)

        reservation = super().create(vals)

        # Crée un événement dans le calendrier visible pour tout le monde
        event = self.env['calendar.event'].sudo().create({
            'name': f"{reservation.name} - {reservation.unit_id.name}",
            'start': reservation.start_date,
            'stop': reservation.end_date,
            'description': f"Client: {reservation.partner_id.name}\nUnité: {reservation.unit_id.name}\n💰 Prix: {reservation.total_price}€",
            'location': reservation.unit_id.name,
            'allday': False,
            'privacy': 'public',
            'show_as': 'busy',
        })

        # Lier l'événement à la réservation
        reservation.calendar_event_id = event.id
        return reservation

    # Mise à jour automatique de l'événement si la réservation change
    def write(self, vals):
        res = super().write(vals)
        for reservation in self:
            if reservation.calendar_event_id:
                reservation.calendar_event_id.sudo().write({
                    'name': f"{reservation.name} - {reservation.unit_id.name}",
                    'start': reservation.start_date,
                    'stop': reservation.end_date,
                    'description': f"Client: {reservation.partner_id.name}\nUnité: {reservation.unit_id.name}",
                    'location': reservation.unit_id.name,
                })
        return res

    # Suppression automatique de l'événement si la réservation est supprimée
    def unlink(self):
        for reservation in self:
            if reservation.calendar_event_id:
                reservation.calendar_event_id.sudo().unlink()
        return super().unlink()