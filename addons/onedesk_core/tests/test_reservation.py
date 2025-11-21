"""Tests pour le modèle onedesk.reservation"""
from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class TestOneDeskReservation(TransactionCase):
    """Test cases for onedesk.reservation model"""

    def setUp(self):
        """Set up test data"""
        super().setUp()

        # Create company
        self.company = self.env['res.company'].create({
            'name': 'Test Company Reservation',
        })

        # Create property
        self.property = self.env['onedesk.property'].create({
            'name': 'Test Property',
            'address': '123 Test Street',
            'property_type': 'apartment',
            'company_id': self.company.id,
        })

        # Create unit
        self.unit = self.env['onedesk.unit'].create({
            'name': 'Test Unit',
            'property_id': self.property.id,
            'bedrooms': 2,
            'bathrooms': 1,
            'capacity': 4,
            'price_per_night': 100.0,
        })

        # Create partner
        self.partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'test@example.com',
            'phone': '+33612345678',
        })

    def test_reservation_creation(self):
        """Test that a reservation can be created"""
        start_date = datetime.now() + timedelta(days=7)
        end_date = start_date + timedelta(days=3)

        reservation = self.env['onedesk.reservation'].create({
            'name': 'TEST-001',
            'unit_id': self.unit.id,
            'partner_id': self.partner.id,
            'start_date': start_date,
            'end_date': end_date,
        })

        self.assertIsNotNone(reservation.id)
        self.assertEqual(reservation.unit_id, self.unit)
        self.assertEqual(reservation.partner_id, self.partner)
        self.assertEqual(reservation.number_of_nights, 3)
        self.assertEqual(reservation.price_per_night, 100.0)
        self.assertEqual(reservation.total_price, 300.0)

    def test_reservation_overlapping_detection(self):
        """Test that overlapping reservations are detected"""
        start_date = datetime.now() + timedelta(days=7)
        end_date = start_date + timedelta(days=3)

        # Create first reservation
        reservation1 = self.env['onedesk.reservation'].create({
            'name': 'TEST-001',
            'unit_id': self.unit.id,
            'partner_id': self.partner.id,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'paid',
        })

        # Try to create overlapping reservation
        with self.assertRaises(ValidationError):
            self.env['onedesk.reservation'].create({
                'name': 'TEST-002',
                'unit_id': self.unit.id,
                'partner_id': self.partner.id,
                'start_date': start_date + timedelta(days=1),
                'end_date': end_date + timedelta(days=1),
                'status': 'paid',
            })

    def test_reservation_status_workflow(self):
        """Test reservation status transitions"""
        start_date = datetime.now() + timedelta(days=7)
        end_date = start_date + timedelta(days=3)

        reservation = self.env['onedesk.reservation'].create({
            'name': 'TEST-001',
            'unit_id': self.unit.id,
            'partner_id': self.partner.id,
            'start_date': start_date,
            'end_date': end_date,
        })

        # Initial status
        self.assertEqual(reservation.status, 'draft')

        # Cancelled reservations don't block availability
        reservation.status = 'cancelled'
        
        # Can create another reservation on same dates
        reservation2 = self.env['onedesk.reservation'].create({
            'name': 'TEST-002',
            'unit_id': self.unit.id,
            'partner_id': self.partner.id,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'paid',
        })

        self.assertEqual(reservation2.status, 'paid')

    def test_reservation_calendar_event_creation(self):
        """Test that calendar event is created automatically"""
        start_date = datetime.now() + timedelta(days=7)
        end_date = start_date + timedelta(days=3)

        reservation = self.env['onedesk.reservation'].create({
            'name': 'TEST-001',
            'unit_id': self.unit.id,
            'partner_id': self.partner.id,
            'start_date': start_date,
            'end_date': end_date,
        })

        self.assertIsNotNone(reservation.calendar_event_id)
        self.assertEqual(reservation.calendar_event_id.start, start_date)
        self.assertEqual(reservation.calendar_event_id.stop, end_date)

    def test_reservation_company_inherited(self):
        """Test that reservation inherits company_id from unit"""
        start_date = datetime.now() + timedelta(days=7)
        end_date = start_date + timedelta(days=3)

        reservation = self.env['onedesk.reservation'].create({
            'name': 'TEST-001',
            'unit_id': self.unit.id,
            'partner_id': self.partner.id,
            'start_date': start_date,
            'end_date': end_date,
        })

        self.assertEqual(reservation.company_id, self.unit.company_id)

    def test_reservation_payment_status(self):
        """Test payment status"""
        start_date = datetime.now() + timedelta(days=7)
        end_date = start_date + timedelta(days=3)

        reservation = self.env['onedesk.reservation'].create({
            'name': 'TEST-001',
            'unit_id': self.unit.id,
            'partner_id': self.partner.id,
            'start_date': start_date,
            'end_date': end_date,
        })

        # Initial payment status
        self.assertEqual(reservation.payment_status, 'pending')

        # Change to completed
        reservation.payment_status = 'completed'
        self.assertEqual(reservation.payment_status, 'completed')