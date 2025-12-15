# Website OneDesk - Changelog

Documentation des versions et modifications fonctionnelles du module **Website OneDesk**.

---

## Version 1.0.0 (Actuelle)

### 🎯 Fonctionnalités principales

**Objectif**: Créer un site web public pour OneDesk permettant:
1. Affichage et réservation de propriétés en ligne
2. Gestion des souscriptions SaaS multi-tenant
3. Interface client intuitive et responsive

### Architecture du module

```
Website OneDesk
├── Pages Publiques (Propriétés)
│   ├── /onedesk/properties → Listing de toutes les propriétés
│   ├── /onedesk/property/<id> → Détail d'une propriété
│   └── /onedesk/unit/<id> → Détail d'une unité + formulaire de réservation
│
├── Système de Réservation
│   ├── POST /onedesk/booking → Créer une réservation
│   └── POST /onedesk/unit/<id>/availability → Vérifier disponibilité + prix
│
└── Système de Souscription SaaS
    ├── /onedesk/subscription → Plans d'abonnement
    ├── /onedesk/subscription/<plan_id> → Formulaire de souscription
    └── POST /onedesk/subscription/create → Créer une souscription
```

---

## 📋 Section 1: Système de Réservation en Ligne

### 1.1 Page de Listing des Propriétés

**Fichier**: `templates/pages.xml` (lignes 6-148)
**Route**: `/onedesk/properties`
**Controller**: `controllers/main.py:31-46`

**Fonctionnalités**:
- Liste TOUTES les propriétés disponibles sous forme de cartes
- Affiche les unités "orphelines" (importées via intégrations mais sans propriété associée)
- Chaque carte affiche:
  - Photo de couverture (ou dégradé par défaut)
  - Nom et adresse de la propriété
  - Nombre d'unités
  - Taux d'occupation global
  - Type de propriété (badge)

**Code clé** (`main.py:31-46`):
```python
@http.route('/onedesk/properties', type='http', auth='public', website=True)
def properties_list(self, **kw):
    """Page de listing de toutes les propriétés"""
    properties = request.env['onedesk.property'].search([])

    # Aussi récupère les unités "orphelines" (sans propriété)
    orphaned_units = request.env['onedesk.unit'].search([
        ('property_id', '=', False),
        ('external_listing_id', '!=', False)  # Seulement les importées
    ])

    return request.render('website_onedesk.properties_list', {
        'properties': properties,
        'orphaned_units': orphaned_units,
        'page_title': 'Nos propriétés',
    })
```

**Design**:
- Responsive grid (Bootstrap 5)
- Cartes avec effet hover (`hover-shadow`)
- Dégradé violet pour photos manquantes: `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`

---

### 1.2 Page de Détail Propriété

**Fichier**: `templates/pages.xml` (lignes 153-312)
**Route**: `/onedesk/property/<id>`
**Controller**: `controllers/main.py:48-62`

**Fonctionnalités**:
- Carousel de photos (avec image de couverture en premier)
- Informations complètes de la propriété
- Liste des équipements/amenities
- Cartes de toutes les unités disponibles
- Statistiques: revenu mensuel, taux d'occupation moyen

**Code clé** (`main.py:48-62`):
```python
@http.route('/onedesk/property/<model("onedesk.property"):property_id>',
            type='http', auth='public', website=True)
def property_detail(self, property_id, **kw):
    """Page de détail d'une propriété"""
    units = property_id.unit_ids

    # Calcul des stats
    total_revenue = sum(units.mapped('revenue_this_month'))
    avg_occupancy = sum(units.mapped('occupancy_percentage')) / len(units) if units else 0

    return request.render('website_onedesk.property_detail', {
        'property': property_id,
        'units': units,
        'total_revenue': total_revenue,
        'avg_occupancy': avg_occupancy,
    })
```

**Template features**:
- Carousel Bootstrap avec contrôles prev/next
- Section contact avec bouton email
- Grid responsive pour listing des unités

---

### 1.3 Page de Réservation d'Unité

