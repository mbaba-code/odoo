from odoo import models, fields, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class OneDesk_DashboardReservations(models.Model):
    _name = 'onedesk.dashboard.reservations'
    _description = 'OneDesk Reservations Dashboard'
    _order = 'user_id, period_type'

    # ==================== BASIC FIELDS ====================
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='cascade')

    # ==================== PERIOD FILTERING ====================
    period_type = fields.Selection([
        ('today', 'Today'),
        ('week', 'This Week'),
        ('month', 'This Month'),
        ('year', 'This Year'),
        ('custom', 'Custom Period')
    ], default='month', string='Period Type')

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')

    # ==================== COMPUTED METRICS ====================
    # Primary metrics
    total_reservations = fields.Integer(compute='_compute_reservation_metrics', string='Total Reservations')
    active_reservations = fields.Integer(compute='_compute_reservation_metrics', string='Active Reservations')
    pending_reservations = fields.Integer(compute='_compute_reservation_metrics', string='Pending Reservations')
    cancelled_reservations = fields.Integer(compute='_compute_reservation_metrics', string='Cancelled Reservations')

    # Occupancy metrics
    total_nights = fields.Integer(compute='_compute_reservation_metrics', string='Total Nights')
    occupancy_rate = fields.Float(compute='_compute_reservation_metrics', string='Occupancy Rate (%)', digits=(5, 2))
    average_stay = fields.Float(compute='_compute_reservation_metrics', string='Average Stay (nights)', digits=(5, 2))

    # Comparison metrics
    previous_period_reservations = fields.Integer(compute='_compute_reservation_metrics', string='Previous Period Reservations')
    reservation_growth = fields.Float(compute='_compute_reservation_metrics', string='Reservation Growth (%)', digits=(16, 2))

    # ==================== ACCESS CONTROL ====================
    @api.model
    def _get_accessible_companies(self):
        """Get companies accessible based on user role"""
        user = self.env.user
        if user.has_group('onedesk_core.group_onedesk_master_admin') or user.has_group('onedesk_core.group_onedesk_support'):
            return self.env['res.company'].search([])
        return user.company_ids or self.env.user.company_id

    # ==================== DATE RANGE CALCULATION ====================
    def _get_date_range(self):
        """Calculate date range based on period_type"""
        today = fields.Date.today()

        if self.period_type == 'today':
            return today, today
        elif self.period_type == 'week':
            start = today - timedelta(days=today.weekday())
            return start, today
        elif self.period_type == 'month':
            start = today.replace(day=1)
            return start, today
        elif self.period_type == 'year':
            start = today.replace(month=1, day=1)
            return start, today
        elif self.period_type == 'custom':
            return self.date_from or today, self.date_to or today

        return today, today

    def _get_previous_period_range(self):
        """Get previous period date range with same length"""
        date_from, date_to = self._get_date_range()
        period_length = (date_to - date_from).days + 1
        prev_to = date_from - timedelta(days=1)
        prev_from = prev_to - timedelta(days=period_length - 1)
        return prev_from, prev_to

    # ==================== COMPUTE METHODS ====================
    @api.depends('period_type', 'date_from', 'date_to', 'user_id', 'company_id')
    def _compute_reservation_metrics(self):
        """Compute all reservation-related metrics"""
        for dashboard in self:
            companies = dashboard._get_accessible_companies()
            date_from, date_to = dashboard._get_date_range()

            # Get all reservations in the period
            reservations = self.env['onedesk.reservation'].search([
                ('company_id', 'in', companies.ids),
                ('start_date', '<=', date_to),
                ('end_date', '>=', date_from),
                ('active', '=', True)
            ])

            # Primary counts
            dashboard.total_reservations = len(reservations)
            dashboard.active_reservations = len(reservations.filtered(lambda r: r.status in ['confirmed', 'paid', 'checked_in']))
            dashboard.pending_reservations = len(reservations.filtered(lambda r: r.status == 'pending_payment'))
            dashboard.cancelled_reservations = len(reservations.filtered(lambda r: r.status == 'cancelled'))

            # Calculate total nights and occupancy
            total_nights = sum(reservations.mapped('number_of_nights'))
            dashboard.total_nights = int(total_nights)

            # Calculate occupancy rate (nights booked / possible nights)
            all_units = self.env['onedesk.unit'].search([('company_id', 'in', companies.ids)])
            possible_nights = len(all_units) * ((date_to - date_from).days + 1)
            dashboard.occupancy_rate = (total_nights / possible_nights * 100) if possible_nights > 0 else 0.0

            # Average stay
            dashboard.average_stay = (total_nights / dashboard.total_reservations) if dashboard.total_reservations > 0 else 0.0

            # Previous period metrics
            prev_from, prev_to = dashboard._get_previous_period_range()
            prev_reservations = self.env['onedesk.reservation'].search([
                ('company_id', 'in', companies.ids),
                ('start_date', '<=', prev_to),
                ('end_date', '>=', prev_from),
                ('active', '=', True)
            ])

            dashboard.previous_period_reservations = len(prev_reservations)

            # Calculate growth
            if dashboard.previous_period_reservations > 0:
                growth = ((dashboard.total_reservations - dashboard.previous_period_reservations) / dashboard.previous_period_reservations) * 100
                dashboard.reservation_growth = round(growth, 2)
            else:
                dashboard.reservation_growth = 0.0 if dashboard.total_reservations == 0 else 100.0

    # ==================== ODOO HOOKS ====================
    @api.model
    def default_get(self, fields_list):
        """Set defaults when creating or accessing dashboard"""
        res = super().default_get(fields_list)

        # Try to get or create dashboard for current user
        user_dashboard = self.search([
            ('user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.user.company_id.id)
        ], limit=1)

        if user_dashboard:
            # Load existing dashboard defaults
            for field in fields_list:
                if field in ['period_type', 'date_from', 'date_to']:
                    res[field] = getattr(user_dashboard, field)
        else:
            # New dashboard defaults
            res['user_id'] = self.env.user.id
            res['company_id'] = self.env.user.company_id.id
            res['period_type'] = 'month'

        return res

    @api.model
    def web_search_read(self, domain=None, specification=None, offset=0, limit=None, order=None):
        """Auto-create dashboard if none exists"""
        result = super().web_search_read(domain, specification, offset, limit, order)

        if not result['records']:
            # Auto-create dashboard for current user
            dashboard = self.create({
                'user_id': self.env.user.id,
                'company_id': self.env.user.company_id.id,
                'period_type': 'month'
            })
            result['records'] = [dashboard.read(specification)[0]] if specification else [dashboard.read()[0]]
            result['length'] = 1

        return result

    # ==================== DASHBOARD DATA METHOD ====================
    def get_dashboard_data(self):
        """Return all dashboard metrics as dictionary (for API)"""
        self.ensure_one()
        return {
            'total_reservations': self.total_reservations,
            'active_reservations': self.active_reservations,
            'pending_reservations': self.pending_reservations,
            'cancelled_reservations': self.cancelled_reservations,
            'total_nights': self.total_nights,
            'occupancy_rate': round(self.occupancy_rate, 2),
            'average_stay': round(self.average_stay, 2),
            'previous_period_reservations': self.previous_period_reservations,
            'reservation_growth': self.reservation_growth,
            'period_type': self.period_type,
            'date_from': str(self.date_from) if self.date_from else '',
            'date_to': str(self.date_to) if self.date_to else ''
        }

    # ==================== DATABASE CONSTRAINTS ====================
    _sql_constraints = [
        ('unique_user_company', 'unique(user_id, company_id)',
         'Only one reservations dashboard per user per company allowed')
    ]
