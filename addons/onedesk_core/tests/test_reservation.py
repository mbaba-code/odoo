"""Tests pour le modèle onedesk.reservation"""
from datetime import datetime, timedelta
from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError


class TestOneDeskReservation(TransactionCase):
    """Test cases for onedesk.reservation model"""

    def setUp(self):
        """Set up test data"""
        super().setUp()

        # Create a test company
        self.company = self.env['res.company'].create({
            'name': 'Test Company',
        })

        # Create a test partner (customer)
        self.partner = self.env['res.partner'].create({
            'name': 'Jean Dupont',
            'email': 'jean@example.com',
            'phone': '+33 6 12 34 56 78',
        })

        # Create a test property
        self.property = self.env['onedesk.property'].create({
            'name': 'Apartement Test',
            'description': 'Un bel appartement test',
            'address': '42 Rue Test, 75000 Paris',
            'property_type': 'apartment',
            'city': 'Paris',
            'postal_code': '75000',
            'country_id': self.env.ref('base.fr').id,
        })

        # Create a test unit
        self.unit = self.env['onedesk.unit'].create({
            'name': 'Studio Test',
            'property_id': self.property.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'unit_type': 'room',
        })

        # Create a reservation
        self.reservation_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        self.reservation_end = self.reservation_start + timedelta(days=5)

        self.reservation = self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': self.partner.id,
            'start_date': self.reservation_start,
            'end_date': self.reservation_end,
            'status': 'draft',
            'guest_notes': 'Notes du client',
        })

    def test_reservation_creation(self):
        """Test that a reservation can be created"""
        self.assertIsNotNone(self.reservation.id)
        self.assertEqual(self.reservation.unit_id, self.unit)
        self.assertEqual(self.reservation.partner_id, self.partner)
        self.assertEqual(self.reservation.status, 'draft')

    def test_reservation_number_of_nights(self):
        """Test calculation of number of nights"""
        expected_nights = (self.reservation_end.date() - self.reservation_start.date()).days
        self.assertEqual(self.reservation.number_of_nights, expected_nights)

    def test_overlapping_reservations_raises_error(self):
        """Test that overlapping reservations raise a validation error"""
        # Create a second partner
        partner2 = self.env['res.partner'].create({
            'name': 'Marie Martin',
            'email': 'marie@example.com',
        })

        # Try to create an overlapping reservation (should fail)
        with self.assertRaises(ValidationError):
            self.env['onedesk.reservation'].create({
                'unit_id': self.unit.id,
                'partner_id': partner2.id,
                'start_date': self.reservation_start + timedelta(days=2),
                'end_date': self.reservation_start + timedelta(days=7),
                'status': 'draft',
            })

    def test_cancelled_reservation_does_not_block(self):
        """Test that cancelled reservations don't block new ones"""
        # Cancel the first reservation
        self.reservation.status = 'cancelled'

        # Partner 2
        partner2 = self.env['res.partner'].create({
            'name': 'Marie Martin',
            'email': 'marie@example.com',
        })

        # Create a new reservation in the same dates (should work)
        reservation2 = self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': partner2.id,
            'start_date': self.reservation_start,
            'end_date': self.reservation_end,
            'status': 'draft',
        })

        self.assertIsNotNone(reservation2.id)

    def test_check_availability_for_unit(self):
        """Test availability check method"""
        # Check availability for a free period
        is_available, conflicts, message = self.env['onedesk.reservation'].check_availability_for_unit(
            self.unit.id,
            self.reservation_start + timedelta(days=10),
            self.reservation_start + timedelta(days=15),
        )
        self.assertTrue(is_available)
        self.assertEqual(len(conflicts), 0)

        # Check availability for booked period
        is_available, conflicts, message = self.env['onedesk.reservation'].check_availability_for_unit(
            self.unit.id,
            self.reservation_start,
            self.reservation_end,
        )
        self.assertFalse(is_available)
        self.assertEqual(len(conflicts), 1)
        self.assertIsNotNone(message)

    def test_send_confirmation_email(self):
        """Test confirmation email sending"""
        # This test just ensures the method exists and doesn't crash
        result = self.reservation.send_confirmation_email()
        self.assertTrue(result)

    def test_reservation_workflow_transitions(self):
        """Test reservation status transitions"""
        # Draft -> Pending Payment
        self.reservation.status = 'pending_payment'
        self.assertEqual(self.reservation.status, 'pending_payment')

        # Pending Payment -> Paid
        self.reservation.status = 'paid'
        self.assertEqual(self.reservation.status, 'paid')

        # Paid -> Checked In
        self.reservation.status = 'checked_in'
        self.assertEqual(self.reservation.status, 'checked_in')

        # Checked In -> Completed
        self.reservation.status = 'completed'
        self.assertEqual(self.reservation.status, 'completed')

    def test_reservation_with_special_requests(self):
        """Test reservation with special requests"""
        self.reservation.special_requests = 'Chaise haute pour bébé'
        self.assertEqual(self.reservation.special_requests, 'Chaise haute pour bébé')

    def test_reservation_internal_notes(self):
        """Test internal notes for staff"""
        self.reservation.internal_notes = 'Client VIP - Offrir welcome package'
        self.assertEqual(self.reservation.internal_notes, 'Client VIP - Offrir welcome package')
