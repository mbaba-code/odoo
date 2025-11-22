"""Wizard pour upload multiple de photos"""
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class OneDeskImageUploadWizard(models.TransientModel):
    """Wizard pour uploader plusieurs photos à la fois"""
    _name = 'onedesk.image.upload.wizard'
    _description = 'Wizard Upload Multiple Photos'

    # Type de document auquel ajouter les photos
    document_type = fields.Selection([
        ('property', 'Propriété'),
        ('unit', 'Unité'),
        ('reservation', 'Réservation'),
    ], string='Ajouter les photos à', required=True, default='property')

    # IDs des documents (on en utilise qu'un à la fois)
    property_id = fields.Many2one('onedesk.property', string='Propriété')
    unit_id = fields.Many2one('onedesk.unit', string='Unité')
    reservation_id = fields.Many2one('onedesk.reservation', string='Réservation')

    # Pour réservations: type de photos
    image_type = fields.Selection([
        ('check_in', 'Arrivée (Check-in)'),
        ('check_out', 'Départ (Check-out)'),
        ('damage', 'Dégâts/Problèmes'),
        ('other', 'Autre'),
    ], string='Type de photos', default='check_in',
        help="Uniquement pour les réservations")

    # Upload de plusieurs fichiers
    images = fields.Many2many(
        'ir.attachment',
        relation='onedesk_image_wizard_attachment_rel',
        string='Photos à uploader',
        help="Sélectionnez une ou plusieurs photos (JPG, PNG)"
    )

    # Note optionnelle pour toutes les photos
    note_prefix = fields.Char(
        string='Préfixe pour les titres',
        help="Ex: 'Chambre' → Les photos seront nommées 'Chambre 1', 'Chambre 2', etc.",
        placeholder="Optionnel: laisser vide = noms auto"
    )

    # Flag pour savoir si on doit afficher les sélecteurs (non renseignés dans le contexte)
    show_document_selector = fields.Boolean(
        default=True,
        help="Si False, cache les sélecteurs de document (fourni via contexte)"
    )

    @api.model
    def create(self, vals):
        """Auto-populate les champs basé sur le contexte"""
        # Vérifier le contexte pour l'ID du document
        context = self.env.context

        # Si on vient d'une propriété
        if context.get('default_property_id'):
            vals['property_id'] = context['default_property_id']
            vals['document_type'] = 'property'
            vals['show_document_selector'] = False

        # Si on vient d'une unité
        elif context.get('default_unit_id'):
            vals['unit_id'] = context['default_unit_id']
            vals['document_type'] = 'unit'
            vals['show_document_selector'] = False

        # Si on vient d'une réservation
        elif context.get('default_reservation_id'):
            vals['reservation_id'] = context['default_reservation_id']
            vals['document_type'] = 'reservation'
            vals['show_document_selector'] = False

        return super().create(vals)

    @api.onchange('document_type')
    def _onchange_document_type(self):
        """Réinitialiser les IDs quand le type change"""
        self.property_id = False
        self.unit_id = False
        self.reservation_id = False
        self.image_type = 'check_in'

    def action_upload_images(self):
        """Uploader toutes les photos sélectionnées"""
        self.ensure_one()

        if not self.images:
            raise ValueError('Sélectionnez au moins une photo!')

        # Compter les photos créées
        count = 0

        # Déterminer le document cible et le modèle
        if self.document_type == 'property':
            if not self.property_id:
                raise ValueError('Sélectionnez une propriété!')
            target_id = self.property_id.id
            model_name = 'onedesk.property.image'
            id_field = 'property_id'

        elif self.document_type == 'unit':
            if not self.unit_id:
                raise ValueError('Sélectionnez une unité!')
            target_id = self.unit_id.id
            model_name = 'onedesk.unit.image'
            id_field = 'unit_id'

        elif self.document_type == 'reservation':
            if not self.reservation_id:
                raise ValueError('Sélectionnez une réservation!')
            target_id = self.reservation_id.id
            model_name = 'onedesk.reservation.image'
            id_field = 'reservation_id'

        else:
            raise ValueError('Type de document invalide!')

        # Créer une image pour chaque fichier
        image_model = self.env[model_name]
        for idx, attachment in enumerate(self.images, 1):
            try:
                # Lire le contenu binaire de l'image depuis l'attachment
                image_data = attachment.datas

                # Générer le titre
                if self.note_prefix:
                    title = f"{self.note_prefix} {idx}"
                else:
                    title = attachment.name.split('.')[0]  # Nom sans extension

                # Créer les valeurs communes
                vals = {
                    id_field: target_id,
                    'name': title,
                    'image': image_data,
                    'sequence': idx * 10,  # 10, 20, 30, etc.
                }

                # Ajouter le type de photo pour les réservations
                if self.document_type == 'reservation':
                    vals['image_type'] = self.image_type

                # Créer l'image
                image_model.create(vals)
                count += 1
                _logger.info(f'✅ Photo créée: {title}')

            except Exception as e:
                _logger.error(f'❌ Erreur création photo {idx}: {str(e)}')

        # Afficher notification de succès
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': f'✅ {count} photo(s) uploadée(s)!',
                'message': f'{count} photo(s) ont été ajoutées avec succès.',
                'sticky': False,
            }
        }
