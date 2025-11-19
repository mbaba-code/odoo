from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json


class UsersDashboardController(http.Controller):
    """API endpoints for Users Dashboard data and analytics"""

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

    # ==================== USER ACTIVITY ====================
    @http.route('/onedesk/dashboard/users/activity-by-user', type='json', auth='user')
    def activity_by_user(self, period_type='month', date_from=None, date_to=None, limit=15, **kwargs):
        """Activity metrics for each user"""
        try:
            user = request.env.user
            companies = self._get_accessible_companies(user)

            date_from, date_to = self._get_date_range(period_type, date_from, date_to)

            # Get all users
            users = request.env['res.users'].search([
                ('company_id', 'in', companies.ids),
                ('active', '=', True)
            ])

            # Get all tasks
            all_tasks = request.env['onedesk.task'].search([
                ('company_id', 'in', companies.ids)
            ])

            user_data = {}
            for u in users:
                # Count assigned tasks
                assigned = len(all_tasks.filtered(lambda t: t.assigned_to.id == u.id))
                # Count completed tasks
                completed = len(all_tasks.filtered(lambda t: t.assigned_to.id == u.id and t.status == 'completed'))

                if assigned > 0:
                    completion_rate = (completed / assigned) * 100
                else:
                    completion_rate = 0.0

                user_data[u.id] = {
                    'name': u.name,
                    'assigned': assigned,
                    'completed': completed,
                    'completion_rate': round(completion_rate, 2)
                }

            # Sort by most active and limit
            sorted_users = sorted(user_data.items(), key=lambda x: x[1]['assigned'], reverse=True)[:limit]

            labels = [u[1]['name'] for u in sorted_users]
            assigned = [u[1]['assigned'] for u in sorted_users]
            completed = [u[1]['completed'] for u in sorted_users]

            return {
                'status': 'success',
                'labels': labels,
                'assigned': assigned,
                'completed': completed,
                'period': period_type
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/onedesk/dashboard/users/productivity-score', type='json', auth='user')
    def productivity_score(self, **kwargs):
        """Overall team productivity score"""
        try:
            user = request.env.user
            companies = self._get_accessible_companies(user)

            # Get all tasks
            all_tasks = request.env['onedesk.task'].search([
                ('company_id', 'in', companies.ids)
            ])

            # Calculate completion rate
            total_tasks = len(all_tasks)
            completed_tasks = len(all_tasks.filtered(lambda t: t.status == 'completed'))
            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0

            # Get active users count
            active_users = len(request.env['res.users'].search([
                ('company_id', 'in', companies.ids),
                ('active', '=', True)
            ]))

            # Actions per user
            avg_actions = total_tasks / active_users if active_users > 0 else 0.0

            # Productivity score (weighted)
            # 70% completion rate + 30% action rate
            productivity_score = (completion_rate * 0.7) + (min(avg_actions / 10 * 100, 100) * 0.3)

            return {
                'status': 'success',
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'completion_rate': round(completion_rate, 2),
                'active_users': active_users,
                'avg_actions_per_user': round(avg_actions, 2),
                'productivity_score': round(productivity_score, 2)
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/onedesk/dashboard/users/task-status-distribution', type='json', auth='user')
    def task_status_distribution(self, **kwargs):
        """Distribution of tasks by status"""
        try:
            user = request.env.user
            companies = self._get_accessible_companies(user)

            # Get all tasks
            all_tasks = request.env['onedesk.task'].search([
                ('company_id', 'in', companies.ids)
            ])

            # Count by status
            status_counts = {}
            for task in all_tasks:
                status = task.status or 'unknown'
                status_counts[status] = status_counts.get(status, 0) + 1

            labels = list(status_counts.keys())
            data = list(status_counts.values())

            return {
                'status': 'success',
                'labels': labels,
                'data': data
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/onedesk/dashboard/users/team-performance', type='json', auth='user')
    def team_performance(self, limit=10, **kwargs):
        """Top performing users"""
        try:
            user = request.env.user
            companies = self._get_accessible_companies(user)

            # Get all users
            users = request.env['res.users'].search([
                ('company_id', 'in', companies.ids),
                ('active', '=', True)
            ])

            # Get all tasks
            all_tasks = request.env['onedesk.task'].search([
                ('company_id', 'in', companies.ids)
            ])

            user_performance = {}
            for u in users:
                # Count tasks
                assigned = len(all_tasks.filtered(lambda t: t.assigned_to.id == u.id))
                completed = len(all_tasks.filtered(lambda t: t.assigned_to.id == u.id and t.status == 'completed'))

                # Calculate score
                if assigned > 0:
                    completion_rate = (completed / assigned) * 100
                    score = (completion_rate * 0.7) + (min(assigned / 5 * 30, 30))
                else:
                    score = 0.0

                if score > 0:
                    user_performance[u.id] = {
                        'name': u.name,
                        'score': round(score, 2),
                        'assigned': assigned,
                        'completed': completed
                    }

            # Sort by score and limit
            sorted_users = sorted(user_performance.items(), key=lambda x: x[1]['score'], reverse=True)[:limit]

            labels = [u[1]['name'] for u in sorted_users]
            scores = [u[1]['score'] for u in sorted_users]

            return {
                'status': 'success',
                'labels': labels,
                'scores': scores,
                'limit': limit
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
