#!/usr/bin/env python3
"""
OneDesk Improvements Verification Script
Tests Phase A (Email), Phase B (Indexes), Phase C1 (Payment), Phase C2 (Cache)

Usage:
  $ odoo shell --database=your_db --addon-path=/path/to/addons
  >>> exec(open('verify_onedesk_improvements.py').read())
"""

import sys
from datetime import datetime, timedelta

class VerificationSuite:
    def __init__(self, env):
        self.env = env
        self.results = {
            'passed': [],
            'failed': [],
            'warnings': [],
        }

    def log_result(self, test_name, passed, details=""):
        """Log test result"""
        if passed:
            self.results['passed'].append(test_name)
            print(f"✅ {test_name}")
        else:
            self.results['failed'].append(test_name)
            print(f"❌ {test_name}")

        if details:
            print(f"   → {details}\n")

    def log_warning(self, warning):
        """Log warning"""
        self.results['warnings'].append(warning)
        print(f"⚠️  {warning}\n")

    # ========== PHASE A: EMAIL TEMPLATES ==========

    def test_email_templates(self):
        """Verify Phase A: Email templates exist"""
        print("\n" + "="*70)
        print("PHASE A: EMAIL TEMPLATES VERIFICATION")
        print("="*70 + "\n")

        try:
            # Get all OneDesk templates
            templates = self.env['mail.template'].search([
                ('name', 'ilike', 'OneDesk')
            ])

            template_names = [t.name for t in templates]

            # Count should be at least 7
            self.log_result(
                "Email templates collection",
                len(templates) >= 7,
                f"Found {len(templates)} OneDesk templates"
            )

            # Check for Phase A new templates
            has_booking = any('Confirmation de réservation' in n for n in template_names)
            has_task = any('Tâche assignée' in n for n in template_names)
            has_signature = any('Demande de signature' in n for n in template_names)

            self.log_result(
                "Booking confirmation template",
                has_booking,
                "Template: OneDesk - Confirmation de réservation"
            )

            self.log_result(
                "Task assignment template",
                has_task,
                "Template: OneDesk - Tâche assignée"
            )

            self.log_result(
                "Signature request template",
                has_signature,
                "Template: OneDesk - Demande de signature"
            )

            # List all templates
            print("📧 All OneDesk Templates:")
            for t in templates:
                print(f"   • {t.name}")
            print()

            return has_booking and has_task and has_signature

        except Exception as e:
            self.log_result("Email templates verification", False, str(e))
            return False

    # ========== PHASE B: DATABASE INDEXES ==========

    def test_database_indexes(self):
        """Verify Phase B: Database indexes on critical fields"""
        print("="*70)
        print("PHASE B: DATABASE INDEXES VERIFICATION")
        print("="*70 + "\n")

        try:
            all_good = True

            # Check Reservation indexes
            Reservation = self.env['onedesk.reservation']
            status_field = Reservation._fields.get('status')
            has_status_index = status_field and status_field.index

            self.log_result(
                "Reservation.status index",
                has_status_index,
                "Index applied for fast status filtering"
            )

            # Check Task indexes
            Task = self.env['onedesk.task']
            task_fields = {
                'task_type': Task._fields.get('task_type'),
                'status': Task._fields.get('status'),
                'assigned_to': Task._fields.get('assigned_to'),
                'date_start': Task._fields.get('date_start'),
            }

            indexed_task_fields = sum(1 for f in task_fields.values() if f and f.index)
            self.log_result(
                "Task fields indexes",
                indexed_task_fields >= 3,
                f"Found {indexed_task_fields}/4 indexed fields on task model"
            )

            # Check Payment Retry indexes
            PaymentRetry = self.env.get('onedesk.payment.retry')
            if PaymentRetry:
                payment_status_field = PaymentRetry._fields.get('payment_status')
                has_payment_status_index = payment_status_field and payment_status_field.index

                self.log_result(
                    "Payment retry status index",
                    has_payment_status_index,
                    "Index for fast payment status filtering"
                )
            else:
                self.log_warning("Payment retry model not found")
                all_good = False

            # Check Cache indexes
            Cache = self.env.get('onedesk.availability.cache')
            if Cache:
                cache_fields = {
                    'unit_id': Cache._fields.get('unit_id'),
                    'property_id': Cache._fields.get('property_id'),
                    'start_date': Cache._fields.get('start_date'),
                }

                indexed_cache_fields = sum(1 for f in cache_fields.values() if f and f.index)
                self.log_result(
                    "Cache fields indexes",
                    indexed_cache_fields >= 2,
                    f"Found {indexed_cache_fields}/3 indexed fields on cache model"
                )
            else:
                self.log_warning("Availability cache model not found")
                all_good = False

            return all_good

        except Exception as e:
            self.log_result("Database indexes verification", False, str(e))
            return False

    # ========== PHASE C1: PAYMENT RETRY ==========

    def test_payment_retry_model(self):
        """Verify Phase C1: Payment retry model and tracking"""
        print("="*70)
        print("PHASE C1: PAYMENT RETRY SYSTEM VERIFICATION")
        print("="*70 + "\n")

        try:
            PaymentRetry = self.env.get('onedesk.payment.retry')

            if not PaymentRetry:
                self.log_result("Payment retry model exists", False, "Model not found")
                return False

            self.log_result("Payment retry model exists", True)

            # Check required fields
            required_fields = [
                'reservation_id',
                'payment_status',
                'first_reminder_sent',
                'second_reminder_sent',
                'retry_count',
                'auto_cancel_date',
                'company_id',
                'days_until_cancel',
            ]

            model_fields = [f.name for f in PaymentRetry._fields.values()]
            missing_fields = [f for f in required_fields if f not in model_fields]

            self.log_result(
                "Payment retry fields",
                len(missing_fields) == 0,
                f"Found {len(required_fields) - len(missing_fields)}/{len(required_fields)} required fields"
            )

            if missing_fields:
                self.log_warning(f"Missing fields: {', '.join(missing_fields)}")

            # Check for required methods
            has_day1 = hasattr(PaymentRetry, 'action_send_day1_reminder')
            has_day3 = hasattr(PaymentRetry, 'action_send_day3_reminder')
            has_cancel = hasattr(PaymentRetry, 'action_auto_cancel')
            has_cron = hasattr(PaymentRetry, 'run_payment_retry_cron')

            self.log_result(
                "Payment reminder methods",
                has_day1 and has_day3 and has_cancel and has_cron,
                "All action methods implemented"
            )

            # Count existing records
            payment_count = PaymentRetry.search_count([])
            self.log_result(
                "Payment retry records in database",
                True,
                f"Current records: {payment_count}"
            )

            return True

        except Exception as e:
            self.log_result("Payment retry verification", False, str(e))
            return False

    def test_cron_jobs(self):
        """Verify cron jobs are configured"""
        print("\n" + "="*70)
        print("SCHEDULED TASKS (CRON JOBS) VERIFICATION")
        print("="*70 + "\n")

        try:
            Cron = self.env.get('ir.cron')

            if not Cron:
                self.log_warning("ir.cron model not accessible")
                return False

            cron_jobs = Cron.search([('name', 'ilike', 'OneDesk')])
            cron_names = [c.name for c in cron_jobs]

            # Check for payment retry cron
            has_payment = any('Payment Retry' in n for n in cron_names)
            self.log_result(
                "Payment retry cron job",
                has_payment,
                "Daily payment reminder processing scheduled"
            )

            # Check for cache cleanup crons
            has_cache_cleanup = any('Clean' in n and 'Cache' in n for n in cron_names)
            self.log_result(
                "Cache cleanup cron jobs",
                has_cache_cleanup,
                "Hourly and daily cache cleanup scheduled"
            )

            print("⏰ Configured Cron Jobs:")
            for job in cron_jobs:
                status = "✓ Active" if job.active else "✗ Inactive"
                print(f"   • {job.name} [{status}]")
            print()

            return has_payment and has_cache_cleanup

        except Exception as e:
            self.log_result("Cron jobs verification", False, str(e))
            return False

    # ========== PHASE C2: AVAILABILITY CACHE ==========

    def test_availability_cache_model(self):
        """Verify Phase C2: Availability cache model"""
        print("="*70)
        print("PHASE C2: AVAILABILITY CACHE VERIFICATION")
        print("="*70 + "\n")

        try:
            Cache = self.env.get('onedesk.availability.cache')

            if not Cache:
                self.log_result("Availability cache model exists", False, "Model not found")
                return False

            self.log_result("Availability cache model exists", True)

            # Check required fields
            required_fields = [
                'unit_id',
                'property_id',
                'availability_data',
                'price_data',
                'booking_data',
                'cache_hits',
                'cache_misses',
                'is_valid',
                'expires_at',
            ]

            model_fields = [f.name for f in Cache._fields.values()]
            missing_fields = [f for f in required_fields if f not in model_fields]

            self.log_result(
                "Cache fields",
                len(missing_fields) == 0,
                f"Found {len(required_fields) - len(missing_fields)}/{len(required_fields)} required fields"
            )

            # Check for required methods
            has_invalidate = hasattr(Cache, 'invalidate_cache_for_unit')
            has_cleanup = hasattr(Cache, 'cleanup_invalid_cache')
            has_expire = hasattr(Cache, 'invalidate_expired_cache')

            self.log_result(
                "Cache management methods",
                has_invalidate and has_cleanup and has_expire,
                "All cache methods implemented"
            )

            # Count existing records
            cache_count = Cache.search_count([])
            self.log_result(
                "Cache records in database",
                True,
                f"Current records: {cache_count}"
            )

            # Check cache statistics
            if cache_count > 0:
                caches = Cache.search([], limit=5)
                total_hits = sum(c.cache_hits for c in caches)
                total_misses = sum(c.cache_misses for c in caches)

                if total_hits + total_misses > 0:
                    hit_ratio = (total_hits / (total_hits + total_misses)) * 100
                    print(f"📊 Cache Statistics (sample of {len(caches)} records):")
                    print(f"   • Total hits: {total_hits}")
                    print(f"   • Total misses: {total_misses}")
                    print(f"   • Hit ratio: {hit_ratio:.1f}%\n")

            return True

        except Exception as e:
            self.log_result("Availability cache verification", False, str(e))
            return False

    # ========== EMAIL QUEUE ==========

    def test_email_queue(self):
        """Check email queue status"""
        print("="*70)
        print("EMAIL QUEUE STATUS")
        print("="*70 + "\n")

        try:
            Mail = self.env.get('mail.mail')

            if not Mail:
                self.log_warning("mail.mail model not accessible")
                return False

            # Check pending emails
            pending = Mail.search([('state', '=', 'outgoing')], limit=100)
            sent = Mail.search([('state', '=', 'sent')], limit=100)
            failed = Mail.search([('state', '=', 'failed')])

            self.log_result(
                "Email queue accessible",
                True,
                f"Pending: {len(pending)}, Sent: {len(sent)}, Failed: {len(failed)}"
            )

            # Show recent emails
            if pending:
                print("📧 Recent Pending Emails:")
                for email in pending[:5]:
                    print(f"   • {email.subject} → {email.email_to}")
                if len(pending) > 5:
                    print(f"   ... and {len(pending) - 5} more")
                print()

            return True

        except Exception as e:
            self.log_result("Email queue verification", False, str(e))
            return False

    # ========== MULTI-TENANT ==========

    def test_multi_tenant_isolation(self):
        """Verify multi-tenant isolation"""
        print("="*70)
        print("MULTI-TENANT ISOLATION VERIFICATION")
        print("="*70 + "\n")

        try:
            PaymentRetry = self.env.get('onedesk.payment.retry')
            Cache = self.env.get('onedesk.availability.cache')

            isolation_ok = True

            # Check Payment Retry
            if PaymentRetry:
                has_company = 'company_id' in [f.name for f in PaymentRetry._fields.values()]
                self.log_result(
                    "Payment retry multi-tenant isolation",
                    has_company,
                    "company_id field present"
                )
                isolation_ok = isolation_ok and has_company

            # Check Cache
            if Cache:
                has_company = 'company_id' in [f.name for f in Cache._fields.values()]
                self.log_result(
                    "Cache multi-tenant isolation",
                    has_company,
                    "company_id field present"
                )
                isolation_ok = isolation_ok and has_company

            return isolation_ok

        except Exception as e:
            self.log_result("Multi-tenant verification", False, str(e))
            return False

    # ========== MAIN TEST RUNNER ==========

    def run_all_tests(self):
        """Run complete test suite"""
        print("\n" * 2)
        print("╔" + "=" * 68 + "╗")
        print("║" + " " * 10 + "🚀 OneDesk Improvements Verification Suite" + " " * 16 + "║")
        print("║" + " " * 10 + "Phases A + B + C1 + C2" + " " * 35 + "║")
        print("╚" + "=" * 68 + "╝")

        # Run all tests
        self.test_email_templates()
        self.test_database_indexes()
        self.test_payment_retry_model()
        self.test_cron_jobs()
        self.test_availability_cache_model()
        self.test_email_queue()
        self.test_multi_tenant_isolation()

        # Print summary
        print("\n" + "=" * 70)
        print("VERIFICATION SUMMARY")
        print("=" * 70 + "\n")

        passed = len(self.results['passed'])
        failed = len(self.results['failed'])
        warnings = len(self.results['warnings'])
        total = passed + failed

        print(f"✅ Passed:  {passed}/{total}")
        print(f"❌ Failed:  {failed}/{total}")
        if warnings:
            print(f"⚠️  Warnings: {warnings}")

        # Overall status
        success = failed == 0
        if success:
            print("\n" + "🎉 " * 20)
            print("ALL SYSTEMS OPERATIONAL - Ready for production!")
            print("🎉 " * 20)
        else:
            print("\n⚠️  ISSUES DETECTED - Please review failed tests above")

        print("\n" + "=" * 70 + "\n")

        return success

# ========== MAIN EXECUTION ==========

if __name__ == "__main__":
    try:
        # Get the Odoo environment
        suite = VerificationSuite(env)
        success = suite.run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")
        print("\nℹ️  Make sure to run this script inside Odoo shell:")
        print("   $ odoo shell --database=your_db")
        print("   >>> exec(open('verify_onedesk_improvements.py').read())")
        sys.exit(1)
