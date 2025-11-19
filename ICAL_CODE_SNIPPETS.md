# OneDesk iCal Integration - Code Snippets & Detailed Analysis

## QUICK REFERENCE

### The Three Problems:

1. **SUMMARY field not mapped to unit_name** in `_sync_ical()`
2. **LOCATION (address) used as property.name** in `_find_or_create_property()`
3. **Unit name auto-generated from property name** in `_find_or_create_unit()`

---

## PROBLEM 1: MISSING SUMMARY → UNIT_NAME MAPPING

### Location: `/home/user/odoo/addons/onedesk_core/models/onedesk_integration.py`
### Method: `_sync_ical()` 
### Lines: 394-417

```python
# CURRENT CODE (INCORRECT)
cal = Calendar.from_ical(response.content)

count = 0
for component in cal.walk():
    if component.name == "VEVENT":
        description = str(component.get('description', ''))
        
        # Parse la description pour extraire les infos
        guest_info = self._parse_ical_description(description)
        
        res_data = {
            'id': str(component.get('uid')),
            'name': str(component.get('summary', 'Réservation')),  # ← Uses SUMMARY
            'start_date': component.get('dtstart').dt if component.get('dtstart') else False,
            'end_date': component.get('dtend').dt if component.get('dtend') else False,
            'description': description,
            'location': str(component.get('location', '')),  # ← Uses LOCATION
            'guest_name': guest_info.get('guest_name'),
            'guest_email': guest_info.get('guest_email'),
            'guest_phone': guest_info.get('guest_phone'),
            'price': guest_info.get('price'),
            'adults': guest_info.get('adults'),
            'children': guest_info.get('children'),
        }
        # ❌ PROBLEM: 'unit_name' is MISSING!
        # ❌ PROBLEM: 'property_name' is NOT extracted!
        
        if self._process_reservation(res_data):
            count += 1
```

### What's Missing:
```python
# SHOULD ALSO INCLUDE:
res_data = {
    ...existing fields...
    'unit_name': str(component.get('summary', '')),  # ← ADD THIS (iCal SUMMARY is unit name)
    'property_name': None,  # ← Let _find_or_create_property() handle location parsing
}
```

---

## PROBLEM 2: LOCATION USED AS PROPERTY NAME

### Location: `/home/user/odoo/addons/onedesk_core/models/onedesk_integration.py`
### Method: `_find_or_create_property()`
### Lines: 574-601

```python
def _find_or_create_property(self, data):
    """Trouve ou crée la propriété pour une unité importée"""
    property_name = (
        data.get('property_name') or        # ← First priority (None for iCal)
        data.get('listing_name') or         # ← Second priority (None for iCal)
        data.get('location') or             # ← THIRD: Uses address! (For iCal)
        'Propriété importée'                # ← Final fallback
    )
    # ❌ PROBLEM: property_name = "42 Rue des Francs-Bourgeois, 75004 Paris"
    
    Property = self.env['onedesk.property']
    
    # Cherche une propriété correspondante
    prop = Property.search([
        ('name', 'ilike', property_name),   # ← Search for property by ADDRESS name
    ], limit=1)
    
    # Crée une propriété si elle n'existe pas
    if not prop:
        prop = Property.sudo().create({
            'name': property_name,          # ❌ Property name = ADDRESS
            'address': data.get('location', ''),  # ✓ Address is correct
            'property_type': 'apartment',
            'description': f"Propriété importée depuis {self.provider_id.name}",
            'company_id': self.company_id.id,
        })
        _logger.info(f"🏘️ Nouvelle propriété créée: {property_name}")
    
    return prop
```

### Example Result:
```
Data from iCal:
  location = "42 Rue des Francs-Bourgeois, 75004 Paris"

Created Property:
  name = "42 Rue des Francs-Bourgeois, 75004 Paris"  ❌ (address, not name!)
  address = "42 Rue des Francs-Bourgeois, 75004 Paris"  ✓
```

---

## PROBLEM 3: AUTO-GENERATED UNIT NAME FROM PROPERTY NAME

### Location: `/home/user/odoo/addons/onedesk_core/models/onedesk_integration.py`
### Method: `_find_or_create_unit()`
### Lines: 603-667

