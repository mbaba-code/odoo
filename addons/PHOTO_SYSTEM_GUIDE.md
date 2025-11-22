# Système de Photos OneDesk - Documentation Complète

## Vue d'Ensemble

Le système de photos OneDesk fonctionne avec **3 modèles distincts** qui gèrent les images pour les propriétés, unités et réservations. Chaque système a sa propre galerie avec des caractéristiques spécifiques.

---

## 1. Architecture Générale

### Modèles d'Images

```
┌─ Property (propriété)
│  └─ image_ids (One2many)
│     └─ onedesk.property.image [Galerie complète]
│
├─ Unit (unité)
│  └─ image_ids (One2many)
│     └─ onedesk.unit.image [Galerie complète]
│
└─ Reservation (réservation)
   └─ image_ids (One2many)
      └─ onedesk.reservation.image [Documentation check-in/out]
```

---

## 2. Système de Photos pour PROPERTY

### Structure de Données

**Modèle: `onedesk.property` → Fichier: `onedesk_property.py`**

```python
# Photo principale (directe)
main_image = fields.Image(
    string="Photo principale",
    max_width=1024,
    max_height=1024,
    help="Photo de couverture de la propriété"
)

# Galerie complète
image_ids = fields.One2many(
    'onedesk.property.image',
    'property_id',
    string='Galerie de photos',
    help="Galerie complète de photos de la propriété"
)

# Photo de couverture (auto-extraite de la galerie)
cover_image = fields.Image(
    string="Photo de couverture (Galerie)",
    compute='_compute_cover_image',
    readonly=True
)

# ID de la photo de couverture (pour kanban)
cover_image_id = fields.Integer(
    compute='_compute_cover_image_id',
    readonly=True
)
```

### Modèle d'Image: `onedesk.property.image`

**Fichier: `onedesk_image.py`**

```python
class OnedeskoPropertyImage(models.Model):
    _name = 'onedesk.property.image'
    _description = 'Property Photo/Image'
    _order = 'sequence, id'  # Tri par séquence puis ID

    property_id = fields.Many2one(
        'onedesk.property',
        string="Propriété",
        required=True,
        ondelete='cascade'  # Supprimer l'image si la propriété est supprimée
    )

    name = fields.Char(
        string="Titre de la photo",
        help="Ex: Vue d'ensemble, Chambre principale, Cuisine"
    )

    image = fields.Image(
        string="Photo",
        max_width=2048,
        max_height=2048,
        required=True
    )

    is_cover = fields.Boolean(
        string="📌 Photo de couverture",
        default=False,
        help="Marquez comme photo de couverture principale"
    )

    sequence = fields.Integer(
        string="Ordre d'affichage",
        default=10,
        help="Plus bas = affiché en premier"
    )
```

### Logique de Couverture

```python
@api.depends('image_ids', 'image_ids.is_cover', 'image_ids.image')
def _compute_cover_image(self):
    """Sélectionne automatiquement la photo de couverture"""
    for record in self:
        # 1️⃣ Chercher une image marquée comme couverture
        cover_img = record.image_ids.filtered(lambda x: x.is_cover)
        if cover_img:
            record.cover_image = cover_img[0].image
        # 2️⃣ Sinon, utiliser la première image de la galerie
        elif record.image_ids:
            record.cover_image = record.image_ids[0].image
        # 3️⃣ Sinon, utiliser la photo principale
        else:
            record.cover_image = record.main_image
```

**Priorité d'affichage:**
1. Image marquée `is_cover = True`
2. Première image de la galerie
3. Photo principale (`main_image`)
4. Icône de placeholder

---

## 3. Système de Photos pour UNIT

### Structure de Données

**Modèle: `onedesk.unit` → Fichier: `onedesk_unit.py`**

```python
# Photo principale (directe)
main_image = fields.Image(
    string="Photo principale",
    max_width=1024,
    max_height=1024
)

# Galerie complète
image_ids = fields.One2many(
    'onedesk.unit.image',
    'unit_id',
    string='Galerie de photos',
    help="Galerie complète de photos de l'unité"
)

# Photo de couverture (auto-extraite)
cover_image = fields.Image(
    string="Photo de couverture (Galerie)",
    compute='_compute_cover_image',
    readonly=True
)

# ID pour affichage kanban
cover_image_id = fields.Integer(
    compute='_compute_cover_image_id',
    readonly=True
)
```

### Modèle d'Image: `onedesk.unit.image`

