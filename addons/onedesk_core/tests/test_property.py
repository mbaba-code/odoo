"""Tests pour le modèle onedesk.property"""
from odoo.tests import TransactionCase


class TestOneDeskProperty(TransactionCase):
    """Test cases for onedesk.property model"""

    def setUp(self):
        """Set up test data"""
        super().setUp()
        
        # Create a test company
        self.company = self.env['res.company'].create({
            'name': 'Test Company Property',
        })

    def test_property_creation(self):
        """Test that a property can be created"""
        property_obj = self.env['onedesk.property'].create({
            'name': 'Appartement Paris Centre',
            'description': 'Bel appartement au cœur de Paris',
            'address': '42 Rue des Francs-Bourgeois, 75004 Paris',
            'property_type': 'apartment',
            'company_id': self.company.id,
        })

        self.assertIsNotNone(property_obj.id)
        self.assertEqual(property_obj.name, 'Appartement Paris Centre')
        self.assertEqual(property_obj.property_type, 'apartment')
        self.assertEqual(property_obj.company_id, self.company)

    def test_property_with_units(self):
        """Test property with multiple units"""
        property_obj = self.env['onedesk.property'].create({
            'name': 'Immeuble Multi-Units',
            'address': '123 Avenue Principale, 75000 Paris',
            'property_type': 'apartment',
            'company_id': self.company.id,
        })

        # Create units
        unit1 = self.env['onedesk.unit'].create({
            'name': 'Unité 1',
            'property_id': property_obj.id,
            'bedrooms': 2,
            'bathrooms': 1,
            'capacity': 4,
            'price_per_night': 100.0,
        })

        unit2 = self.env['onedesk.unit'].create({
            'name': 'Unité 2',
            'property_id': property_obj.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'price_per_night': 80.0,
        })

        self.assertEqual(len(property_obj.unit_ids), 2)
        self.assertEqual(property_obj.total_units, 2)

    def test_property_images(self):
        """Test adding images to a property"""
        property_obj = self.env['onedesk.property'].create({
            'name': 'Property with Images',
            'address': '456 Rue Test, 75000 Paris',
            'property_type': 'apartment',
            'company_id': self.company.id,
        })

        # Create property images
        image1 = self.env['onedesk.property.image'].create({
            'property_id': property_obj.id,
            'name': 'Vue extérieure',
            'sequence': 1,
            'is_cover': True,
        })

        image2 = self.env['onedesk.property.image'].create({
            'property_id': property_obj.id,
            'name': 'Salon',
            'sequence': 2,
            'is_cover': False,
        })

        self.assertEqual(len(property_obj.image_ids), 2)
        self.assertTrue(image1.is_cover)
        self.assertFalse(image2.is_cover)

    def test_property_amenities(self):
        """Test property amenities"""
        property_obj = self.env['onedesk.property'].create({
            'name': 'Property Luxe',
            'address': '100 Avenue Luxe, 06000 Nice',
            'property_type': 'villa',
            'company_id': self.company.id,
            'amenities': 'Piscine, WiFi, Climatisation, Parking',
        })

        self.assertIn('Piscine', property_obj.amenities)
        self.assertIn('WiFi', property_obj.amenities)

    def test_property_types(self):
        """Test different property types"""
        property_types = [
            ('apartment', 'Appartement'),
            ('house', 'Maison'),
            ('villa', 'Villa'),
            ('studio', 'Studio'),
        ]

        for prop_type, description in property_types:
            property_obj = self.env['onedesk.property'].create({
                'name': f'Property {description}',
                'address': '1 Rue Test, 75000 Paris',
                'property_type': prop_type,
                'company_id': self.company.id,
            })

            self.assertEqual(property_obj.property_type, prop_type)

    def test_property_company_required(self):
        """Test that company_id is set automatically"""
        property_obj = self.env['onedesk.property'].create({
            'name': 'Property Company Test',
            'address': '200 Rue Test, 75000 Paris',
            'property_type': 'apartment',
        })

        # Should use default company
        self.assertIsNotNone(property_obj.company_id)

    def test_property_active_flag(self):
        """Test property active/inactive status"""
        property_obj = self.env['onedesk.property'].create({
            'name': 'Property Active Test',
            'address': '300 Rue Active, 75000 Paris',
            'property_type': 'apartment',
            'company_id': self.company.id,
            'active': True,
        })

        self.assertTrue(property_obj.active)

        # Deactivate
        property_obj.active = False
        self.assertFalse(property_obj.active)