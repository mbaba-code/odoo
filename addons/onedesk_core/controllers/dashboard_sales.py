from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json


class SalesDashboardController(http.Controller):
    """API endpoints for Sales Dashboard data and analytics"""

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

    def _get_previous_period_range(self, date_from, date_to):
        """Get previous period date range with same length"""
        period_length = (date_to - date_from).days + 1
        prev_to = date_from - timedelta(days=1)
        prev_from = prev_to - timedelta(days=period_length - 1)
        return prev_from, prev_to

    def _get_accessible_companies(self, user):
        """Get companies accessible based on user role"""
        if user.has_group('onedesk_core.group_onedesk_master_admin') or user.has_group('onedesk_core.group_onedesk_support'):
            return request.env['res.company'].search([])
        return user.company_ids or user.company_id

    # ==================== REVENUE ANALYTICS ====================
    @http.route('/onedesk/dashboard/sales/revenue-trend', type='jsonrpc', auth='user')
    def revenue_trend(self, period_type='month', date_from=None, date_to=None, **kwargs):
        """Revenue trend data grouped by week or day"""
        try:
            user = request.env.user
            companies = self._get_accessible_companies(user)

            date_from, date_to = self._get_date_range(period_type, date_from, date_to)

            # Get reservations in period
            reservations = request.env['onedesk.reservation'].search([
                ('company_id', 'in', companies.ids),
                ('start_date', '<=', date_to),
                ('end_date', '>=', date_from),
                ('status', 'in', ['paid', 'checked_in', 'completed']),
                ('active', '=', True)
            ])

            # Group by week
            revenue_by_week = {}
            for res in reservations:
                week_start = res.start_date - timedelta(days=res.start_date.weekday())
                week_key = str(week_start)
                if week_key not in revenue_by_week:
                    revenue_by_week[week_key] = 0.0
                revenue_by_week[week_key] += res.total_price

            labels = sorted(revenue_by_week.keys())
            data = [revenue_by_week[label] for label in labels]

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

    @http.route('/onedesk/dashboard/sales/top-properties', type='jsonrpc', auth='user')
    def top_properties(self, period_type='month', date_from=None, date_to=None, limit=10, **kwargs):
        """Top properties by revenue"""
        try:
            user = request.env.user
            companies = self._get_accessible_companies(user)

            date_from, date_to = self._get_date_range(period_type, date_from, date_to)

            # Get reservations in period
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
                        property_revenues[prop_id] = {'name': prop_name, 'revenue': 0.0, 'count': 0}
                    property_revenues[prop_id]['revenue'] += res.total_price
                    property_revenues[prop_id]['count'] += 1

            # Sort and limit
            sorted_props = sorted(property_revenues.items(), key=lambda x: x[1]['revenue'], reverse=True)[:limit]

            labels = [prop[1]['name'] for prop in sorted_props]
            revenues = [prop[1]['revenue'] for prop in sorted_props]
            counts = [prop[1]['count'] for prop in sorted_props]

            return {
                'status': 'success',
                'labels': labels,
                'revenues': revenues,
                'counts': counts,
                'period': period_type
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/onedesk/dashboard/sales/period-comparison', type='jsonrpc', auth='user')
    def period_comparison(self, period_type='month', date_from=None, date_to=None, **kwargs):
        """Compare current period with previous period"""
        try:
            user = request.env.user
            companies = self._get_accessible_companies(user)

            date_from, date_to = self._get_date_range(period_type, date_from, date_to)
            prev_from, prev_to = self._get_previous_period_range(date_from, date_to)

            # Current period
            current_reservations = request.env['onedesk.reservation'].search([
                ('company_id', 'in', companies.ids),
                ('start_date', '<=', date_to),
                ('end_date', '>=', date_from),
                ('status', 'in', ['paid', 'checked_in', 'completed']),
                ('active', '=', True)
            ])

            current_revenue = sum(current_reservations.mapped('total_price'))
            current_count = len(current_reservations)
            current_avg = current_revenue / current_count if current_count > 0 else 0.0

            # Previous period
            previous_reservations = request.env['onedesk.reservation'].search([
                ('company_id', 'in', companies.ids),
                ('start_date', '<=', prev_to),
                ('end_date', '>=', prev_from),
                ('status', 'in', ['paid', 'checked_in', 'completed']),
                ('active', '=', True)
            ])

            previous_revenue = sum(previous_reservations.mapped('total_price'))
            previous_count = len(previous_reservations)
            previous_avg = previous_revenue / previous_count if previous_count > 0 else 0.0

            # Calculate growth rates
            revenue_growth = ((current_revenue - previous_revenue) / previous_revenue * 100) if previous_revenue > 0 else (100.0 if current_revenue > 0 else 0.0)
            count_growth = ((current_count - previous_count) / previous_count * 100) if previous_count > 0 else (100.0 if current_count > 0 else 0.0)

            return {
                'status': 'success',
                'current': {
                    'revenue': round(current_revenue, 2),
                    'count': current_count,
                    'average': round(current_avg, 2)
                },
                'previous': {
                    'revenue': round(previous_revenue, 2),
                    'count': previous_count,
                    'average': round(previous_avg, 2)
                },
                'growth': {
                    'revenue_percent': round(revenue_growth, 2),
                    'count_percent': round(count_growth, 2)
                },
                'period': period_type
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