```python
class OnedeskoUnitImage(models.Model):
    _name = 'onedesk.unit.image'
    _description = 'Unit Photo/Image'
    _order = 'sequence, id'

    unit_id = fields.Many2one(
        'onedesk.unit',
        string="Unité",
        required=True,
        ondelete='cascade'
    )

    name = fields.Char(
        string="Titre de la photo",
        help="Ex: Chambre, Salle de bain, Salon"
    )

    image = fields.Image(
        string="Photo",
        max_width=2048,
        max_height=2048,
        required=True
    )

    is_cover = fields.Boolean(
        string="📌 Photo de couverture",
        default=False
    )

    sequence = fields.Integer(
        string="Ordre d'affichage",
        default=10,
        help="Plus bas = affiché en premier"
    )
```

### Logique Identique à Property

La logique de sélection de couverture est **identique à celle de Property**:
1. Chercher image avec `is_cover = True`
2. Sinon première image de la galerie
3. Sinon photo principale
4. Sinon placeholder

---

## 4. Système de Photos pour RESERVATION

### Structure Unique

**Modèle: `onedesk.reservation` → Fichier: `onedesk_reservation.py`**

```python
# Galerie de documentation (Check-in/Check-out)
image_ids = fields.One2many(
    'onedesk.reservation.image',
    'reservation_id',
    string='Galerie d\'inspection',
    help="Galerie complète de photos d'inspection (check-in et check-out)"
)

# Photo de couverture (similaire à property/unit)
cover_image = fields.Image(
    string="Photo de couverture",
    compute='_compute_cover_image',
    readonly=True
)

cover_image_id = fields.Integer(
    compute='_compute_cover_image_id',
    readonly=True
)
```

### Modèle d'Image: `onedesk.reservation.image`

**Différence clé: `image_type` pour catégoriser les photos**

```python
class OnedeskoReservationImage(models.Model):
    _name = 'onedesk.reservation.image'
    _description = 'Reservation Photo/Image (Check-in/Check-out documentation)'
    _order = 'sequence, id'

    reservation_id = fields.Many2one(
        'onedesk.reservation',
        string="Réservation",
        required=True,
        ondelete='cascade'
    )

    name = fields.Char(
        string="Titre de la photo",
        help="Ex: État du salon, Cuisine avant nettoyage"
    )

    image = fields.Image(
        string="Photo",
        max_width=2048,
        max_height=2048,
        required=True
    )

    # 🔑 UNIQUE: Type de photo (Check-in, Check-out, Dégâts, etc.)
    image_type = fields.Selection([
        ('check_in', 'Arrivée (Check-in)'),
        ('check_out', 'Départ (Check-out)'),
        ('damage', 'Dégâts/Problèmes'),
        ('other', 'Autre'),
    ], string="Type de photo", default='other')

    sequence = fields.Integer(
        string="Ordre d'affichage",
        default=10
    )
```

### Utilité de `image_type`

```
check_in   ➜ Photos au moment de l'arrivée du client
check_out  ➜ Photos au moment du départ
damage     ➜ Documentation des dégâts ou problèmes détectés
other      ➜ Autres photos de documentation
```

**Exemple d'utilisation:**
- Client arrive: Photographier l'état général (Check-in)
- Avant nettoyage: Documenter toute saleté ou dégât (Damage)
- Après nettoyage: Photographier l'état final (Check-out)

---

## 5. Affichage des Images dans les Views

### A. Vue Kanban (Galerie)

**Fichier: `onedesk_image_views.xml`**

#### Code HTML/Template:

```xml
<kanban string="Photo Gallery">
    <field name="id"/>
    <field name="image" widget="binary"/>
    <field name="name"/>
    <field name="is_cover"/>
    <field name="sequence"/>
    <templates>
        <t t-name="card">
            <div class="oe_kanban_card">
                <!-- Conteneur image avec hover effect -->
                <div style="height: 150px; margin-bottom: 10px; border-radius: 5px;
                            overflow: hidden; background: #f0f0f0; display: flex;
                            align-items: center; justify-content: center; position: relative;
                            cursor: pointer; transition: transform 0.2s;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);"
                     onmouseover="this.style.transform='scale(1.05)'; this.style.boxShadow='0 4px 8px rgba(0,0,0,0.2)'"
                     onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 2px 4px rgba(0,0,0,0.1)'"
                     onclick="if(record.image.raw_value) window.showImageModal(...)">

                    <!-- Affichage image ou placeholder -->
                    <t t-if="record.image.raw_value">
                        <img t-att-src="'data:image/*;base64,' + record.image.raw_value"
                             style="width: 100%; height: 100%; object-fit: cover;"
                             alt="Photo"/>
                    </t>
                    <t t-else="">
                        <i class="fa fa-image fa-3x" style="color: #ccc;"></i>
                    </t>

                    <!-- Badge "Couverture" si is_cover=true -->
                    <t t-if="record.is_cover.value">
                        <div style="position: absolute; top: 5px; right: 5px;
                                    background: #28a745; color: white; padding: 5px 10px;
                                    border-radius: 3px; font-weight: bold; font-size: 11px;">
                            📌 Couverture
                        </div>
                    </t>

                    <!-- Icône de zoom -->
                    <div style="position: absolute; bottom: 5px; right: 5px;
                                background: rgba(0,0,0,0.5); color: white;
                                width: 30px; height: 30px; border-radius: 50%;
                                display: flex; align-items: center; justify-content: center;">
                        🔍
                    </div>
                </div>

                <!-- Titre -->
                <h4 style="margin: 5px 0; font-weight: bold; font-size: 12px;">
                    <field name="name"/>
                </h4>

                <!-- Bouton définir comme couverture -->
                <button type="button" class="btn btn-sm btn-outline-primary"
                        name="action_set_cover" string="📌 Couverture"/>
            </div>
        </t>
    </templates>
</kanban>
```

#### Caractéristiques:
- 📸 Images affichées en base64 (encode directement dans HTML)
- 🎯 `object-fit: cover` - L'image remplit le conteneur en conservant l'aspect
- ✨ Hover effect - Scale 1.05 avec ombre augmentée
- 🔍 Zoom modal au clic
- 📌 Badge vert pour la couverture
- 🔄 Bouton pour définir comme couverture

### B. Vue Form (Édition)

```xml
<form string="Property Photo">
    <sheet>
        <group>
            <group>
                <field name="name"/>
                <field name="is_cover" widget="boolean"/>
                <field name="sequence"/>
            </group>
            <group>
                <field name="property_id"/>
            </group>
        </group>
        <!-- Affichage large de l'image -->
        <field name="image" widget="image"/>
    </sheet>
</form>
```

### C. Integration dans la vue principale (Property)

```xml
<!-- Affichage photo de couverture -->
<group>
    <field name="cover_image" widget="image" options="{'size': [300, 300]}"/>
</group>

<!-- Galerie en mode kanban (vue par défaut) -->
<separator string="🖼️ Galerie complète de photos (Mode Grille)"/>
<field name="image_ids" mode="kanban">
    <!-- Kanban view défini dans onedesk_image_views.xml -->
</field>

<!-- Galerie en mode liste (pour ajouter/modifier rapidement) -->
<field name="image_ids">
    <list string="Photos" editable="bottom">
        <field name="sequence" widget="handle"/>
        <field name="is_cover" widget="boolean"/>
        <field name="name"/>
        <field name="image" widget="image" optional="hide"/>
    </list>
</field>
```

---

## 6. Kanban Card Affichage Principal

### Affichage dans la Vue Kanban de Property

```xml
<kanban>
    <field name="cover_image_id"/>  <!-- ID de la photo de couverture -->
    <templates>
        <t t-name="card">
            <div class="oe_kanban_card">
                <!-- Affichage image ou placeholder -->
                <div style="height: 200px; border-radius: 5px; overflow: hidden; background: #f0f0f0;">
                    <t t-if="record.cover_image_id.value">
                        <!-- Affichage via URL Odoo (meilleur pour kanban) -->
                        <img t-att-src="'/web/image/onedesk.property.image/' +
                                         record.cover_image_id.value + '/image'"
                             style="width: 100%; height: 100%; object-fit: cover;"
                             alt="Property photo"/>
                    </t>
                    <t t-else="">
                        <i class="fa fa-image fa-3x" style="color: #ccc;"></i>
                    </t>
                </div>

                <!-- Infos propriété -->
                <h3><field name="name"/></h3>
                <span class="badge badge-light">
                    <field name="property_type"/>
                </span>
            </div>
        </t>
    </templates>
</kanban>
```

### Approches d'Affichage Image