**Fichier**: `templates/pages.xml` (lignes 317-619)
**Route**: `/onedesk/unit/<id>`
**Controller**: `controllers/main.py:64-77`

**Fonctionnalités principales**:
- Carousel de photos de l'unité
- Informations détaillées (chambres, sdb, capacité, tarif)
- **Formulaire de réservation interactif avec**:
  - Date picker (arrivée/départ)
  - Vérification de disponibilité en temps réel (AJAX)
  - Calcul automatique du prix total
  - Champs: nom, email, téléphone, message
- Sidebar avec politique d'annulation et séjour minimum

**JavaScript - Vérification de disponibilité** (lignes 501-544):
```javascript
function checkAvailability() {
    const startDate = document.getElementById('start_date').value;
    const endDate = document.getElementById('end_date').value;

    if (!startDate || !endDate) return;

    fetch('/onedesk/unit/' + unitId + '/availability', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrfToken,
        },
        body: JSON.stringify({
            start_date: startDate,
            end_date: endDate,
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data && data.available) {
            // Affiche prix calculé: nuits, prix/nuit, total avec nettoyage
            document.getElementById('price_info').innerHTML = '✅ Disponible! ...';
        } else {
            // Cache le prix si indisponible
            document.getElementById('price_info').style.display = 'none';
        }
    });
}
```

**JavaScript - Soumission du formulaire** (lignes 546-616):
```javascript
document.getElementById('booking_form').addEventListener('submit', function(e) {
    e.preventDefault();

    fetch('/onedesk/booking', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrfToken,
        },
        body: JSON.stringify({
            unit_id: unitId,
            name: name,
            email: email,
            phone: phone,
            start_date: startDate,
            end_date: endDate,
            message: message,
        })
    })
    .then(r => r.text().then(text => {
        // Parse JSON avec gestion d'erreurs robuste
        let data = JSON.parse(text);
        if (!r.ok) throw new Error(data.message);
        return data;
    }))
    .then(data => {
        if (data.status === 'success') {
            alert(data.message);
            form.reset();
        }
    });
});
```

---

### 1.4 Endpoint AJAX: Vérification de Disponibilité

**Fichier**: `controllers/main.py` (lignes 257-339)
**Route**: `POST /onedesk/unit/<id>/availability`
**Type**: `jsonrpc`
**Auth**: `public`

**Logique**:

1. **Parse les dates** du JSON body
2. **Cherche les réservations qui se chevauchent**:
   ```python
   overlapping = request.env['onedesk.reservation'].search([
       ('unit_id', '=', unit_id.id),
       ('status', '!=', 'cancelled'),
       ('start_date', '<', end_dt),
       ('end_date', '>', start_dt),
   ])
   ```

3. **Si indisponible**: Retourne la liste des périodes occupées
4. **Si disponible**: Calcule et retourne:
   - Nombre de nuits
   - Prix par nuit (avec pricing saisonnier)
   - Prix total
   - Frais de nettoyage
   - Total avec nettoyage

**Réponse JSON**:
```json
{
  "available": true,
  "nights": 5,
  "price_per_night": 150.00,
  "total_price": 750.00,
  "cleaning_fee": 50.00,
  "total_with_cleaning": 800.00
}
```

---

### 1.5 Endpoint: Création de Réservation

**Fichier**: `controllers/main.py` (lignes 81-255)
**Route**: `POST /onedesk/booking`
**Type**: `http`
**Auth**: `public` (mais vérifie si utilisateur connecté)
**CSRF**: Désactivé (`csrf=False`)

**Logique détaillée**:

**Étape 1: Vérification de l'authentification** (lignes 109-119):
```python
if request.env.user._is_public():
    return {
        'status': 'error',
        'message': '🔒 Vous devez créer un compte ou vous connecter',
        'action': 'login_required',
        'login_url': '/web/login',
        'signup_url': '/web/signup',
    }
```

**Étape 2: Validation des champs requis** (lignes 122-130):
```python
required_fields = ['name', 'email', 'unit_id', 'start_date', 'end_date']
for field in required_fields:
    if not data.get(field):
        return {'status': 'error', 'message': f'Le champ "{field}" est requis.'}
```

