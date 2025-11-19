# OneDesk iCal Integration Analysis Report

## Executive Summary

I've analyzed the OneDesk codebase and identified the root cause of the issue where **property names and unit names become identical** during iCal imports.

---

## 1. HOW ICAL IMPORTS ARE CURRENTLY HANDLED

### File: `/home/user/odoo/addons/onedesk_core/models/onedesk_integration.py`

#### Key Method: `_sync_ical()` (lines 374-421)

This method handles iCal file parsing and import. It:
- Fetches the iCal file from the configured URL
- Parses each VEVENT component
- Extracts: UID, SUMMARY, LOCATION, DTSTART, DTEND, DESCRIPTION
- Creates res_data dictionary with extracted values
- Calls _process_reservation() for each event

**Critical extraction (line 394-410):**
```
SUMMARY field → res_data['name'] (used for reservation name)
LOCATION field → res_data['location'] (used for property info)
```

**Problem:** SUMMARY is NOT being mapped to unit_name in res_data

---

## 2. THE PROPERTY MODEL: `onedesk.property`

### File: `/home/user/odoo/addons/onedesk_core/models/onedesk_property.py`

**Purpose:** Represents a physical property/building that contains multiple units

**Key Fields:**
- `name`: Property name (required)
- `address`: Property address (required)
- `property_type`: house, apartment, villa, etc.
- `unit_ids`: One2many relationship to units
- `company_id`: Multi-tenant support

---

## 3. THE UNIT MODEL: `onedesk.unit`

### File: `/home/user/odoo/addons/onedesk_core/models/onedesk_unit.py`

**Purpose:** Represents a single rental unit within a property

**Key Fields:**
- `name`: Unit name (required) - e.g., "Apartment 101" or "Studio A"
- `property_id`: Reference to parent property (required)
- `external_listing_id`: ID from external platform (Airbnb, Booking, etc.)
- `integration_id`: Reference to the integration source
- `price_per_night`: Base price
- `capacity`: Max guests
- `bedrooms`, `bathrooms`: Unit features

**Relationship:** Many units per property (1:N)

---

## 4. ROOT CAUSE: THE MAPPING LOGIC ISSUE

### The Problem Chain:

**Step 1: iCal SUMMARY is not mapped to unit_name**
- File: onedesk_integration.py, _sync_ical() method, lines 394-410
- SUMMARY → res_data['name'] (reservation name)
- SUMMARY NOT → res_data['unit_name'] (empty!)
- LOCATION → res_data['location'] (property address)

**Step 2: Property creation gets address as name**
- File: onedesk_integration.py, _find_or_create_property() lines 576-614
- property_name = data.get('location') = "42 Rue des Francs-Bourgeois, 75004 Paris"
- Creates property with name = address ⚠️

**Step 3: Unit name generated from property name**
- File: onedesk_integration.py, _find_or_create_unit() lines 640-645
- unit_name = data.get('unit_name') = EMPTY (for iCal)
- Since unit_name is empty: unit_name = "{property_name} - Unité {count}"
- Results in: unit_name = "42 Rue... - Unité 1" ⚠️

**Result:** property.name ≈ unit.name ❌

---

## 5. TEST ICAL FILE STRUCTURE

### File: `/home/user/odoo/addons/onedesk_core/fichier_test/test_ical.ics`

**Example entries:**

```ical
BEGIN:VEVENT
UID:RES-20251120-001@onedesk.com
SUMMARY:Appartement Paris Centre - Marais          ← Unit name
LOCATION:42 Rue des Francs-Bourgeois, 75004 Paris  ← Property address
DTSTART;VALUE=DATE:20251120
DTEND;VALUE=DATE:20251125
DESCRIPTION:Reservation confirmee...
END:VEVENT

BEGIN:VEVENT
UID:RES-20251122-002@onedesk.com
SUMMARY:Studio Centre Ville Lyon                   ← Unit name
LOCATION:123 Rue de la Paix, 69000 Lyon            ← Property address
...
```

---

## 6. WHAT SHOULD HAPPEN vs WHAT HAPPENS

### Should Be:
```
iCal Event:
  SUMMARY: "Appartement Paris Centre - Marais"
  LOCATION: "42 Rue des Francs-Bourgeois, 75004 Paris"
                ↓
Result:
  Property.name = "42 Rue des Francs-Bourgeois..." OR "Paris Centre - Marais"
  Property.address = "42 Rue des Francs-Bourgeois..."
  Unit.name = "Appartement Paris Centre - Marais"
```