| Approche | Syntaxe | Utilisation | Avantages |
|----------|---------|-------------|-----------|
| **Base64** | `'data:image/*;base64,' + record.image.raw_value` | Galerie kanban | Performance pour petites images |
| **URL Odoo** | `/web/image/model/id/field` | Kanban principal | Optimisé par serveur, cache |
| **Widget image** | `<field name="image" widget="image"/>` | Form | Meilleure UI |

---

## 7. Modal de Zoom

### JavaScript dans `onedesk_image_views.xml`

```javascript
function showImageModal(imageSrc, imageTitle) {
    const modal = document.getElementById('imageModal');

    // Créer modal s'il n'existe pas
    if (!modal) {
        const newModal = document.createElement('div');
        newModal.id = 'imageModal';
        newModal.innerHTML = `
            <span class="image-modal-close" onclick="closeImageModal()">&times;</span>
            <div class="image-modal-content">
                <img id="modalImage" src="" alt="Full size image"/>
                <div class="image-modal-title" id="imageTitle"></div>
            </div>
        `;
        document.body.appendChild(newModal);
    }

    // Remplir et afficher
    document.getElementById('modalImage').src = imageSrc;
    document.getElementById('imageTitle').textContent = imageTitle || 'Photo';
    document.getElementById('imageModal').style.display = 'block';

    // Fermer au clic en dehors ou Escape
    document.onkeydown = (e) => {
        if (e.key === 'Escape') closeImageModal();
    };
}

function closeImageModal() {
    const modal = document.getElementById('imageModal');
    if (modal) modal.style.display = 'none';
    document.onkeydown = null;
}

window.showImageModal = showImageModal;
window.closeImageModal = closeImageModal;
```

### CSS Modal

```css
.image-modal {
    display: none;
    position: fixed;
    z-index: 9999;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.8);  /* Fond semi-transparent */
    animation: fadeIn 0.3s ease-in;
}

.image-modal-content {
    position: relative;
    margin: auto;
    max-width: 90vw;
    max-height: 90vh;
    top: 50%;
    transform: translateY(-50%);
    animation: zoomIn 0.3s ease-in;
}

.image-modal-close {
    position: absolute;
    top: 20px;
    right: 30px;
    color: white;
    font-size: 40px;
    cursor: pointer;
    z-index: 10001;
}

.image-modal-title {
    position: absolute;
    bottom: 20px;
    left: 20px;
    color: white;
    background-color: rgba(0, 0, 0, 0.6);
    padding: 10px 15px;
    border-radius: 5px;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes zoomIn {
    from { transform: translateY(-50%) scale(0.8); opacity: 0; }
    to { transform: translateY(-50%) scale(1); opacity: 1; }
}
```

---

## 8. Flux d'Utilisation Complet

### Pour une PROPERTY:

```
1. Créer Property
   ↓
2. Ajouter Photos dans Galerie
   ├─ Uploader image
   ├─ Donner un titre (Ex: "Chambre principale")
   ├─ Cocher "📌 Photo de couverture" si c'est la couverture
   └─ Définir sequence (ordre d'affichage)
   ↓
3. La "Photo de couverture" s'affiche automatiquement:
   ├─ Dans la fiche de la propriété
   ├─ Dans le kanban card
   └─ Dans les vues publiques
   ↓
4. Voir la galerie:
   ├─ Mode Kanban = Vue d'ensemble avec hover/zoom
   └─ Mode Liste = Édition rapide et sequence
```

### Pour une RESERVATION:

```
1. Créer Reservation
   ↓
2. Check-in:
   ├─ Photographier état général → image_type='check_in'
   ├─ Documenter dégâts → image_type='damage'
   └─ Écrire titre/observations
   ↓
3. Pendant séjour:
   └─ Ajouter photos si problèmes → image_type='damage'
   ↓
4. Check-out:
   ├─ Photographier état final → image_type='check_out'
   ├─ Comparer avec check-in
   └─ Documenter nettoyage
   ↓
5. Justification:
   └─ Galerie photos de toute la réservation pour litiges
```

---

## 9. Comparaison Property vs Unit vs Reservation

| Aspect | Property | Unit | Reservation |
|--------|----------|------|-------------|
| **Modèle** | onedesk.property | onedesk.unit | onedesk.reservation |
| **Table images** | property.image | unit.image | reservation.image |
| **Photo principale** | `main_image` | `main_image` | ❌ Non |
| **Galerie** | `image_ids` (One2many) | `image_ids` (One2many) | `image_ids` (One2many) |
| **Cover auto** | ✅ Oui | ✅ Oui | ✅ Oui |
| **Champs image** | name, image, is_cover, sequence | name, image, is_cover, sequence | name, image, **image_type**, sequence |
| **image_type** | ❌ Non | ❌ Non | ✅ Oui (check_in, check_out, damage) |
| **Ordre d'affichage** | ✅ Sequence | ✅ Sequence | ✅ Sequence |
| **Taille max** | 2048x2048 | 2048x2048 | 2048x2048 |
| **Utilité** | Portfolio immobilier | Détails logement | Documentation location |

