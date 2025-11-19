# OneDesk iCal Integration - Correct Structure

## 📋 Overview

This document shows the **correct iCal structure** for OneDesk integration after the 3 bugs have been fixed.

---

## ✅ Correct iCal Format

### Field Mapping

| iCal Field | Maps To | Notes |
|------------|---------|-------|
| **SUMMARY** | `unit.name` | The unit/apartment identifier (e.g., "Apartment 101", "Studio A") |
| **LOCATION** | `property.address` | Full address (street, city, country) |
| **UID** | `external_id` | Unique identifier for deduplication |
| **DTSTART** | `start_date` | Check-in date |
| **DTEND** | `end_date` | Check-out date |
| **DESCRIPTION** | Guest info + reservation notes | Can include guest name, email, phone, price, guests |

---

## 📝 Complete iCal Example

```ical
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//OneDesk//OneDesk Reservations//FR
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Mes Reservations OneDesk
X-WR-CALDESC:Calendrier de toutes mes reservations de logement

BEGIN:VEVENT
UID:RES-20251120-001@onedesk.com
DTSTAMP:20251117T132023Z
DTSTART;VALUE=DATE:20251120
DTEND;VALUE=DATE:20251125
SUMMARY:Appartement Paris Centre - Marais
LOCATION:42 Rue des Francs-Bourgeois, 75004 Paris, France
DESCRIPTION:Reservation confirmee pour l'appartement Paris Centre - Marais.
  Voyageur: Jean Dupont
  Email: jean@example.com
  Téléphone: +33612345678
  Prix: 500
  Adultes: 2
  Enfants: 1
URL:https://onedesk.com/reservations/RES-001
STATUS:CONFIRMED
TRANSP:OPAQUE
END:VEVENT

BEGIN:VEVENT
UID:RES-20251122-002@onedesk.com
DTSTAMP:20251117T132023Z
DTSTART;VALUE=DATE:20251122
DTEND;VALUE=DATE:20251124
SUMMARY:Studio Centre Ville Lyon
LOCATION:123 Rue de la Paix, 69000 Lyon, France
DESCRIPTION:Reservation confirmee pour un studio au coeur de Lyon.
  Voyageur: Marie Martin
  Email: marie@example.com
  Téléphone: +33698765432
  Prix: 350
  Adultes: 1
  Enfants: 0
URL:https://onedesk.com/reservations/RES-002
STATUS:CONFIRMED
TRANSP:OPAQUE
END:VEVENT

BEGIN:VEVENT
UID:RES-20251215-003@onedesk.com
DTSTAMP:20251117T132023Z
DTSTART;VALUE=DATE:20251215
DTEND;VALUE=DATE:20251220
SUMMARY:Villa avec piscine - Cote d'Azur
LOCATION:456 Avenue de la Mer, 06600 Antibes, France
DESCRIPTION:Reservation en attente de confirmation pour une villa avec piscine.
  Voyageur: Pierre Dupuis
  Email: pierre@example.com
  Téléphone: +33756432109
  Prix: 800
  Adultes: 4
  Enfants: 2
GEO:43.5890;7.1230
URL:https://onedesk.com/reservations/RES-003
STATUS:TENTATIVE
TRANSP:TRANSPARENT
END:VEVENT

END:VCALENDAR
```

---

## 🔄 Data Flow After Fixes

### Event 1: "Appartement Paris Centre - Marais"

**Input (iCal VEVENT):**
```
SUMMARY: "Appartement Paris Centre - Marais"          ← Unit identifier
LOCATION: "42 Rue des Francs-Bourgeois, 75004 Paris"  ← Full address
DESCRIPTION: "Reservation confirmee... Voyageur: Jean..."
```

**Processing:**

