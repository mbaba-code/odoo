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

            # Valide les données requises
            required_fields = ['name', 'email', 'unit_id', 'start_date', 'end_date']
            for field in required_fields:
                if not data.get(field):
                    return {
                        'status': 'error',
                        'message': f'Le champ "{field}" est requis.',
                    }

            # IMPORTANT: Vérifie la disponibilité AVANT de créer la réservation
            unit_id = int(data.get('unit_id'))
            unit = request.env['onedesk.unit'].browse(unit_id)

            if not unit.exists():
                return {
                    'status': 'error',
                    'message': 'Cette unité n\'existe pas.',
                }

            start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()

            # Convertir en datetime pour la comparaison
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())

            # Cherche les réservations qui se chevauchent
            conflicting = request.env['onedesk.reservation'].search([
                ('unit_id', '=', unit_id),
                ('status', '!=', 'cancelled'),
                ('start_date', '<', end_datetime),
                ('end_date', '>', start_datetime),
            ])

            if conflicting:
                # Formate le message d'erreur avec les périodes occupées
                conflict_dates = []
                for res in conflicting:
                    start_str = res.start_date.strftime('%d/%m/%Y')
                    end_str = res.end_date.strftime('%d/%m/%Y')
                    conflict_dates.append(f"{start_str} au {end_str}")

                error_msg = (
                    f"❌ Cette unité n'est pas disponible pour la période sélectionnée.\n\n"
                    f"Périodes occupées:\n"
                    + "\n".join(f"  • {date}" for date in conflict_dates)
                    + f"\n\nVeuillez choisir une autre période."
                )
                _logger.warning(f'Période indisponible pour unité {unit.name}: {error_msg}')
                return {
                    'status': 'error',
                    'message': error_msg,
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

            # Crée la réservation en brouillon
            reservation = request.env['onedesk.reservation'].create({
                'unit_id': unit_id,
                'partner_id': partner.id,
                'start_date': start_datetime.isoformat(),
                'end_date': end_datetime.isoformat(),
                'guest_notes': data.get('message', ''),
                'status': 'draft',  # En attente de confirmation
            })

            return {
                'status': 'success',
                'message': f'✅ Réservation confirmée!\n\nUn email de confirmation a été envoyé à {partner.email}.\n\nNuméro de réservation: {reservation.name}',
                'reservation_id': reservation.id,
            }

        except ValueError as e:
            error_str = str(e)
            _logger.warning(f'Erreur de format dans booking: {error_str}')
            return {
                'status': 'error',
                'message': f'Format de date invalide. Veuillez utiliser le format YYYY-MM-DD.',
            }
        except ValidationError as e:
            # Erreur de validation (ex: chevauchement de réservation)
            error_msg = str(e).replace('<class \'odoo.exceptions.ValidationError\'>', '').strip()
            _logger.warning(f'Erreur de validation booking: {error_msg}')
            return {
                'status': 'error',
                'message': error_msg or 'Cette réservation n\'est pas possible. Veuillez vérifier les dates.',
            }
        except Exception as e:
            _logger.exception('Erreur lors de la création de réservation')
            error_msg = str(e) if str(e) else 'Une erreur inconnue s\'est produite'
            return {
                'status': 'error',
                'message': error_msg,
            }

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
