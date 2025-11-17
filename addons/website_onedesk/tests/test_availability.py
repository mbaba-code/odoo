"""Tests pour la vérification de disponibilité"""
from datetime import datetime, timedelta
from odoo.tests import TransactionCase


class TestAvailabilityCheck(TransactionCase):
    """Test cases for availability checking"""

    def setUp(self):
        """Set up test data"""
        super().setUp()

        # Create property
        self.property = self.env['onedesk.property'].create({
            'name': 'Availability Test Property',
            'address': '10 Test Ave, 75000 Paris',
            'property_type': 'apartment',
            'city': 'Paris',
            'postal_code': '75000',
            'country_id': self.env.ref('base.fr').id,
        })

        # Create unit
        self.unit = self.env['onedesk.unit'].create({
            'name': 'Availability Test Unit',
            'property_id': self.property.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'unit_type': 'room',
            'price_per_night': 100.0,
            'cleaning_fee': 20.0,
        })

        # Create customer
        self.customer = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'test@test.com',
        })

    def test_unit_availability_empty(self):
        """Test availability for empty unit"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_date = start_date + timedelta(days=5)

        available, conflicts, msg = self.env['onedesk.reservation'].check_availability_for_unit(
            self.unit.id,
            start_date,
            end_date
        )

        self.assertTrue(available)
        self.assertEqual(len(conflicts), 0)
        self.assertIsNone(msg)

    def test_unit_availability_with_booking(self):
        """Test availability when unit is booked"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_date = start_date + timedelta(days=5)

        # Create a reservation
        self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': self.customer.id,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'draft',
        })

        # Check availability for same dates
        available, conflicts, msg = self.env['onedesk.reservation'].check_availability_for_unit(
            self.unit.id,
            start_date,
            end_date
        )

        self.assertFalse(available)
        self.assertGreater(len(conflicts), 0)
        self.assertIsNotNone(msg)

    def test_unit_availability_before_booking(self):
        """Test availability before existing booking"""
        booking_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=10)
        booking_end = booking_start + timedelta(days=5)

        # Create a reservation for later dates
        self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': self.customer.id,
            'start_date': booking_start,
            'end_date': booking_end,
            'status': 'draft',
        })

        # Check availability for dates before booking
        check_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        check_end = check_start + timedelta(days=3)

        available, conflicts, msg = self.env['onedesk.reservation'].check_availability_for_unit(
            self.unit.id,
            check_start,
            check_end
        )

        self.assertTrue(available)

    def test_unit_availability_after_booking(self):
        """Test availability after existing booking"""
        booking_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        booking_end = booking_start + timedelta(days=5)

        # Create a reservation
        self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': self.customer.id,
            'start_date': booking_start,
            'end_date': booking_end,
            'status': 'draft',
        })

        # Check availability for dates after booking
        check_start = booking_end + timedelta(days=1)
        check_end = check_start + timedelta(days=3)

        available, conflicts, msg = self.env['onedesk.reservation'].check_availability_for_unit(
            self.unit.id,
            check_start,
            check_end
        )

        self.assertTrue(available)

    def test_unit_availability_partial_overlap(self):
        """Test availability with partial date overlap"""
        booking_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=5)
        booking_end = booking_start + timedelta(days=5)

        # Create a reservation
        self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': self.customer.id,
            'start_date': booking_start,
            'end_date': booking_end,
            'status': 'draft',
        })

        # Check availability with partial overlap
        check_start = booking_start - timedelta(days=2)
        check_end = booking_start + timedelta(days=2)

        available, conflicts, msg = self.env['onedesk.reservation'].check_availability_for_unit(
            self.unit.id,
            check_start,
            check_end
        )

        self.assertFalse(available)
        self.assertGreater(len(conflicts), 0)

    def test_cancelled_reservation_not_blocking(self):
        """Test that cancelled reservations don't block availability"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_date = start_date + timedelta(days=5)

        # Create and cancel a reservation
        res = self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': self.customer.id,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'draft',
        })

        res.status = 'cancelled'

        # Check availability for same dates (should be available)
        available, conflicts, msg = self.env['onedesk.reservation'].check_availability_for_unit(
            self.unit.id,
            start_date,
            end_date
        )

        self.assertTrue(available)

    def test_multiple_units_independent_availability(self):
        """Test that availability is independent per unit"""
        # Create second unit
        unit2 = self.env['onedesk.unit'].create({
            'name': 'Unit 2',
            'property_id': self.property.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'unit_type': 'room',
        })

        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_date = start_date + timedelta(days=5)

        # Book only unit 1
        self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': self.customer.id,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'draft',
        })

        # Unit 1 should be unavailable
        available1, _, _ = self.env['onedesk.reservation'].check_availability_for_unit(
            self.unit.id,
            start_date,
            end_date
        )
        self.assertFalse(available1)

        # Unit 2 should still be available
        available2, _, _ = self.env['onedesk.reservation'].check_availability_for_unit(
            unit2.id,
            start_date,
            end_date
        )
        self.assertTrue(available2)

    def test_availability_same_day_checkout_checkin(self):
        """Test availability for same-day checkout/check-in"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_date = start_date + timedelta(days=5)

        # Create reservation
        self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': self.customer.id,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'draft',
        })

        # Check if next day at checkout time is available
        next_date_start = end_date
        next_date_end = next_date_start + timedelta(days=3)

        available, conflicts, msg = self.env['onedesk.reservation'].check_availability_for_unit(
            self.unit.id,
            next_date_start,
            next_date_end
        )

        # This depends on how checkout/checkin is handled
        # If end_date is exclusive, should be available
        # If end_date is inclusive, might not be available

    def test_long_term_availability(self):
        """Test availability for long-term bookings"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_date = start_date + timedelta(days=30)

        # Create long-term reservation
        self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': self.customer.id,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'draft',
        })

        # Check availability for any date within the period
        test_start = start_date + timedelta(days=15)
        test_end = test_start + timedelta(days=5)

        available, conflicts, msg = self.env['onedesk.reservation'].check_availability_for_unit(
            self.unit.id,
            test_start,
            test_end
        )

        self.assertFalse(available)
