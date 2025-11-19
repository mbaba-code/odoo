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
