"""
Contrôleur pour les réservations publiques (utilisateurs anonymes)
Permet aux visiteurs du site de créer des réservations sans authentification
"""

import json
from datetime import datetime
from odoo import http, fields
from odoo.http import request


class PublicReservationController(http.Controller):
    """
    Contrôleur public pour la création de réservations
    Accessible sans authentification - utilise sudo() pour contourner les permissions
    """

    @http.route('/onedesk/public/reservation/form', type='http', auth='public', csrf=False)
    def reservation_form(self, **kwargs):
        """Afficher le formulaire public de réservation"""
        # Récupérer les propriétés et unités disponibles (public)
        Unit = request.env['onedesk.unit'].sudo()
        units = Unit.search([('active', '=', True)])

        return request.render('onedesk_core.public_reservation_form_template', {
            'units': units,
        })

    @http.route('/onedesk/public/reservation/create', type='json', auth='public', csrf=False)
    def create_reservation(self, **data):
        """
        Créer une réservation publique
        POST data:
        {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'email': 'jean@example.com',
            'phone': '+33612345678',
            'unit_id': 5,
            'start_date': '2024-12-20',
            'end_date': '2024-12-25',
            'guest_notes': 'Notes additionnelles...'
        }
        """
        try:
            # Valider les données
            self._validate_reservation_data(data)

            # Créer ou récupérer le contact
            partner = self._get_or_create_partner(data)

            # Créer la réservation
            reservation = self._create_reservation(partner, data)

            # Envoyer l'email de confirmation
            self._send_confirmation_email(partner, reservation)

            return {
                'status': 'success',
                'message': 'Réservation créée avec succès! Un email de confirmation a été envoyé.',
                'reservation_id': reservation.id,
                'reservation_ref': reservation.name,
                'redirect_url': f'/onedesk/public/reservation/confirm/{reservation.id}',
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
            }

    @http.route('/onedesk/public/reservation/confirm/<int:reservation_id>', type='http', auth='public')
    def reservation_confirm(self, reservation_id, **kwargs):
        """Page de confirmation de réservation"""
        Reservation = request.env['onedesk.reservation'].sudo()
        reservation = Reservation.browse(reservation_id)

        if not reservation.exists():
            return request.render('onedesk_core.reservation_not_found_template', {
                'message': 'Réservation non trouvée',
            })

        return request.render('onedesk_core.public_reservation_confirm_template', {
            'reservation': reservation,
            'unit': reservation.unit_id,
            'partner': reservation.partner_id,
        })

    @staticmethod
    def _validate_reservation_data(data):
        """Valider les données de réservation"""
        required_fields = ['first_name', 'last_name', 'email', 'unit_id', 'start_date', 'end_date']

        for field in required_fields:
            if not data.get(field):
                raise ValueError(f"Le champ '{field}' est requis")

        # Vérifier le format email
        if '@' not in data.get('email', ''):
            raise ValueError("Email invalide")

        # Vérifier les dates
        try:
            start = datetime.fromisoformat(data['start_date'])
            end = datetime.fromisoformat(data['end_date'])

            if start >= end:
                raise ValueError("La date de fin doit être après la date de début")

            if start < datetime.now():
                raise ValueError("Impossible de réserver dans le passé")

        except ValueError as e:
            raise ValueError(f"Format de date invalide: {str(e)}")

        # Vérifier que l'unité existe
        Unit = request.env['onedesk.unit'].sudo()
        unit = Unit.browse(int(data['unit_id']))

        if not unit.exists() or not unit.active:
            raise ValueError("L'unité sélectionnée n'existe pas ou est inactive")

    @staticmethod
    def _get_or_create_partner(data):
        """Créer ou récupérer le contact client"""
        Partner = request.env['res.partner'].sudo()

        # Chercher un contact avec le même email
        existing = Partner.search([('email', '=', data['email'])], limit=1)

        if existing:
            # Mettre à jour le contact existant
            existing.write({
                'name': f"{data['first_name']} {data['last_name']}",
                'phone': data.get('phone', ''),
            })
            return existing

        # Créer un nouveau contact
        partner = Partner.create({
            'name': f"{data['first_name']} {data['last_name']}",
            'email': data['email'],
            'phone': data.get('phone', ''),
            'type': 'contact',
        })

        return partner

    @staticmethod
    def _create_reservation(partner, data):
        """Créer la réservation"""
        Reservation = request.env['onedesk.reservation'].sudo()
        Unit = request.env['onedesk.unit'].sudo()

        unit = Unit.browse(int(data['unit_id']))

        # Parser les dates
        start_date = datetime.fromisoformat(data['start_date'])
        end_date = datetime.fromisoformat(data['end_date'])

        # Créer la réservation
        reservation = Reservation.create({
            'unit_id': unit.id,
            'partner_id': partner.id,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'pending_payment',  # Réservation publique commence en attente de paiement
            'guest_notes': data.get('guest_notes', ''),
        })

        return reservation

    @staticmethod
    def _send_confirmation_email(partner, reservation):
        """Envoyer un email de confirmation"""
        try:
            # Récupérer le template d'email
            email_template = request.env.ref('onedesk_core.email_template_reservation_confirm').sudo()

            if email_template:
                email_template.with_context(
                    reservation_id=reservation.id,
                    partner_email=partner.email
                ).send_mail(reservation.id, force_send=True)

        except Exception as e:
            # Log l'erreur mais ne pas bloquer le processus
            try:
                request.env['onedesk.system.log'].sudo().create({
                    'level': 'warning',
                    'module': 'public_reservation',
                    'message': f'Erreur lors de l\'envoi de l\'email de confirmation: {str(e)}',
                })
            except:
                pass

    @http.route('/onedesk/public/units/available', type='json', auth='public')
    def get_available_units(self, **kwargs):
        """API pour récupérer les unités disponibles"""
        Unit = request.env['onedesk.unit'].sudo()
        units = Unit.search([('active', '=', True)])

        return {
            'status': 'success',
            'units': [
                {
                    'id': unit.id,
                    'name': unit.name,
                    'property': unit.property_id.name,
                    'price': unit.nightly_price,
                }
                for unit in units
            ]
        }
