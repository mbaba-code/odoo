from odoo import models, fields, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class OneDesk_DashboardSales(models.Model):
    _name = 'onedesk.dashboard.sales'
    _description = 'OneDesk Sales Dashboard'
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
    total_revenue = fields.Float(compute='_compute_revenue_metrics', string='Total Revenue', digits=(16, 2))
    revenue_count = fields.Integer(compute='_compute_revenue_metrics', string='Number of Transactions')
    average_transaction = fields.Float(compute='_compute_revenue_metrics', string='Average Transaction', digits=(16, 2))

    # Comparison metrics
    previous_period_revenue = fields.Float(compute='_compute_revenue_metrics', string='Previous Period Revenue', digits=(16, 2))
    revenue_growth = fields.Float(compute='_compute_revenue_metrics', string='Revenue Growth (%)', digits=(16, 2))

    # Top performers
    top_property_id = fields.Many2one('onedesk.property', compute='_compute_revenue_metrics', string='Top Property by Revenue')
    top_property_revenue = fields.Float(compute='_compute_revenue_metrics', string='Top Property Revenue', digits=(16, 2))

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
    def _compute_revenue_metrics(self):
        """Compute all revenue-related metrics"""
        for dashboard in self:
            companies = dashboard._get_accessible_companies()
            date_from, date_to = dashboard._get_date_range()

            # Get all reservations in the period
            reservations = self.env['onedesk.reservation'].search([
                ('company_id', 'in', companies.ids),
                ('start_date', '<=', date_to),
                ('end_date', '>=', date_from),
                ('status', 'in', ['paid', 'checked_in', 'completed']),
                ('active', '=', True)
            ])

            # Calculate primary metrics
            dashboard.revenue_count = len(reservations)
            dashboard.total_revenue = sum(reservations.mapped('total_price'))
            dashboard.average_transaction = dashboard.total_revenue / dashboard.revenue_count if dashboard.revenue_count > 0 else 0.0

            # Calculate previous period metrics
            prev_from, prev_to = dashboard._get_previous_period_range()
            prev_reservations = self.env['onedesk.reservation'].search([
                ('company_id', 'in', companies.ids),
                ('start_date', '<=', prev_to),
                ('end_date', '>=', prev_from),
                ('status', 'in', ['paid', 'checked_in', 'completed']),
                ('active', '=', True)
            ])

            dashboard.previous_period_revenue = sum(prev_reservations.mapped('total_price'))

            # Calculate growth
            if dashboard.previous_period_revenue > 0:
                growth = ((dashboard.total_revenue - dashboard.previous_period_revenue) / dashboard.previous_period_revenue) * 100
                dashboard.revenue_growth = round(growth, 2)
            else:
                dashboard.revenue_growth = 0.0 if dashboard.total_revenue == 0 else 100.0

            # Find top property
            if reservations:
                property_revenues = {}
                for res in reservations:
                    if res.unit_id and res.unit_id.property_id:
                        prop_id = res.unit_id.property_id.id
                        property_revenues[prop_id] = property_revenues.get(prop_id, 0.0) + res.total_price

                if property_revenues:
                    top_prop_id = max(property_revenues, key=property_revenues.get)
                    dashboard.top_property_id = top_prop_id
                    dashboard.top_property_revenue = property_revenues[top_prop_id]
                else:
                    dashboard.top_property_id = False
                    dashboard.top_property_revenue = 0.0
            else:
                dashboard.top_property_id = False
                dashboard.top_property_revenue = 0.0

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
            'total_revenue': self.total_revenue,
            'revenue_count': self.revenue_count,
            'average_transaction': self.average_transaction,
            'previous_period_revenue': self.previous_period_revenue,
            'revenue_growth': self.revenue_growth,
            'top_property_name': self.top_property_id.name if self.top_property_id else '',
            'top_property_revenue': self.top_property_revenue,
            'period_type': self.period_type,
            'date_from': str(self.date_from) if self.date_from else '',
            'date_to': str(self.date_to) if self.date_to else ''
        }

    # ==================== DATABASE CONSTRAINTS ====================
    _sql_constraints = [
        ('unique_user_company', 'unique(user_id, company_id)',
         'Only one sales dashboard per user per company allowed')
    ]
