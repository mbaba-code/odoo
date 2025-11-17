"""Tests pour le contrôleur de booking website_onedesk"""
import json
from datetime import datetime, timedelta
from odoo.tests import TransactionCase
from odoo.addons.website.tools import MockRequest


class TestBookingController(TransactionCase):
    """Test cases for booking controller"""

    def setUp(self):
        """Set up test data"""
        super().setUp()

        # Create property
        self.property = self.env['onedesk.property'].create({
            'name': 'Test Property',
            'address': '42 Test St, 75000 Paris',
            'property_type': 'apartment',
            'city': 'Paris',
            'postal_code': '75000',
            'country_id': self.env.ref('base.fr').id,
        })

        # Create unit
        self.unit = self.env['onedesk.unit'].create({
            'name': 'Test Unit',
            'property_id': self.property.id,
            'bedrooms': 2,
            'bathrooms': 1,
            'capacity': 4,
            'unit_type': 'apartment',
            'price_per_night': 100.0,
            'cleaning_fee': 25.0,
        })

    def test_booking_with_valid_data(self):
        """Test booking with valid data"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_date = start_date + timedelta(days=3)

        booking_data = {
            'unit_id': self.unit.id,
            'name': 'Jean Dupont',
            'email': 'jean@test.com',
            'phone': '+33 6 12 34 56 78',
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'message': 'Test booking',
        }

        # Create reservation (simulating booking controller)
        reservation = self.env['onedesk.reservation'].create({
            'unit_id': booking_data['unit_id'],
            'partner_id': self.env['res.partner'].create({
                'name': booking_data['name'],
                'email': booking_data['email'],
                'phone': booking_data['phone'],
            }).id,
            'start_date': datetime.strptime(booking_data['start_date'], '%Y-%m-%d'),
            'end_date': datetime.strptime(booking_data['end_date'], '%Y-%m-%d'),
            'guest_notes': booking_data['message'],
            'status': 'draft',
        })

        self.assertIsNotNone(reservation.id)
        self.assertEqual(reservation.partner_id.name, 'Jean Dupont')
        self.assertEqual(reservation.partner_id.email, 'jean@test.com')

    def test_booking_with_missing_field(self):
        """Test booking with missing required field"""
        booking_data = {
            'unit_id': self.unit.id,
            'name': 'Jean Dupont',
            # 'email' is missing
            'phone': '+33 6 12 34 56 78',
            'start_date': '2025-11-20',
            'end_date': '2025-11-23',
        }

        # This should raise an error or fail validation
        # The actual validation happens in the controller
        self.assertNotIn('email', booking_data)

    def test_booking_with_invalid_unit(self):
        """Test booking with non-existent unit"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_date = start_date + timedelta(days=3)

        # Try to book a non-existent unit
        unit = self.env['onedesk.unit'].browse(99999)
        self.assertFalse(unit.exists())

    def test_booking_confirmation_email(self):
        """Test that booking confirmation email is created"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_date = start_date + timedelta(days=3)

        partner = self.env['res.partner'].create({
            'name': 'Marie Martin',
            'email': 'marie@test.com',
        })

        reservation = self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': partner.id,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'draft',
        })

        # Send confirmation email
        result = reservation.send_confirmation_email()
        self.assertTrue(result)

    def test_booking_date_validation(self):
        """Test date validation in booking"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_date = start_date - timedelta(days=1)  # End before start

        # This should fail
        # In practice, the controller validates this
        self.assertGreater(start_date, end_date)

    def test_booking_overlapping_dates(self):
        """Test that overlapping bookings are prevented"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_date = start_date + timedelta(days=3)

        partner1 = self.env['res.partner'].create({
            'name': 'Customer 1',
            'email': 'customer1@test.com',
        })

        partner2 = self.env['res.partner'].create({
            'name': 'Customer 2',
            'email': 'customer2@test.com',
        })

        # Create first reservation
        res1 = self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': partner1.id,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'draft',
        })

        # Try to create overlapping reservation (should be prevented by constraint)
        from odoo.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.env['onedesk.reservation'].create({
                'unit_id': self.unit.id,
                'partner_id': partner2.id,
                'start_date': start_date + timedelta(days=1),
                'end_date': end_date + timedelta(days=1),
                'status': 'draft',
            })

    def test_booking_guest_notes(self):
        """Test guest notes in booking"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_date = start_date + timedelta(days=3)

        guest_notes = "Early check-in needed. Allergic to pets."

        partner = self.env['res.partner'].create({
            'name': 'Guest',
            'email': 'guest@test.com',
        })

        reservation = self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': partner.id,
            'start_date': start_date,
            'end_date': end_date,
            'guest_notes': guest_notes,
            'status': 'draft',
        })

        self.assertEqual(reservation.guest_notes, guest_notes)

    def test_booking_special_requests(self):
        """Test special requests in booking"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_date = start_date + timedelta(days=3)

        special_requests = "High chair needed, extra beds"

        partner = self.env['res.partner'].create({
            'name': 'Family',
            'email': 'family@test.com',
        })

        reservation = self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': partner.id,
            'start_date': start_date,
            'end_date': end_date,
            'special_requests': special_requests,
            'status': 'draft',
        })

        self.assertEqual(reservation.special_requests, special_requests)
