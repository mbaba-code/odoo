from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class OnedeskPaymentRetry(models.Model):
    """Track payment reminders and retry attempts"""
    _name = 'onedesk.payment.retry'
    _description = 'Payment Retry Tracking'
    _inherit = ['mail.thread']
    _rec_name = 'reservation_id'

    # ========== RELATIONS ==========
    reservation_id = fields.Many2one(
        'onedesk.reservation',
        string='Réservation',
        required=True,
        ondelete='cascade',
        index=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Entreprise',
        related='reservation_id.company_id',
        store=True,
        readonly=True
    )

    # ========== PAYMENT STATUS ==========
    payment_status = fields.Selection([
        ('pending', '⏳ En attente'),
        ('sent_day1', '📧 Email Jour 1 envoyé'),
        ('sent_day3', '📧 Email Jour 3 envoyé'),
        ('paid', '✅ Payée'),
        ('cancelled', '❌ Annulée'),
    ], string='Statut', default='pending', tracking=True, index=True)

    # ========== RETRY TRACKING ==========
    created_date = fields.Datetime(string='Date création', default=fields.Datetime.now, readonly=True)
    first_reminder_sent = fields.Datetime(string='1er rappel envoyé')
    second_reminder_sent = fields.Datetime(string='2e rappel envoyé')
    last_retry_date = fields.Datetime(string='Dernier essai', readonly=True)
    retry_count = fields.Integer(string='Nombre de tentatives', default=0, readonly=True)

    # ========== AUTO-CANCEL SETTINGS ==========
    days_until_cancel = fields.Integer(
        string='Jours avant annulation',
        default=7,
        help="Nombre de jours sans paiement avant annulation auto"
    )
    auto_cancel_date = fields.Datetime(string='Date d\'annulation auto prévue')

    @api.model
    def _get_pending_payments(self):
        """Get all pending payments older than 1 day"""
        return self.search([
            ('payment_status', '=', 'pending'),
            ('created_date', '<=', datetime.now() - timedelta(days=1))
        ])

    @api.model
    def _get_day3_reminders(self):
        """Get all pending payments older than 3 days"""
        return self.search([
            ('payment_status', '=', 'sent_day1'),
            ('first_reminder_sent', '<=', datetime.now() - timedelta(days=2))
        ])

    @api.model
    def _get_auto_cancel(self):
        """Get all reservations that should be cancelled (7 days no payment)"""
        return self.search([
            ('payment_status', 'in', ['pending', 'sent_day1', 'sent_day3']),
            ('created_date', '<=', datetime.now() - timedelta(days=7))
        ])

    def action_send_day1_reminder(self):
        """Send Day 1 payment reminder email"""
        for retry in self:
            if retry.payment_status != 'pending':
                continue

            try:
                reservation = retry.reservation_id

                # Send email via mail.mail
                mail_values = {
                    'subject': f"💳 Paiement en attente - {reservation.name}",
                    'body_html': f"""
                    <p>Bonjour {reservation.partner_id.name},</p>
                    <p>Nous avons remarqué que le paiement de votre réservation n'a pas encore été reçu.</p>
                    <p><strong>Réservation:</strong> {reservation.name}</p>
                    <p><strong>Montant à payer:</strong> {reservation.total_price}€</p>
                    <p><a href="{self.env['ir.config_parameter'].sudo().get_param('web.base.url')}/onedesk/payment/{reservation.id}"
                           style="background-color: #1f77d2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                           Payer maintenant
                        </a></p>
                    <p>Merci!</p>
                    """,
                    'email_to': reservation.partner_id.email,
                    'email_from': reservation.company_id.email or self.env.user.email,
                    'company_id': reservation.company_id.id,
                }
                mail = self.env['mail.mail'].sudo().create(mail_values)
                mail.send()

                # Update tracking
                retry.payment_status = 'sent_day1'
                retry.first_reminder_sent = datetime.now()
                retry.message_post(body="📧 Email de rappel Jour 1 envoyé", message_type='comment')

            except Exception as e:
                self.message_post(body=f"⚠️ Erreur envoi email Day 1: {str(e)}", message_type='comment')

    def action_send_day3_reminder(self):
        """Send Day 3 payment reminder email (URGENT)"""
        for retry in self:
            if retry.payment_status != 'sent_day1':
                continue

            try:
                reservation = retry.reservation_id

                # Send URGENT email
                mail_values = {
                    'subject': f"🚨 URGENT: Paiement requis - {reservation.name}",
                    'body_html': f"""
                    <p>Bonjour {reservation.partner_id.name},</p>
                    <p><strong style="color: red;">Votre paiement est maintenant en retard!</strong></p>
                    <p>Si nous ne recevons pas votre paiement sous 4 jours, votre réservation sera annulée automatiquement.</p>
                    <p><strong>Réservation:</strong> {reservation.name}</p>
                    <p><strong>Montant à payer:</strong> {reservation.total_price}€</p>
                    <p><a href="{self.env['ir.config_parameter'].sudo().get_param('web.base.url')}/onedesk/payment/{reservation.id}"
                           style="background-color: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                           PAYER MAINTENANT
                        </a></p>
                    <p>Cordialement,<br/>L'équipe OneDesk</p>
                    """,
                    'email_to': reservation.partner_id.email,
                    'email_from': reservation.company_id.email or self.env.user.email,
                    'company_id': reservation.company_id.id,
                }
                mail = self.env['mail.mail'].sudo().create(mail_values)
                mail.send()

                # Update tracking
                retry.payment_status = 'sent_day3'
                retry.second_reminder_sent = datetime.now()
                retry.auto_cancel_date = datetime.now() + timedelta(days=4)
                retry.message_post(body="🚨 Email URGENT Jour 3 envoyé", message_type='comment')

            except Exception as e:
                retry.message_post(body=f"⚠️ Erreur envoi email Day 3: {str(e)}", message_type='comment')

    def action_auto_cancel(self):
        """Auto-cancel reservation if no payment after 7 days"""
        for retry in self:
            try:
                reservation = retry.reservation_id

                # Cancel reservation
                reservation.status = 'cancelled'
                reservation.message_post(
                    body="❌ Réservation annulée automatiquement - Paiement non reçu après 7 jours",
                    message_type='comment'
                )

                # Update retry status
                retry.payment_status = 'cancelled'
                retry.message_post(body="❌ Réservation annulée automatiquement", message_type='comment')

                # Send cancellation email to customer
                mail_values = {
                    'subject': f"⚠️ Réservation annulée - {reservation.name}",
                    'body_html': f"""
                    <p>Bonjour {reservation.partner_id.name},</p>
                    <p>Votre réservation <strong>{reservation.name}</strong> a été annulée en raison du non-paiement.</p>
                    <p>Si vous pensez que c'est une erreur, veuillez nous contacter au plus tôt.</p>
                    <p>Cordialement,<br/>L'équipe OneDesk</p>
                    """,
                    'email_to': reservation.partner_id.email,
                    'email_from': reservation.company_id.email or self.env.user.email,
                    'company_id': reservation.company_id.id,
                }
                mail = self.env['mail.mail'].sudo().create(mail_values)
                mail.send()

            except Exception as e:
                retry.message_post(body=f"⚠️ Erreur annulation auto: {str(e)}", message_type='comment')

    @api.model
    def run_payment_retry_cron(self):
        """Cron job to run payment reminders (called daily)"""
        _logger.info("▶️ Starting payment retry cron job")

        # Day 1 reminders
        day1_retries = self._get_pending_payments()
        for retry in day1_retries:
            retry.action_send_day1_reminder()

        # Day 3 reminders
        day3_retries = self._get_day3_reminders()
        for retry in day3_retries:
            retry.action_send_day3_reminder()

        # Auto-cancel
        cancel_retries = self._get_auto_cancel()
        for retry in cancel_retries:
            retry.action_auto_cancel()

        _logger.info(f"✅ Cron completed: {len(day1_retries)} Day1, {len(day3_retries)} Day3, {len(cancel_retries)} cancelled")