**Étape 3: Vérification de disponibilité AVANT création** (lignes 153-183):
```python
conflicting = request.env['onedesk.reservation'].sudo().search([
    ('unit_id', '=', unit_id),
    ('status', '!=', 'cancelled'),
    ('start_date', '<', end_datetime),
    ('end_date', '>', start_datetime),
])

if conflicting:
    # Formate le message avec les périodes occupées
    conflict_dates = []
    for res in conflicting:
        conflict_dates.append(f"{start_str} au {end_str}")

    return {
        'status': 'error',
        'message': f"❌ Cette unité n'est pas disponible...\n{conflict_dates}"
    }
```

**Étape 4: Création du partner** (lignes 185-196):
```python
partner = request.env['res.partner'].sudo().search([
    ('email', '=', data.get('email'))
], limit=1)

if not partner:
    partner = request.env['res.partner'].sudo().create({
        'name': data.get('name'),
        'email': data.get('email'),
        'phone': data.get('phone', ''),
    })
```

**Étape 5: Création de la réservation** (lignes 201-208):
```python
reservation = request.env['onedesk.reservation'].sudo().create({
    'unit_id': unit_id,
    'partner_id': partner.id,
    'start_date': start_date.isoformat(),
    'end_date': end_date.isoformat(),
    'guest_notes': data.get('message', ''),
    'status': 'draft',  # En attente de confirmation
})
```

**Étape 6: Envoi email de confirmation** (lignes 213-217):
```python
try:
    reservation.send_confirmation_email()
    _logger.info(f'Confirmation email sent for reservation {reservation.name}')
except Exception as e:
    _logger.error(f'Error sending confirmation email: {str(e)}')
```

**Gestion d'erreurs**:
- `ValueError`: Format de date invalide
- `ValidationError`: Erreur de validation Odoo (chevauchement, etc.)
- `Exception`: Erreur générique

---

## 📋 Section 2: Système de Souscription SaaS

### 2.1 Page de Plans d'Abonnement

**Fichier**: `templates/pages.xml` (lignes 625-822)
**Route**: `/onedesk/subscription`
**Controller**: `controllers/main.py:343-353`

**Fonctionnalités**:
- Affiche tous les plans d'abonnement actifs
- Design "pricing table" moderne et responsive
- Chaque carte de plan affiche:
  - Nom et description du plan
  - **Modèle de tarification**:
    - `per_unit`: Prix par unité/mois
    - `commission`: Pourcentage de commission
  - Frais de setup (si applicable)
  - **Limites incluses**:
    - Max propriétés (ou illimité)
    - Max unités (ou illimité)
    - Nombre d'utilisateurs
  - **Fonctionnalités**:
    - Niveau de support (24/7, business hours, email only)
    - Channel Manager (oui/non)
    - Module comptable (oui/non)
    - Analytique avancée (oui/non)
  - Bouton CTA "Choisir ce plan"

**Code Controller** (`main.py:343-353`):
```python
@http.route('/onedesk/subscription', type='http', auth='public', website=True)
def subscription_plans(self, **kw):
    """Page de plans d'abonnement"""
    plans = request.env['onedesk.subscription.plan'].search([
        ('active', '=', True)
    ], order='sequence')

    return request.render('website_onedesk.subscription_plans', {
        'plans': plans,
        'page_title': 'Plans d\'abonnement OneDesk',
    })
```

**Design features**:
- Cartes avec effet hover (translateY + shadow)
- Badge pour fonctionnalités incluses (icônes Font Awesome)
- Footer avec CTA de contact

---

### 2.2 Formulaire de Souscription

**Fichier**: `templates/subscription.xml` (lignes 6-189)
**Route**: `/onedesk/subscription/<plan_id>`
**Controller**: `controllers/main.py:355-361`

**Sections du formulaire**:

**1. Informations Entreprise**:
- Nom de l'entreprise (requis)
- Nombre d'unités (requis)

