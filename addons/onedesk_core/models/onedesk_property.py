from odoo import models, fields, api

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
