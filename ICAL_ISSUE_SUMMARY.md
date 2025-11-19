# OneDesk iCal Integration Issue - Executive Summary

## The Issue

When importing reservations via iCal, **property names and unit names become identical or very similar**, causing confusion and data duplication in the system.

### Example:
```
Property created: "42 Rue des Francs-Bourgeois, 75004 Paris"
Unit created:    "42 Rue des Francs-Bourgeois... - Unité 1"

Expected:
Unit name:       "Appartement Paris Centre - Marais" (from iCal SUMMARY)
Property name:   "Paris Centre - Marais" or "Property 1"
```

---

## Root Cause Analysis

The iCal integration has **three interconnected bugs** in the mapping logic:

### Bug #1: SUMMARY Not Mapped to unit_name

**File:** `/home/user/odoo/addons/onedesk_core/models/onedesk_integration.py`  
**Method:** `_sync_ical()` (lines 394-417)  
**Issue:** The iCal SUMMARY field (unit identifier) is extracted but only used for the reservation name. It's NOT passed as `unit_name` in the res_data dictionary.

**Current:**
```python
res_data = {
    'id': str(component.get('uid')),
    'name': str(component.get('summary', 'Réservation')),  # Uses SUMMARY
    'location': str(component.get('location', '')),        # Uses LOCATION
    # Missing: 'unit_name' key!
}
```

**Should Be:**
```python
res_data = {
    ...
    'unit_name': str(component.get('summary', '')),  # ADD THIS LINE
    ...
}
```

---

### Bug #2: LOCATION (Address) Used as Property Name

**File:** `/home/user/odoo/addons/onedesk_core/models/onedesk_integration.py`  
**Method:** `_find_or_create_property()` (lines 576-579)  
**Issue:** When creating a property, the LOCATION field (the actual address) is used as the property NAME, rather than a meaningful identifier.

**Problem Code:**
```python
property_name = (
    data.get('property_name') or
    data.get('listing_name') or
    data.get('location') or  # ← Uses address as property name!
    'Propriété importée'
)

prop = Property.sudo().create({
    'name': property_name,           # ❌ = "42 Rue des Francs-Bourgeois..."
    'address': data.get('location', ''),  # ✓ = "42 Rue des Francs-Bourgeois..."
})
```

---

### Bug #3: Unit Name Auto-Generated from Property Name