**2. Informations Contact**:
- Nom du responsable (requis)
- Email (requis)
- Téléphone (optionnel)

**3. Résumé du Plan**:
- Plan sélectionné
- Tarif (par unité ou commission)
- Frais de setup

**4. Conditions d'Utilisation**:
- Checkbox d'acceptation (requis)

**JavaScript de soumission** (lignes 132-172):
```javascript
document.getElementById('subscription_form').addEventListener('submit', function(e) {
    e.preventDefault();

    const formData = new FormData(this);
    const data = {
        'plan_id': formData.get('plan_id'),
        'company_name': formData.get('company_name'),
        'contact_name': formData.get('contact_name'),
        'email': formData.get('email'),
        'phone': formData.get('phone'),
        'num_units': formData.get('num_units'),
        'terms_accepted': formData.get('terms_accepted') ? 'on' : 'off',
    };

    fetch('/onedesk/subscription/create', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: new URLSearchParams(data),
    })
    .then(r => r.json())
    .then(response => {
        if (response.status === 'success') {
            alert(response.message);
            window.location.href = '/onedesk/subscription';
        } else {
            alert('❌ ' + response.message);
        }
    });
});
```

---

### 2.3 Endpoint: Création de Souscription

**Fichier**: `controllers/main.py` (lignes 363-524)
**Route**: `POST /onedesk/subscription/create`
**Type**: `http`
**Auth**: `public`
**CSRF**: Désactivé (`csrf=False`)

**Logique complète**:

**Étape 1: Validation des données** (lignes 376-393):
```python
required_fields = ['company_name', 'contact_name', 'email', 'num_units']
if not all([company_name, contact_name, email, num_units]):
    return {'status': 'error', 'message': 'Tous les champs requis.'}

if not terms_accepted:
    return {'status': 'error', 'message': 'Acceptez les CGU.'}
```

**Étape 2: Création ou récupération de la Company** (lignes 407-413):
```python
Company = request.env['res.company']
company = Company.search([('name', '=', company_name)], limit=1)
if not company:
    company = Company.sudo().create({
        'name': company_name,
        'is_onedesk_client': True,
    })
```

**Étape 3: Création ou récupération du Partner** (lignes 416-424):
```python
Partner = request.env['res.partner']
partner = Partner.search([('email', '=', email)], limit=1)
if not partner:
    partner = Partner.sudo().create({
        'name': contact_name,
        'email': email,
        'phone': phone if phone else False,
        'company_id': company.id,
    })
```

**Étape 4: Création de la Souscription** (lignes 427-433):
```python
subscription = request.env['onedesk.subscription'].sudo().create({
    'company_id': company.id,
    'plan_id': plan.id,
    'state': 'draft',
    'billing_contact_id': partner.id,
    'requested_units': num_units,
})
```

**Étape 5: Création du Client OneDesk** (lignes 436-449):
```python
client = request.env['onedesk.client'].sudo().search(
    [('company_id', '=', company.id)], limit=1
)
if not client:
    client = request.env['onedesk.client'].sudo().create({
        'company_id': company.id,
        'owner_partner_id': partner.id,
        'subscription_id': subscription.id,
        'state': 'pending_setup',
    })
else:
    client.write({'subscription_id': subscription.id})
```

**Étape 6: Création Audit Log** (lignes 454-463):
```python
request.env['onedesk.audit.log'].sudo().create({
    'log_type': 'subscription_created',
    'severity': 'info',
    'company_id': company.id,
    'subscription_id': subscription.id,
    'description': f'Nouvelle souscription: {subscription.subscription_id}',
    'actor_name': contact_name,
    'actor_email': email,
    'result': 'success',
})
```

**Étape 7: Envoi des emails** (lignes 476-495):

**Email au client**:
```python
template_client = request.env.ref('website_onedesk.email_subscription_confirmation')
template_client.send_mail(subscription.id, force_send=True, email_values={
    'email_to': email,
})
```

