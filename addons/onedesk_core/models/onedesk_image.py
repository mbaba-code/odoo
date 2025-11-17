from odoo import models, fields


class OnedeskoPropertyImage(models.Model):
    _name = 'onedesk.property.image'
    _description = 'Property Photo/Image'
    _order = 'sequence, id'

    property_id = fields.Many2one('onedesk.property', string="Propriété", required=True, ondelete='cascade')
    name = fields.Char(string="Titre de la photo", help="Ex: Vue d'ensemble, Chambre principale, Cuisine")
    image = fields.Image(string="Photo", attachment=True, required=True)
    is_cover = fields.Boolean(string="📌 Photo de couverture", default=False,
                             help="Marquez comme photo de couverture principale")
    sequence = fields.Integer(string="Ordre d'affichage", default=10, help="Plus bas = affiché en premier")

    def _compute_display_name(self):
        for record in self:
            prefix = "📌 " if record.is_cover else ""
            record.display_name = prefix + (record.name or f"Photo {record.sequence}")


class OnedeskoUnitImage(models.Model):
    _name = 'onedesk.unit.image'
    _description = 'Unit Photo/Image'
    _order = 'sequence, id'

    unit_id = fields.Many2one('onedesk.unit', string="Unité", required=True, ondelete='cascade')
    name = fields.Char(string="Titre de la photo", help="Ex: Chambre, Salle de bain, Salon")
    image = fields.Image(string="Photo", attachment=True, required=True)
    is_cover = fields.Boolean(string="📌 Photo de couverture", default=False,
                             help="Marquez comme photo de couverture principale")
    sequence = fields.Integer(string="Ordre d'affichage", default=10, help="Plus bas = affiché en premier")

    def _compute_display_name(self):
        for record in self:
            prefix = "📌 " if record.is_cover else ""
            record.display_name = prefix + (record.name or f"Photo {record.sequence}")


class OnedeskoReservationImage(models.Model):
    _name = 'onedesk.reservation.image'
    _description = 'Reservation Photo/Image (Check-in/Check-out documentation)'
    _order = 'sequence, id'

    reservation_id = fields.Many2one('onedesk.reservation', string="Réservation", required=True, ondelete='cascade')
    name = fields.Char(string="Titre de la photo", help="Ex: État du salon, Cuisine avant nettoyage")
    image = fields.Image(string="Photo", attachment=True, required=True)
    image_type = fields.Selection([
        ('check_in', 'Arrivée (Check-in)'),
        ('check_out', 'Départ (Check-out)'),
        ('damage', 'Dégâts/Problèmes'),
        ('other', 'Autre'),
    ], string="Type de photo", default='other')
    sequence = fields.Integer(string="Ordre d'affichage", default=10)

    def _compute_display_name(self):
        for record in self:
            type_label = dict(record._fields['image_type'].selection).get(record.image_type, '')
            record.display_name = record.name or f"{type_label} - Photo {record.sequence}"
