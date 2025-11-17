"""Tests pour le modèle onedesk.property"""
from odoo.tests import TransactionCase


class TestOneDeskProperty(TransactionCase):
    """Test cases for onedesk.property model"""

    def setUp(self):
        """Set up test data"""
        super().setUp()

    def test_property_creation(self):
        """Test that a property can be created"""
        property_obj = self.env['onedesk.property'].create({
            'name': 'Apartement Paris Centre',
            'description': 'Bel appartement au cœur de Paris',
            'address': '42 Rue des Francs-Bourgeois, 75004 Paris',
            'property_type': 'apartment',
            'city': 'Paris',
            'postal_code': '75004',
            'country_id': self.env.ref('base.fr').id,
        })

        self.assertIsNotNone(property_obj.id)
        self.assertEqual(property_obj.name, 'Apartement Paris Centre')
        self.assertEqual(property_obj.city, 'Paris')

    def test_property_with_units(self):
        """Test property with multiple units"""
        property_obj = self.env['onedesk.property'].create({
            'name': 'Immeuble Multi-Units',
            'address': '123 Avenue Principale, 75000 Paris',
            'property_type': 'apartment',
            'city': 'Paris',
            'postal_code': '75000',
            'country_id': self.env.ref('base.fr').id,
        })

        # Create units
        unit1 = self.env['onedesk.unit'].create({
            'name': 'Unité 1',
            'property_id': property_obj.id,
            'bedrooms': 2,
            'bathrooms': 1,
            'capacity': 4,
            'unit_type': 'apartment',
        })

        unit2 = self.env['onedesk.unit'].create({
            'name': 'Unité 2',
            'property_id': property_obj.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'unit_type': 'room',
        })

        self.assertEqual(len(property_obj.unit_ids), 2)

    def test_property_images(self):
        """Test adding images to a property"""
        property_obj = self.env['onedesk.property'].create({
            'name': 'Property with Images',
            'address': '456 Rue Test, 75000 Paris',
            'property_type': 'apartment',
            'city': 'Paris',
            'postal_code': '75000',
            'country_id': self.env.ref('base.fr').id,
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

    def test_property_location_data(self):
        """Test property location and coordinates"""
        property_obj = self.env['onedesk.property'].create({
            'name': 'Property Geo',
            'address': '789 Rue Géo, 69000 Lyon',
            'property_type': 'villa',
            'city': 'Lyon',
            'postal_code': '69000',
            'country_id': self.env.ref('base.fr').id,
        })

        self.assertEqual(property_obj.city, 'Lyon')
        self.assertEqual(property_obj.postal_code, '69000')

    def test_property_amenities(self):
        """Test property amenities"""
        property_obj = self.env['onedesk.property'].create({
            'name': 'Property Luxe',
            'address': '100 Avenue Luxe, 06000 Nice',
            'property_type': 'villa',
            'city': 'Nice',
            'postal_code': '06000',
            'country_id': self.env.ref('base.fr').id,
            'description': 'Villa de luxe avec piscine',
        })

        self.assertIn('piscine', property_obj.description.lower())

    def test_property_types(self):
        """Test different property types"""
        property_types = [
            ('apartment', 'Apartement'),
            ('house', 'Maison'),
            ('villa', 'Villa'),
            ('room', 'Chambre'),
        ]

        for prop_type, description in property_types:
            property_obj = self.env['onedesk.property'].create({
                'name': f'Property {description}',
                'address': '1 Rue Test, 75000 Paris',
                'property_type': prop_type,
                'city': 'Paris',
                'postal_code': '75000',
                'country_id': self.env.ref('base.fr').id,
            })

            self.assertEqual(property_obj.property_type, prop_type)

    def test_property_status(self):
        """Test property status"""
        property_obj = self.env['onedesk.property'].create({
            'name': 'Property Status',
            'address': '200 Rue Status, 75000 Paris',
            'property_type': 'apartment',
            'city': 'Paris',
            'postal_code': '75000',
            'country_id': self.env.ref('base.fr').id,
        })

        if hasattr(property_obj, 'status'):
            self.assertIn(property_obj.status, ['draft', 'active', 'inactive', 'archived'])

    def test_property_external_id(self):
        """Test external integration ID"""
        property_obj = self.env['onedesk.property'].create({
            'name': 'Property External',
            'address': '300 Rue External, 75000 Paris',
            'property_type': 'apartment',
            'city': 'Paris',
            'postal_code': '75000',
            'country_id': self.env.ref('base.fr').id,
            'external_id': 'AIRBNB-123456',
        })

        self.assertEqual(property_obj.external_id, 'AIRBNB-123456')
