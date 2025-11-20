from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class OnedeskProperty(models.Model):
    _name = 'onedesk.property'
    _description = 'Propriété OneDesk'
    _inherit = ['mail.thread']

    # ========== MULTI-TENANT ==========
    company_id = fields.Many2one(
        'res.company',
        string="Entreprise",
        required=True,
        default=lambda self: self.env.company,
        ondelete='cascade',
        help="Entreprise propriétaire de cette propriété"
    )

    # ========== ARCHIVE ==========
    active = fields.Boolean(default=True)

    # ========== BASIC INFO ==========
    name = fields.Char(string="Nom de la propriété", required=True, tracking=True)
    address = fields.Char(string="Adresse", required=True)
    description = fields.Text(string="Description",
                             help="Description complète de la propriété (équipements, localisation, etc.)")

    # ========== PROPERTY TYPE & CATEGORY ==========
    property_type = fields.Selection([
        ('house', 'Maison'),
        ('apartment', 'Appartement'),
        ('villa', 'Villa'),
        ('studio', 'Studio'),
        ('cottage', 'Chalet'),
        ('townhouse', 'Maison de ville'),
        ('other', 'Autre'),
    ], string='Type de propriété', default='house', required=True, tracking=True)

    # ========== CONTACT INFO ==========
    owner_name = fields.Char(string="Nom du propriétaire")
    owner_phone = fields.Char(string="Téléphone du propriétaire")
    owner_email = fields.Char(string="Email du propriétaire")

    # ========== AMENITIES ==========
    amenities = fields.Text(string="Équipements et services",
                           help="Liste des équipements disponibles (WiFi, Piscine, Parking, etc.)")

    # ========== IMAGES ==========
    main_image = fields.Image(string="Photo principale", max_width=1024, max_height=1024,
                             help="Photo de couverture de la propriété (max 1024x1024)")
    image_ids = fields.One2many('onedesk.property.image', 'property_id', string='Galerie de photos',
                               help="Galerie complète de photos de la propriété")

    # Computed field: Get cover image from gallery if available
    cover_image = fields.Image(string="Photo de couverture (Galerie)", max_width=1024, max_height=1024,
                              compute='_compute_cover_image', readonly=True,
                              help="Photo marquée comme couverture dans la galerie")
    # Computed field: ID of cover image (for kanban use)
    cover_image_id = fields.Integer(compute='_compute_cover_image_id', readonly=True,
                                    help="ID de la photo de couverture pour les vues kanban")

    # ========== CALENDAR FIELDS (required for calendar view) ==========
    date_start = fields.Date(string="Date de début")
    date_stop = fields.Date(string="Date de fin")

    # ========== RELATIONS ==========
    user_id = fields.Many2one('res.users', string="Responsable",
                             default=lambda self: self.env.user, tracking=True)
    unit_ids = fields.One2many('onedesk.unit', 'property_id', string='Unités')

    # ========== CREATE METHOD WITH LIMIT CHECKING ==========
    @api.model
    def create(self, vals):
        """Créer une propriété avec vérification des limites du plan"""
        property = super().create(vals)

        # Vérifier les limites du plan d'abonnement
        company_id = vals.get('company_id') or self.env.company.id
        subscription = self.env['onedesk.subscription'].search([
            ('company_id', '=', company_id),
            ('state', '=', 'active')
        ], limit=1)

        if subscription:
            try:
                # Recompute current usage to get actual counts
                subscription._compute_current_usage()
                subscription._check_limits()
            except Exception as e:
                _logger.warning(f'Limit check failed for subscription {subscription.id}: {str(e)}')

        return property

    # ========== COMPUTED FIELDS ==========
    total_units = fields.Integer(string='Nombre d\'unités',
                                compute='_compute_total_units', store=True)
    total_revenue_month = fields.Float(string='Revenu ce mois',
                                      compute='_compute_total_revenue_month')
    total_occupancy_percentage = fields.Float(string='Taux d\'occupation',
                                             compute='_compute_total_occupancy_percentage')

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

    @api.depends('unit_ids')
    def _compute_total_units(self):
        """Compte le nombre total d'unités dans la propriété"""
        for record in self:
            record.total_units = len(record.unit_ids)

    def _compute_total_revenue_month(self):
        """Calcule le revenu total du mois pour toutes les unités"""
        for record in self:
            record.total_revenue_month = sum(
                record.unit_ids.mapped('revenue_this_month')
            )

    def _compute_total_occupancy_percentage(self):
        """Calcule le taux d'occupation moyen pour la propriété"""
        for record in self:
            if not record.unit_ids:
                record.total_occupancy_percentage = 0
            else:
                avg_occupancy = sum(
                    record.unit_ids.mapped('occupancy_percentage')
                ) / len(record.unit_ids)
                record.total_occupancy_percentage = avg_occupancy


    # ==================== PROPERTY PERFORMANCE METRICS ====================
    @api.model
    def get_property_ranking(self, limit=10, order_by='revenue'):
        """Get properties ranked by performance"""
        properties = self.env['onedesk.property'].search([], order='create_date desc')

        ranking_data = []
        for prop in properties:
            units = self.env['onedesk.unit'].search([('property_id', '=', prop.id)])
            
            # Revenue this month
            today = datetime.now()
            month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_revenue = sum(self.env['onedesk.reservation'].search([
                ('unit_id', 'in', units.ids),
                ('status', '=', 'completed'),
                ('end_date', '>=', month_start)
            ]).mapped('total_price'))

            # Occupancy rate
            occupied_units = 0
            for unit in units:
                if self.env['onedesk.reservation'].search_count([
                    ('unit_id', '=', unit.id),
                    ('status', 'in', ['confirmed', 'checked_in']),
                    ('start_date', '<=', today.date()),
                    ('end_date', '>=', today.date())
                ]):
                    occupied_units += 1
            
            occupancy_rate = (occupied_units / len(units) * 100) if units else 0

            # Total reservations
            total_reservations = self.env['onedesk.reservation'].search_count([
                ('unit_id', 'in', units.ids),
                ('status', 'in', ['confirmed', 'checked_in', 'completed'])
            ])

            ranking_data.append({
                'id': prop.id,
                'name': prop.name,
                'revenue_month': month_revenue,
                'occupancy_rate': occupancy_rate,
                'total_reservations': total_reservations,
                'active_units': len(units.filtered('active')),
                'total_units': len(units),
            })

        # Sort by order_by parameter
        if order_by == 'revenue':
            ranking_data.sort(key=lambda x: x['revenue_month'], reverse=True)
        elif order_by == 'occupancy':
            ranking_data.sort(key=lambda x: x['occupancy_rate'], reverse=True)
        elif order_by == 'reservations':
            ranking_data.sort(key=lambda x: x['total_reservations'], reverse=True)

        return ranking_data[:limit]
