"""Tests pour les images et photos des modèles"""
import base64
from odoo.tests import TransactionCase


class TestImageFields(TransactionCase):
    """Test cases for image fields (photos) in all models"""

    def setUp(self):
        """Set up test data"""
        super().setUp()

        # Créer une image test (petit PNG 1x1 pixel)
        self.test_image_base64 = (
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
        )
        self.test_image_binary = base64.b64decode(self.test_image_base64)

        # Créer une company
        self.company = self.env['res.company'].create({
            'name': 'Test Company Images',
        })

        # Créer une propriété de test
        self.property = self.env['onedesk.property'].create({
            'name': 'Property avec Photos',
            'description': 'Une propriété pour tester les photos',
            'address': '42 Rue Photos, 75000 Paris',
            'property_type': 'apartment',
            'company_id': self.company.id,
        })

        # Créer une unité de test
        self.unit = self.env['onedesk.unit'].create({
            'name': 'Unité avec Photos',
            'property_id': self.property.id,
            'bedrooms': 2,
            'bathrooms': 1,
            'capacity': 4,
            'price_per_night': 100.0,
        })

        # Créer un client de test
        self.customer = self.env['res.partner'].create({
            'name': 'Photo Customer',
            'email': 'photo@test.com',
        })

    def test_property_image_creation_with_binary_data(self):
        """Test creating property image with actual binary image data"""
        image = self.env['onedesk.property.image'].create({
            'property_id': self.property.id,
            'name': 'Entrée',
            'image': self.test_image_base64,
            'sequence': 1,
            'is_cover': True,
        })

        self.assertIsNotNone(image.id)
        self.assertEqual(image.name, 'Entrée')
        self.assertTrue(image.is_cover)
        self.assertEqual(image.sequence, 1)
        self.assertIsNotNone(image.image)

    def test_property_main_image(self):
        """Test property main_image field"""
        self.property.main_image = self.test_image_base64
        self.assertIsNotNone(self.property.main_image)

    def test_unit_image_creation_with_binary_data(self):
        """Test creating unit image with actual binary image data"""
        image = self.env['onedesk.unit.image'].create({
            'unit_id': self.unit.id,
            'name': 'Chambre principale',
            'image': self.test_image_base64,
            'sequence': 1,
            'is_cover': True,
        })

        self.assertIsNotNone(image.id)
        self.assertEqual(image.unit_id, self.unit)
        self.assertTrue(image.is_cover)
        self.assertIsNotNone(image.image)

    def test_reservation_image_creation(self):
        """Test creating reservation images"""
        from datetime import datetime, timedelta

        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_date = start_date + timedelta(days=3)

        reservation = self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': self.customer.id,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'draft',
        })

        # Créer des images dans la galerie
        image = self.env['onedesk.reservation.image'].create({
            'reservation_id': reservation.id,
            'name': 'Check-in photo',
            'image': self.test_image_base64,
        })

        self.assertIsNotNone(image.id)

    def test_property_image_gallery(self):
        """Test property image gallery with multiple images"""
        images = []
        for i in range(3):
            img = self.env['onedesk.property.image'].create({
                'property_id': self.property.id,
                'name': f'Photo {i+1}',
                'image': self.test_image_base64,
                'sequence': i + 1,
                'is_cover': i == 0,
            })
            images.append(img)

        self.assertEqual(len(self.property.image_ids), 3)

        cover_image = self.property.image_ids.filtered(lambda x: x.is_cover)
        self.assertEqual(len(cover_image), 1)
        self.assertEqual(cover_image.sequence, 1)

    def test_unit_image_gallery(self):
        """Test unit image gallery with multiple images"""
        for i in range(4):
            self.env['onedesk.unit.image'].create({
                'unit_id': self.unit.id,
                'name': f'Pièce {i+1}',
                'image': self.test_image_base64,
                'sequence': i + 1,
                'is_cover': i == 0,
            })

        self.assertEqual(len(self.unit.image_ids), 4)

    def test_image_sequence_ordering(self):
        """Test image ordering by sequence"""
        img3 = self.env['onedesk.property.image'].create({
            'property_id': self.property.id,
            'name': 'Image 3',
            'sequence': 3,
            'image': self.test_image_base64,
        })

        img1 = self.env['onedesk.property.image'].create({
            'property_id': self.property.id,
            'name': 'Image 1',
            'sequence': 1,
            'image': self.test_image_base64,
        })

        img2 = self.env['onedesk.property.image'].create({
            'property_id': self.property.id,
            'name': 'Image 2',
            'sequence': 2,
            'image': self.test_image_base64,
        })

        images = self.property.image_ids.sorted(key=lambda x: x.sequence)
        self.assertEqual(images[0].sequence, 1)
        self.assertEqual(images[1].sequence, 2)
        self.assertEqual(images[2].sequence, 3)

    def test_image_set_as_cover(self):
        """Test setting an image as cover"""
        img1 = self.env['onedesk.property.image'].create({
            'property_id': self.property.id,
            'name': 'Image 1',
            'image': self.test_image_base64,
            'is_cover': True,
        })

        img2 = self.env['onedesk.property.image'].create({
            'property_id': self.property.id,
            'name': 'Image 2',
            'image': self.test_image_base64,
            'is_cover': False,
        })

        self.assertTrue(img1.is_cover)
        self.assertFalse(img2.is_cover)

        img1.is_cover = False
        img2.is_cover = True

        self.assertFalse(img1.is_cover)
        self.assertTrue(img2.is_cover)

    def test_image_deletion(self):
        """Test image deletion"""
        image = self.env['onedesk.property.image'].create({
            'property_id': self.property.id,
            'name': 'Image à supprimer',
            'image': self.test_image_base64,
        })

        image_id = image.id
        image.unlink()

        deleted_image = self.env['onedesk.property.image'].browse(image_id)
        self.assertFalse(deleted_image.exists())

    def test_unit_image_with_name_description(self):
        """Test unit image with name and description"""
        image = self.env['onedesk.unit.image'].create({
            'unit_id': self.unit.id,
            'name': 'Cuisine équipée',
            'image': self.test_image_base64,
            'sequence': 1,
        })

        self.assertEqual(image.name, 'Cuisine équipée')
        self.assertTrue(len(image.name) > 0)

    def test_property_image_count(self):
        """Test counting images in property"""
        for i in range(5):
            self.env['onedesk.property.image'].create({
                'property_id': self.property.id,
                'name': f'Photo {i+1}',
                'image': self.test_image_base64,
            })

        image_count = len(self.property.image_ids)
        self.assertEqual(image_count, 5)

    def test_image_data_integrity(self):
        """Test that image data is preserved correctly"""
        image = self.env['onedesk.property.image'].create({
            'property_id': self.property.id,
            'name': 'Test Intégrité',
            'image': self.test_image_base64,
        })

        retrieved_image = self.env['onedesk.property.image'].browse(image.id)
        self.assertEqual(retrieved_image.image, self.test_image_base64)

    def test_multiple_units_images_independent(self):
        """Test that images are independent for different units"""
        unit2 = self.env['onedesk.unit'].create({
            'name': 'Unit 2',
            'property_id': self.property.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'price_per_night': 80.0,
        })

        for i in range(3):
            self.env['onedesk.unit.image'].create({
                'unit_id': self.unit.id,
                'name': f'Unit1 Photo {i+1}',
                'image': self.test_image_base64,
            })

        for i in range(2):
            self.env['onedesk.unit.image'].create({
                'unit_id': unit2.id,
                'name': f'Unit2 Photo {i+1}',
                'image': self.test_image_base64,
            })

        self.assertEqual(len(self.unit.image_ids), 3)
        self.assertEqual(len(unit2.image_ids), 2)