1. **_sync_ical()** extracts:
   ```python
   res_data = {
       'id': 'RES-20251120-001@onedesk.com',
       'name': 'Appartement Paris Centre - Marais',      # ← res_name
       'unit_name': 'Appartement Paris Centre - Marais',  # ✅ FIX #1: Now extracted!
       'location': '42 Rue des Francs-Bourgeois, 75004 Paris',
       'guest_name': 'Jean Dupont',
       'guest_email': 'jean@example.com',
       'guest_phone': '+33612345678',
       'price': 500,
       'adults': 2,
       'children': 1,
   }
   ```

2. **_find_or_create_property()** creates:
   ```python
   property_name = extract_from_location("42 Rue..., 75004 Paris, France")
   # → "Paris" (extracted city)

   Property = {
       'name': 'Paris',                                 # ✅ FIX #2: Meaningful name!
       'address': '42 Rue des Francs-Bourgeois, 75004 Paris',
       'property_type': 'apartment',
   }
   ```

3. **_find_or_create_unit()** creates:
   ```python
   unit_name = data.get('unit_name')  # ✅ FIX #1: Now has value!
   # → "Appartement Paris Centre - Marais"

   Unit = {
       'name': 'Appartement Paris Centre - Marais',     # ✅ FIX #3: Uses SUMMARY!
       'property_id': 1,  # → Paris property
       'capacity': 2,
       'bedrooms': 1,
       'bathrooms': 1,
       'price_per_night': 500,
   }
   ```

4. **Result:**
   ```
   Property: name="Paris", address="42 Rue des Francs-Bourgeois, 75004 Paris"
   Unit: name="Appartement Paris Centre - Marais", property_id=1

   ✅ Property and Unit names are DIFFERENT and MEANINGFUL!
   ```

---

## 🏗️ Model Relationships After Import

```
OnedeskProperty
├── id: 1
├── name: "Paris"                           ← Extracted from LOCATION
├── address: "42 Rue des Francs-Bourgeois, 75004 Paris"
├── property_type: "apartment"
└── unit_ids: [1, 2, ...]

  └─ OnedeskUnit (id: 1)
     ├── name: "Appartement Paris Centre - Marais"   ← From SUMMARY
     ├── property_id: 1
     ├── capacity: 2
     ├── bedrooms: 1
     ├── bathrooms: 1
     ├── price_per_night: 500
     └── reservation_ids: [1, ...]

       └─ OnedeskReservation (id: 1)
          ├── name: "Appartement Paris Centre - Marais"
          ├── unit_id: 1
          ├── start_date: 2025-11-20
          ├── end_date: 2025-11-25
          ├── external_id: "RES-20251120-001@onedesk.com"
          ├── guest_id: Partner with name "Jean Dupont"
          └── total_price: 500
```

---

## 📋 Multiple Properties Example

### Lyon Property

```ical
BEGIN:VEVENT
UID:RES-20251122-002@onedesk.com
DTSTART;VALUE=DATE:20251122
DTEND;VALUE=DATE:20251124
SUMMARY:Studio Centre Ville Lyon
LOCATION:123 Rue de la Paix, 69000 Lyon, France
DESCRIPTION:Reservation confirmee...
  Voyageur: Marie Martin
  Email: marie@example.com
  Prix: 350
  Adultes: 1
END:VEVENT
```

**Result:**
- Property: name="Lyon", address="123 Rue de la Paix, 69000 Lyon, France"
- Unit: name="Studio Centre Ville Lyon", property_id=2

### Antibes Property

```ical
BEGIN:VEVENT
UID:RES-20251215-003@onedesk.com
DTSTART;VALUE=DATE:20251215
DTEND;VALUE=DATE:20251220
SUMMARY:Villa avec piscine - Cote d'Azur
LOCATION:456 Avenue de la Mer, 06600 Antibes, France
DESCRIPTION:Reservation...
  Voyageur: Pierre Dupuis
  Prix: 800
  Adultes: 4
  Enfants: 2
END:VEVENT
```

