from odoo import models, fields, api
from odoo.fields import Command
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

    # Override prix manuel
    override_price_per_night = fields.Float(string='Prix par nuit (override)',
                                           help="Laissez vide pour utiliser le prix calculé automatiquement")
    override_reason = fields.Char(string='Raison de l\'override',
                                 help="Ex: Remise client, Prix spécial, Correction erreur, etc.")

    # ========== PAIEMENT ==========
    payment_status = fields.Selection([
        ('pending', 'En attente'),
        ('completed', 'Payée'),
        ('cancelled', 'Annulée'),
    ], string='Statut paiement', default='pending', tracking=True)
    payment_link = fields.Char(string='Lien de paiement', copy=False,
                              help="Lien pour que le client paie cette réservation")

    # Link to payment transactions (NEW - pour Odoo payment module)
    transaction_ids = fields.Many2many(
        'payment.transaction',
        relation='onedesk_reservation_payment_transaction_rel',
        column1='reservation_id',
        column2='transaction_id',
        readonly=True,
        copy=False,
        help="Transactions de paiement liées à cette réservation"
    )

    # Amount paid (computed)
    amount_paid = fields.Float(
        string='Montant payé',
        compute='_compute_amount_paid',
        store=False
    )

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

    @api.depends('price_per_night', 'number_of_nights', 'override_price_per_night')
    def _compute_total_price(self):
        """Calcule le prix total (utilise override si rempli)"""
        for record in self:
            # Utilise override_price_per_night si rempli, sinon prix calculé
            price_to_use = record.override_price_per_night or record.price_per_night
            record.total_price = price_to_use * record.number_of_nights

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

    # ========== PAIEMENT METHODS (Odoo Payment Module) ==========

    def _compute_amount_paid(self):
        """Calcule le montant déjà payé via les transactions de paiement"""
        for record in self:
            record.amount_paid = sum(
                record.transaction_ids.filtered(
                    lambda tx: tx.state in ('authorized', 'done')
                ).mapped('amount')
            )

    def _get_default_payment_link_values(self):
        """
        MÉTHODE REQUISE par payment.link.wizard
        Retourne les valeurs par défaut pour le lien de paiement
        """
        self.ensure_one()
        return {
            'currency_id': self.env.company.currency_id.id,
            'partner_id': self.partner_id.id,
            'amount': self.total_price,
            'amount_max': self.total_price,
        }

    def get_base_url(self):
        """
        MÉTHODE REQUISE par payment.link.wizard
        Retourne l'URL de base pour cette réservation
        """
        return self.env.company.get_base_url()

    def action_generate_payment_link(self):
        """
        Génère un lien de paiement pour cette réservation
        Appelé depuis le bouton dans la vue
        """
        self.ensure_one()

        # Crée un wizard payment link
        wizard = self.env['payment.link.wizard'].with_context(
            active_id=self.id,
            active_model=self._name
        ).create({
            'amount': self.total_price,
            'res_model': self._name,
            'res_id': self.id,
        })

        # Sauvegarde le lien de paiement
        self.payment_link = wizard.link

        # Retourne une notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Lien de paiement généré',
                'message': f'Lien généré pour {self.total_price}€. Partagez-le avec le client!',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_check_payment_status(self):
        """
        Vérifie si le paiement a été complété
        Met à jour payment_status selon l'état de la transaction
        """
        self.ensure_one()

        # Cherche les transactions confirmées
        confirmed_transactions = self.transaction_ids.filtered(
            lambda tx: tx.state in ('authorized', 'done')
        )

        if confirmed_transactions:
            # Paiement réussi
            self.payment_status = 'completed'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Paiement confirmé',
                    'message': f'Montant payé: {self.amount_paid}€',
                    'type': 'success',
                }
            }
        elif self.transaction_ids.filtered(lambda tx: tx.state == 'cancel'):
            # Paiement annulé
            self.payment_status = 'cancelled'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Paiement annulé',
                    'message': 'Le paiement a été annulé.',
                    'type': 'danger',
                }
            }
        else:
            # Toujours en attente
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Statut du paiement',
                    'message': 'Le paiement est toujours en attente.',
                    'type': 'warning',
                }
            }