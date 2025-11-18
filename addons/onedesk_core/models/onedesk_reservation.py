from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.fields import Command
from datetime import datetime
from odoo.tools import format_datetime

class OneDeskReservation(models.Model):
    _name = 'onedesk.reservation'
    _description = 'Reservation'
    _inherit = ['mail.thread']

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

    # ========== STATUS WORKFLOW ==========
    status = fields.Selection([
        ('draft', 'Brouillon'),
        ('pending_payment', 'En attente paiement'),
        ('paid', 'Payée'),
        ('checked_in', 'Client arrivé'),
        ('completed', 'Terminée'),
        ('cancelled', 'Annulée'),
    ], string='Statut réservation', default='draft', tracking=True, readonly=False)

    # ========== PAIEMENT ==========
    payment_status = fields.Selection([
        ('pending', 'En attente'),
        ('completed', 'Payée'),
        ('cancelled', 'Annulée'),
    ], string='Statut paiement', default='pending', tracking=True)
    payment_link = fields.Char(string='Lien de paiement', copy=False,
                              help="Lien pour que le client paie cette réservation")

    # Invoice relation
    invoice_id = fields.Many2one('account.move', string='Facture générée',
                                copy=False, readonly=True,
                                help="Facture automatiquement générée après paiement")

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

    # ========== NOTES & REQUESTS ==========
    guest_notes = fields.Text(string='Notes du client',
                             help="Notes spéciales du client (allergies, préférences, etc.)")
    internal_notes = fields.Text(string='Notes internes',
                                help="Notes pour l'équipe (instructions nettoyage, problèmes connus, etc.)")
    special_requests = fields.Text(string='Demandes particulières',
                                  help="Demandes spéciales du client (lit bébé, chaise haute, etc.)")

    # ========== IMAGES & DOCUMENTS ==========
    image_ids = fields.One2many('onedesk.reservation.image', 'reservation_id', string='Galerie d\'inspection',
                               help="Galerie complète de photos d'inspection (check-in et check-out)")

    # Computed field: Get cover image from gallery if available
    cover_image = fields.Image(string="Photo de couverture (Galerie)", max_width=1024, max_height=1024,
                              compute='_compute_cover_image', readonly=True,
                              help="Photo marquée comme couverture dans la galerie")
    # Computed field: ID of cover image (for kanban use)
    cover_image_id = fields.Integer(compute='_compute_cover_image_id', readonly=True,
                                    help="ID de la photo de couverture pour les vues kanban")

    @api.depends('image_ids', 'image_ids.image')
    def _compute_cover_image(self):
        """Get cover image from gallery, use first image"""
        for record in self:
            if record.image_ids:
                record.cover_image = record.image_ids[0].image
            else:
                record.cover_image = False

    @api.depends('image_ids')
    def _compute_cover_image_id(self):
        """Get ID of cover image for kanban"""
        for record in self:
            if record.image_ids:
                record.cover_image_id = record.image_ids[0].id
            else:
                record.cover_image_id = False

    @api.constrains('unit_id', 'start_date', 'end_date', 'status')
    def _check_no_overlapping_reservations(self):
        """Vérifie qu'il n'y a pas de réservations qui se chevauchent sur la même unité"""
        for record in self:
            # Ignore les réservations annulées
            if record.status == 'cancelled':
                continue

            # Cherche les réservations qui se chevauchent
            overlapping = self.search([
                ('unit_id', '=', record.unit_id.id),
                ('status', '!=', 'cancelled'),
                ('id', '!=', record.id),
                ('start_date', '<', record.end_date),
                ('end_date', '>', record.start_date),
            ])

            if overlapping:
                raise ValidationError(
                    f"⚠️ Chevauchement de réservation détecté!\n"
                    f"L'unité {record.unit_id.name} est déjà réservée pour ces dates.\n"
                    f"Réservations en conflit: {', '.join(r.name for r in overlapping)}"
                )

    def check_availability_for_unit(self, unit_id, start_date, end_date):
        """
        Vérifie la disponibilité d'une unité pour une période donnée
        Args:
            unit_id: ID de l'unité à vérifier
            start_date: Date de début (datetime)
            end_date: Date de fin (datetime)
        Retourne: (available: bool, conflicting_reservations: list, error_message: str)
        """
        # Cherche les réservations qui se chevauchent pour cette unité
        overlapping = self.search([
            ('unit_id', '=', unit_id),
            ('status', '!=', 'cancelled'),
            ('start_date', '<', end_date),
            ('end_date', '>', start_date),
        ])

        if overlapping:
            # Formate les dates pour le message
            conflict_dates = []
            for res in overlapping:
                start_str = res.start_date.strftime('%d/%m/%Y')
                end_str = res.end_date.strftime('%d/%m/%Y')
                conflict_dates.append(f"{start_str} au {end_str}")

            error_msg = (
                f"Cette unité n'est pas disponible pour la période sélectionnée.\n"
                f"Périodes occupées:\n"
                + "\n".join(f"  • {date}" for date in conflict_dates)
            )

            return False, overlapping, error_msg

        return True, [], None

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
    def create(self, vals_list):
        # Calcule le prix automatiquement avant création pour chaque enregistrement
        for vals in vals_list:
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

        reservations = super().create(vals_list)

        # Traiter chaque réservation créée
        for reservation in reservations:
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

            # Envoie un email de confirmation automatiquement
            try:
                reservation._send_confirmation_email()
            except Exception as e:
                # Log l'erreur mais ne bloque pas la création
                reservation.message_post(
                    body=f"⚠️ Erreur lors de l'envoi de l'email de confirmation: {str(e)}",
                    message_type='comment'
                )

        return reservations

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
        ET envoie automatiquement l'email au client
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

        # Envoie l'email au client
        try:
            self._send_payment_link_email()
            email_notification = f"Email envoyé à {self.partner_id.email}"
        except Exception as e:
            email_notification = f"⚠️ Erreur envoi email: {str(e)}"

        # Retourne une notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Lien de paiement généré',
                'message': f'Lien généré pour {self.total_price}€. {email_notification}',
                'type': 'success',
                'sticky': False,
            }
        }

    def _send_confirmation_email(self):
        """
        Envoie un email de confirmation de réservation au client
        """
        self.ensure_one()

        # Vérifie que le client a un email
        if not self.partner_id.email:
            return False

        # Prépare le contenu de l'email
        subject = f"Confirmation de réservation - {self.name}"

        # Corps de l'email en HTML
        body_html = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Bonjour {self.partner_id.name},</h2>

            <p>Merci d'avoir choisi notre propriété! Votre réservation a bien été confirmée. Veuillez trouver les détails ci-dessous:</p>

            <h3>📋 Détails de votre réservation:</h3>
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f9f9f9;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Référence:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{self.name}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Propriété:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{self.unit_id.property_id.name if self.unit_id.property_id else 'N/A'}</td>
                </tr>
                <tr style="background-color: #f9f9f9;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Unité:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{self.unit_id.name}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>📅 Date d'arrivée:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>{self.start_date.strftime('%d/%m/%Y à %H:%M')}</strong></td>
                </tr>
                <tr style="background-color: #f9f9f9;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>📅 Date de départ:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>{self.end_date.strftime('%d/%m/%Y à %H:%M')}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>🌙 Nombre de nuits:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{self.number_of_nights}</td>
                </tr>
                <tr style="background-color: #f0f0f0;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>💰 Prix total:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd; font-size: 18px; font-weight: bold; color: #28a745;">{self.total_price}€</td>
                </tr>
            </table>

            <h3>🏠 Informations sur la propriété:</h3>
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Adresse:</strong> {self.unit_id.property_id.address if self.unit_id.property_id else 'N/A'}</p>
                <p><strong>Capacité:</strong> {self.unit_id.capacity} personnes</p>
                <p><strong>Chambres:</strong> {self.unit_id.bedrooms} | <strong>Salles de bain:</strong> {self.unit_id.bathrooms}</p>
                <p><strong>Équipements:</strong> {self.unit_id.property_id.amenities or 'Voir la liste complète sur notre site'}</p>
            </div>

            <h3>📝 Prochaines étapes:</h3>
            <ol style="margin: 20px 0;">
                <li><strong>Paiement:</strong> Un lien de paiement vous sera envoyé sous peu. Veuillez finaliser le paiement avant votre arrivée.</li>
                <li><strong>Instructions d'accès:</strong> Vous recevrez les instructions d'accès 24 heures avant votre arrivée.</li>
                <li><strong>Contact:</strong> En cas de question, contactez-nous à {self.env.company.email or 'support@example.com'}</li>
            </ol>

            <p style="color: #666; font-size: 12px; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 15px;">
                Bon séjour!<br/>
                L'équipe de {self.env.company.name}
            </p>
        </div>
        """

        # Crée et envoie l'email
        mail_values = {
            'subject': subject,
            'body_html': body_html,
            'email_to': self.partner_id.email,
            'email_from': self.env.company.email or self.env.user.email,
        }

        mail = self.env['mail.mail'].create(mail_values)
        mail.send()

        # Log l'action
        self.message_post(
            body=f"📧 Email de confirmation envoyé à {self.partner_id.email}",
            message_type='comment'
        )

        return True

    def _send_payment_link_email(self):
        """
        Envoie le lien de paiement par email au client
        """
        self.ensure_one()

        # Vérifie que le client a un email
        if not self.partner_id.email:
            raise ValueError(f"Le client {self.partner_id.name} n'a pas d'adresse email")

        # Prépare le contenu de l'email
        subject = f"Lien de paiement - Réservation {self.name}"

        # Corps de l'email en HTML (simplifié pour MVP)
        body_html = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Bonjour {self.partner_id.name},</h2>

            <p>Nous vous remercions de votre réservation! Veuillez finaliser votre paiement en cliquant sur le lien ci-dessous:</p>

            <div style="margin: 20px 0;">
                <a href="{self.payment_link}" style="background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                    💳 Payer maintenant
                </a>
            </div>

            <h3>Détails de votre réservation:</h3>
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f9f9f9;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Unité:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{self.unit_id.name}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Arrivée:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{self.start_date.strftime('%d/%m/%Y')}</td>
                </tr>
                <tr style="background-color: #f9f9f9;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Départ:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{self.end_date.strftime('%d/%m/%Y')}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Nombre de nuits:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{self.number_of_nights}</td>
                </tr>
                <tr style="background-color: #f0f0f0;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Montant à payer:</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd; font-size: 18px; font-weight: bold; color: #28a745;">{self.total_price}€</td>
                </tr>
            </table>

            <p style="color: #666; font-size: 12px;">
                Si vous avez des questions, n'hésitez pas à nous contacter.
            </p>

            <p style="color: #666;">
                Cordialement,<br/>
                <strong>{self.env.company.name}</strong>
            </p>
        </div>
        """

        # Crée et envoie l'email
        mail_values = {
            'subject': subject,
            'body_html': body_html,
            'email_to': self.partner_id.email,
            'email_from': self.env.company.email or self.env.user.email,
        }

        mail = self.env['mail.mail'].create(mail_values)
        mail.send()

        # Log l'action
        self.message_post(
            body=f"📧 Email de paiement envoyé à {self.partner_id.email}",
            message_type='comment'
        )

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
            # Passe automatiquement au statut "paid"
            self.status = 'paid'

            # Génère automatiquement la facture
            try:
                self._generate_invoice()
            except Exception as e:
                self.message_post(
                    body=f"⚠️ Erreur lors de la génération de la facture: {str(e)}",
                    message_type='comment'
                )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Paiement confirmé',
                    'message': f'Montant payé: {self.amount_paid}€ - Facture générée',
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

    # ========== STATE TRANSITIONS ==========

    def action_confirm(self):
        """Passe de draft à pending_payment et envoie la demande de paiement"""
        self.ensure_one()
        if self.status != 'draft':
            raise ValidationError("Seules les réservations en brouillon peuvent être confirmées")

        self.status = 'pending_payment'
        self.message_post(body="✅ Réservation confirmée - En attente de paiement")

        # Génère automatiquement le lien de paiement
        return self.action_generate_payment_link()

    def action_mark_checked_in(self):
        """Marque la réservation comme client arrivé"""
        self.ensure_one()
        if self.status != 'paid':
            raise ValidationError("Seules les réservations payées peuvent être marquées comme 'Client arrivé'")

        self.status = 'checked_in'
        self.message_post(body="🔑 Client arrivé à la propriété")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Check-in effectué',
                'message': f'Client {self.partner_id.name} arrivé à {self.unit_id.name}',
                'type': 'success',
            }
        }

    def action_mark_completed(self):
        """Marque la réservation comme terminée"""
        self.ensure_one()
        if self.status not in ('checked_in', 'paid'):
            raise ValidationError("Seules les réservations payées ou en cours peuvent être complétées")

        self.status = 'completed'
        self.message_post(body="✔️ Séjour terminé - Merci pour votre visite!")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Réservation complétée',
                'message': 'Le séjour est maintenant terminé.',
                'type': 'success',
            }
        }

    def action_cancel(self):
        """Annule la réservation"""
        self.ensure_one()
        if self.status == 'completed':
            raise ValidationError("Impossible d'annuler une réservation complétée")

        self.status = 'cancelled'
        self.message_post(body="❌ Réservation annulée")

        # Supprime les tâches associées
        self.env['onedesk.task'].search([
            ('reservation_id', '=', self.id)
        ]).unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Réservation annulée',
                'message': 'La réservation et ses tâches ont été supprimées.',
                'type': 'warning',
            }
        }

    # ========== INVOICING ==========

    def _generate_invoice(self):
        """
        Génère automatiquement une facture (account.move) pour la réservation payée
        Appelée quand le statut passe à 'paid'
        """
        self.ensure_one()

        # Vérifie que le modèle account.move existe (require l'app Accounting)
        if not self.env['ir.model'].search([('model', '=', 'account.move')]):
            self.message_post(
                body="⚠️ Module Accounting non installé - Impossible de générer la facture",
                message_type='comment'
            )
            return None

        # Crée les lignes de facture
        invoice_lines = []

        # Ligne 1: Nuitées
        invoice_lines.append((0, 0, {
            'name': f"Séjour à {self.unit_id.name} - {self.number_of_nights} nuit(s)",
            'quantity': self.number_of_nights,
            'price_unit': self.price_per_night,
            'product_id': False,  # Pas de produit spécifique, utilise 'service' par défaut
            'account_id': self.env.company.expense_accrual_account_id.id or self.env['account.account'].search([('code', '=', '701000')], limit=1).id,
        }))

        # Ligne 2: Frais de nettoyage (si applicable)
        if self.unit_id.cleaning_fee > 0:
            invoice_lines.append((0, 0, {
                'name': f"Frais de nettoyage - {self.unit_id.name}",
                'quantity': 1,
                'price_unit': self.unit_id.cleaning_fee,
                'product_id': False,
                'account_id': self.env.company.expense_accrual_account_id.id or self.env['account.account'].search([('code', '=', '701000')], limit=1).id,
            }))

        # Prépare les valeurs de la facture
        invoice_vals = {
            'move_type': 'out_invoice',  # Facture client
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.today(),
            'ref': self.name,  # Référence de la réservation
            'narration': f"Facture pour la réservation {self.name}\nUnité: {self.unit_id.name}\nPériode: {self.start_date.strftime('%d/%m/%Y')} - {self.end_date.strftime('%d/%m/%Y')}",
            'invoice_line_ids': invoice_lines,
            'company_id': self.env.company.id,
        }

        try:
            # Crée la facture
            invoice = self.env['account.move'].create(invoice_vals)

            # Stocker la référence de la facture
            self.invoice_id = invoice.id

            # Log l'action
            self.message_post(
                body=f"📄 Facture générée: <a href='#' class='o_field_widget o_readonly' title='{invoice.name}'>{invoice.name}</a>",
                message_type='comment'
            )

            return invoice

        except Exception as e:
            # Log l'erreur mais ne bloque pas le workflow
            self.message_post(
                body=f"⚠️ Erreur lors de la génération de la facture: {str(e)}",
                message_type='comment'
            )
            return None

    def _auto_generate_invoice_on_payment(self):
        """
        Appelée automatiquement quand le paiement est confirmé
        Génère la facture si elle n'existe pas déjà
        """
        self.ensure_one()

        # Vérifie qu'on a un modèle invoice_id (à ajouter)
        if not hasattr(self, 'invoice_id'):
            return

        # Crée la facture si elle n'existe pas
        if not self.invoice_id and self.total_price > 0:
            self._generate_invoice()

    def send_confirmation_email(self):
        """Envoie un email de confirmation de réservation au client"""
        self.ensure_one()

        # Données pour l'email
        email_subject = f"Confirmation de réservation - {self.name}"

        # Format des dates
        start_date_str = self.start_date.strftime('%d %B %Y')
        end_date_str = self.end_date.strftime('%d %B %Y')

        # Body de l'email en HTML
        email_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2>Confirmation de votre réservation</h2>

                <p>Chère(e) {self.partner_id.name},</p>

                <p>Merci de votre réservation ! Voici les détails de votre séjour :</p>

                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Numéro de réservation :</strong> {self.name}</p>
                    <p><strong>Unité :</strong> {self.unit_id.name}</p>
                    <p><strong>Propriété :</strong> {self.unit_id.property_id.name if self.unit_id.property_id else 'N/A'}</p>

                    <hr style="border: none; border-top: 1px solid #ddd; margin: 15px 0;">

                    <p><strong>Dates de séjour :</strong></p>
                    <p>Arrivée : {start_date_str}</p>
                    <p>Départ : {end_date_str}</p>
                    <p><strong>Nombre de nuits :</strong> {self.number_of_nights}</p>

                    <hr style="border: none; border-top: 1px solid #ddd; margin: 15px 0;">

                    <p><strong>Tarification :</strong></p>
                    <p>Prix par nuit : {self.price_per_night:.2f}€</p>
                    <p>Sous-total : {self.total_price:.2f}€</p>
                </div>

                <p>Votre réservation est actuellement en <strong>attente de confirmation</strong>.</p>

                <p style="color: #666; font-size: 12px; margin-top: 30px;">
                    <strong>Questions ou modifications ?</strong><br>
                    N'hésitez pas à nous contacter pour toute question concernant votre réservation.
                </p>

                <p style="color: #666; font-size: 12px;">
                    Cordialement,<br>
                    L'équipe OneDesk
                </p>
            </body>
        </html>
        """

        try:
            # Envoie l'email
            self.env['mail.mail'].create({
                'subject': email_subject,
                'email_from': self.env.user.company_id.email or self.env['ir.config_parameter'].sudo().get_param('mail.default_from'),
                'email_to': self.partner_id.email,
                'body_html': email_body,
                'model': self._name,
                'res_id': self.id,
            }).send()

            # Log l'action
            self.message_post(
                body=f"✉️ Email de confirmation envoyé à {self.partner_id.email}",
                message_type='comment'
            )

            return True

        except Exception as e:
            # Log l'erreur
            self.message_post(
                body=f"⚠️ Erreur lors de l'envoi de l'email: {str(e)}",
                message_type='comment'
            )
            return False