**Result:**
- Property: name="Antibes", address="456 Avenue de la Mer, 06600 Antibes, France"
- Unit: name="Villa avec piscine - Cote d'Azur", property_id=3

---

## 🔄 Location Parsing Examples

The new `_extract_property_name_from_location()` function extracts meaningful property names:

| Location Input | Extracted Name |
|----------------|-----------------|
| "42 Rue des Francs-Bourgeois, 75004 Paris, France" | "Paris" |
| "123 Rue de la Paix, 69000 Lyon, France" | "Lyon" |
| "456 Avenue de la Mer, 06600 Antibes, France" | "Antibes" |
| "1 Rue de la Monnaie, 13000 Marseille, France" | "Marseille" |
| "Apartment 5, 10015 Milano, Italy" | "Milano" |

**Logic:**
1. Split location by commas
2. Extract postal code + city (second-to-last part): "75004 Paris"
3. Parse postal code: "75004"
4. Extract city name: "Paris"
5. Return city name

---

## 📊 Expected vs Before/After

### BEFORE (With 3 Bugs)

```
iCal Input:
├── SUMMARY: "Appartement Paris Centre - Marais"
└── LOCATION: "42 Rue des Francs-Bourgeois, 75004 Paris, France"

Result:
├── Property: name = "42 Rue des Francs-Bourgeois, 75004 Paris, France"  ❌
│                   (full address used as name!)
│
└── Unit: name = "42 Rue des Francs-Bourgeois... - Unité 1"  ❌
          (auto-generated from property address!)

PROBLEM: Property and Unit names are nearly identical!
```

### AFTER (Bugs Fixed)

```
iCal Input:
├── SUMMARY: "Appartement Paris Centre - Marais"
└── LOCATION: "42 Rue des Francs-Bourgeois, 75004 Paris, France"

Result:
├── Property: name = "Paris"                          ✅
│            address = "42 Rue..., 75004 Paris..."   ✅
│
└── Unit: name = "Appartement Paris Centre - Marais"  ✅
          (from SUMMARY as intended!)

SOLUTION: Property and Unit names are distinct and meaningful!
```

---

## 🧪 Testing

To test the integration with the sample iCal:

1. Upload test_ical.ics to a URL
2. Create OneDesk integration with that URL
3. Run sync

**Expected Results:**
- 3 properties: "Paris", "Lyon", "Antibes"
- 3 units with distinct names from SUMMARY
- Each unit linked to correct property
- Guest information parsed from DESCRIPTION

---

## 🔧 Optional Fields in DESCRIPTION

You can include guest details in the DESCRIPTION field. The parser looks for:

```
Voyageur: [Guest Name]
Email: [Guest Email]
Téléphone: [Guest Phone]
Tel: [Guest Phone]
Phone: [Guest Phone]
Prix: [Numeric Price]
Adultes: [Number]
Enfants: [Number]
```

**Example:**
```
Reservation confirmee!
Voyageur: Jean Dupont
Email: jean@example.com
Téléphone: +33612345678
Prix: 500
Adultes: 2
Enfants: 1
```

---

## ✨ Summary

After the fixes:
- ✅ iCal SUMMARY → unit.name (not property.name)
- ✅ iCal LOCATION → property.address (with extracted property.name)
- ✅ Property and Unit have distinct, meaningful names
- ✅ Multiple units per property work correctly
- ✅ Guest info from DESCRIPTION is properly parsed
- ✅ Deduplication via UID works reliably

---

## 📂 Related Files

- **Integration Logic:** `/home/user/odoo/addons/onedesk_core/models/onedesk_integration.py`
- **Property Model:** `/home/user/odoo/addons/onedesk_core/models/onedesk_property.py`
- **Unit Model:** `/home/user/odoo/addons/onedesk_core/models/onedesk_unit.py`
- **Test iCal:** `/home/user/odoo/addons/onedesk_core/fichier_test/test_ical.ics`
