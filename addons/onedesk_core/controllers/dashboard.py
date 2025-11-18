import json
from odoo import http
from odoo.http import request, Controller, route


class OnedeaskDashboardController(Controller):
    """Controller for real-time dashboard data refresh"""

    @route('/onedesk/dashboard/data', type='json', auth='user')
    def get_dashboard_data(self, **kwargs):
        """
        Get current dashboard data for the user
        Returns JSON with all dashboard metrics
        """
        dashboard = request.env['onedesk.dashboard'].get_user_dashboard()
        data = dashboard.get_dashboard_data()
        return {
            'status': 'success',
            'data': data,
            'timestamp': request.env['ir.model'].sudo().get_external_id(dashboard.id)
        }

    @route('/onedesk/dashboard/config', type='json', auth='user', methods=['GET'])
    def get_dashboard_config(self, **kwargs):
        """
        Get dashboard configuration for the user
        Returns widget visibility and refresh settings
        """
        dashboard = request.env['onedesk.dashboard'].get_user_dashboard()
        return {
            'status': 'success',
            'auto_refresh': dashboard.auto_refresh,
            'refresh_interval': dashboard.refresh_interval,
            'widgets': {
                'properties': dashboard.show_properties_kpi,
                'units': dashboard.show_units_kpi,
                'reservations': dashboard.show_reservations_today,
                'tasks': dashboard.show_tasks_urgent,
                'financial': dashboard.show_financial,
                'occupancy_chart': dashboard.show_occupancy_chart,
                'revenue_chart': dashboard.show_revenue_chart,
            }
        }

    @route('/onedesk/dashboard/config', type='json', auth='user', methods=['POST'])
    def update_dashboard_config(self, **kwargs):
        """
        Update dashboard configuration
        Accepts JSON with configuration changes
        """
        try:
            dashboard = request.env['onedesk.dashboard'].get_user_dashboard()

            # Update auto refresh settings
            if 'auto_refresh' in kwargs:
                dashboard.auto_refresh = kwargs['auto_refresh']
            if 'refresh_interval' in kwargs:
                interval = int(kwargs['refresh_interval'])
                # Enforce minimum 60 seconds for performance
                dashboard.refresh_interval = max(60, interval)

            # Update widget visibility
            if 'widgets' in kwargs:
                widgets = kwargs['widgets']
                if 'properties' in widgets:
                    dashboard.show_properties_kpi = widgets['properties']
                if 'units' in widgets:
                    dashboard.show_units_kpi = widgets['units']
                if 'reservations' in widgets:
                    dashboard.show_reservations_today = widgets['reservations']
                if 'tasks' in widgets:
                    dashboard.show_tasks_urgent = widgets['tasks']
                if 'financial' in widgets:
                    dashboard.show_financial = widgets['financial']
                if 'occupancy_chart' in widgets:
                    dashboard.show_occupancy_chart = widgets['occupancy_chart']
                if 'revenue_chart' in widgets:
                    dashboard.show_revenue_chart = widgets['revenue_chart']

            return {
                'status': 'success',
                'message': 'Dashboard configuration updated',
                'config': {
                    'auto_refresh': dashboard.auto_refresh,
                    'refresh_interval': dashboard.refresh_interval,
                }
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    @route('/onedesk/dashboard/metrics/<string:metric_type>', type='json', auth='user')
    def get_specific_metric(self, metric_type, **kwargs):
        """
        Get specific metric group (properties, units, reservations, tasks, financial)
        Allows selective refresh of only needed metrics for better performance
        """
        dashboard = request.env['onedesk.dashboard'].get_user_dashboard()
        data = dashboard.get_dashboard_data()

        metric_data = data.get(metric_type)
        if metric_data is None:
            return {
                'status': 'error',
                'message': f'Unknown metric type: {metric_type}'
            }

        return {
            'status': 'success',
            'metric_type': metric_type,
            'data': metric_data
        }

    @route('/onedesk/dashboard/health', type='json', auth='user')
    def health_check(self, **kwargs):
        """
        Simple health check endpoint for dashboard
        Useful for monitoring real-time updates
        """
        return {
            'status': 'ok',
            'user': request.env.user.name,
            'company': request.env.user.company_id.name,
        }
