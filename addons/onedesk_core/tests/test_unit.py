"""Tests pour le modèle onedesk.unit"""
from odoo.tests import TransactionCase
from datetime import datetime, timedelta


class TestOneDeskUnit(TransactionCase):
    """Test cases for onedesk.unit model"""

    def setUp(self):
        """Set up test data"""
        super().setUp()

        # Create a test company
        self.company = self.env['res.company'].create({
            'name': 'Test Company Unit',
        })

        # Create a test property
        self.property = self.env['onedesk.property'].create({
            'name': 'Property Test',
            'description': 'Test property',
            'address': '42 Rue Test, 75000 Paris',
            'property_type': 'apartment',
            'company_id': self.company.id,
        })

    def test_unit_creation(self):
        """Test that a unit can be created"""
        unit = self.env['onedesk.unit'].create({
            'name': 'Studio Test',
            'property_id': self.property.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'price_per_night': 100.0,
        })

        self.assertIsNotNone(unit.id)
        self.assertEqual(unit.name, 'Studio Test')
        self.assertEqual(unit.property_id, self.property)
        self.assertEqual(unit.bedrooms, 1)
        self.assertEqual(unit.capacity, 2)
        self.assertEqual(unit.price_per_night, 100.0)

    def test_unit_price_calculation(self):
        """Test price calculation for dates"""
        unit = self.env['onedesk.unit'].create({
            'name': 'Studio Standard',
            'property_id': self.property.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'price_per_night': 100.0,
        })

        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=3)

        # Test get_price_for_dates
        price = unit.get_price_for_dates(start_date, end_date)
        self.assertEqual(price, 100.0)

        # Test get_total_price_for_dates
        total_price = unit.get_total_price_for_dates(start_date, end_date)
        self.assertEqual(total_price, 300.0)  # 100 * 3 nights

    def test_unit_image_creation(self):
        """Test adding images to a unit"""
        unit = self.env['onedesk.unit'].create({
            'name': 'Studio with Images',
            'property_id': self.property.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'price_per_night': 100.0,
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
            'price_per_night': 100.0,
        })

        unit2 = self.env['onedesk.unit'].create({
            'name': 'Studio 2',
            'property_id': self.property.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'price_per_night': 120.0,
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
            'price_per_night': 100.0,
            'active': True,
        })

        self.assertTrue(unit.active)

        # Deactivate the unit
        unit.active = False
        self.assertFalse(unit.active)

    def test_unit_cleaning_fee(self):
        """Test unit with cleaning fee"""
        unit = self.env['onedesk.unit'].create({
            'name': 'Studio Cleaning',
            'property_id': self.property.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'price_per_night': 100.0,
            'cleaning_fee': 50.0,
        })

        self.assertEqual(unit.cleaning_fee, 50.0)

    def test_unit_maintenance_mode(self):
        """Test unit maintenance mode"""
        unit = self.env['onedesk.unit'].create({
            'name': 'Studio Maintenance',
            'property_id': self.property.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'price_per_night': 100.0,
            'maintenance_mode': True,
            'maintenance_notes': 'Réparation plomberie',
        })

        self.assertTrue(unit.maintenance_mode)
        self.assertEqual(unit.maintenance_notes, 'Réparation plomberie')

    def test_unit_company_inherited(self):
        """Test that unit inherits company_id from property"""
        unit = self.env['onedesk.unit'].create({
            'name': 'Studio Company Test',
            'property_id': self.property.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'price_per_night': 100.0,
        })

        self.assertEqual(unit.company_id, self.property.company_id)