### Actually Happens:
```
iCal Event:
  SUMMARY: "Appartement Paris Centre - Marais"    → res_data['name']
  LOCATION: "42 Rue des Francs-Bourgeois..."      → res_data['location']
                ↓
  unit_name = None (not extracted from SUMMARY!)
  property_name = "42 Rue des Francs-Bourgeois..."
                ↓
Result:
  Property.name = "42 Rue des Francs-Bourgeois..." ⚠️
  Property.address = "42 Rue des Francs-Bourgeois..."
  Unit.name = "42 Rue... - Unité 1" ⚠️

PROBLEM: Property and Unit have identical/similar names!
```

---

## 7. KEY CODE SECTIONS

### `_sync_ical()` - Where iCal is parsed (lines 374-421)

```python
res_data = {
    'id': str(component.get('uid')),
    'name': str(component.get('summary', 'Réservation')),  # ← SUMMARY for reservation
    'start_date': component.get('dtstart').dt if component.get('dtstart') else False,
    'end_date': component.get('dtend').dt if component.get('dtend') else False,
    'description': description,
    'location': str(component.get('location', '')),  # ← LOCATION (address)
    # MISSING: 'unit_name': str(component.get('summary', '')) ← SHOULD ADD THIS!
    # MISSING: 'property_name': ...  ← Should extract meaningful property name
}
```

### `_find_or_create_property()` - Creates property (lines 574-601)

```python
property_name = (
    data.get('property_name') or
    data.get('listing_name') or
    data.get('location') or  # ← Uses address as property name!
    'Propriété importée'
)

# Creates: property.name = address
prop = Property.sudo().create({
    'name': property_name,  # ⚠️ = "42 Rue..."
    'address': data.get('location', ''),
})
```

### `_find_or_create_unit()` - Creates unit (lines 603-667)

```python
unit_name = data.get('unit_name') or data.get('listing_name')  # ← EMPTY for iCal!
property_name = (
    data.get('property_name') or
    data.get('listing_name') or
    data.get('location') or
    'Propriété importée'
)

if not unit and self.auto_create_units:
    property_id = self._find_or_create_property(data)
    
    if not unit_name:  # ← True for iCal!
        unit_count = Unit.search_count([
            ('property_id', '=', property_id.id),
        ]) + 1
        unit_name = f"{property_name} - Unité {unit_count}"  # ← Auto-generated!
    
    unit = Unit.sudo().create({
        'name': unit_name,  # ⚠️ = "42 Rue... - Unité 1"
        'property_id': property_id.id,
    })
```

---

## 8. MAPPING DATA FLOW

```
_sync_ical()
    │
    ├─ SUMMARY → res_data['name']
    └─ LOCATION → res_data['location']
        │
        ↓
    _process_reservation(res_data)
        │
        ↓
    _find_or_create_unit(data)
        │
        ├─ unit_name = data.get('unit_name')  ← EMPTY
        ├─ property_name = data.get('location')  ← "42 Rue..."
        │
        ↓
        _find_or_create_property(data)
            │
            └─ property.name = "42 Rue..."
        │
        └─ unit.name = "42 Rue... - Unité 1"
```

---

## 9. SUMMARY OF FINDINGS

### Issue #1: Missing SUMMARY → unit_name mapping
- **Location:** _sync_ical() method (line 406)
- **Status:** CONFIRMED
- **Impact:** unit_name is empty for all iCal imports

### Issue #2: LOCATION used as property.name
- **Location:** _find_or_create_property() (line 576-579)
- **Status:** CONFIRMED
- **Impact:** Property named after address instead of meaningful name

### Issue #3: Auto-generated unit name from property name
- **Location:** _find_or_create_unit() (line 640-645)
- **Status:** CONFIRMED
- **Impact:** Unit and property have identical/similar names

---

## 10. KEY FILE PATHS (absolute)

- `/home/user/odoo/addons/onedesk_core/models/onedesk_integration.py`
- `/home/user/odoo/addons/onedesk_core/models/onedesk_property.py`
- `/home/user/odoo/addons/onedesk_core/models/onedesk_unit.py`
- `/home/user/odoo/addons/onedesk_core/fichier_test/test_ical.ics`
- `/home/user/odoo/addons/onedesk_core/tests/test_integration.py`