**Email à l'admin**:
```python
admin_email = request.env['ir.config_parameter'].sudo().get_param('onedesk.admin_email')
if admin_email:
    template_admin = request.env.ref('website_onedesk.email_subscription_admin_notification')
    template_admin.send_mail(subscription.id, force_send=True, email_values={
        'email_to': admin_email,
    })
```

---

### 2.4 Templates d'Email

**Fichier**: `templates/subscription.xml` (lignes 196-353)

#### Email de Confirmation Client

**Record ID**: `email_subscription_confirmation`
**Sujet**: "Bienvenue sur OneDesk - Votre souscription a été enregistrée"

**Contenu**:
- Header avec titre "✅ Souscription confirmée!"
- Tableau récapitulatif:
  - Numéro de souscription
  - Entreprise
  - Plan choisi
  - Date de début
- Détails de facturation (selon modèle: per_unit ou commission)
- Liste des prochaines étapes:
  1. Examen de la souscription par l'équipe
  2. Réception des détails d'accès
  3. Possibilité de gérer immédiatement
- Informations de support

**Variables disponibles**:
```python
${object.subscription_id}           # Numéro de souscription
${object.company_id.name}            # Nom de l'entreprise
${object.plan_id.name}               # Nom du plan
${object.start_date}                 # Date de début
${object.billing_contact_id.name}    # Nom du contact
```

#### Email de Notification Admin

**Record ID**: `email_subscription_admin_notification`
**Sujet**: "🔔 Nouvelle souscription OneDesk - Action requise"

**Contenu**:
- Header vert "🔔 Nouvelle souscription en attente"
- Tableau avec détails complets:
  - Numéro, Entreprise, Contact
  - Email, Téléphone
  - Plan, Date souscription
- **Liste d'actions à faire**:
  1. Vérifier informations entreprise
  2. Activer compte client
  3. Configurer permissions et accès
  4. Envoyer identifiants au client
  5. Mettre à jour état à "Actif"
- Bouton CTA "➜ Voir la souscription" (lien vers backend)
- Alerte: Statut actuel "Brouillon"

---

## 📁 Structure des Fichiers

### Controllers

**`controllers/main.py`** (524 lignes):
```
OneDeskWebsite (Controller principal)
├── Test Routes
│   ├── /onedesk/test                    → Test simple
│   └── /onedesk/booking-test            → Test JSON
│
├── Pages Publiques
│   ├── /onedesk/properties              → Listing propriétés
│   ├── /onedesk/property/<id>           → Détail propriété
│   └── /onedesk/unit/<id>               → Détail unité + formulaire
│
├── AJAX Endpoints
│   ├── POST /onedesk/booking            → Créer réservation
│   └── POST /onedesk/unit/<id>/availability → Check disponibilité
│
└── Souscription/Pricing
    ├── /onedesk/subscription            → Plans d'abonnement
    ├── /onedesk/subscription/<plan_id>  → Formulaire souscription
    └── POST /onedesk/subscription/create → Créer souscription
```

### Templates

**`templates/pages.xml`** (825 lignes):
- `properties_list` (lignes 6-148): Listing propriétés
- `property_detail` (lignes 153-312): Détail propriété
- `unit_detail` (lignes 317-619): Détail unité + booking form
- `subscription_plans` (lignes 625-822): Pricing table

**`templates/subscription.xml`** (356 lignes):
- `subscription_form` (lignes 6-189): Formulaire souscription
- `email_subscription_confirmation` (lignes 196-272): Email client
- `email_subscription_admin_notification` (lignes 275-353): Email admin

### Assets

**`static/css/website_onedesk.css`**:
- Variables CSS pour couleurs principales
- Styles pour cartes et hover effects
- Responsive design pour mobile
- Animations et transitions

---

## 🔐 Sécurité et Authentification

### Routes Publiques

**Toutes les routes sont publiques** (`auth='public'`):
- `/onedesk/properties`
- `/onedesk/property/<id>`
- `/onedesk/unit/<id>`
- `/onedesk/subscription`
- `/onedesk/subscription/<plan_id>`

### Protection CSRF

