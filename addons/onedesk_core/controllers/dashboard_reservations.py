from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json


class ReservationsDashboardController(http.Controller):
    """API endpoints for Reservations Dashboard data and analytics"""

    # ==================== HELPER METHODS ====================
    def _get_date_range(self, period_type, date_from=None, date_to=None):
        """Calculate date range based on period_type"""
        today = datetime.now().date()

        if period_type == 'today':
            return today, today
        elif period_type == 'week':
            start = today - timedelta(days=today.weekday())
            return start, today
        elif period_type == 'month':
            start = today.replace(day=1)
            return start, today
        elif period_type == 'year':
            start = today.replace(month=1, day=1)
            return start, today
        elif period_type == 'custom' and date_from and date_to:
            return date_from, date_to

        return today, today

    def _get_accessible_companies(self, user):
        """Get companies accessible based on user role"""
        if user.has_group('onedesk_core.group_onedesk_master_admin') or user.has_group('onedesk_core.group_onedesk_support'):
            return request.env['res.company'].search([])
        return user.company_ids or user.company_id

    # ==================== OCCUPANCY ANALYTICS ====================
    @http.route('/onedesk/dashboard/reservations/occupancy-by-unit', type='json', auth='user')
    def occupancy_by_unit(self, period_type='month', date_from=None, date_to=None, limit=15, **kwargs):
        """Top units by occupancy rate"""
        try:
            user = request.env.user
            companies = self._get_accessible_companies(user)

            date_from, date_to = self._get_date_range(period_type, date_from, date_to)
            period_days = (date_to - date_from).days + 1

            # Get all units
            units = request.env['onedesk.unit'].search([('company_id', 'in', companies.ids)])

            # Calculate occupancy per unit
            unit_occupancy = {}
            for unit in units:
                # Get reservations for this unit
                reservations = request.env['onedesk.reservation'].search([
                    ('unit_id', '=', unit.id),
                    ('start_date', '<=', date_to),
                    ('end_date', '>=', date_from),
                    ('status', '!=', 'cancelled'),
                    ('active', '=', True)
                ])

                total_nights = sum(reservations.mapped('number_of_nights'))
                possible_nights = period_days
                occupancy = (total_nights / possible_nights * 100) if possible_nights > 0 else 0.0

                unit_occupancy[unit.id] = {
                    'name': unit.name,
                    'property': unit.property_id.name if unit.property_id else 'N/A',
                    'occupancy': occupancy,
                    'nights_booked': int(total_nights),
                    'capacity': possible_nights
                }

            # Sort by occupancy and limit
            sorted_units = sorted(unit_occupancy.items(), key=lambda x: x[1]['occupancy'], reverse=True)[:limit]

            labels = [unit[1]['name'] for unit in sorted_units]
            occupancies = [round(unit[1]['occupancy'], 2) for unit in sorted_units]

            return {
                'status': 'success',
                'labels': labels,
                'occupancies': occupancies,
                'period': period_type
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/onedesk/dashboard/reservations/status-distribution', type='json', auth='user')
    def status_distribution(self, period_type='month', date_from=None, date_to=None, **kwargs):
        """Distribution of reservations by status"""
        try:
            user = request.env.user
            companies = self._get_accessible_companies(user)

            date_from, date_to = self._get_date_range(period_type, date_from, date_to)

            # Get all reservations
            reservations = request.env['onedesk.reservation'].search([
                ('company_id', 'in', companies.ids),
                ('start_date', '<=', date_to),
                ('end_date', '>=', date_from),
                ('active', '=', True)
            ])

            # Count by status
            status_counts = {}
            for res in reservations:
                status = res.status or 'unknown'
                status_counts[status] = status_counts.get(status, 0) + 1

            labels = list(status_counts.keys())
            data = list(status_counts.values())

            return {
                'status': 'success',
                'labels': labels,
                'data': data,
                'period': period_type
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/onedesk/dashboard/reservations/booking-trend', type='json', auth='user')
    def booking_trend(self, period_type='month', date_from=None, date_to=None, **kwargs):
        """Reservation volume trend over time"""
        try:
            user = request.env.user
            companies = self._get_accessible_companies(user)

            date_from, date_to = self._get_date_range(period_type, date_from, date_to)

            # Get reservations
            reservations = request.env['onedesk.reservation'].search([
                ('company_id', 'in', companies.ids),
                ('start_date', '<=', date_to),
                ('end_date', '>=', date_from),
                ('active', '=', True)
            ])

            # Group by start date (week)
            booking_by_week = {}
            for res in reservations:
                week_start = res.start_date - timedelta(days=res.start_date.weekday())
                week_key = str(week_start)
                if week_key not in booking_by_week:
                    booking_by_week[week_key] = 0
                booking_by_week[week_key] += 1

            labels = sorted(booking_by_week.keys())
            data = [booking_by_week[label] for label in labels]

            return {
                'status': 'success',
                'labels': labels,
                'data': data,
                'period': period_type
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/onedesk/dashboard/reservations/cancellation-rate', type='json', auth='user')
    def cancellation_rate(self, period_type='month', date_from=None, date_to=None, **kwargs):
        """Cancellation rate and comparison"""
        try:
            user = request.env.user
            companies = self._get_accessible_companies(user)

            date_from, date_to = self._get_date_range(period_type, date_from, date_to)

            # Current period
            reservations = request.env['onedesk.reservation'].search([
                ('company_id', 'in', companies.ids),
                ('start_date', '<=', date_to),
                ('end_date', '>=', date_from),
                ('active', '=', True)
            ])

            total = len(reservations)
            cancelled = len(reservations.filtered(lambda r: r.status == 'cancelled'))
            cancellation_rate = (cancelled / total * 100) if total > 0 else 0.0

            return {
                'status': 'success',
                'total': total,
                'cancelled': cancelled,
                'cancellation_rate': round(cancellation_rate, 2),
                'period': period_type
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
