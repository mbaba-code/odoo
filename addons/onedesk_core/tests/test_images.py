"""Tests pour les images et photos des modèles"""
import base64
from odoo.tests import TransactionCase


class TestImageFields(TransactionCase):
    """Test cases for image fields (photos) in all models"""

    def setUp(self):
        """Set up test data"""
        super().setUp()

        # Créer une image test (petit PNG 1x1 pixel)
        # C'est une image PNG valide en base64
        self.test_image_base64 = (
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
        )
        self.test_image_binary = base64.b64decode(self.test_image_base64)

        # Créer une propriété de test
        self.property = self.env['onedesk.property'].create({
            'name': 'Property avec Photos',
            'description': 'Une propriété pour tester les photos',
            'address': '42 Rue Photos, 75000 Paris',
            'property_type': 'apartment',
            'city': 'Paris',
            'postal_code': '75000',
            'country_id': self.env.ref('base.fr').id,
        })

        # Créer une unité de test
        self.unit = self.env['onedesk.unit'].create({
            'name': 'Unité avec Photos',
            'property_id': self.property.id,
            'bedrooms': 2,
            'bathrooms': 1,
            'capacity': 4,
            'unit_type': 'apartment',
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
        # Vérifier que l'image est stockée
        self.assertIsNotNone(image.image)

    def test_property_main_image(self):
        """Test property main_image field"""
        # Ajouter une image principale à la propriété
        self.property.main_image = self.test_image_base64

        self.assertIsNotNone(self.property.main_image)
        # Vérifier qu'on peut récupérer l'image
        self.assertEqual(len(self.property.main_image), len(self.test_image_binary))

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

        # Créer une réservation
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_date = start_date + timedelta(days=3)

        reservation = self.env['onedesk.reservation'].create({
            'unit_id': self.unit.id,
            'partner_id': self.customer.id,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'draft',
        })

        # Ajouter une image de check-in
        reservation.check_in_photo = self.test_image_base64

        self.assertIsNotNone(reservation.check_in_photo)

    def test_property_image_gallery(self):
        """Test property image gallery with multiple images"""
        # Créer plusieurs images pour la galerie
        images = []
        for i in range(3):
            img = self.env['onedesk.property.image'].create({
                'property_id': self.property.id,
                'name': f'Photo {i+1}',
                'image': self.test_image_base64,
                'sequence': i + 1,
                'is_cover': i == 0,  # La première est la couverture
            })
            images.append(img)

        # Vérifier que les images sont créées
        self.assertEqual(len(self.property.image_ids), 3)

        # Vérifier la couverture
        cover_image = self.property.image_ids.filtered(lambda x: x.is_cover)
        self.assertEqual(len(cover_image), 1)
        self.assertEqual(cover_image.sequence, 1)

    def test_unit_image_gallery(self):
        """Test unit image gallery with multiple images"""
        # Créer plusieurs images
        for i in range(4):
            self.env['onedesk.unit.image'].create({
                'unit_id': self.unit.id,
                'name': f'Pièce {i+1}',
                'image': self.test_image_base64,
                'sequence': i + 1,
                'is_cover': i == 0,
            })

        # Vérifier que toutes les images sont créées
        self.assertEqual(len(self.unit.image_ids), 4)

    def test_image_sequence_ordering(self):
        """Test image ordering by sequence"""
        # Créer des images avec différentes séquences
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

        # Récupérer les images triées
        images = self.property.image_ids.sorted(key=lambda x: x.sequence)
        self.assertEqual(images[0].sequence, 1)
        self.assertEqual(images[1].sequence, 2)
        self.assertEqual(images[2].sequence, 3)

    def test_image_set_as_cover(self):
        """Test setting an image as cover"""
        # Créer deux images
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

        # Vérifier que img1 est la couverture
        self.assertTrue(img1.is_cover)
        self.assertFalse(img2.is_cover)

        # Changer la couverture
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

        # Vérifier que l'image est supprimée
        deleted_image = self.env['onedesk.property.image'].browse(image_id)
        self.assertFalse(deleted_image.exists())

    def test_check_in_check_out_photos(self):
        """Test check-in and check-out photos for reservations"""
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

        # Ajouter photos check-in et check-out
        reservation.check_in_photo = self.test_image_base64
        reservation.check_out_photo = self.test_image_base64

        # Vérifier que les deux photos sont présentes
        self.assertIsNotNone(reservation.check_in_photo)
        self.assertIsNotNone(reservation.check_out_photo)
        self.assertNotEqual(reservation.check_in_photo, reservation.check_out_photo)

    def test_unit_image_with_name_description(self):
        """Test unit image with name and description"""
        image = self.env['onedesk.unit.image'].create({
            'unit_id': self.unit.id,
            'name': 'Cuisine équipée',
            'image': self.test_image_base64,
            'sequence': 1,
        })

        self.assertEqual(image.name, 'Cuisine équipée')
        # Vérifier que le nom n'est pas vide
        self.assertTrue(len(image.name) > 0)

    def test_property_image_count(self):
        """Test counting images in property"""
        # Créer 5 images
        for i in range(5):
            self.env['onedesk.property.image'].create({
                'property_id': self.property.id,
                'name': f'Photo {i+1}',
                'image': self.test_image_base64,
            })

        # Vérifier le total
        image_count = len(self.property.image_ids)
        self.assertEqual(image_count, 5)

    def test_image_data_integrity(self):
        """Test that image data is preserved correctly"""
        # Créer une image
        image = self.env['onedesk.property.image'].create({
            'property_id': self.property.id,
            'name': 'Test Intégrité',
            'image': self.test_image_base64,
        })

        # Récupérer l'image et vérifier
        retrieved_image = self.env['onedesk.property.image'].browse(image.id)
        self.assertEqual(retrieved_image.image, self.test_image_base64)

    def test_multiple_units_images_independent(self):
        """Test that images are independent for different units"""
        # Créer une seconde unité
        unit2 = self.env['onedesk.unit'].create({
            'name': 'Unit 2',
            'property_id': self.property.id,
            'bedrooms': 1,
            'bathrooms': 1,
            'capacity': 2,
            'unit_type': 'room',
        })

        # Ajouter images à unit1
        for i in range(3):
            self.env['onedesk.unit.image'].create({
                'unit_id': self.unit.id,
                'name': f'Unit1 Photo {i+1}',
                'image': self.test_image_base64,
            })

        # Ajouter images à unit2
        for i in range(2):
            self.env['onedesk.unit.image'].create({
                'unit_id': unit2.id,
                'name': f'Unit2 Photo {i+1}',
                'image': self.test_image_base64,
            })

        # Vérifier que chaque unité a le bon nombre d'images
        self.assertEqual(len(self.unit.image_ids), 3)
        self.assertEqual(len(unit2.image_ids), 2)