- **CSRF désactivé** pour endpoints JSON: `csrf=False`
- **Token CSRF** injecté dans les pages pour usage JavaScript:
  ```javascript
  const csrfToken = '<t t-esc="request.csrf_token()"/>';
  ```

### Vérification d'Authentification

**Pour créer une réservation** (`main.py:109-119`):
```python
if request.env.user._is_public():
    return {
        'status': 'error',
        'message': '🔒 Vous devez créer un compte ou vous connecter',
        'action': 'login_required',
        'login_url': '/web/login',
        'signup_url': '/web/signup',
    }
```

**Implication**: Les visiteurs peuvent VOIR les propriétés, mais doivent se connecter pour RÉSERVER.

### Élévation de Privilèges

**Usage de `.sudo()`**:
- Création de partners: `request.env['res.partner'].sudo().create(...)`
- Création de réservations: `request.env['onedesk.reservation'].sudo().create(...)`
- Création de souscriptions: `request.env['onedesk.subscription'].sudo().create(...)`

**Raison**: Les utilisateurs publics n'ont pas les permissions de créer ces enregistrements directement.

---

## 🎨 Design et UX

### Palette de Couleurs

**Dégradés principaux**:
```css
/* Propriétés */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Unités */
background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
```

**Couleurs Bootstrap**:
- Primary: `#007bff` (bleu)
- Success: `#28a745` (vert)
- Danger: `#dc3545` (rouge)
- Warning: `#ffc107` (jaune)

### Effets Visuels

**Hover sur cartes**:
```css
.plan-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 1rem 2rem rgba(0, 0, 0, 0.15) !important;
}
```

**Carousel Bootstrap 5**:
- Contrôles prev/next
- Indicateurs de position
- Transitions automatiques

### Responsive Design

**Breakpoints Bootstrap**:
- `col-lg-*`: Desktop (≥ 992px)
- `col-md-*`: Tablette (≥ 768px)
- `col-*`: Mobile (< 768px)

**Grid Properties Listing**:
```html
<div class="col-lg-4 col-md-6 mb-4">
  <!-- Card -->
</div>
```
- Desktop: 3 colonnes
- Tablette: 2 colonnes
- Mobile: 1 colonne

---

## 🔄 Intégration avec OneDesk Core

### Modèles Utilisés

**Lecture**:
- `onedesk.property` - Propriétés
- `onedesk.unit` - Unités/chambres
- `onedesk.reservation` - Réservations
- `onedesk.seasonal_price` - Tarification saisonnière
- `onedesk.subscription.plan` - Plans d'abonnement

**Création**:
- `res.partner` - Contacts clients
- `res.company` - Sociétés clientes
- `onedesk.reservation` - Nouvelles réservations
- `onedesk.subscription` - Nouvelles souscriptions
- `onedesk.client` - Nouveaux clients
- `onedesk.audit.log` - Logs d'audit

### Champs Clés

**Property**:
- `name`, `address`, `property_type`, `amenities`, `description`
- `image_ids` (relation), `unit_ids` (relation)
- `total_units` (computed), `total_occupancy_percentage` (computed)

**Unit**:
- `name`, `bedrooms`, `bathrooms`, `capacity`
- `price_per_night`, `cleaning_fee`, `minimum_stay`
- `cancellation_policy`, `maintenance_notes`
- `image_ids` (relation)
- `occupancy_percentage` (computed), `revenue_this_month` (computed)
- `get_price_for_dates(start, end)` (method)

**Reservation**:
- `unit_id`, `partner_id`, `start_date`, `end_date`
- `status`: `draft`, `confirmed`, `cancelled`
- `guest_notes`, `special_requests`
- `send_confirmation_email()` (method)

**Subscription**:
- `company_id`, `plan_id`, `billing_contact_id`
- `state`: `draft`, `active`, `suspended`, `cancelled`
- `subscription_id` (auto-generated), `start_date`, `requested_units`

---

## 📧 Configuration Email

### Paramètres Système

**Email Admin** (pour notifications):
```python
admin_email = request.env['ir.config_parameter'].sudo().get_param('onedesk.admin_email')
```