**File:** `/home/user/odoo/addons/onedesk_core/models/onedesk_integration.py`  
**Method:** `_find_or_create_unit()` (lines 640-645)  
**Issue:** When unit_name is empty (which it always is for iCal due to Bug #1), the system generates a unit name by combining the property name with a counter.

**Problem Code:**
```python
unit_name = data.get('unit_name') or data.get('listing_name')  # ← Empty for iCal

if not unit_name:  # ← Always True due to Bug #1
    unit_count = Unit.search_count([
        ('property_id', '=', property_id.id),
    ]) + 1
    unit_name = f"{property_name} - Unité {unit_count}"  # ← Auto-generated from Bug #2 name
```

---

## Data Flow Showing All Three Bugs

```
iCal VEVENT
    ↓
SUMMARY: "Appartement Paris Centre - Marais"  → res_data['name'] only ❌ Bug #1
LOCATION: "42 Rue des Francs-Bourgeois, 75004 Paris" → res_data['location']
    ↓
_process_reservation(res_data)
    ↓
_find_or_create_unit(data)
    ├─ unit_name = None ❌ Bug #1 (not extracted from SUMMARY)
    ├─ property_name = "42 Rue..." ❌ Bug #2 (from LOCATION/address)
    ├─ Creates property with name = "42 Rue..."
    ├─ unit_name = "42 Rue... - Unité 1" ❌ Bug #3 (auto-generated)
    └─ Creates unit with name = "42 Rue... - Unité 1"

RESULT: Property and Unit names are nearly identical! ❌
```

---

## Expected vs Actual Results

### Expected Behavior:
```
iCal VEVENT Components:
├── SUMMARY: "Appartement Paris Centre - Marais" → unit.name ✓
├── LOCATION: "42 Rue des Francs-Bourgeois, 75004 Paris" → property.address ✓
└── Property name should be extracted from LOCATION or SUMMARY ✓

Result:
- Property: name="42 Rue des Francs-Bourgeois" or "Paris Centre - Marais", address="42 Rue..."
- Unit: name="Appartement Paris Centre - Marais"
- Relationship: Unit.property_id → Property
```

### Actual Behavior (With Bugs):
```
Result:
- Property: name="42 Rue des Francs-Bourgeois, 75004 Paris", address="42 Rue..."
- Unit: name="42 Rue des Francs-Bourgeois... - Unité 1"
- Problem: Names are nearly identical!
```

---

## Key Files Involved

| File | Purpose | Lines |
|------|---------|-------|
| `/home/user/odoo/addons/onedesk_core/models/onedesk_integration.py` | iCal sync & mapping logic | 374-667 |
| `/home/user/odoo/addons/onedesk_core/models/onedesk_property.py` | Property model definition | 1-190 |
| `/home/user/odoo/addons/onedesk_core/models/onedesk_unit.py` | Unit model definition | 1-295 |
| `/home/user/odoo/addons/onedesk_core/fichier_test/test_ical.ics` | Test iCal file | 1-56 |
| `/home/user/odoo/addons/onedesk_core/tests/test_integration.py` | Integration tests | 1-263 |

---

## Detailed Documentation

For more detailed analysis with code snippets and examples, see:

1. **ICAL_INTEGRATION_ANALYSIS.md** - Comprehensive analysis of the iCal integration flow
2. **ICAL_CODE_SNIPPETS.md** - Detailed code sections with annotations

---

## Quick Fix Summary

### Fix #1: Add unit_name extraction in _sync_ical()
Line 417, add:
```python
'unit_name': str(component.get('summary', '')),
```

### Fix #2: Improve property name extraction
In `_find_or_create_property()`, extract a meaningful name from LOCATION/SUMMARY instead of using the full address as the property name.

### Fix #3: Preserve unit_name extraction
Ensure unit_name is properly used when auto-generating unit names in `_find_or_create_unit()`.

---

## Model Relationship Diagram

```
OnedeskProperty (Parent)
├── name: "Paris Centre - Marais" (or extracted from location)
├── address: "42 Rue des Francs-Bourgeois, 75004 Paris"
├── property_type: apartment
└── unit_ids: [
    OnedeskUnit (Child)
    ├── name: "Appartement Paris Centre - Marais"
    ├── property_id: → OnedeskProperty.id
    ├── bedrooms: 2
    ├── bathrooms: 1
    ├── price_per_night: 100.0
    └── reservation_ids: [
        OnedeskReservation
        ├── name: "Appartement Paris Centre - Marais"
        ├── unit_id: → OnedeskUnit.id
        ├── start_date: 2025-11-20
        ├── end_date: 2025-11-25
        └── external_id: "ical:RES-20251120-001@onedesk.com"
    ]
]
```

---

## iCal Standard Field Mapping

| iCal Field | Current Mapping | Should Map To |
|----------|-----------------|---------------|
| SUMMARY | res_data['name'] | unit.name + res_data['unit_name'] |
| LOCATION | res_data['location'] | property.address + property.name (extract) |
| UID | res_data['id'] | external_id |
| DTSTART | res_data['start_date'] | reservation.start_date |
| DTEND | res_data['end_date'] | reservation.end_date |
| DESCRIPTION | parsed for guest info | guest_name, guest_email, etc. |

---

## Testing

Test file location: `/home/user/odoo/addons/onedesk_core/fichier_test/test_ical.ics`

Three VEVENT examples:
1. "Appartement Paris Centre - Marais" at "42 Rue des Francs-Bourgeois, 75004 Paris"
2. "Studio Centre Ville Lyon" at "123 Rue de la Paix, 69000 Lyon"
3. "Villa avec piscine - Cote d'Azur" at "456 Avenue de la Mer, 06600 Antibes"

Each can be tested to verify that unit names are correctly mapped from SUMMARY and distinct from property names.

---

## Configuration Options

The integration can be configured with:
- `auto_create_units`: Auto-creates units if not found (default: True)
- `auto_create_contacts`: Auto-creates guest contacts (default: True)
- `default_unit_id`: Fallback unit if mapping fails
- `default_property_id`: Fallback property if mapping fails

These options interact with the mapping bugs, potentially masking or exacerbating the issue.

---

## Impact Assessment

- **Severity:** High - Data integrity issue
- **Scope:** All iCal imports (affects data organization)
- **Frequency:** Occurs on every iCal import
- **User Impact:** Confusing property/unit naming, potential booking errors

