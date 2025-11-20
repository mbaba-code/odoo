from odoo import models, fields, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class OnedeaskDashboard(models.Model):
    """OneDesk Dashboard - Configurable real-time statistics and metrics"""
    _name = 'onedesk.dashboard'
    _description = 'OneDesk Dashboard Configuration'
    _rec_name = 'user_id'

    user_id = fields.Many2one('res.users', string="User", default=lambda self: self.env.user, required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)


    _constraints_ = [
        models.Constraint(
            'unique(user_id, company_id)',
            'Un utilisateur ne peut avoir qu\'un seul tableau de bord par compagnie'
        )
    ]
    # Helper method to get accessible companies based on user role
    def _get_accessible_companies(self):
        """Returns list of company IDs accessible to current user based on their role"""
        user = self.user_id or self.env.user

        # Master Admin and Support can see ALL companies
        if user.has_group('onedesk_core.group_onedesk_master_admin') or user.has_group('onedesk_core.group_onedesk_support'):
            return self.env['res.company'].search([]).ids

        # Other users can only see their own company
        return [user.company_id.id]

    # Widget visibility configuration
    show_properties_kpi = fields.Boolean(string="Show Properties KPI", default=True)
    show_units_kpi = fields.Boolean(string="Show Units KPI", default=True)
    show_reservations_today = fields.Boolean(string="Show Reservations Today", default=True)
    show_tasks_urgent = fields.Boolean(string="Show Urgent Tasks", default=True)
    show_financial = fields.Boolean(string="Show Financial Summary", default=True)
    show_occupancy_chart = fields.Boolean(string="Show Occupancy Chart", default=True)
    show_revenue_chart = fields.Boolean(string="Show Revenue Chart", default=True)

    # ==================== PERIOD FILTERING ====================
    period_type = fields.Selection([
        ('today', 'Today (Aujourd\'hui)'),
        ('week', 'This Week (Cette Semaine)'),
        ('month', 'This Month (Ce Mois)'),
        ('year', 'This Year (Cette Année)'),
        ('custom', 'Custom Period (Période Personnalisée)')
    ], string="Period / Période", default='month')

    date_from = fields.Date(string="Start Date / Date de Début")
    date_to = fields.Date(string="End Date / Date de Fin")

    # Refresh interval in seconds
    refresh_interval = fields.Integer(string="Auto-Refresh Interval (seconds)", default=300)  # 5 minutes
    auto_refresh = fields.Boolean(string="Enable Auto-Refresh", default=True)

    # ==================== PROPERTIES METRICS ====================
    total_properties = fields.Integer(string="Total Properties", compute='_compute_properties_metrics')
    active_properties = fields.Integer(string="Active Properties", compute='_compute_properties_metrics')
    inactive_properties = fields.Integer(string="Inactive Properties", compute='_compute_properties_metrics')
    properties_occupancy_rate = fields.Float(string="Properties Occupancy Rate", compute='_compute_properties_metrics')
    revenue_this_month = fields.Float(string="Revenue This Month", compute='_compute_properties_metrics')

    @api.depends('company_id', 'user_id')
    def _compute_properties_metrics(self):
        """Calculate properties-related metrics"""
        for dashboard in self:
            company_ids = dashboard._get_accessible_companies()
            properties = self.env['onedesk.property'].search([('company_id', 'in', company_ids)])

            dashboard.total_properties = len(properties)
            dashboard.active_properties = len(properties.filtered('active'))
            dashboard.inactive_properties = len(properties.filtered(lambda p: not p.active))

            # Calculate occupancy rate
            if dashboard.total_properties > 0:
                occupied_units = self.env['onedesk.unit'].search_count([
                    ('property_id', 'in', properties.ids),
                    ('active', '=', True)
                ])
                total_units = self.env['onedesk.unit'].search_count([
                    ('property_id', 'in', properties.ids)
                ])
                dashboard.properties_occupancy_rate = (occupied_units / total_units * 100) if total_units > 0 else 0
            else:
                dashboard.properties_occupancy_rate = 0

            # Revenue this month
            today = datetime.now()
            month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            units = self.env['onedesk.unit'].search([('property_id', 'in', properties.ids)])
            completed_reservations = self.env['onedesk.reservation'].search([
                ('unit_id', 'in', units.ids),
                ('status', '=', 'completed'),
                ('end_date', '>=', month_start)
            ])
            dashboard.revenue_this_month = sum(completed_reservations.mapped('total_price'))

    # ==================== UNITS METRICS ====================
    total_units = fields.Integer(string="Total Units", compute='_compute_units_metrics')
    available_units = fields.Integer(string="Available Units", compute='_compute_units_metrics')
    maintenance_units = fields.Integer(string="Units in Maintenance", compute='_compute_units_metrics')
    units_occupancy_rate = fields.Float(string="Units Occupancy Rate", compute='_compute_units_metrics')

    @api.depends('company_id', 'user_id')
    def _compute_units_metrics(self):
        """Calculate units-related metrics"""
        for dashboard in self:
            company_ids = dashboard._get_accessible_companies()
            properties = self.env['onedesk.property'].search([('company_id', 'in', company_ids)])
            units = self.env['onedesk.unit'].search([('property_id', 'in', properties.ids)])

            dashboard.total_units = len(units)
            dashboard.available_units = len(units.filtered('active'))
            dashboard.maintenance_units = len(units.filtered('maintenance_mode'))

            # Units occupancy
            if dashboard.total_units > 0:
                today = datetime.now().date()
                occupied = len(units.filtered(lambda u: self.env['onedesk.reservation'].search_count([
                    ('unit_id', '=', u.id),
                    ('status', 'in', ['confirmed', 'checked_in']),
                    ('start_date', '<=', today),
                    ('end_date', '>=', today)
                ])))
                dashboard.units_occupancy_rate = (occupied / dashboard.total_units * 100)
            else:
                dashboard.units_occupancy_rate = 0

    # ==================== RESERVATIONS METRICS ====================
    reservations_today_checkin = fields.Integer(string="Check-ins Today", compute='_compute_reservations_metrics')
    reservations_today_checkout = fields.Integer(string="Check-outs Today", compute='_compute_reservations_metrics')
    reservations_pending_payment = fields.Integer(string="Pending Payments", compute='_compute_reservations_metrics')
    reservations_pending_payment_amount = fields.Float(string="Pending Payment Amount", compute='_compute_reservations_metrics')
    reservations_confirmed_month = fields.Integer(string="Confirmed This Month", compute='_compute_reservations_metrics')

    @api.depends('company_id', 'user_id')
    def _compute_reservations_metrics(self):
        """Calculate reservations-related metrics"""
        for dashboard in self:
            company_ids = dashboard._get_accessible_companies()
            properties = self.env['onedesk.property'].search([('company_id', 'in', company_ids)])

            today = datetime.now().date()
            month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Check-ins/Check-outs today
            units = self.env['onedesk.unit'].search([('property_id', 'in', properties.ids)])
            reservations = self.env['onedesk.reservation'].search([
                ('unit_id', 'in', units.ids)
            ])

            dashboard.reservations_today_checkin = len(reservations.filtered(lambda r: r.start_date.date() == today))
            dashboard.reservations_today_checkout = len(reservations.filtered(lambda r: r.end_date.date() == today))

            # Pending payments
            pending = reservations.filtered(lambda r: r.payment_status == 'pending')
            dashboard.reservations_pending_payment = len(pending)
            dashboard.reservations_pending_payment_amount = sum(pending.mapped('total_price'))

            # Confirmed this month
            dashboard.reservations_confirmed_month = len(reservations.filtered(
                lambda r: r.status == 'confirmed' and r.start_date >= month_start
            ))

    # ==================== TASKS METRICS ====================
    tasks_overdue = fields.Integer(string="Overdue Tasks", compute='_compute_tasks_metrics')
    tasks_due_today = fields.Integer(string="Tasks Due Today", compute='_compute_tasks_metrics')
    tasks_urgent_total = fields.Integer(string="Urgent Tasks Total", compute='_compute_tasks_metrics')
    tasks_in_progress = fields.Integer(string="Tasks In Progress", compute='_compute_tasks_metrics')

    @api.depends('company_id', 'user_id')
    def _compute_tasks_metrics(self):
        """Calculate tasks-related metrics"""
        for dashboard in self:
            company_ids = dashboard._get_accessible_companies()
            properties = self.env['onedesk.property'].search([('company_id', 'in', company_ids)])
            units = self.env['onedesk.unit'].search([('property_id', 'in', properties.ids)])

            # Tasks are related to reservations, which are linked to units
            reservations = self.env['onedesk.reservation'].search([('unit_id', 'in', units.ids)])
            tasks = self.env['onedesk.task'].search([
                ('reservation_id', 'in', reservations.ids)
            ])

            today = datetime.now().date()

            dashboard.tasks_overdue = len(tasks.filtered(lambda t: t.date_start.date() < today and t.status != 'done'))
            dashboard.tasks_due_today = len(tasks.filtered(lambda t: t.date_start.date() == today and t.status != 'done'))
            dashboard.tasks_urgent_total = len(tasks.filtered(lambda t: t.priority == 'urgent' and t.status != 'done'))
            dashboard.tasks_in_progress = len(tasks.filtered(lambda t: t.status == 'in_progress'))

    # ==================== FINANCIAL METRICS ====================
    revenue_today = fields.Float(string="Revenue Today", compute='_compute_financial_metrics')
    revenue_this_week = fields.Float(string="Revenue This Week", compute='_compute_financial_metrics')
    outstanding_payments = fields.Float(string="Outstanding Payments", compute='_compute_financial_metrics')
    occupancy_rate_week = fields.Float(string="Occupancy Rate (This Week)", compute='_compute_financial_metrics')

    @api.depends('company_id', 'user_id')
    def _compute_financial_metrics(self):
        """Calculate financial metrics"""
        for dashboard in self:
            company_ids = dashboard._get_accessible_companies()
            properties = self.env['onedesk.property'].search([('company_id', 'in', company_ids)])
            units = self.env['onedesk.unit'].search([('property_id', 'in', properties.ids)])

            today = datetime.now()
            today_date = today.date()
            week_start = today - timedelta(days=today.weekday())

            # Revenue today
            completed_today = self.env['onedesk.reservation'].search([
                ('unit_id', 'in', units.ids),
                ('status', '=', 'completed'),
                ('end_date', '>=', today_date)
            ])
            dashboard.revenue_today = sum(completed_today.mapped('total_price'))

            # Revenue this week
            completed_week = self.env['onedesk.reservation'].search([
                ('unit_id', 'in', units.ids),
                ('status', '=', 'completed'),
                ('end_date', '>=', week_start)
            ])
            dashboard.revenue_this_week = sum(completed_week.mapped('total_price'))

            # Outstanding payments
            pending = self.env['onedesk.reservation'].search([
                ('unit_id', 'in', units.ids),
                ('payment_status', '=', 'pending')
            ])
            dashboard.outstanding_payments = sum(pending.mapped('total_price'))

            # Occupancy rate this week
            if len(units) > 0:
                occupied_week = len(units.filtered(lambda u: self.env['onedesk.reservation'].search_count([
                    ('unit_id', '=', u.id),
                    ('status', 'in', ['confirmed', 'checked_in']),
                    ('start_date', '<=', today_date),
                    ('end_date', '>=', week_start)
                ])))
                dashboard.occupancy_rate_week = (occupied_week / len(units) * 100)
            else:
                dashboard.occupancy_rate_week = 0

    # ==================== ACTIONS ====================
    @api.model
    def default_get(self, fields):
        """Set default values when creating/loading dashboard"""
        res = super().default_get(fields)

        # Try to get existing dashboard for current user
        dashboard = self.search([
            ('user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if dashboard:
            # Load existing dashboard values
            for field in fields:
                if field in dashboard._fields:
                    value = dashboard[field]
                    # Handle Many2One fields - return ID instead of browse record
                    field_obj = dashboard._fields[field]
                    if field_obj.relational:
                        res[field] = value.id if value else False
                    else:
                        res[field] = value
        else:
            # Set defaults for new dashboard
            res['user_id'] = self.env.user.id
            res['company_id'] = self.env.company.id
            res['auto_refresh'] = True
            res['refresh_interval'] = 300  # 5 minutes default

        return res

    @api.model
    def get_user_dashboard(self):
        """Get or create dashboard for current user"""
        dashboard = self.search([
            ('user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if not dashboard:
            dashboard = self.create({
                'user_id': self.env.user.id,
                'company_id': self.env.company.id,
                'auto_refresh': True,
                'refresh_interval': 300
            })

        return dashboard

    @api.model
    def web_search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Override web_search_read to auto-create dashboard if needed"""
        # Ensure user has a dashboard before loading list view
        self.get_user_dashboard()

        # Call parent method
        return super().web_search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    def get_dashboard_data(self):
        """Get all dashboard data for real-time refresh"""
        self.ensure_one()

        return {
            'properties': {
                'total': self.total_properties,
                'active': self.active_properties,
                'inactive': self.inactive_properties,
                'occupancy_rate': self.properties_occupancy_rate,
                'revenue_this_month': self.revenue_this_month,
            },
            'units': {
                'total': self.total_units,
                'available': self.available_units,
                'maintenance': self.maintenance_units,
                'occupancy_rate': self.units_occupancy_rate,
            },
            'reservations': {
                'checkin_today': self.reservations_today_checkin,
                'checkout_today': self.reservations_today_checkout,
                'pending_payment': self.reservations_pending_payment,
                'pending_payment_amount': self.reservations_pending_payment_amount,
                'confirmed_month': self.reservations_confirmed_month,
            },
            'tasks': {
                'overdue': self.tasks_overdue,
                'due_today': self.tasks_due_today,
                'urgent': self.tasks_urgent_total,
                'in_progress': self.tasks_in_progress,
            },
            'financial': {
                'revenue_today': self.revenue_today,
                'revenue_this_week': self.revenue_this_week,
                'outstanding_payments': self.outstanding_payments,
                'occupancy_rate_week': self.occupancy_rate_week,
            },
            'config': {
                'auto_refresh': self.auto_refresh,
                'refresh_interval': self.refresh_interval,
                'widgets': {
                    'properties': self.show_properties_kpi,
                    'units': self.show_units_kpi,
                    'reservations': self.show_reservations_today,
                    'tasks': self.show_tasks_urgent,
                    'financial': self.show_financial,
                    'occupancy_chart': self.show_occupancy_chart,
                    'revenue_chart': self.show_revenue_chart,
                }
            }
        }
