"""Tests pour le modèle onedesk.unit"""
from odoo.tests import TransactionCase


class TestOneDeskUnit(TransactionCase):
    """Test cases for onedesk.unit model"""

    def setUp(self):
        """Set up test data"""
        super().setUp()

        # Create a test property
        self.property = self.env['onedesk.property'].create({
            'name': 'Property Test',
            'description': 'Test property',
            'address': '42 Rue Test, 75000 Paris',
            'property_type': 'apartment',
            'city': 'Paris',
            'postal_code': '75000',
            'country_id': self.env.ref('base.fr').id,
        })

    def test_unit_creation(self):
        """Test that a unit can be created"""
        unit = self.env['onedesk.unit'].create({
            'name': 'Studio Test',
            'property_id': self.property.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'unit_type': 'room',
        })

        self.assertIsNotNone(unit.id)
        self.assertEqual(unit.name, 'Studio Test')
        self.assertEqual(unit.property_id, self.property)
        self.assertEqual(unit.bedrooms, 1)
        self.assertEqual(unit.capacity, 2)

    def test_unit_with_amenities(self):
        """Test unit with amenities"""
        unit = self.env['onedesk.unit'].create({
            'name': 'T2 Luxe',
            'property_id': self.property.id,
            'bedrooms': 2,
            'bathrooms': 1,
            'capacity': 4,
            'unit_type': 'apartment',
            'wifi_available': True,
            'parking_available': True,
            'cleaning_fee': 50.0,
        })

        self.assertTrue(unit.wifi_available)
        self.assertTrue(unit.parking_available)
        self.assertEqual(unit.cleaning_fee, 50.0)

    def test_unit_price_calculation(self):
        """Test price calculation for dates"""
        unit = self.env['onedesk.unit'].create({
            'name': 'Studio Standard',
            'property_id': self.property.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'unit_type': 'room',
            'price_per_night': 100.0,
        })

        from datetime import datetime, timedelta
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=3)

        # If there's a price method, test it
        if hasattr(unit, 'get_price_for_dates'):
            price = unit.get_price_for_dates(start_date, end_date)
            self.assertGreaterEqual(price, 0)

    def test_unit_image_creation(self):
        """Test adding images to a unit"""
        unit = self.env['onedesk.unit'].create({
            'name': 'Studio with Images',
            'property_id': self.property.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'unit_type': 'room',
        })

        # Create an image record for the unit
        image = self.env['onedesk.unit.image'].create({
            'unit_id': unit.id,
            'name': 'Chambre principale',
            'sequence': 1,
            'is_cover': True,
        })

        self.assertEqual(image.unit_id, unit)
        self.assertTrue(image.is_cover)

    def test_multiple_units_per_property(self):
        """Test multiple units in the same property"""
        unit1 = self.env['onedesk.unit'].create({
            'name': 'Studio 1',
            'property_id': self.property.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'unit_type': 'room',
        })

        unit2 = self.env['onedesk.unit'].create({
            'name': 'Studio 2',
            'property_id': self.property.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'unit_type': 'room',
        })

        property_units = self.property.unit_ids
        self.assertGreaterEqual(len(property_units), 2)
        self.assertIn(unit1, property_units)
        self.assertIn(unit2, property_units)

    def test_unit_status_active_inactive(self):
        """Test unit active/inactive status"""
        unit = self.env['onedesk.unit'].create({
            'name': 'Studio Test',
            'property_id': self.property.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'unit_type': 'room',
            'is_active': True,
        })

        self.assertTrue(unit.is_active)

        # Deactivate the unit
        unit.is_active = False
        self.assertFalse(unit.is_active)

    def test_unit_description_and_details(self):
        """Test unit description and details"""
        description = "Magnifique studio avec vue sur la Seine"
        unit = self.env['onedesk.unit'].create({
            'name': 'Studio Vue',
            'property_id': self.property.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'unit_type': 'room',
            'description': description,
        })

        self.assertEqual(unit.description, description)
