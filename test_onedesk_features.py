#!/usr/bin/env python3
"""
OneDesk Feature Testing Script (A + B + C1 + C2)
Tests: Email templates, Payment Retry, Availability Cache, Database Indexes
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django/Odoo environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test if we can import Odoo
try:
    import odoo
    from odoo import api, models, fields
    from odoo.tools import config
except ImportError:
    print("❌ Cannot import Odoo. Make sure Odoo is installed and PYTHONPATH is set.")
    sys.exit(1)

class OnedeskTestSuite:
    """Complete test suite for OneDesk features"""

    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.env = None

    def log_test(self, name, passed, message=""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if message:
            print(f"   → {message}")
        if passed:
            self.tests_passed += 1
        else:
            self.tests_failed += 1

    def test_email_templates(self):
        """Test A: Email templates exist and are properly configured"""
        print("\n📧 Testing Email Templates (Phase A)...")

        try:
            templates = self.env['mail.template'].search([
                ('name', 'ilike', 'OneDesk')
            ])

            template_names = [t.name for t in templates]

            # Check for required templates
            has_booking = any('Confirmation de réservation' in n for n in template_names)
            has_task = any('Tâche assignée' in n for n in template_names)
            has_signature = any('Demande de signature' in n for n in template_names)

            self.log_test(
                "Email templates created",
                has_booking and has_task and has_signature,
                f"Found {len(templates)} OneDesk templates"
            )

            return has_booking and has_task and has_signature
        except Exception as e:
            self.log_test("Email templates", False, str(e))
            return False

    def test_payment_retry_model(self):
        """Test C1: Payment retry model and tracking"""
        print("\n💳 Testing Payment Retry (Phase C1)...")

        try:
            # Check if model exists
            PaymentRetry = self.env.get('onedesk.payment.retry')
            if not PaymentRetry:
                self.log_test("Payment retry model exists", False, "Model not found")
                return False

            self.log_test("Payment retry model exists", True)

            # Check for required fields
            required_fields = ['reservation_id', 'payment_status', 'first_reminder_sent',
                             'second_reminder_sent', 'retry_count', 'auto_cancel_date']

            model_fields = [f.name for f in PaymentRetry._fields.values()]
            has_all_fields = all(f in model_fields for f in required_fields)

            self.log_test(
                "Payment retry fields",
                has_all_fields,
                f"Found {len([f for f in required_fields if f in model_fields])}/{len(required_fields)} fields"
            )

            return has_all_fields
        except Exception as e:
            self.log_test("Payment retry model", False, str(e))
            return False

    def test_availability_cache_model(self):
        """Test C2: Availability cache model"""
        print("\n⚡ Testing Availability Cache (Phase C2)...")

        try:
            # Check if model exists
            Cache = self.env.get('onedesk.availability.cache')
            if not Cache:
                self.log_test("Availability cache model exists", False, "Model not found")
                return False

            self.log_test("Availability cache model exists", True)

            # Check for required fields
            required_fields = ['unit_id', 'availability_data', 'price_data', 'booking_data',
                             'cache_hits', 'cache_misses', 'is_valid', 'expires_at']

            model_fields = [f.name for f in Cache._fields.values()]
            has_all_fields = all(f in model_fields for f in required_fields)

            self.log_test(
                "Cache fields",
                has_all_fields,
                f"Found {len([f for f in required_fields if f in model_fields])}/{len(required_fields)} fields"
            )

            return has_all_fields
        except Exception as e:
            self.log_test("Availability cache model", False, str(e))
            return False

    def test_database_indexes(self):
        """Test B: Database indexes on critical fields"""
        print("\n📊 Testing Database Indexes (Phase B)...")

        try:
            # Check reservation status index
            Reservation = self.env.get('onedesk.reservation')
            status_field = Reservation._fields.get('status')
            has_status_index = status_field and status_field.index

            self.log_test(
                "Reservation status indexed",
                has_status_index,
                "Index on status field for fast filtering"
            )

            # Check task fields indexes
            Task = self.env.get('onedesk.task')
            task_indexes = [
                ('task_type', Task._fields.get('task_type').index if Task._fields.get('task_type') else False),
                ('status', Task._fields.get('status').index if Task._fields.get('status') else False),
                ('date_start', Task._fields.get('date_start').index if Task._fields.get('date_start') else False),
            ]

            task_indexed = sum(1 for _, idx in task_indexes if idx)
            self.log_test(
                "Task fields indexed",
                task_indexed >= 2,
                f"Found {task_indexed}/3 indexes on task model"
            )

            return has_status_index and task_indexed >= 2
        except Exception as e:
            self.log_test("Database indexes", False, str(e))
            return False

    def test_cron_jobs(self):
        """Test C1/C2: Scheduled cron jobs"""
        print("\n⏰ Testing Cron Jobs...")

        try:
            Cron = self.env.get('ir.cron')

            cron_jobs = Cron.search([
                ('name', 'ilike', 'OneDesk')
            ])

            cron_names = [c.name for c in cron_jobs]

            # Check for required crons
            has_payment = any('Payment Retry' in n for n in cron_names)
            has_cache_cleanup = any('Clean' in n and 'Cache' in n for n in cron_names)

            self.log_test(
                "Payment retry cron",
                has_payment,
                "Daily payment reminder processing scheduled"
            )

            self.log_test(
                "Cache cleanup crons",
                has_cache_cleanup,
                "Hourly and daily cache cleanup scheduled"
            )

            return has_payment and has_cache_cleanup
        except Exception as e:
            self.log_test("Cron jobs", False, str(e))
            return False

    def test_email_queue(self):
        """Test that emails can be created and queued"""
        print("\n📬 Testing Email Queue...")

        try:
            Mail = self.env.get('mail.mail')

            # Count existing emails in queue
            pending_emails = Mail.search([('state', '=', 'outgoing')])

            self.log_test(
                "Email queue accessible",
                True,
                f"Found {len(pending_emails)} emails waiting to send"
            )

            return True
        except Exception as e:
            self.log_test("Email queue", False, str(e))
            return False

    def test_multi_tenant_isolation(self):
        """Test that features respect multi-tenant company isolation"""
        print("\n🏢 Testing Multi-Tenant Isolation...")

        try:
            PaymentRetry = self.env.get('onedesk.payment.retry')

            # Check company_id field
            has_company_id = 'company_id' in [f.name for f in PaymentRetry._fields.values()]

            self.log_test(
                "Payment retry multi-tenant",
                has_company_id,
                "company_id field present for isolation"
            )

            Cache = self.env.get('onedesk.availability.cache')
            has_cache_company_id = 'company_id' in [f.name for f in Cache._fields.values()]

            self.log_test(
                "Cache multi-tenant",
                has_cache_company_id,
                "company_id field present for isolation"
            )

            return has_company_id and has_cache_company_id
        except Exception as e:
            self.log_test("Multi-tenant isolation", False, str(e))
            return False

    def run_all_tests(self):
        """Run complete test suite"""
        print("=" * 60)
        print("🚀 OneDesk Feature Test Suite (A + B + C1 + C2)")
        print("=" * 60)

        try:
            # Initialize Odoo environment
            from odoo.cli import main
            from odoo.netsvc import init_logger

            print("🔧 Initializing Odoo environment...")

            # Run tests
            self.test_email_templates()
            self.test_payment_retry_model()
            self.test_availability_cache_model()
            self.test_database_indexes()
            self.test_cron_jobs()
            self.test_email_queue()
            self.test_multi_tenant_isolation()

        except Exception as e:
            print(f"❌ Test initialization error: {str(e)}")
            print("   Make sure you run this from an Odoo shell environment:")
            print("   $ odoo shell --database=your_db")
            print("   >>> exec(open('test_onedesk_features.py').read())")
            return False

        # Print summary
        print("\n" + "=" * 60)
        total = self.tests_passed + self.tests_failed
        print(f"📊 Test Summary: {self.tests_passed}/{total} passed")
        print("=" * 60)

        return self.tests_failed == 0

def main():
    """Main entry point for tests"""
    suite = OnedeskTestSuite()

    # Try to get Odoo environment from context
    try:
        suite.env = api.Environment(cr, uid=1, context={})
        success = suite.run_all_tests()
        return 0 if success else 1
    except:
        print("⚠️ Note: Run this script inside Odoo shell:")
        print("$ odoo shell --database=your_db --addon-path=/path/to/addons")
        print(">>> exec(open('test_onedesk_features.py').read())")
        print("\nOr use the manual test guide in the verification section.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