**Configuration requise**:
1. Aller dans: **Paramètres** → **Technique** → **Paramètres système**
2. Créer: `onedesk.admin_email` = `admin@onedesk.com`

### Templates Email

**Deux templates dans `subscription.xml`**:
1. `email_subscription_confirmation` - Envoyé au client
2. `email_subscription_admin_notification` - Envoyé à l'admin

**Configuration SMTP**:
- **Paramètres** → **Technique** → **Serveurs de messagerie sortants**
- Configurer: SMTP host, port, username, password
- Tester: Bouton "Tester la connexion"

---

## 🐛 Gestion d'Erreurs

### Erreurs de Réservation

**1. Utilisateur non connecté**:
```json
{
  "status": "error",
  "message": "🔒 Vous devez créer un compte ou vous connecter",
  "action": "login_required",
  "login_url": "/web/login"
}
```

**2. Champs manquants**:
```json
{
  "status": "error",
  "message": "Le champ \"email\" est requis."
}
```

**3. Unité indisponible**:
```json
{
  "status": "error",
  "message": "❌ Cette unité n'est pas disponible...\nPériodes occupées:\n  • 20/12/2024 au 25/12/2024"
}
```

**4. Format de date invalide**:
```json
{
  "status": "error",
  "message": "Format de date invalide. Veuillez utiliser YYYY-MM-DD."
}
```

### Erreurs de Souscription

**1. Champs requis manquants**:
```json
{
  "status": "error",
  "message": "Tous les champs marqués avec * sont requis."
}
```

**2. CGU non acceptées**:
```json
{
  "status": "error",
  "message": "Veuillez accepter les conditions d'utilisation."
}
```

**3. Plan inexistant**:
```json
{
  "status": "error",
  "message": "Ce plan n'existe pas."
}
```

### Logging

**Tous les endpoints logguent**:
```python
_logger.info('✅ Subscription created: {sub_id} for {company}')
_logger.error('❌ Erreur lors de la migration: {e}', exc_info=True)
_logger.warning('⚠️ Groupe {ref} introuvable: {e}')
```

**Visualiser les logs**:
```bash
# Odoo log file
tail -f /var/log/odoo/odoo.log

# Ou journalctl si service systemd
journalctl -u odoo -f
```

---

## 🧪 Tests

**Fichier**: `tests/test_booking_controller.py`

### Test de Création de Réservation

**Tests inclus**:
- Créer une réservation valide
- Vérifier qu'un partner est créé
- Vérifier que la réservation est en état `draft`
- Tester les erreurs de validation

### Test de Disponibilité

**Tests inclus**:
- Vérifier disponibilité pour dates valides
- Vérifier indisponibilité si réservation existante
- Tester calcul du prix avec saisonnalité

### Test de Souscription

**Fichier**: `tests/test_subscription_portal.py`

**Tests inclus**:
- Affichage correct des plans
- Soumission du formulaire
- Création company + partner + subscription
- Envoi des emails

---

## 📊 Performance

### Optimisations

**1. Queries ORM optimisées**:
```python
# Bon: Single query avec préchargement
properties = request.env['onedesk.property'].search([])
# Les relations image_ids, unit_ids sont préchargées automatiquement

# Éviter: N+1 queries
for property in properties:
    images = property.image_ids  # Évite query supplémentaire
```

**2. Cache Odoo**:
- Les records sont automatiquement cachés par l'ORM
- Pas besoin de cache manuel pour lectures

**3. AJAX pour calculs**:
- Vérification de disponibilité en temps réel (pas de rechargement page)
- Calcul de prix instantané

### Limites

**Pas de pagination**:
```python
# Affiche TOUTES les propriétés
properties = request.env['onedesk.property'].search([])
```

**Recommandation**: Ajouter pagination si > 50 propriétés:
```python
# Exemple avec pagination
page = int(kw.get('page', 1))
limit = 12
offset = (page - 1) * limit
properties = request.env['onedesk.property'].search([], limit=limit, offset=offset)
```

---

## 🚀 Améliorations Futures