```python
def _find_or_create_unit(self, data):
    """Trouve ou crée l'unité"""
    
    # STEP 1: Try to get unit_name from data
    unit_name = data.get('unit_name') or data.get('listing_name')
    # ❌ PROBLEM: For iCal, unit_name = None (it was never extracted)
    
    # STEP 2: Determine property_name
    property_name = (
        data.get('property_name') or        # ← None for iCal
        data.get('listing_name') or         # ← None for iCal
        data.get('location') or             # ← "42 Rue..." for iCal
        'Propriété importée'
    )
    # ❌ PROBLEM: property_name = "42 Rue des Francs-Bourgeois, 75004 Paris"
    
    Unit = self.env['onedesk.unit']
    external_listing_id = data.get('external_listing_id') or data.get('listing_id')
    
    # Cherche par ID externe en priorité
    unit = False
    if external_listing_id:
        unit = Unit.search([
            ('external_listing_id', '=', external_listing_id),
            ('integration_id', '=', self.id),
        ], limit=1)
    
    # Sinon cherche par nom + propriété
    if not unit and unit_name:
        unit = Unit.search([
            ('name', 'ilike', unit_name),
            ('property_id.name', 'ilike', property_name),
        ], limit=1)
    
    # Crée l'unité si elle n'existe pas
    if not unit and self.auto_create_units:
        # Auto-crée la propriété associée
        property_id = self._find_or_create_property(data)
        
        # STEP 3: AUTO-GENERATE UNIT NAME (THE BUG!)
        if not unit_name:  # ← Always True for iCal!
            # Compte le nombre d'unités existantes dans la propriété
            unit_count = Unit.search_count([
                ('property_id', '=', property_id.id),
            ]) + 1
            unit_name = f"{property_name} - Unité {unit_count}"
            # ❌ RESULT: unit_name = "42 Rue... - Unité 1"
        
        # Creates unit with auto-generated name matching property name
        unit = Unit.sudo().create({
            'name': unit_name,  # ❌ = "42 Rue... - Unité 1"
            'property_id': property_id.id if property_id else (self.default_property_id.id if self.default_property_id else False),
            'external_listing_id': external_listing_id,
            'integration_id': self.id,
            'available': True,
            'capacity': capacity,
            'bedrooms': bedrooms,
            'bathrooms': bathrooms,
            'price_per_night': price,
            'company_id': self.company_id.id,
        })
        _logger.info(f"🏠 Nouvelle unité créée: {unit_name}...")
    
    return unit
```

### Example Result for iCal Event:
```
iCal VEVENT:
  SUMMARY: "Appartement Paris Centre - Marais"
  LOCATION: "42 Rue des Francs-Bourgeois, 75004 Paris"

Step 1: unit_name = None (not extracted)
Step 2: property_name = "42 Rue des Francs-Bourgeois, 75004 Paris"
Step 3: Auto-generate: unit_name = "42 Rue... - Unité 1"

Result:
  Property.name = "42 Rue des Francs-Bourgeois, 75004 Paris"
  Unit.name = "42 Rue... - Unité 1"
  
PROBLEM: Names are now identical! ❌
```

---

## WHAT SHOULD HAPPEN

### Corrected Flow:

```python
# In _sync_ical(), add unit_name extraction:
res_data = {
    'id': str(component.get('uid')),
    'name': str(component.get('summary', 'Réservation')),
    'unit_name': str(component.get('summary', '')),  # ← ADD THIS!
    'start_date': component.get('dtstart').dt,
    'end_date': component.get('dtend').dt,
    'description': description,
    'location': str(component.get('location', '')),
    'guest_name': guest_info.get('guest_name'),
    ...
}
```

```python
# In _find_or_create_unit():
if not unit_name:
    # For iCal, unit_name SHOULD be populated from SUMMARY
    # But if it's STILL empty, THEN fall back to generating from LOCATION
    # Extract a meaningful property name from location (city, address)
    location = data.get('location', '')
    if location:
        # Extract city or meaningful part
        property_name = location.split(',')[0] if ',' in location else location
    else:
        property_name = 'Propriété importée'
    
    unit_name = f"{property_name} - Unité {unit_count}"
```

---

