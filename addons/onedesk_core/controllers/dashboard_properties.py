from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json


class PropertiesDashboardController(http.Controller):
    """API endpoints for Properties Dashboard data and analytics"""

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

    # ==================== PROPERTY RANKING ====================
    @http.route('/onedesk/dashboard/properties/ranking', type='jsonrpc', auth='user')
    def property_ranking(self, period_type='month', date_from=None, date_to=None, order_by='revenue', limit=15, **kwargs):
        """Property ranking by revenue, occupancy, or reservations"""
        try:
            user = request.env.user
            companies = self._get_accessible_companies(user)

            date_from, date_to = self._get_date_range(period_type, date_from, date_to)
            period_days = (date_to - date_from).days + 1

            # Get all properties
            properties = request.env['onedesk.property'].search([
                ('company_id', 'in', companies.ids),
                ('active', '=', True)
            ])

            property_data = {}
            for prop in properties:
                # Get units for this property
                units = request.env['onedesk.unit'].search([('property_id', '=', prop.id)])

                # Get reservations for this property
                reservations = request.env['onedesk.reservation'].search([
                    ('company_id', 'in', companies.ids),
                    ('unit_id', 'in', units.ids),
                    ('start_date', '<=', date_to),
                    ('end_date', '>=', date_from),
                    ('status', 'in', ['paid', 'checked_in', 'completed']),
                    ('active', '=', True)
                ])

                total_revenue = sum(reservations.mapped('total_price'))
                total_nights = sum(reservations.mapped('number_of_nights'))
                possible_nights = len(units) * period_days
                occupancy = (total_nights / possible_nights * 100) if possible_nights > 0 else 0.0

                property_data[prop.id] = {
                    'name': prop.name,
                    'revenue': round(total_revenue, 2),
                    'occupancy': round(occupancy, 2),
                    'reservations': len(reservations),
                    'active_units': len(units),
                    'total_units': len(units)
                }

            # Sort by requested order
            if order_by == 'revenue':
                sorted_props = sorted(property_data.items(), key=lambda x: x[1]['revenue'], reverse=True)
            elif order_by == 'occupancy':
                sorted_props = sorted(property_data.items(), key=lambda x: x[1]['occupancy'], reverse=True)
            elif order_by == 'reservations':
                sorted_props = sorted(property_data.items(), key=lambda x: x[1]['reservations'], reverse=True)
            else:
                sorted_props = sorted(property_data.items(), key=lambda x: x[1]['revenue'], reverse=True)

            sorted_props = sorted_props[:limit]

            labels = [prop[1]['name'] for prop in sorted_props]
            revenues = [prop[1]['revenue'] for prop in sorted_props]
            occupancies = [prop[1]['occupancy'] for prop in sorted_props]

            return {
                'status': 'success',
                'labels': labels,
                'revenues': revenues,
                'occupancies': occupancies,
                'order_by': order_by,
                'period': period_type
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/onedesk/dashboard/properties/revenue-by-property', type='jsonrpc', auth='user')
    def revenue_by_property(self, period_type='month', date_from=None, date_to=None, limit=10, **kwargs):
        """Revenue distributed by property"""
        try:
            user = request.env.user
            companies = self._get_accessible_companies(user)

            date_from, date_to = self._get_date_range(period_type, date_from, date_to)

            # Get reservations
            reservations = request.env['onedesk.reservation'].search([
                ('company_id', 'in', companies.ids),
                ('start_date', '<=', date_to),
                ('end_date', '>=', date_from),
                ('status', 'in', ['paid', 'checked_in', 'completed']),
                ('active', '=', True)
            ])

            # Group by property
            property_revenues = {}
            for res in reservations:
                if res.unit_id and res.unit_id.property_id:
                    prop_id = res.unit_id.property_id.id
                    prop_name = res.unit_id.property_id.name
                    if prop_id not in property_revenues:
                        property_revenues[prop_id] = {'name': prop_name, 'revenue': 0.0}
                    property_revenues[prop_id]['revenue'] += res.total_price

            # Sort and limit
            sorted_props = sorted(property_revenues.items(), key=lambda x: x[1]['revenue'], reverse=True)[:limit]

            labels = [prop[1]['name'] for prop in sorted_props]
            data = [prop[1]['revenue'] for prop in sorted_props]

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

    @http.route('/onedesk/dashboard/properties/portfolio-status', type='jsonrpc', auth='user')
    def portfolio_status(self, **kwargs):
        """Portfolio status: active, inactive, maintenance"""
        try:
            user = request.env.user
            companies = self._get_accessible_companies(user)

            # Active properties
            active = len(request.env['onedesk.property'].search([
                ('company_id', 'in', companies.ids),
                ('active', '=', True)
            ]))

            # Inactive properties
            inactive = len(request.env['onedesk.property'].search([
                ('company_id', 'in', companies.ids),
                ('active', '=', False)
            ]))

            # Maintenance units
            maintenance_units = request.env['onedesk.unit'].search([
                ('company_id', 'in', companies.ids),
                ('maintenance_mode', '=', True)
            ])
            maintenance = len(set(maintenance_units.mapped('property_id.id')))

            return {
                'status': 'success',
                'active': active,
                'inactive': inactive,
                'maintenance': maintenance,
                'total': active + inactive
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
