from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class OneDeskWebsite(http.Controller):

    # ==================== TEST ROUTE ====================

    @http.route('/onedesk/test', type='http', auth='public')
    def test_route(self, **kw):
        """Route de test simple"""
        return "✅ OneDesk Website module est actif!"

    @http.route('/onedesk/booking-test', type='json', auth='public', website=True, methods=['POST'])
    def test_booking(self, **kw):
        """Route de test pour JSON"""
        _logger.info('Test booking route called!')
        return {
            'status': 'success',
            'message': '✅ Test - La route /onedesk/booking fonctionne!'
        }

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

    @http.route('/onedesk/booking', type='http', auth='public', website=True, methods=['POST'], csrf=False)
    def create_booking_request(self, **kw):
        """Crée une demande de réservation (lead/contact)"""
        _logger.info('===== START create_booking_request =====')
        _logger.info(f'Request method: {request.httprequest.method}')
        _logger.info(f'Has jsonrequest: {hasattr(request, "jsonrequest")}')
        _logger.info(f'jsonrequest value: {request.jsonrequest if hasattr(request, "jsonrequest") else "N/A"}')
        _logger.info(f'Raw data: {request.httprequest.data}')

        try:
            # Extrait les données du JSON body de manière robuste
            data = {}
            if hasattr(request, 'jsonrequest') and request.jsonrequest:
                _logger.info('Using request.jsonrequest')
                data = request.jsonrequest
            else:
                # Fallback: parse le JSON manuellement du body
                _logger.info('Using manual JSON parsing')
                if request.httprequest.data:
                    try:
                        data = json.loads(request.httprequest.data.decode('utf-8'))
                        _logger.info(f'Manual parse success: {data}')
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        _logger.error(f"Erreur parsing JSON: {e}")
                        data = {}

            _logger.info(f'Data extracted: {data}')

            # Valide les données requises
            required_fields = ['name', 'email', 'unit_id', 'start_date', 'end_date']
            for field in required_fields:
                if not data.get(field):
                    response = {
                        'status': 'error',
                        'message': f'Le champ "{field}" est requis.',
                    }
                    _logger.info(f'Returning response: {response}')
                    return http.Response(json.dumps(response), content_type='application/json')

            # IMPORTANT: Vérifie la disponibilité AVANT de créer la réservation
            unit_id = int(data.get('unit_id'))
            unit = request.env['onedesk.unit'].browse(unit_id)

            if not unit.exists():
                response = {
                    'status': 'error',
                    'message': 'Cette unité n\'existe pas.',
                }
                _logger.info(f'Returning response: {response}')
                return http.Response(json.dumps(response), content_type='application/json')

            start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()

            # Convertir en datetime pour la comparaison
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())

            _logger.info(f'Booking request: unit={unit_id}, start={start_datetime}, end={end_datetime}')

            # Cherche les réservations qui se chevauchent
            conflicting = request.env['onedesk.reservation'].search([
                ('unit_id', '=', unit_id),
                ('status', '!=', 'cancelled'),
                ('start_date', '<', end_datetime),
                ('end_date', '>', start_datetime),
            ])

            _logger.info(f'Conflicting reservations found: {len(conflicting)}')

            if conflicting:
                # Formate le message d'erreur avec les périodes occupées
                conflict_dates = []
                for res in conflicting:
                    start_str = res.start_date.strftime('%d/%m/%Y')
                    end_str = res.end_date.strftime('%d/%m/%Y')
                    conflict_dates.append(f"{start_str} au {end_str}")

                error_msg = (
                    f"{unit.name}: ❌ Cette unité n'est pas disponible pour la période sélectionnée.\n\n"
                    f"Périodes occupées:\n"
                    + "\n".join(f"  • {date}" for date in conflict_dates)
                    + f"\n\nVeuillez choisir une autre période."
                )
                _logger.warning(f'Période indisponible pour unité {unit.name}')
                response = {
                    'status': 'error',
                    'message': error_msg,
                }
                _logger.info(f'Returning conflict response: {response}')
                return http.Response(json.dumps(response), content_type='application/json')

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
                _logger.info(f'Created partner: {partner.id}')

            # Crée la réservation en brouillon
            _logger.info(f'Creating reservation with start={start_datetime.isoformat()}, end={end_datetime.isoformat()}')

            reservation = request.env['onedesk.reservation'].create({
                'unit_id': unit_id,
                'partner_id': partner.id,
                'start_date': start_date.isoformat(),  # Envoyer juste la date, pas la datetime
                'end_date': end_date.isoformat(),      # Envoyer juste la date, pas la datetime
                'guest_notes': data.get('message', ''),
                'status': 'draft',  # En attente de confirmation
            })

            _logger.info(f'Reservation created successfully: {reservation.name}')

            response = {
                'status': 'success',
                'message': f'✅ Réservation confirmée!\n\nUn email de confirmation a été envoyé à {partner.email}.\n\nNuméro de réservation: {reservation.name}',
                'reservation_id': reservation.id,
            }
            _logger.info(f'Returning success response: {response}')
            return http.Response(json.dumps(response), content_type='application/json')

        except ValueError as e:
            error_str = str(e)
            _logger.error(f'ValueError during booking: {error_str}')
            response = {
                'status': 'error',
                'message': f'Format de date invalide. Veuillez utiliser le format YYYY-MM-DD.',
            }
            return http.Response(json.dumps(response), content_type='application/json')

        except ValidationError as e:
            # Erreur de validation (ex: chevauchement de réservation)
            error_msg = str(e).replace('<class \'odoo.exceptions.ValidationError\'>', '').strip()
            _logger.error(f'ValidationError during booking: {error_msg}')
            response = {
                'status': 'error',
                'message': error_msg or 'Cette réservation n\'est pas possible. Veuillez vérifier les dates.',
            }
            return http.Response(json.dumps(response), content_type='application/json')

        except Exception as e:
            error_msg = str(e) if str(e) else 'Une erreur inconnue s\'est produite'
            _logger.exception(f'Unexpected error during booking: {error_msg}')
            _logger.error(f'Exception type: {type(e).__name__}')
            response = {
                'status': 'error',
                'message': error_msg,
            }
            _logger.error(f'Returning error response: {response}')
            return http.Response(json.dumps(response), content_type='application/json')

    @http.route('/onedesk/unit/<model("onedesk.unit"):unit_id>/availability', type='json', auth='public', website=True, methods=['POST'])
    def check_availability(self, unit_id, **kw):
        """Vérifie la disponibilité d'une unité pour une période"""
        try:
            # Extrait les données du JSON body de manière robuste
            data = {}
            if hasattr(request, 'jsonrequest') and request.jsonrequest:
                data = request.jsonrequest
            else:
                # Fallback: parse le JSON manuellement du body
                if request.httprequest.data:
                    try:
                        data = json.loads(request.httprequest.data.decode('utf-8'))
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        _logger.warning(f"Erreur parsing JSON: {e}")
                        data = {}

            start_date = data.get('start_date')
            end_date = data.get('end_date')

            if not start_date or not end_date:
                return {
                    'available': False,
                    'message': 'Les dates de début et fin sont requises.',
                }

            # Convertir les dates en datetime objects (avec min/max time pour les comparaisons)
            start_dt = datetime.combine(
                datetime.strptime(start_date, '%Y-%m-%d').date(),
                datetime.min.time()
            )
            end_dt = datetime.combine(
                datetime.strptime(end_date, '%Y-%m-%d').date(),
                datetime.max.time()
            )

            # Cherche les réservations qui se chevauchent
            overlapping = request.env['onedesk.reservation'].search([
                ('unit_id', '=', unit_id.id),
                ('status', '!=', 'cancelled'),
                ('start_date', '<', end_dt),
                ('end_date', '>', start_dt),
            ])

            if overlapping:
                # Formate le message avec les périodes occupées
                conflict_dates = []
                for res in overlapping:
                    start_str = res.start_date.strftime('%d/%m/%Y')
                    end_str = res.end_date.strftime('%d/%m/%Y')
                    conflict_dates.append(f"{start_str} au {end_str}")

                error_msg = (
                    f"{unit_id.name}: ❌ Cette unité n'est pas disponible pour la période sélectionnée.\n\n"
                    f"Périodes occupées:\n"
                    + "\n".join(f"  • {date}" for date in conflict_dates)
                    + f"\n\nVeuillez choisir une autre période."
                )
                return {
                    'available': False,
                    'message': error_msg,
                }

            # Calcule le prix
            nights = (end_dt.date() - start_dt.date()).days
            avg_price = unit_id.get_price_for_dates(start_dt.date(), end_dt.date())
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
            _logger.exception('Erreur lors de la vérification de disponibilité')
            return {
                'available': False,
                'message': f'Erreur: {str(e)}',
            }
