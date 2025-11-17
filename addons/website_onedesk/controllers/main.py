from odoo import http
from odoo.http import request
from datetime import datetime, timedelta


class OneDeskWebsite(http.Controller):

    # ==================== TEST ROUTE ====================

    @http.route('/onedesk/test', type='http', auth='public')
    def test_route(self, **kw):
        """Route de test simple"""
        return "✅ OneDesk Website module est actif!"

    # ==================== PAGES PUBLIQUES ====================

    @http.route('/onedesk/properties', type='http', auth='public', website=True)
    def properties_list(self, **kw):
        """Page de listing de toutes les propriétés"""
        properties = request.env['onedesk.property'].search([])

        # Aussi récupère les unités "orphelines" (sans propriété) qui viennent des intégrations
        orphaned_units = request.env['onedesk.unit'].search([
            ('property_id', '=', False),
            ('external_listing_id', '!=', False)  # Seulement les importées
        ])

        return request.render('website_onedesk.properties_list', {
            'properties': properties,
            'orphaned_units': orphaned_units,
            'page_title': 'Nos propriétés',
        })

    @http.route('/onedesk/property/<model("onedesk.property"):property_id>', type='http', auth='public', website=True)
    def property_detail(self, property_id, **kw):
        """Page de détail d'une propriété"""
        units = property_id.unit_ids

        # Calcul des stats
        total_revenue = sum(units.mapped('revenue_this_month'))
        avg_occupancy = sum(units.mapped('occupancy_percentage')) / len(units) if units else 0

        return request.render('website_onedesk.property_detail', {
            'property': property_id,
            'units': units,
            'total_revenue': total_revenue,
            'avg_occupancy': avg_occupancy,
        })

    @http.route('/onedesk/unit/<model("onedesk.unit"):unit_id>', type='http', auth='public', website=True)
    def unit_detail(self, unit_id, **kw):
        """Page de détail d'une unité (chambre/appartement)"""
        # Récupère les réservations confirmées pour afficher le calendrier
        reservations = request.env['onedesk.reservation'].search([
            ('unit_id', '=', unit_id.id),
            ('status', '!=', 'cancelled'),
        ])

        return request.render('website_onedesk.unit_detail', {
            'unit': unit_id,
            'property': unit_id.property_id,
            'reservations': reservations,
        })

    # ==================== AJAX / FORMULAIRES ====================

    @http.route('/onedesk/booking', type='json', auth='public', website=True, methods=['POST'])
    def create_booking_request(self, **kw):
        """Crée une demande de réservation (lead/contact)"""
        try:
            # Extrait les données du JSON body
            data = request.jsonrequest or {}

            # Valide les données requises
            required_fields = ['name', 'email', 'unit_id', 'start_date', 'end_date']
            for field in required_fields:
                if not data.get(field):
                    return {
                        'status': 'error',
                        'message': f'Le champ "{field}" est requis.',
                    }

            # Crée un partner si nécessaire
            partner = request.env['res.partner'].search([
                ('email', '=', data.get('email'))
            ], limit=1)

            if not partner:
                partner = request.env['res.partner'].create({
                    'name': data.get('name'),
                    'email': data.get('email'),
                    'phone': data.get('phone', ''),
                })

            # Crée une réservation en brouillon
            unit_id = int(data.get('unit_id'))
            start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date().isoformat()
            end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date().isoformat()

            reservation = request.env['onedesk.reservation'].create({
                'unit_id': unit_id,
                'partner_id': partner.id,
                'start_date': start_date,
                'end_date': end_date,
                'guest_notes': data.get('message', ''),
                'status': 'draft',  # En attente de confirmation
            })

            return {
                'status': 'success',
                'message': f'Demande de réservation créée! Vous allez recevoir un email de confirmation.',
                'reservation_id': reservation.id,
            }

        except ValueError as e:
            return {
                'status': 'error',
                'message': f'Erreur de format: {str(e)}',
            }
        except Exception as e:
            import traceback
            _logger = __import__('logging').getLogger(__name__)
            _logger.exception('Erreur lors de la création de réservation')
            return {
                'status': 'error',
                'message': f'Erreur serveur: {str(e) or "Erreur inconnue"}',
            }

    @http.route('/onedesk/unit/<model("onedesk.unit"):unit_id>/availability', type='json', auth='public', website=True, methods=['POST'])
    def check_availability(self, unit_id, **kw):
        """Vérifie la disponibilité d'une unité pour une période"""
        try:
            # Extrait les données du JSON body
            data = request.jsonrequest or {}
            start_date = data.get('start_date')
            end_date = data.get('end_date')

            if not start_date or not end_date:
                return {
                    'available': False,
                    'message': 'Les dates de début et fin sont requises.',
                }

            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()

            # Cherche les réservations qui se chevauchent
            overlapping = request.env['onedesk.reservation'].search([
                ('unit_id', '=', unit_id.id),
                ('status', '!=', 'cancelled'),
                ('start_date', '<', end.isoformat()),
                ('end_date', '>', start.isoformat()),
            ])

            if overlapping:
                return {
                    'available': False,
                    'message': 'Malheureusement, cette période n\'est pas disponible.',
                }

            # Calcule le prix
            nights = (end - start).days
            avg_price = unit_id.get_price_for_dates(start, end)
            total_price = avg_price * nights

            return {
                'available': True,
                'nights': nights,
                'price_per_night': avg_price,
                'total_price': total_price,
                'cleaning_fee': unit_id.cleaning_fee,
                'total_with_cleaning': total_price + unit_id.cleaning_fee,
            }

        except Exception as e:
            return {
                'available': False,
                'message': f'Erreur: {str(e)}',
            }
