"""Tests d'intégration pour onedesk_core"""
from datetime import datetime, timedelta
from odoo.tests import TransactionCase


class TestOneDeskIntegration(TransactionCase):
    """Integration tests for onedesk_core module"""

    def setUp(self):
        """Set up test data"""
        super().setUp()

        # Create property
        self.property = self.env['onedesk.property'].create({
            'name': 'Integration Property',
            'address': '42 Test Street, 75000 Paris',
            'property_type': 'apartment',
            'city': 'Paris',
            'postal_code': '75000',
            'country_id': self.env.ref('base.fr').id,
        })

        # Create unit
        self.unit = self.env['onedesk.unit'].create({
            'name': 'Integration Unit',
            'property_id': self.property.id,
            'bedrooms': 2,
            'bathrooms': 1,
            'capacity': 4,
            'unit_type': 'apartment',
            'price_per_night': 150.0,
            'cleaning_fee': 50.0,
        })

        # Create customer
        self.customer = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'customer@test.com',
            'phone': '+33 6 12 34 56 78',
        })

    def test_complete_reservation_workflow(self):
        """Test complete reservation workflow from booking to completion"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_date = start_date + timedelta(days=5)

        # 1. Create reservation
        reservation = self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': self.customer.id,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'draft',
            'guest_notes': 'Early check-in please',
        })

        self.assertEqual(reservation.status, 'draft')
        self.assertEqual(reservation.number_of_nights, 5)

        # 2. Transition to pending payment
        reservation.status = 'pending_payment'
        self.assertEqual(reservation.status, 'pending_payment')

        # 3. Mark as paid
        reservation.status = 'paid'
        self.assertEqual(reservation.status, 'paid')

        # 4. Check-in
        reservation.status = 'checked_in'
        self.assertEqual(reservation.status, 'checked_in')

        # 5. Complete
        reservation.status = 'completed'
        self.assertEqual(reservation.status, 'completed')

    def test_multiple_reservations_different_units(self):
        """Test multiple reservations for different units in same property"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_date = start_date + timedelta(days=3)

        # Create second unit
        unit2 = self.env['onedesk.unit'].create({
            'name': 'Unit 2',
            'property_id': self.property.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'unit_type': 'room',
        })

        # Create second customer
        customer2 = self.env['res.partner'].create({
            'name': 'Customer 2',
            'email': 'customer2@test.com',
        })

        # Create reservations
        res1 = self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': self.customer.id,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'draft',
        })

        res2 = self.env['onedesk.reservation'].create({
            'unit_id': unit2.id,
            'partner_id': customer2.id,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'draft',
        })

        self.assertIsNotNone(res1.id)
        self.assertIsNotNone(res2.id)
        self.assertNotEqual(res1.id, res2.id)

    def test_property_with_complete_data(self):
        """Test property with all complete data"""
        property_obj = self.env['onedesk.property'].create({
            'name': 'Complete Property',
            'description': 'Complete property with all info',
            'address': '999 Full Street, 75000 Paris',
            'property_type': 'villa',
            'city': 'Paris',
            'postal_code': '75000',
            'country_id': self.env.ref('base.fr').id,
        })

        # Add units
        for i in range(3):
            self.env['onedesk.unit'].create({
                'name': f'Unit {i+1}',
                'property_id': property_obj.id,
                'bedrooms': 2,
                'bathrooms': 1,
                'capacity': 4,
                'unit_type': 'apartment',
            })

        # Add images
        for i in range(2):
            self.env['onedesk.property.image'].create({
                'property_id': property_obj.id,
                'name': f'Image {i+1}',
                'sequence': i + 1,
                'is_cover': i == 0,
            })

        self.assertEqual(len(property_obj.unit_ids), 3)
        self.assertEqual(len(property_obj.image_ids), 2)

    def test_email_sending_integration(self):
        """Test email sending integration with reservation"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_date = start_date + timedelta(days=3)

        reservation = self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': self.customer.id,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'draft',
        })

        # Send confirmation email
        result = reservation.send_confirmation_email()
        self.assertTrue(result)

    def test_property_search_and_filter(self):
        """Test searching and filtering properties"""
        # Create properties with different types
        apt = self.env['onedesk.property'].create({
            'name': 'Test Apartment',
            'address': '1 Apt St, Paris',
            'property_type': 'apartment',
            'city': 'Paris',
            'postal_code': '75000',
            'country_id': self.env.ref('base.fr').id,
        })

        villa = self.env['onedesk.property'].create({
            'name': 'Test Villa',
            'address': '2 Villa St, Nice',
            'property_type': 'villa',
            'city': 'Nice',
            'postal_code': '06000',
            'country_id': self.env.ref('base.fr').id,
        })

        # Search apartments
        apartments = self.env['onedesk.property'].search([
            ('property_type', '=', 'apartment')
        ])
        self.assertGreaterEqual(len(apartments), 1)

        # Search properties in Paris
        paris_props = self.env['onedesk.property'].search([
            ('city', '=', 'Paris')
        ])
        self.assertGreaterEqual(len(paris_props), 1)

    def test_unit_availability_check(self):
        """Test unit availability checking"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_date = start_date + timedelta(days=3)

        # Create a reservation
        self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': self.customer.id,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'draft',
        })

        # Check availability for same dates (should be unavailable)
        available, conflicts, msg = self.env['onedesk.reservation'].check_availability_for_unit(
            self.unit.id,
            start_date,
            end_date
        )
        self.assertFalse(available)
        self.assertGreater(len(conflicts), 0)

        # Check availability for different dates (should be available)
        other_start = start_date + timedelta(days=10)
        other_end = other_start + timedelta(days=3)
        available, conflicts, msg = self.env['onedesk.reservation'].check_availability_for_unit(
            self.unit.id,
            other_start,
            other_end
        )
        self.assertTrue(available)
        self.assertEqual(len(conflicts), 0)

    def test_customer_multiple_reservations(self):
        """Test one customer with multiple reservations"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

        # Create multiple reservations for same customer, different dates
        res1 = self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': self.customer.id,
            'start_date': start_date,
            'end_date': start_date + timedelta(days=3),
            'status': 'draft',
        })

        res2 = self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': self.customer.id,
            'start_date': start_date + timedelta(days=10),
            'end_date': start_date + timedelta(days=14),
            'status': 'draft',
        })

        # Verify both reservations exist
        customer_reservations = self.env['onedesk.reservation'].search([
            ('partner_id', '=', self.customer.id)
        ])
        self.assertGreaterEqual(len(customer_reservations), 2)
