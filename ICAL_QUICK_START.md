# OneDesk iCal Integration - Quick Start Guide

## ⚡ 5-Minute Overview

After fixing the 3 bugs, here's what happens when you import an iCal event:

### Input iCal Event
```ical
BEGIN:VEVENT
UID:RES-20251120-001@onedesk.com
SUMMARY:Appartement Paris Centre - Marais
LOCATION:42 Rue des Francs-Bourgeois, 75004 Paris, France
DTSTART;VALUE=DATE:20251120
DTEND;VALUE=DATE:20251125
DESCRIPTION:Reservation confirmee
  Voyageur: Jean Dupont
  Email: jean@example.com
  Prix: 500
  Adultes: 2
END:VEVENT
```

### What OneDesk Creates

#### Property (Auto-created if not exists)
```
Name:    Paris
Address: 42 Rue des Francs-Bourgeois, 75004 Paris, France
Type:    apartment
```

#### Unit (Auto-created if not exists)
```
Name:        Appartement Paris Centre - Marais
Property:    Paris
Capacity:    2
Bedrooms:    1
Bathrooms:   1
Price/Night: 500€
```

#### Reservation
```
Name:     Appartement Paris Centre - Marais
Unit:     Appartement Paris Centre - Marais
Guest:    Jean Dupont (jean@example.com)
Start:    2025-11-20
End:      2025-11-25
Price:    500€
Adults:   2
Children: 0
```

---

## 🔧 The 3 Fixes Explained

### Fix #1: SUMMARY → unit_name
**Before:** SUMMARY only used for reservation name
**After:** SUMMARY also mapped to unit_name

### Fix #2: Intelligent Property Name Extraction
**Before:** Full address used as property name
```
name = "42 Rue des Francs-Bourgeois, 75004 Paris, France"  ❌
```
**After:** Extract city from address
```
name = "Paris"  ✅
```

### Fix #3: Using Extracted unit_name
**Before:** Auto-generated unit name from property address
```
name = "42 Rue... - Unité 1"  ❌
```
**After:** Uses SUMMARY from iCal
```
name = "Appartement Paris Centre - Marais"  ✅
```

---

## 📋 iCal Field Reference

| Field | Purpose | Example |
|-------|---------|---------|
| **UID** | Unique ID for deduplication | `RES-20251120-001@onedesk.com` |
| **SUMMARY** | Unit/property identifier | `Appartement Paris Centre - Marais` |
| **LOCATION** | Full address | `42 Rue des Francs-Bourgeois, 75004 Paris, France` |
| **DTSTART** | Check-in date | `20251120` |
| **DTEND** | Check-out date | `20251125` |
| **DESCRIPTION** | Guest info & notes | `Voyageur: Jean...\nEmail: ...\nPrix: 500` |

---

## 🚀 Integration Setup

1. **Create a OneDesk Integration:**
   - Go to: OneDesk → Settings → Integration Management
   - Provider: iCal (select if available)
   - iCal URL: `https://your-url.com/calendar.ics`
   - Enable Auto-create: ✓

2. **Prepare Your iCal File:**
   - Each VEVENT = One reservation
   - SUMMARY = Unit name
   - LOCATION = Property address
   - DESCRIPTION = Optional guest details

3. **Run Import:**
   - Sync button will fetch and import from the URL
   - Watch logs for success/errors
   - Check OneDesk → Reservations for new bookings

---

## ✅ Validation Checklist

After import, verify in OneDesk:

- [ ] Properties created with city names (not full addresses)
- [ ] Units named from iCal SUMMARY field
- [ ] Each unit linked to correct property
- [ ] Reservations show correct dates and pricing
- [ ] Guest information captured from DESCRIPTION
- [ ] No duplicate entries (UID deduplication works)

---

## 🐛 Troubleshooting

**Issue:** Properties and units have similar names
**Solution:** Ensure SUMMARY and LOCATION are distinct in iCal

**Issue:** Address appears in property name
**Solution:** Location parsing needs postal code format: "12345 CityName"

**Issue:** Guest info not imported
**Solution:** Check DESCRIPTION format matches parser (Voyageur:, Email:, Prix:, etc.)

**Issue:** Duplicates created
**Solution:** Ensure UID is unique for each event

---

## 📁 Files Modified

1. **onedesk_integration.py**
   - Added: `_extract_property_name_from_location()` method
   - Fixed: `_sync_ical()` line 407 (added unit_name mapping)
   - Fixed: `_find_or_create_property()` to use smart extraction
   - Fixed: `_find_or_create_unit()` to use extracted names

---

## 📚 Full Documentation

See: `ICAL_STRUCTURE_CORRECT.md` for complete technical details