---

## 10. Tips et Optimisations

### ✅ Bonnes Pratiques

1. **Compression images**: Les images doivent être < 500KB
2. **Format optimal**: JPG pour photos, PNG pour captures
3. **Résolution**: 1920x1280 minimum pour qualité
4. **Titre descriptif**: "Chambre principale - Vue fenêtre" vs "Photo 1"
5. **Couverture prioritaire**: Toujours marquer la meilleure photo comme couverture

### ⚠️ À Éviter

- Images > 2MB (erreur de stockage)
- Photos floues ou mal cadrées comme couverture
- Trop de photos (>50) = performance dégradée
- Pas de titres = galerie peu compréhensible

### 🚀 Améliorations Futures

```python
# Compression automatique
from PIL import Image
img = Image.open(uploaded_file)
img.thumbnail((2048, 2048))
img.save(format='JPEG', quality=85)

# Génération miniatures
cover_image_thumb = compute_thumbnail(image, (300, 300))

# Tri intelligent des images
image_ids = self.image_ids.sorted(
    key=lambda x: (not x.is_cover, x.sequence)
)
```

---

## 11. Fichiers Importants

| Fichier | Rôle |
|---------|------|
| `onedesk_property.py` | Modèle Property avec logique cover_image |
| `onedesk_unit.py` | Modèle Unit avec logique cover_image |
| `onedesk_reservation.py` | Modèle Reservation |
| `onedesk_image.py` | 3 modèles d'images (Property, Unit, Reservation) |
| `onedesk_image_views.xml` | Vues kanban/form pour images + modal JS/CSS |
| `onedesk_property_views.xml` | Integration images dans Property form |
| `onedesk_unit_views.xml` | Integration images dans Unit form |
| `onedesk_reservation_views.xml` | Integration images dans Reservation form |

---

## Résumé Visuel

```
┌─────────────────────────────────────────────────────┐
│              SYSTÈME D'IMAGES OneDesk                │
├─────────────────────────────────────────────────────┤
│                                                       │
│  PROPERTY                                            │
│  ├─ main_image → Photo principale                   │
│  ├─ image_ids → [onedesk.property.image]           │
│  │  ├─ name, image, is_cover, sequence             │
│  │  └─ cover_image (computed) ← Auto-sélection     │
│  │     Priorité: is_cover > 1ère image > main      │
│  └─ Affichage: Kanban (galerie) + List (édition)   │
│                                                       │
│  UNIT                                                │
│  ├─ main_image → Photo principale                   │
│  ├─ image_ids → [onedesk.unit.image]               │
│  │  ├─ name, image, is_cover, sequence             │
│  │  └─ cover_image (computed) ← Auto-sélection     │
│  └─ Affichage: Kanban (galerie) + List (édition)   │
│                                                       │
│  RESERVATION                                         │
│  ├─ image_ids → [onedesk.reservation.image]        │
│  │  ├─ name, image, image_type, sequence           │
│  │  │  image_type = check_in, check_out, damage    │
│  │  └─ cover_image (computed)                       │
│  └─ Affichage: Kanban (galerie) + List (édition)   │
│                                                       │
│  VUE KANBAN:                                         │
│  ├─ Base64 encoding pour affichage rapide          │
│  ├─ Hover effect (scale 1.05)                      │
│  ├─ Badge "📌 Couverture" si is_cover              │
│  ├─ Icône 🔍 zoom                                   │
│  └─ Modal click pour voir full-size                │
│                                                       │
│  MODAL ZOOM:                                        │
│  ├─ Full-screen avec image centrée                 │
│  ├─ Titre en bas à gauche                          │
│  ├─ Fermeture: Escape ou clic dehors               │
│  └─ Animations fadeIn/zoomIn                        │
│                                                       │
└─────────────────────────────────────────────────────┘
```

Voilà ! Le système d'images OneDesk est conçu pour être **intuitif**, **performant** et **flexible**, avec support pour différents cas d'usage (portfolio, documentation, inspection).
