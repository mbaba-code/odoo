from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class OnedeskDashboardController(http.Controller):
    """Handle Dashboard API endpoints for charts and metrics"""

    def _get_date_range(self, dashboard_rec):
        """Get date range based on selected period"""
        today = datetime.now().date()
        period_type = dashboard_rec.period_type

        if period_type == 'today':
            date_from = today
            date_to = today
        elif period_type == 'week':
            date_from = today - timedelta(days=today.weekday())
            date_to = date_from + timedelta(days=6)
        elif period_type == 'month':
            date_from = today.replace(day=1)
            date_to = (date_from + relativedelta(months=1)) - timedelta(days=1)
        elif period_type == 'year':
            date_from = today.replace(month=1, day=1)
            date_to = today.replace(month=12, day=31)
        elif period_type == 'custom':
            date_from = dashboard_rec.date_from or today.replace(day=1)
            date_to = dashboard_rec.date_to or today
        else:
            date_from = today.replace(day=1)
            date_to = today

        return date_from, date_to

    @http.route('/onedesk/dashboard/revenue-chart', type='json', auth='user')
    def revenue_chart(self):
        """Get revenue data for chart"""
        dashboard = request.env['onedesk.dashboard'].search([
            ('user_id', '=', request.env.user.id),
            ('company_id', '=', request.env.company.id)
        ], limit=1)

        if not dashboard:
            return {'status': 'error', 'message': 'Dashboard not found'}

        date_from, date_to = self._get_date_range(dashboard)
        company_ids = dashboard._get_accessible_companies()

        # Get properties and units
        properties = request.env['onedesk.property'].search([('company_id', 'in', company_ids)])
        units = request.env['onedesk.unit'].search([('property_id', 'in', properties.ids)])

        # Get reservations for period
        reservations = request.env['onedesk.reservation'].search([
            ('unit_id', 'in', units.ids),
            ('status', '=', 'completed'),
            ('end_date', '>=', date_from),
            ('end_date', '<=', date_to)
        ])

        # Group by week depending on period
        labels = []
        revenues = []
        
        if dashboard.period_type == 'month':
            # By week
            current = date_from
            while current <= date_to:
                week_end = min(current + timedelta(days=6), date_to)
                week_revenue = sum(reservations.filtered(
                    lambda r: current <= r.end_date.date() <= week_end
                ).mapped('total_price'))
                labels.append(current.strftime('%m/%d'))
                revenues.append(week_revenue)
                current = week_end + timedelta(days=1)
        elif dashboard.period_type == 'year':
            # By month
            for month in range(1, 13):
                month_start = date_from.replace(month=month, day=1)
                if month < 12:
                    month_end = date_from.replace(month=month+1, day=1) - timedelta(days=1)
                else:
                    month_end = date_from.replace(month=12, day=31)
                
                month_revenue = sum(reservations.filtered(
                    lambda r: month_start <= r.end_date.date() <= month_end
                ).mapped('total_price'))
                labels.append(month_start.strftime('%b'))
                revenues.append(month_revenue)
        else:
            # By day
            current = date_from
            while current <= date_to:
                day_revenue = sum(reservations.filtered(
                    lambda r: r.end_date.date() == current
                ).mapped('total_price'))
                labels.append(current.strftime('%a'))
                revenues.append(day_revenue)
                current += timedelta(days=1)

        return {
            'status': 'success',
            'labels': labels,
            'data': revenues,
            'period': dashboard.period_type
        }

    @http.route('/onedesk/dashboard/occupancy-chart', type='json', auth='user')
    def occupancy_chart(self):
        """Get occupancy data by property"""
        dashboard = request.env['onedesk.dashboard'].search([
            ('user_id', '=', request.env.user.id),
            ('company_id', '=', request.env.company.id)
        ], limit=1)

        if not dashboard:
            return {'status': 'error', 'message': 'Dashboard not found'}

        date_from, date_to = self._get_date_range(dashboard)
        company_ids = dashboard._get_accessible_companies()

        # Get properties
        properties = request.env['onedesk.property'].search([('company_id', 'in', company_ids)])

        labels = []
        occupancy_rates = []

        for prop in properties[:10]:  # Top 10 properties
            units = request.env['onedesk.unit'].search([('property_id', '=', prop.id)])
            if not units:
                continue

            occupied = 0
            for unit in units:
                reservations_count = request.env['onedesk.reservation'].search_count([
                    ('unit_id', '=', unit.id),
                    ('status', 'in', ['confirmed', 'checked_in']),
                    ('start_date', '<=', date_to),
                    ('end_date', '>=', date_from)
                ])
                if reservations_count > 0:
                    occupied += 1

            rate = (occupied / len(units) * 100) if units else 0
            labels.append(prop.name)
            occupancy_rates.append(round(rate, 2))

        return {
            'status': 'success',
            'labels': labels,
            'data': occupancy_rates,
            'period': dashboard.period_type
        }

    @http.route('/onedesk/dashboard/reservations-chart', type='json', auth='user')
    def reservations_chart(self):
        """Get reservations data by status"""
        dashboard = request.env['onedesk.dashboard'].search([
            ('user_id', '=', request.env.user.id),
            ('company_id', '=', request.env.company.id)
        ], limit=1)

        if not dashboard:
            return {'status': 'error', 'message': 'Dashboard not found'}

        company_ids = dashboard._get_accessible_companies()
        properties = request.env['onedesk.property'].search([('company_id', 'in', company_ids)])
        units = request.env['onedesk.unit'].search([('property_id', 'in', properties.ids)])

        statuses = ['draft', 'confirmed', 'checked_in', 'completed', 'cancelled']
        labels = ['Pending', 'Confirmed', 'Checked In', 'Completed', 'Cancelled']
        data = []

        for status in statuses:
            count = request.env['onedesk.reservation'].search_count([
                ('unit_id', 'in', units.ids),
                ('status', '=', status)
            ])
            data.append(count)

        return {
            'status': 'success',
            'labels': labels,
            'data': data,
            'period': dashboard.period_type
        }

    @http.route('/onedesk/dashboard/properties-ranking', type='json', auth='user')
    def properties_ranking(self, order_by='revenue'):
        """Get property ranking by performance"""
        try:
            ranking = request.env['onedesk.property'].get_property_ranking(limit=10, order_by=order_by)
            return {
                'status': 'success',
                'data': ranking
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/onedesk/dashboard/user-activity', type='json', auth='user')
    def user_activity(self):
        """Get user activity and productivity metrics"""
        company_ids = request.env['onedesk.dashboard'].search([
            ('user_id', '=', request.env.user.id),
            ('company_id', '=', request.env.company.id)
        ], limit=1)._get_accessible_companies()

        today = datetime.now().date()
        month_start = datetime.now().replace(day=1).date()

        # Get all users with reservations in accessible companies
        all_users = request.env['res.users'].search([
            ('company_id', 'in', company_ids),
            ('active', '=', True)
        ])

        user_stats = []
        for user in all_users[:20]:  # Top 20 active users
            # Reservations created by user this month
            reservations_created = request.env['onedesk.reservation'].search_count([
                ('create_uid', '=', user.id),
                ('create_date', '>=', month_start)
            ])

            # Tasks created by user this month
            tasks_created = request.env['onedesk.task'].search_count([
                ('create_uid', '=', user.id),
                ('create_date', '>=', month_start)
            ])

            # Tasks completed by user this month
            tasks_completed = request.env['onedesk.task'].search_count([
                ('user_id', '=', user.id),
                ('status', '=', 'done'),
                ('write_date', '>=', month_start)
            ])

            if reservations_created > 0 or tasks_created > 0 or tasks_completed > 0:
                user_stats.append({
                    'user_id': user.id,
                    'user_name': user.name,
                    'reservations_created': reservations_created,
                    'tasks_created': tasks_created,
                    'tasks_completed': tasks_completed,
                    'productivity_score': (reservations_created * 10) + (tasks_created * 5) + (tasks_completed * 7)
                })

        # Sort by productivity score
        user_stats.sort(key=lambda x: x['productivity_score'], reverse=True)

        return {
            'status': 'success',
            'data': user_stats
        }

    @http.route('/onedesk/dashboard/period-comparison', type='json', auth='user')
    def period_comparison(self, metric='revenue'):
        """Compare current period with previous period"""
        dashboard = request.env['onedesk.dashboard'].search([
            ('user_id', '=', request.env.user.id),
            ('company_id', '=', request.env.company.id)
        ], limit=1)

        if not dashboard:
            return {'status': 'error', 'message': 'Dashboard not found'}

        date_from, date_to = self._get_date_range(dashboard)
        company_ids = dashboard._get_accessible_companies()
        properties = request.env['onedesk.property'].search([('company_id', 'in', company_ids)])
        units = request.env['onedesk.unit'].search([('property_id', 'in', properties.ids)])

        # Get previous period (same length as current period)
        period_length = (date_to - date_from).days + 1
        prev_date_to = date_from - timedelta(days=1)
        prev_date_from = prev_date_to - timedelta(days=period_length - 1)

        # Calculate current period metric
        if metric == 'revenue':
            current = sum(request.env['onedesk.reservation'].search([
                ('unit_id', 'in', units.ids),
                ('status', '=', 'completed'),
                ('end_date', '>=', date_from),
                ('end_date', '<=', date_to)
            ]).mapped('total_price'))

            previous = sum(request.env['onedesk.reservation'].search([
                ('unit_id', 'in', units.ids),
                ('status', '=', 'completed'),
                ('end_date', '>=', prev_date_from),
                ('end_date', '<=', prev_date_to)
            ]).mapped('total_price'))

        elif metric == 'reservations':
            current = request.env['onedesk.reservation'].search_count([
                ('unit_id', 'in', units.ids),
                ('status', 'in', ['confirmed', 'checked_in', 'completed']),
                ('start_date', '>=', date_from),
                ('start_date', '<=', date_to)
            ])

            previous = request.env['onedesk.reservation'].search_count([
                ('unit_id', 'in', units.ids),
                ('status', 'in', ['confirmed', 'checked_in', 'completed']),
                ('start_date', '>=', prev_date_from),
                ('start_date', '<=', prev_date_to)
            ])

        elif metric == 'occupancy':
            current_occupied = 0
            for unit in units:
                if request.env['onedesk.reservation'].search_count([
                    ('unit_id', '=', unit.id),
                    ('status', 'in', ['confirmed', 'checked_in']),
                    ('start_date', '<=', date_to),
                    ('end_date', '>=', date_from)
                ]):
                    current_occupied += 1
            current = (current_occupied / len(units) * 100) if units else 0

            previous_occupied = 0
            for unit in units:
                if request.env['onedesk.reservation'].search_count([
                    ('unit_id', '=', unit.id),
                    ('status', 'in', ['confirmed', 'checked_in']),
                    ('start_date', '<=', prev_date_to),
                    ('end_date', '>=', prev_date_from)
                ]):
                    previous_occupied += 1
            previous = (previous_occupied / len(units) * 100) if units else 0
        else:
            current = 0
            previous = 0

        # Calculate percentage change
        if previous > 0:
            percentage_change = ((current - previous) / previous * 100)
        else:
            percentage_change = 0 if current == 0 else 100

        # Determine trend indicator
        if percentage_change > 0:
            trend = '↑'
            trend_class = 'positive'
        elif percentage_change < 0:
            trend = '↓'
            trend_class = 'negative'
        else:
            trend = '→'
            trend_class = 'neutral'

        return {
            'status': 'success',
            'metric': metric,
            'current_value': round(current, 2),
            'previous_value': round(previous, 2),
            'percentage_change': round(percentage_change, 2),
            'trend': trend,
            'trend_class': trend_class,
            'period_length': period_length
        }
