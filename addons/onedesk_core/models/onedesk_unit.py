from odoo import models, fields, api
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

class OnedeskUnit(models.Model):
    _name = 'onedesk.unit'
    _description = 'Unité de propriété'

    # ========== MULTI-TENANT ==========
    company_id = fields.Many2one(
        'res.company',
        string="Entreprise",
        compute='_compute_company_id',
        store=True,
        help="Entreprise (héritée de la propriété)"
    )

    # ========== ARCHIVE ==========
    active = fields.Boolean(default=True)

    name = fields.Char(string="Nom de l'unité", required=True)
    property_id = fields.Many2one('onedesk.property', string="Propriété", required=True)

    # ========== INTEGRATION ==========
    external_listing_id = fields.Char(string="ID Listing Externe",
                                      help="ID du listing sur la plateforme externe (Airbnb, Booking, VRBO, iCal)")
    integration_id = fields.Many2one('onedesk.integration', string="Intégration source",
                                    help="L'intégration d'où vient ce listing")

    # Tarification flexible
    price_per_night = fields.Float(string="Prix par nuit (défaut)", required=True, default=100.0)
    seasonal_price_ids = fields.One2many('onedesk.seasonal_price', 'unit_id', string='Tarifs saisonniers')

    available = fields.Boolean(string="Disponible", default=True)

    # ========== UNIT FEATURES ==========
    capacity = fields.Integer(string="Capacité (nombre de personnes)", default=2,
                             help="Nombre maximum de personnes que l'unité peut accueillir")
    bedrooms = fields.Integer(string="Nombre de chambres", default=1)
    bathrooms = fields.Integer(string="Nombre de salles de bain", default=1)

    # ========== POLICIES ==========
    minimum_stay = fields.Integer(string="Séjour minimum (nuits)", default=1,
                                 help="Nombre minimum de nuits requises pour réserver")
    cancellation_policy = fields.Selection([
        ('flexible', 'Flexible - Annulation gratuite jusqu\'à 48h avant'),
        ('moderate', 'Modérée - 50% remboursé si annulation 7 jours avant'),
        ('strict', 'Strict - Aucun remboursement sauf cas exceptionnel'),
        ('non_refundable', 'Non remboursable'),
    ], string='Politique d\'annulation', default='moderate',
    help="Politique d'annulation pour cette unité")

    # ========== CLEANING & MAINTENANCE ==========
    cleaning_required = fields.Boolean(string="Nettoyage requis", default=True,
                                      help="Le nettoyage est-il obligatoire entre les réservations?")
    cleaning_fee = fields.Float(string="Frais de nettoyage (€)", default=0.0)
    cleaning_duration_hours = fields.Float(string="Durée nettoyage (heures)", default=2.0,
                                          help="Temps estimé pour nettoyer l'unité")
    maintenance_mode = fields.Boolean(string="En maintenance", default=False,
                                     help="Marquer cette unité comme étant en maintenance (non disponible pour les réservations)")
    maintenance_notes = fields.Text(string="Notes d'entretien",
                                   help="Problèmes connus, maintenance récente, etc.")

    # ========== IMAGES ==========
    main_image = fields.Image(string="Photo principale", max_width=1024, max_height=1024)
    image_ids = fields.One2many('onedesk.unit.image', 'unit_id', string='Galerie de photos',
                               help="Galerie complète de photos de l'unité")

    # Computed field: Get cover image from gallery if available
    cover_image = fields.Image(string="Photo de couverture (Galerie)", max_width=1024, max_height=1024,
                              compute='_compute_cover_image', readonly=True,
                              help="Photo marquée comme couverture dans la galerie")
    # Computed field: ID of cover image (for kanban use)
    cover_image_id = fields.Integer(compute='_compute_cover_image_id', readonly=True,
                                    help="ID de la photo de couverture pour les vues kanban")

    # ========== DASHBOARD FIELDS ==========
    reservation_ids = fields.One2many('onedesk.reservation', 'unit_id', string='Réservations')

    # Statistics
    revenue_this_month = fields.Float(string='💰 Revenus ce mois',
                                      compute='_compute_revenue_this_month',
                                      store=False)
    revenue_this_year = fields.Float(string='💰 Revenus cette année',
                                     compute='_compute_revenue_this_year',
                                     store=False)
    occupancy_percentage = fields.Float(string='📈 Occupation %',
                                       compute='_compute_occupancy_percentage',
                                       store=False)
    upcoming_reservations_count = fields.Integer(string='📅 Prochaines réservations (7j)',
                                                compute='_compute_upcoming_reservations_count',
                                                store=False)

    @api.depends('property_id', 'property_id.company_id')
    def _compute_company_id(self):
        """Hériter company_id de la propriété"""
        for record in self:
            record.company_id = record.property_id.company_id if record.property_id else False

    @api.depends('image_ids', 'image_ids.is_cover', 'image_ids.image')
    def _compute_cover_image(self):
        """Get cover image from gallery if marked, otherwise use first image"""
        for record in self:
            # Look for image marked as cover
            cover_img = record.image_ids.filtered(lambda x: x.is_cover)
            if cover_img:
                # Use the cover image's image field
                record.cover_image = cover_img[0].image
            elif record.image_ids:
                # Fall back to first image if no cover marked
                record.cover_image = record.image_ids[0].image
            else:
                # No images in gallery, use main_image field if set
                record.cover_image = record.main_image

    @api.depends('image_ids', 'image_ids.is_cover')
    def _compute_cover_image_id(self):
        """Get ID of cover image for kanban"""
        for record in self:
            # Look for image marked as cover
            cover_img = record.image_ids.filtered(lambda x: x.is_cover)
            if cover_img:
                record.cover_image_id = cover_img[0].id
            elif record.image_ids:
                # Fall back to first image if no cover marked
                record.cover_image_id = record.image_ids[0].id
            else:
                record.cover_image_id = False

    @api.depends('reservation_ids', 'reservation_ids.total_price', 'reservation_ids.payment_status')
    def _compute_revenue_this_month(self):
        """Calcule le revenu du mois en cours (réservations PAYÉES)"""
        today = date.today()
        month_start = today.replace(day=1)
        month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

        for unit in self:
            revenue = 0.0
            for reservation in unit.reservation_ids:
                # Considère payée ou si la réservation a lieu ce mois
                if reservation.payment_status == 'completed':
                    # Vérifie que la réservation chevauche ce mois
                    if reservation.start_date and reservation.end_date:
                        res_start = reservation.start_date.date() if hasattr(reservation.start_date, 'date') else reservation.start_date
                        res_end = reservation.end_date.date() if hasattr(reservation.end_date, 'date') else reservation.end_date

                        if res_start <= month_end and res_end >= month_start:
                            revenue += reservation.total_price

            unit.revenue_this_month = revenue

    @api.depends('reservation_ids', 'reservation_ids.total_price', 'reservation_ids.payment_status')
    def _compute_revenue_this_year(self):
        """Calcule le revenu de l'année en cours (réservations PAYÉES)"""
        today = date.today()
        year_start = today.replace(month=1, day=1)
        year_end = today.replace(month=12, day=31)

        for unit in self:
            revenue = 0.0
            for reservation in unit.reservation_ids:
                if reservation.payment_status == 'completed':
                    if reservation.start_date and reservation.end_date:
                        res_start = reservation.start_date.date() if hasattr(reservation.start_date, 'date') else reservation.start_date
                        res_end = reservation.end_date.date() if hasattr(reservation.end_date, 'date') else reservation.end_date

                        if res_start <= year_end and res_end >= year_start:
                            revenue += reservation.total_price

            unit.revenue_this_year = revenue

    @api.depends('reservation_ids', 'reservation_ids.start_date', 'reservation_ids.end_date')
    def _compute_occupancy_percentage(self):
        """Calcule le % d'occupation du mois en cours"""
        today = date.today()
        month_start = today.replace(day=1)
        month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

        days_in_month = (month_end - month_start).days + 1

        for unit in self:
            occupied_days = 0
            for reservation in unit.reservation_ids:
                if reservation.start_date and reservation.end_date:
                    res_start = reservation.start_date.date() if hasattr(reservation.start_date, 'date') else reservation.start_date
                    res_end = reservation.end_date.date() if hasattr(reservation.end_date, 'date') else reservation.end_date

                    # Chevauchement avec le mois en cours
                    overlap_start = max(res_start, month_start)
                    overlap_end = min(res_end, month_end)

                    if overlap_start < overlap_end:
                        occupied_days += (overlap_end - overlap_start).days

            occupancy = (occupied_days / days_in_month * 100) if days_in_month > 0 else 0
            unit.occupancy_percentage = min(100.0, occupancy)  # Max 100%

    @api.depends('reservation_ids', 'reservation_ids.start_date')
    def _compute_upcoming_reservations_count(self):
        """Compte les réservations dans les 7 prochains jours"""
        today = date.today()
        next_week = today + timedelta(days=7)

        for unit in self:
            count = 0
            for reservation in unit.reservation_ids:
                if reservation.start_date:
                    res_start = reservation.start_date.date() if hasattr(reservation.start_date, 'date') else reservation.start_date
                    if today <= res_start <= next_week:
                        count += 1

            unit.upcoming_reservations_count = count

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

    @api.model
    def create(self, vals_list):
        """Pré-remplir company_id lors de la création"""
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        for vals in vals_list:
            # Si property_id est fourni, hériter company_id de la property
            if vals.get('property_id') and not vals.get('company_id'):
                property = self.env['onedesk.property'].browse(vals['property_id'])
                if property.company_id:
                    vals['company_id'] = property.company_id.id

        return super().create(vals_list)

    def get_total_price_for_dates(self, date_start, date_end):
        """Calcule le prix TOTAL pour une période"""
        nights = (date_end - date_start).days
        avg_price = self.get_price_for_dates(date_start, date_end)
        return avg_price * nights