## TEST ICAL FILE REFERENCE

### File: `/home/user/odoo/addons/onedesk_core/fichier_test/test_ical.ics`

```ical
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//OneDesk//OneDesk Reservations//FR

BEGIN:VEVENT
 UID:RES-20251120-001@onedesk.com
DTSTAMP:20251117T132023Z
DTSTART;VALUE=DATE:20251120
DTEND;VALUE=DATE:20251125
SUMMARY:Appartement Paris Centre - Marais        ← UNIT NAME
DESCRIPTION:Reservation confirmee pour l'appartement...
LOCATION:42 Rue des Francs-Bourgeois\\, 75004 Paris\\, France  ← PROPERTY ADDRESS
STATUS:CONFIRMED
END:VEVENT

BEGIN:VEVENT
 UID:RES-20251122-002@onedesk.com
DTSTAMP:20251117T132023Z
DTSTART;VALUE=DATE:20251122
DTEND;VALUE=DATE:20251124
SUMMARY:Studio Centre Ville Lyon               ← UNIT NAME
DESCRIPTION:Reservation confirmee pour un studio au coeur de Lyon.
LOCATION:123 Rue de la Paix\\, 69000 Lyon\\, France  ← PROPERTY ADDRESS
STATUS:CONFIRMED
END:VEVENT

END:VCALENDAR
```

---

## INTEGRATION MODEL CONFIGURATION

### File: `/home/user/odoo/addons/onedesk_core/models/onedesk_integration.py`
### Lines: 20-83 (Model definition)

```python
class OnedeskIntegration(models.Model):
    _name = 'onedesk.integration'
    
    # ... fields ...
    
    # Méthode de connexion
    connection_method = fields.Selection([
        ('oauth', 'OAuth 2.0 (Recommandé)'),
        ('ical', 'iCal URL'),  # ← iCal integration method
        ('csv', 'Import CSV Manuel'),
    ], string='Méthode', required=True, default='oauth')
    
    # iCal
    ical_url = fields.Char(string='URL iCal')  # ← URL to iCal file
    
    # Options de mapping
    auto_create_units = fields.Boolean(string='Créer unités automatiquement', default=True)
    auto_create_contacts = fields.Boolean(string='Créer contacts automatiquement', default=True)
    default_unit_id = fields.Many2one('onedesk.unit', string='Unité par défaut')
    default_property_id = fields.Many2one('onedesk.property', string='Propriété par défaut')
```

---

## MODELS STRUCTURE

### Property Model: `/home/user/odoo/addons/onedesk_core/models/onedesk_property.py`

```python
class OnedeskProperty(models.Model):
    _name = 'onedesk.property'
    
    name = fields.Char(string="Nom de la propriété", required=True)
    address = fields.Char(string="Adresse", required=True)
    property_type = fields.Selection([
        ('house', 'Maison'),
        ('apartment', 'Appartement'),
        ('villa', 'Villa'),
        ...
    ], default='house', required=True)
    
    company_id = fields.Many2one('res.company', required=True)
    unit_ids = fields.One2many('onedesk.unit', 'property_id', string='Unités')
    
    # Example:
    # name = "42 Rue des Francs-Bourgeois, 75004 Paris"  ❌ (should be meaningful name)
    # address = "42 Rue des Francs-Bourgeois, 75004 Paris"  ✓ (correct)
```

### Unit Model: `/home/user/odoo/addons/onedesk_core/models/onedesk_unit.py`

```python
class OnedeskUnit(models.Model):
    _name = 'onedesk.unit'
    
    name = fields.Char(string="Nom de l'unité", required=True)
    property_id = fields.Many2one('onedesk.property', string="Propriété", required=True)
    
    external_listing_id = fields.Char(string="ID Listing Externe")
    integration_id = fields.Many2one('onedesk.integration', string="Intégration source")
    
    price_per_night = fields.Float(required=True, default=100.0)
    capacity = fields.Integer(default=2)
    bedrooms = fields.Integer(default=1)
    bathrooms = fields.Integer(default=1)
    
    # Example:
    # name = "Appartement Paris Centre - Marais"  ✓ (should come from iCal SUMMARY)
    # property_id = property#123  ✓ (correct reference)
```