### Fonctionnalités Suggérées

**1. Système d'Avis/Reviews**:
- Permettre aux clients de laisser des avis
- Afficher note moyenne sur cartes de propriétés
- Modération des avis par admin

**2. Galeries Photos**:
- Upload multiple d'images
- Zoom/lightbox sur photos
- Tri drag-and-drop des photos

**3. Filtres de Recherche**:
- Filtrer par prix, nombre de chambres, capacité
- Recherche par dates de disponibilité
- Tri par prix, popularité, note

**4. Paiement en Ligne**:
- Intégration Stripe/PayPal
- Paiement immédiat lors de la réservation
- Gestion des remboursements

**5. Multi-langue**:
- Traductions FR/EN/ES
- Sélecteur de langue
- Utiliser module `base` d'Odoo pour traductions

**6. Notifications SMS**:
- Confirmation de réservation par SMS
- Rappel 24h avant arrivée
- Intégration Twilio

**7. Portail Client**:
- Tableau de bord client
- Historique des réservations
- Gestion du profil
- Messages directs avec propriétaire

**8. Calendrier Interactif**:
- Afficher disponibilités sur calendrier visuel
- Bloquer plusieurs dates en un clic
- Intégration Google Calendar/iCal

---

## 📝 Migration et Déploiement

### Installation

**1. Copier le module**:
```bash
cp -r website_onedesk /path/to/odoo/addons/
```

**2. Mettre à jour la liste des modules**:
```bash
./odoo-bin -u website_onedesk -d your_database --stop-after-init
```

**3. Installer via interface**:
- Aller dans **Apps**
- Rechercher "OneDesk Website"
- Cliquer sur **Installer**

### Dépendances

**Modules Odoo requis**:
- `website`: Framework web Odoo
- `onedesk_core`: Module principal OneDesk

**Dépendances Python**:
- Aucune dépendance externe
- Utilise uniquement bibliothèques Python standard

### Configuration Post-Installation

**1. Configurer l'email admin**:
```sql
INSERT INTO ir_config_parameter (key, value)
VALUES ('onedesk.admin_email', 'admin@yourcompany.com');
```

**2. Configurer SMTP**:
- **Paramètres** → **Technique** → **Serveurs de messagerie sortants**

**3. Créer des plans d'abonnement**:
- **OneDesk** → **Configuration** → **Plans d'Abonnement**
- Créer au moins un plan avec `active=True`

**4. Tester le site**:
- Ouvrir: `http://your-domain/onedesk/properties`
- Vérifier affichage des propriétés
- Tester formulaire de réservation

---

## 🔗 Liens Utiles

### URLs Principales

**Frontend**:
- Propriétés: `/onedesk/properties`
- Souscription: `/onedesk/subscription`

**Backend Odoo**:
- Propriétés: **OneDesk** → **Propriétés**
- Réservations: **OneDesk** → **Réservations**
- Souscriptions: **OneDesk** → **Souscriptions**
- Plans: **OneDesk** → **Configuration** → **Plans d'Abonnement**

### Documentation Externe

**Odoo**:
- [Website Framework](https://www.odoo.com/documentation/19.0/developer/reference/frontend/website.html)
- [Controllers](https://www.odoo.com/documentation/19.0/developer/reference/backend/http.html)
- [QWeb Templates](https://www.odoo.com/documentation/19.0/developer/reference/frontend/qweb.html)

**Bootstrap 5**:
- [Documentation](https://getbootstrap.com/docs/5.0/)
- [Grid System](https://getbootstrap.com/docs/5.0/layout/grid/)
- [Components](https://getbootstrap.com/docs/5.0/components/)

---

## 👥 Mainteneurs

- **Auteur**: Merveilles
- **License**: LGPL-3
- **Catégorie**: Website
- **Version Odoo**: 19.0

---

## 📞 Support

Pour toute question ou problème:
- Email: support@onedesk.com
- Documentation: `/addons/website_onedesk/README.md`
- Issues GitHub: (URL du repo si applicable)

---

*Dernière mise à jour: 2025-12-15*
