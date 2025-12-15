from odoo import models, fields, api

class OnedeskTask(models.Model):
    _name = 'onedesk.task'
    _description = 'Tâches du personnel'
    _rec_name = 'name'
    _inherit = ['mail.thread']  # Enable chatter & message_post()

    # ========== ARCHIVE ==========
    active = fields.Boolean(default=True)

    name = fields.Char(string='Nom de la tâche', required=True)
    task_type = fields.Selection([
        ('checkin', 'Check-in'),
        ('checkout', 'Check-out'),
        ('menage', 'Ménage'),
        ('maintenance', 'Maintenance')],
        string='Type de tâche', required=True, index=True)
    assigned_to = fields.Many2one('res.users', string='Assigné à', index=True)
    date_start = fields.Datetime(string='Date début', required=True, index=True)
    date_end = fields.Datetime(string='Date fin')
    status = fields.Selection([
        ('todo', 'À faire'),
        ('in_progress', 'En cours'),
        ('done', 'Terminée')],
        string='Statut', default='todo', tracking=True, index=True)  # Fast filtering by status

    # ========== PRIORITY & IMPORTANCE ==========
    priority = fields.Selection([
        ('low', '🟢 Basse'),
        ('medium', '🟡 Moyenne'),
        ('high', '🔴 Haute'),
        ('urgent', '⚠️ Urgente')],
        string='Priorité', default='medium', tracking=True)

    # ========== TIME TRACKING ==========
    estimated_hours = fields.Float(string='Heures estimées',
                                  help="Durée estimée pour accomplir la tâche (en heures)")
    actual_hours = fields.Float(string='Heures réelles',
                               help="Heures réelles passées sur la tâche")

    # ========== NOTES & CHECKLIST ==========
    description = fields.Text(string='Description/Checklist',
                             help="Instructions détaillées et checklist pour la tâche")
    completion_notes = fields.Text(string='Notes de fin',
                                  help="Observations/problèmes rencontrés lors de l'exécution")
    completion_photo = fields.Image(string='Photo de fin',
                                   help="Photo de preuve de fin de tâche", attachment=True)

    # ========== RELATIONS ==========
    reservation_id = fields.Many2one('onedesk.reservation', string='Réservation associée', ondelete='cascade')
    unit_id = fields.Many2one('onedesk.unit', string='Unité',
                             compute='_compute_unit_id', store=True,
                             help="Unité sur laquelle porte la tâche")
    calendar_event_id = fields.Many2one('calendar.event', string="Événement calendrier")

    @api.depends('reservation_id')
    def _compute_unit_id(self):
        """Calcule l'unité depuis la réservation"""
        for record in self:
            record.unit_id = record.reservation_id.unit_id if record.reservation_id else None

    def _get_estimated_hours_for_type(self, task_type):
        """Retourne les heures estimées selon le type de tâche"""
        estimates = {
            'checkin': 1.0,      # Check-in: 1 heure
            'checkout': 0.5,     # Check-out: 30 min
            'menage': 2.0,       # Nettoyage: 2 heures (peut être overridé par cleaning_duration_hours de l'unité)
            'maintenance': 3.0,  # Maintenance: 3 heures
        }
        return estimates.get(task_type, 1.0)

    @api.model
    def create_task_from_reservation(self, reservation):
        """Créer automatiquement les tâches liées à une réservation"""
        tasks = []

        # Tâche Check-in
        checkin_task = self.create({
            'name': f"Check-in – {reservation.unit_id.name}",
            'task_type': 'checkin',
            'date_start': reservation.start_date,
            'date_end': reservation.start_date,  # même date pour check-in
            'reservation_id': reservation.id,
            'priority': 'high',  # Check-in est prioritaire
            'estimated_hours': self._get_estimated_hours_for_type('checkin'),
            'description': f"Check-in du client: {reservation.partner_id.name}\nUnité: {reservation.unit_id.name}",
        })
        tasks.append(checkin_task)

        # Tâche Ménage / Check-out
        cleaning_hours = reservation.unit_id.cleaning_duration_hours or self._get_estimated_hours_for_type('menage')
        menage_task = self.create({
            'name': f"Ménage – {reservation.unit_id.name}",
            'task_type': 'menage',
            'date_start': reservation.end_date,
            'date_end': reservation.end_date,
            'reservation_id': reservation.id,
            'estimated_hours': cleaning_hours,
            'description': f"Nettoyage après départ du client\nUnité: {reservation.unit_id.name}\nNotes: {reservation.unit_id.maintenance_notes or 'Aucune'}",
        })
        tasks.append(menage_task)

        return tasks

    @api.model
    def create(self, vals_list):
        tasks = super().create(vals_list)
        # Création automatique de l'événement calendrier pour chaque tâche
        for task in tasks:
            event_vals = {
                'name': task.name,
                'start': task.date_start,
                'stop': task.date_end or task.date_start,
                'user_id': task.assigned_to.id if task.assigned_to else False,
                'description': f"Tâche: {task.name}\nType: {task.task_type}",
            }
            # Création avec sudo() pour contourner les ir.rules
            event = self.env['calendar.event'].sudo().create(event_vals)
            # Assignement avec sudo() pour contourner les ir.rules
            task.sudo().write({'calendar_event_id': event.id})

            # ========== EMAIL TRIGGER: Task Assignment ==========
            if task.assigned_to and task.assigned_to.email:
                try:
                    # Get the property/unit company for multi-tenant
                    company_id = task.reservation_id.company_id if task.reservation_id else self.env.company

                    # Create email via mail.mail (simple approach for Odoo 19)
                    mail_values = {
                        'subject': f"📋 Nouvelle tâche: {task.name}",
                        'body_html': f"<p>Bonjour {task.assigned_to.name},</p><p>Une nouvelle tâche vous a été assignée: <strong>{task.name}</strong> ({task.get_task_type_display()})</p><p>Date: {task.date_start.strftime('%d/%m/%Y %H:%M')}</p><p>Durée estimée: {task.estimated_hours}h</p>",
                        'email_to': task.assigned_to.email,
                        'email_from': company_id.email or self.env.user.email,
                        'company_id': company_id.id,
                    }
                    mail = self.env['mail.mail'].sudo().create(mail_values)
                    mail.send()
                    task.message_post(body=f"📧 Email d'assignation envoyé à {task.assigned_to.name}", message_type='comment')
                except Exception as e:
                    task.message_post(body=f"⚠️ Erreur envoi email assignation: {str(e)}", message_type='comment')

        return tasks

    def write(self, vals):
        res = super().write(vals)
        # Mise à jour automatique de l'événement calendrier
        for task in self:
            if task.calendar_event_id:
                update_vals = {}
                if 'name' in vals:
                    update_vals['name'] = vals['name']
                if 'date_start' in vals:
                    update_vals['start'] = vals['date_start']
                if 'date_end' in vals:
                    update_vals['stop'] = vals['date_end']
                if 'assigned_to' in vals:
                    update_vals['user_id'] = vals['assigned_to']
                if update_vals:
                    # Mise à jour avec sudo() pour contourner les ir.rules
                    task.calendar_event_id.sudo().write(update_vals)
        return res
    
    @api.model
    def _valid_field_parameter(self, field, name):
        return name == 'tracking' or super()._valid_field_parameter(field, name)


# Héritage du modèle réservation pour créer automatiquement les tâches
class OnedeskReservation(models.Model):
    _inherit = 'onedesk.reservation'

    @api.model
    def create(self, vals_list):
        reservations = super().create(vals_list)
        # Crée les tâches automatiquement pour chaque réservation
        for reservation in reservations:
            self.env['onedesk.task'].create_task_from_reservation(reservation)
        return reservations
