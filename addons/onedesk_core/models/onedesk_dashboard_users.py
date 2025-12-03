from odoo import models, fields, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class OneDesk_DashboardUsers(models.Model):
    _name = 'onedesk.dashboard.users'
    _description = 'OneDesk Users Dashboard'
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
    # User activity
    total_users = fields.Integer(compute='_compute_user_metrics', string='Total Users')
    active_users = fields.Integer(compute='_compute_user_metrics', string='Active Users')
    inactive_users = fields.Integer(compute='_compute_user_metrics', string='Inactive Users')

    # Activity metrics
    total_actions = fields.Integer(compute='_compute_user_metrics', string='Total Actions')
    average_actions_per_user = fields.Float(compute='_compute_user_metrics', string='Avg Actions per User', digits=(5, 2))
    most_active_user = fields.Many2one('res.users', compute='_compute_user_metrics', string='Most Active User')

    # Task metrics
    total_tasks = fields.Integer(compute='_compute_user_metrics', string='Total Tasks')
    completed_tasks = fields.Integer(compute='_compute_user_metrics', string='Completed Tasks')
    pending_tasks = fields.Integer(compute='_compute_user_metrics', string='Pending Tasks')

    # Productivity score
    team_productivity_score = fields.Float(compute='_compute_user_metrics', string='Team Productivity Score', digits=(5, 2))

    # Comparison metrics
    previous_period_actions = fields.Integer(compute='_compute_user_metrics', string='Previous Period Actions')
    activity_growth = fields.Float(compute='_compute_user_metrics', string='Activity Growth (%)', digits=(16, 2))

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
    def _compute_user_metrics(self):
        """Compute all user-related metrics"""
        for dashboard in self:
            companies = dashboard._get_accessible_companies()
            date_from, date_to = dashboard._get_date_range()

            # Get all users in company
            users = self.env['res.users'].search([
                ('company_id', 'in', companies.ids),
                ('active', '=', True)
            ])

            dashboard.total_users = len(users)
            dashboard.active_users = len(users)
            dashboard.inactive_users = len(self.env['res.users'].search([
                ('company_id', 'in', companies.ids),
                ('active', '=', False)
            ]))

            # Count tasks (filter by unit's company via property)
            all_tasks = self.env['onedesk.task'].search([
                '|',
                ('unit_id.property_id.company_id', 'in', companies.ids),
                ('assigned_to.company_id', 'in', companies.ids)
            ])

            dashboard.total_tasks = len(all_tasks)
            dashboard.completed_tasks = len(all_tasks.filtered(lambda t: t.status == 'done'))
            dashboard.pending_tasks = len(all_tasks.filtered(lambda t: t.status != 'done'))

            # Count user actions (tasks created/assigned in period)
            user_actions = {}
            for task in all_tasks:
                if task.assigned_to:
                    if task.assigned_to.id not in user_actions:
                        user_actions[task.assigned_to.id] = 0
                    user_actions[task.assigned_to.id] += 1

            dashboard.total_actions = len(all_tasks)
            dashboard.average_actions_per_user = dashboard.total_actions / dashboard.total_users if dashboard.total_users > 0 else 0.0

            # Most active user
            if user_actions:
                most_active_id = max(user_actions, key=user_actions.get)
                dashboard.most_active_user = most_active_id
            else:
                dashboard.most_active_user = False

            # Calculate team productivity score (0-100)
            # Based on task completion rate and actions per user
            if dashboard.total_tasks > 0:
                completion_rate = dashboard.completed_tasks / dashboard.total_tasks * 100
                action_rate = min(dashboard.average_actions_per_user / 10 * 100, 100)
                dashboard.team_productivity_score = (completion_rate * 0.7 + action_rate * 0.3)
            else:
                dashboard.team_productivity_score = 0.0

            # Previous period metrics
            all_prev_tasks = self.env['onedesk.task'].search([
                '|',
                ('unit_id.property_id.company_id', 'in', companies.ids),
                ('assigned_to.company_id', 'in', companies.ids)
            ])
            dashboard.previous_period_actions = len(all_prev_tasks)

            # Calculate growth
            if dashboard.previous_period_actions > 0:
                growth = ((dashboard.total_actions - dashboard.previous_period_actions) / dashboard.previous_period_actions) * 100
                dashboard.activity_growth = round(growth, 2)
            else:
                dashboard.activity_growth = 0.0 if dashboard.total_actions == 0 else 100.0

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
            'total_users': self.total_users,
            'active_users': self.active_users,
            'inactive_users': self.inactive_users,
            'total_actions': self.total_actions,
            'average_actions_per_user': round(self.average_actions_per_user, 2),
            'most_active_user': self.most_active_user.name if self.most_active_user else '',
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks,
            'pending_tasks': self.pending_tasks,
            'team_productivity_score': round(self.team_productivity_score, 2),
            'previous_period_actions': self.previous_period_actions,
            'activity_growth': self.activity_growth,
            'period_type': self.period_type,
            'date_from': str(self.date_from) if self.date_from else '',
            'date_to': str(self.date_to) if self.date_to else ''
        }

    # ==================== DATABASE CONSTRAINTS ====================
    
    _constraints_= [
        models.Constraint(
            'unique(user_id, company_id)',
            'Only one users dashboard per user per company allowed'
        )
    ]
