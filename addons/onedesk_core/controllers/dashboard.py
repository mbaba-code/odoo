from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class OnedeskDashboardController(http.Controller):
    """Handle Dashboard API endpoints for charts and metrics"""

    @http.route('/onedesk/dashboard/main/data', type='json', auth='user', methods=['POST'])
    def get_main_dashboard_data(self):
        """
        Route principale: retourne toutes les données du Dashboard Principal en une seule requête
        Pour ApexCharts - Odoo 19
        """
        try:
            dashboard = request.env['onedesk.dashboard'].search([
                ('user_id', '=', request.env.user.id),
                ('company_id', '=', request.env.company.id)
            ], limit=1)

            if not dashboard:
                # Créer le dashboard s'il n'existe pas
                dashboard = request.env['onedesk.dashboard'].create({
                    'user_id': request.env.user.id,
                    'company_id': request.env.company.id,
                })

            company_ids = dashboard._get_accessible_companies()
            properties = request.env['onedesk.property'].sudo().search([('company_id', 'in', company_ids)])
            units = request.env['onedesk.unit'].sudo().search([('property_id', 'in', properties.ids)])

            # 1. Données pour graphique revenus (12 derniers mois)
            revenue_data = self._get_revenue_12_months(units)

            # 2. Données pour graphique réservations par statut
            reservations_data = self._get_reservations_by_status(units)

            # 3. Taux d'occupation global
            occupancy_rate = self._get_occupancy_rate(units)

            # 4. Distribution des propriétés par ville
            properties_by_city = self._get_properties_by_city(properties)

            # 5. Calcul du revenu du mois (en temps réel)
            revenue_this_month = self._get_revenue_this_month(units)

            # 6. KPIs principaux
            kpis = {
                'total_properties': len(properties),
                'total_units': len(units),
                'active_properties': len(properties.filtered('active')),
                'available_units': len(units.filtered('available')),
                'revenue_this_month': revenue_this_month,
                'reservations_confirmed_month': dashboard.reservations_confirmed_month,
            }

            return {
                'status': 'success',
                'data': {
                    'revenue_12_months': revenue_data,
                    'reservations_by_status': reservations_data,
                    'occupancy_rate': occupancy_rate,
                    'properties_by_city': properties_by_city,
                    'kpis': kpis,
                }
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def _get_revenue_12_months(self, units):
        """Revenus des 12 derniers mois (année actuelle vs année précédente)"""
        today = datetime.now()
        current_year = []
        previous_year = []
        months = []

        for i in range(11, -1, -1):
            month_date = today - relativedelta(months=i)
            month_start = month_date.replace(day=1)
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

            # Année actuelle - Inclut paid, checked_in, completed
            current_revenue = sum(request.env['onedesk.reservation'].sudo().search([
                ('unit_id', 'in', units.ids),
                ('status', 'in', ['paid', 'checked_in', 'completed']),
                ('end_date', '>=', month_start),
                ('end_date', '<=', month_end)
            ]).mapped('total_price'))
            current_year.append(round(current_revenue, 2))

            # Année précédente (même mois)
            prev_month_start = month_start - relativedelta(years=1)
            prev_month_end = month_end - relativedelta(years=1)
            previous_revenue = sum(request.env['onedesk.reservation'].sudo().search([
                ('unit_id', 'in', units.ids),
                ('status', 'in', ['paid', 'checked_in', 'completed']),
                ('end_date', '>=', prev_month_start),
                ('end_date', '<=', prev_month_end)
            ]).mapped('total_price'))
            previous_year.append(round(previous_revenue, 2))

            months.append(month_date.strftime('%b'))

        return {
            'months': months,
            'current_year': current_year,
            'previous_year': previous_year
        }

    def _get_reservations_by_status(self, units):
        """Nombre de réservations par statut"""
        statuses = ['draft', 'paid', 'checked_in', 'completed', 'cancelled']
        status_labels = ['Brouillon', 'Payée', 'Enregistré', 'Complétée', 'Annulée']
        counts = []

        for status in statuses:
            count = request.env['onedesk.reservation'].sudo().search_count([
                ('unit_id', 'in', units.ids),
                ('status', '=', status)
            ])
            counts.append(count)

        return {
            'statuses': status_labels,
            'counts': counts
        }

    def _get_occupancy_rate(self, units):
        """Taux d'occupation global actuel"""
        if not units:
            return 0

        today = datetime.now().date()
        occupied = 0

        for unit in units:
            reservation_count = request.env['onedesk.reservation'].sudo().search_count([
                ('unit_id', '=', unit.id),
                ('status', 'in', ['paid', 'checked_in']),
                ('start_date', '<=', today),
                ('end_date', '>=', today)
            ])
            if reservation_count > 0:
                occupied += 1

        return round((occupied / len(units)) * 100, 1)

    def _get_properties_by_city(self, properties):
        """Distribution des propriétés par type"""
        type_data = {}

        # Mapping des types pour affichage
        type_labels = {
            'house': 'Maison',
            'apartment': 'Appartement',
            'villa': 'Villa',
            'studio': 'Studio',
            'cottage': 'Chalet',
            'townhouse': 'Maison de ville',
            'other': 'Autre',
        }

        for prop in properties:
            prop_type = prop.property_type or 'other'
            label = type_labels.get(prop_type, prop_type.capitalize())
            type_data[label] = type_data.get(label, 0) + 1

        return {
            'cities': list(type_data.keys()),  # Gardé comme 'cities' pour compatibilité avec le frontend
            'counts': list(type_data.values())
        }

    def _get_revenue_this_month(self, units):
        """Calcul du revenu du mois en cours (en temps réel)"""
        today = datetime.now()
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        reservations = request.env['onedesk.reservation'].sudo().search([
            ('unit_id', 'in', units.ids),
            ('status', 'in', ['paid', 'checked_in', 'completed']),
            ('end_date', '>=', month_start)
        ])

        return sum(reservations.mapped('total_price'))

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

    @http.route('/onedesk/dashboard/revenue-chart', type='jsonrpc', auth='user')
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

    @http.route('/onedesk/dashboard/occupancy-chart', type='jsonrpc', auth='user')
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
                    ('status', 'in', ['paid', 'checked_in']),
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

    @http.route('/onedesk/dashboard/reservations-chart', type='jsonrpc', auth='user')
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

        statuses = ['draft', 'paid', 'checked_in', 'completed', 'cancelled']
        labels = ['Brouillon', 'Payée', 'Enregistré', 'Complétée', 'Annulée']
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

    @http.route('/onedesk/dashboard/properties-ranking', type='jsonrpc', auth='user')
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

    @http.route('/onedesk/dashboard/user-activity', type='jsonrpc', auth='user')
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

    @http.route('/onedesk/dashboard/period-comparison', type='jsonrpc', auth='user')
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
                ('status', 'in', ['paid', 'checked_in', 'completed']),
                ('start_date', '>=', date_from),
                ('start_date', '<=', date_to)
            ])

            previous = request.env['onedesk.reservation'].search_count([
                ('unit_id', 'in', units.ids),
                ('status', 'in', ['paid', 'checked_in', 'completed']),
                ('start_date', '>=', prev_date_from),
                ('start_date', '<=', prev_date_to)
            ])

        elif metric == 'occupancy':
            current_occupied = 0
            for unit in units:
                if request.env['onedesk.reservation'].search_count([
                    ('unit_id', '=', unit.id),
                    ('status', 'in', ['paid', 'checked_in']),
                    ('start_date', '<=', date_to),
                    ('end_date', '>=', date_from)
                ]):
                    current_occupied += 1
            current = (current_occupied / len(units) * 100) if units else 0

            previous_occupied = 0
            for unit in units:
                if request.env['onedesk.reservation'].search_count([
                    ('unit_id', '=', unit.id),
                    ('status', 'in', ['paid', 'checked_in']),
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

    @http.route('/onedesk/dashboard/export/excel', type='json', auth='user', methods=['POST'])
    def export_dashboard_excel(self):
        """
        Exporter les données du dashboard en Excel
        """
        try:
            import io
            import base64
            import xlsxwriter
            from datetime import datetime

            dashboard = request.env['onedesk.dashboard'].search([
                ('user_id', '=', request.env.user.id),
                ('company_id', '=', request.env.company.id)
            ], limit=1)

            if not dashboard:
                return {'status': 'error', 'message': 'Dashboard non trouvé'}

            company_ids = dashboard._get_accessible_companies()
            properties = request.env['onedesk.property'].sudo().search([('company_id', 'in', company_ids)])
            units = request.env['onedesk.unit'].sudo().search([('property_id', 'in', properties.ids)])

            # Créer le fichier Excel en mémoire
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})

            # Formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#667eea',
                'font_color': 'white',
                'align': 'center',
                'border': 1
            })
            cell_format = workbook.add_format({'border': 1})
            currency_format = workbook.add_format({'num_format': '#,##0.00 €', 'border': 1})

            # Feuille 1: KPIs
            ws_kpis = workbook.add_worksheet('KPIs')
            ws_kpis.write(0, 0, 'Indicateur', header_format)
            ws_kpis.write(0, 1, 'Valeur', header_format)

            kpis_data = [
                ('Total Propriétés', len(properties)),
                ('Propriétés Actives', len(properties.filtered('active'))),
                ('Total Unités', len(units)),
                ('Unités Disponibles', len(units.filtered('available'))),
                ('Revenu du Mois', dashboard.revenue_this_month),
                ('Taux d\'Occupation (%)', self._get_occupancy_rate(units)),
                ('Réservations Confirmées', dashboard.reservations_confirmed_month),
            ]

            for idx, (label, value) in enumerate(kpis_data, start=1):
                ws_kpis.write(idx, 0, label, cell_format)
                if 'Revenu' in label:
                    ws_kpis.write(idx, 1, value, currency_format)
                else:
                    ws_kpis.write(idx, 1, value, cell_format)

            ws_kpis.set_column(0, 0, 30)
            ws_kpis.set_column(1, 1, 15)

            # Feuille 2: Revenus 12 mois
            revenue_data = self._get_revenue_12_months(units)
            ws_revenue = workbook.add_worksheet('Revenus 12 mois')

            ws_revenue.write(0, 0, 'Mois', header_format)
            ws_revenue.write(0, 1, 'Année Actuelle', header_format)
            ws_revenue.write(0, 2, 'Année Précédente', header_format)

            for idx, month in enumerate(revenue_data['months'], start=1):
                ws_revenue.write(idx, 0, month, cell_format)
                ws_revenue.write(idx, 1, revenue_data['current_year'][idx-1], currency_format)
                ws_revenue.write(idx, 2, revenue_data['previous_year'][idx-1], currency_format)

            ws_revenue.set_column(0, 0, 12)
            ws_revenue.set_column(1, 2, 18)

            # Feuille 3: Réservations par Statut
            reservations_data = self._get_reservations_by_status(units)
            ws_reservations = workbook.add_worksheet('Réservations')

            ws_reservations.write(0, 0, 'Statut', header_format)
            ws_reservations.write(0, 1, 'Nombre', header_format)

            for idx, (status, count) in enumerate(zip(reservations_data['statuses'], reservations_data['counts']), start=1):
                ws_reservations.write(idx, 0, status, cell_format)
                ws_reservations.write(idx, 1, count, cell_format)

            ws_reservations.set_column(0, 0, 20)
            ws_reservations.set_column(1, 1, 15)

            # Feuille 4: Propriétés par Ville
            properties_data = self._get_properties_by_city(properties)
            ws_properties = workbook.add_worksheet('Propriétés par Ville')

            ws_properties.write(0, 0, 'Ville', header_format)
            ws_properties.write(0, 1, 'Nombre', header_format)

            for idx, (city, count) in enumerate(zip(properties_data['cities'], properties_data['counts']), start=1):
                ws_properties.write(idx, 0, city, cell_format)
                ws_properties.write(idx, 1, count, cell_format)

            ws_properties.set_column(0, 0, 25)
            ws_properties.set_column(1, 1, 15)

            workbook.close()

            # Créer l'attachement
            output.seek(0)
            excel_data = output.read()
            excel_b64 = base64.b64encode(excel_data)
            filename = f"Dashboard_OneDesk_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

            attachment = request.env['ir.attachment'].sudo().create({
                'name': filename,
                'type': 'binary',
                'datas': excel_b64,
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'public': True,
            })

            return {
                'status': 'success',
                'file_url': f'/web/content/{attachment.id}?download=true'
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/onedesk/dashboard/export/pdf', type='json', auth='user', methods=['POST'])
    def export_dashboard_pdf(self):
        """
        Exporter le dashboard en PDF
        """
        try:
            import base64
            from datetime import datetime

            dashboard = request.env['onedesk.dashboard'].search([
                ('user_id', '=', request.env.user.id),
                ('company_id', '=', request.env.company.id)
            ], limit=1)

            if not dashboard:
                return {'status': 'error', 'message': 'Dashboard non trouvé'}

            company_ids = dashboard._get_accessible_companies()
            properties = request.env['onedesk.property'].sudo().search([('company_id', 'in', company_ids)])
            units = request.env['onedesk.unit'].sudo().search([('property_id', 'in', properties.ids)])

            # Préparer les données
            revenue_data = self._get_revenue_12_months(units)
            reservations_data = self._get_reservations_by_status(units)
            occupancy_rate = self._get_occupancy_rate(units)
            properties_data = self._get_properties_by_city(properties)

            # Générer le HTML pour le PDF
            html_content = f"""
            <html>
            <head>
                <meta charset="utf-8"/>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #667eea; text-align: center; }}
                    h2 {{ color: #333; border-bottom: 2px solid #667eea; padding-bottom: 5px; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                    th {{ background-color: #667eea; color: white; padding: 10px; text-align: left; }}
                    td {{ border: 1px solid #ddd; padding: 8px; }}
                    tr:nth-child(even) {{ background-color: #f2f2f2; }}
                    .kpi-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }}
                    .kpi-card {{ background: #f8f9fa; padding: 15px; border-left: 4px solid #667eea; }}
                    .kpi-value {{ font-size: 24px; font-weight: bold; color: #333; }}
                    .kpi-label {{ color: #666; margin-top: 5px; }}
                </style>
            </head>
            <body>
                <h1>📊 Dashboard OneDesk</h1>
                <p style="text-align: center; color: #666;">Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>

                <h2>Indicateurs Clés</h2>
                <div class="kpi-grid">
                    <div class="kpi-card">
                        <div class="kpi-value">{len(properties)}</div>
                        <div class="kpi-label">Total Propriétés</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-value">{len(units)}</div>
                        <div class="kpi-label">Total Unités</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-value">{occupancy_rate}%</div>
                        <div class="kpi-label">Taux d'Occupation</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-value">{dashboard.revenue_this_month:,.2f} €</div>
                        <div class="kpi-label">Revenu du Mois</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-value">{dashboard.reservations_confirmed_month}</div>
                        <div class="kpi-label">Réservations Confirmées</div>
                    </div>
                </div>

                <h2>Revenus (12 derniers mois)</h2>
                <table>
                    <tr>
                        <th>Mois</th>
                        <th>Année Actuelle</th>
                        <th>Année Précédente</th>
                    </tr>
                    {''.join([f'<tr><td>{month}</td><td>{current:,.2f} €</td><td>{prev:,.2f} €</td></tr>'
                              for month, current, prev in zip(revenue_data['months'],
                                                             revenue_data['current_year'],
                                                             revenue_data['previous_year'])])}
                </table>

                <h2>Réservations par Statut</h2>
                <table>
                    <tr>
                        <th>Statut</th>
                        <th>Nombre</th>
                    </tr>
                    {''.join([f'<tr><td>{status}</td><td>{count}</td></tr>'
                              for status, count in zip(reservations_data['statuses'],
                                                      reservations_data['counts'])])}
                </table>

                <h2>Propriétés par Ville</h2>
                <table>
                    <tr>
                        <th>Ville</th>
                        <th>Nombre de Propriétés</th>
                    </tr>
                    {''.join([f'<tr><td>{city}</td><td>{count}</td></tr>'
                              for city, count in zip(properties_data['cities'],
                                                    properties_data['counts'])])}
                </table>
            </body>
            </html>
            """

            # Générer le PDF avec wkhtmltopdf (Odoo natif)
            # Utiliser _run_wkhtmltopdf avec le bon format pour Odoo 17
            IrActionsReport = request.env['ir.actions.report']

            # Créer un rapport temporaire
            pdf_content, _ = IrActionsReport._run_wkhtmltopdf(
                bodies=[html_content.encode('utf-8')],
                landscape=False,
                specific_paperformat_args={
                    'data-report-margin-top': 10,
                    'data-report-header-spacing': 10
                }
            )

            # Encoder en base64
            pdf_b64 = base64.b64encode(pdf_content)

            # Créer l'attachement
            filename = f"Dashboard_OneDesk_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

            attachment = request.env['ir.attachment'].sudo().create({
                'name': filename,
                'type': 'binary',
                'datas': pdf_b64,
                'mimetype': 'application/pdf',
                'public': True,
            })

            return {
                'status': 'success',
                'file_url': f'/web/content/{attachment.id}?download=true'
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
