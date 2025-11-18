# Integration Import Issues Analysis

## Executive Summary

Staff users cannot successfully import integrations (iCal/integration files), while Master Admin users can. The root causes are:
1. **Missing res.partner create permissions** for Staff role
2. **Missing write permissions on onedesk.integration** for Staff to trigger sync
3. **Missing create permissions on onedesk.property and onedesk.unit** for auto-creation during import
4. **No sudo() calls in import logic** - all operations run with user's permissions

## Issue 1: Partner/Contact Access - Staff Cannot Create Contacts

### Current State
**File**: `/home/user/odoo/addons/onedesk_core/security/ir.model.access.csv`

There is **NO** access rule for `res.partner` model for the `group_onedesk_staff` group.

### Where Contacts Are Created
**File**: `/home/user/odoo/addons/onedesk_core/models/onedesk_integration.py`

1. **Line 519-522**: Creates generic partner when contact info is missing
```python
partner = self.env['res.partner'].create({
    'name': 'Client externe',
    'comment': f"Réservation importée depuis {self.provider_id.name}",
})
```

2. **Line 692-699**: Creates partner from guest data in `_find_or_create_contact()`
```python
partner = Partner.create({
    'name': contact_name,
    'email': guest_email if guest_email else False,
    'phone': guest_phone if guest_phone else False,
    'comment': f"Importé depuis {self.provider_id.name}",
})
```

Both operations use `self.env['res.partner'].create()` **WITHOUT** `.sudo()`, requiring the user to have create permissions.

### Impact
- Staff cannot create contacts during integration import
- Import fails silently or throws permission error
- Reservations cannot be created without a partner_id

---

## Issue 2: Reservation Import Failure for Staff

### Multiple Root Causes

#### 2.1 Staff Cannot Trigger Integration Sync

**File**: `/home/user/odoo/addons/onedesk_core/security/ir.model.access.csv` (Line 28)
```csv
access_onedesk_integration_staff,access_onedesk_integration_staff,model_onedesk_integration,onedesk_core.group_onedesk_staff,1,0,0,0
```
- Staff has: `read=1, write=0, create=0, unlink=0`
- Staff **CANNOT WRITE** to integration records

**Impact in Code**: `/home/user/odoo/addons/onedesk_core/models/onedesk_integration.py` (Line 318-324)
```python
record.write({
    'last_sync_date': fields.Datetime.now(),
    'last_sync_count': count,
    'total_synced': record.total_synced + count,
    'state': 'connected',
    'error_count': 0,
})
```
The `action_sync_now()` method tries to update the integration record after sync, which **FAILS** for Staff users.

#### 2.2 Staff Cannot Create Properties

**File**: `/home/user/odoo/addons/onedesk_core/security/ir.model.access.csv` (Line 3)
```csv
access_onedesk_property_staff,access_onedesk_property_staff,model_onedesk_property,onedesk_core.group_onedesk_staff,1,0,0,0
```
- Staff has: `read=1, write=0, create=0, unlink=0`
- Staff **CANNOT CREATE** properties

**Impact**: In `_find_or_create_property()` (Line 588-593), when auto_create is enabled:
```python
prop = Property.create({
    'name': property_name,
    'address': data.get('location', ''),
    'property_type': 'apartment',
    'description': f"Propriété importée depuis {self.provider_id.name}",
})
```
This **FAILS** for Staff users without create permission.

#### 2.3 Staff Cannot Create Units

**File**: `/home/user/odoo/addons/onedesk_core/security/ir.model.access.csv` (Line 8)
```csv
access_onedesk_unit_staff,access_onedesk_unit_staff,model_onedesk_unit,onedesk_core.group_onedesk_staff,1,0,0,0
```
- Staff has: `read=1, write=0, create=0, unlink=0`
- Staff **CANNOT CREATE** units

**Impact**: In `_find_or_create_unit()` (Line 648-659), when auto_create_units is enabled:
```python
unit = Unit.create({
    'name': unit_name,
    'property_id': property_id.id,
    'external_listing_id': external_listing_id,
    'integration_id': self.id,
    # ... more fields
})
```
This **FAILS** for Staff users without create permission.

#### 2.4 Record Rules Filter by Company ID

**File**: `/home/user/odoo/addons/onedesk_core/data/onedesk_security.xml` (Line 285-294)
```xml
<record id="rule_staff_reservation" model="ir.rule">
    <field name="name">Staff - Company Reservations</field>
    <field name="model_id" ref="model_onedesk_reservation"/>
    <field name="domain_force">[('unit_id.property_id.company_id', '=', user.company_id.id), ('active', '=', True)]</field>
    <field name="groups" eval="[(4, ref('group_onedesk_staff'))]"/>
    <field name="perm_read">True</field>
    <field name="perm_write">True</field>
    <field name="perm_create">True</field>
</record>
```

**The Filter Chain**:
- Reservations filtered by: `unit_id.property_id.company_id == user.company_id.id`
- This means Staff can only see reservations for units in properties belonging to their company

**Impact**:
- Even if reservations are created, Staff cannot see them unless the entire chain is correct
- If property/unit company_id doesn't match user's company_id, reservations are invisible

#### 2.5 Why Master Admin Works

**Master Admin Access Rules**:
- Integration: `access_onedesk_integration_admin` (Line 30) → `1,1,1,1` (full access)
- Property: `access_onedesk_property_admin` (Line 5) → `1,1,1,1` (full access)
- Unit: `access_onedesk_unit_admin` (Line 10) → `1,1,1,1` (full access)
- Reservation: `access_onedesk_reservation_admin` (Line 20) → `1,1,1,1` (full access)

**Master Admin Record Rules** (all bypass company_id filtering):
```xml
<field name="domain_force">[(1, '=', 1)]</field>
```
Master Admin sees **ALL** records across **ALL** companies, no filtering applied.

---

## Detailed Permission Comparison

| Model | Staff Permissions | Master Admin Permissions |
|-------|------------------|-------------------------|
| `onedesk.integration` | Read only (1,0,0,0) | Full access (1,1,1,1) |
| `onedesk.property` | Read only (1,0,0,0) | Full access (1,1,1,1) |
| `onedesk.unit` | Read only (1,0,0,0) | Full access (1,1,1,1) |
| `onedesk.reservation` | Read/Write/Create (1,1,1,0) | Full access (1,1,1,1) |
| `res.partner` | **NO ACCESS RULE** | Inherited from base |

---

## Code Flow Analysis: Import Process

### Current Flow (Staff User)
1. User clicks "Sync Now" on integration → ❌ **FAILS** (no write permission on integration)
2. IF sync could run:
   - Parse iCal/API data
   - Call `_process_reservation(data)` for each reservation
   - Call `_find_or_create_unit(data)` → ❌ **FAILS** (cannot create units)
   - Call `_find_or_create_property(data)` → ❌ **FAILS** (cannot create properties)
   - Call `_find_or_create_contact(data)` → ❌ **FAILS** (cannot create partners)
   - Try to create reservation → ❌ **FAILS** (missing unit_id/partner_id)
3. Try to update integration record → ❌ **FAILS** (no write permission)

**Result**: 0 reservations imported

### Current Flow (Master Admin)
1. User clicks "Sync Now" on integration → ✅ **SUCCESS** (full write permission)
2. Sync runs:
   - Parse iCal/API data
   - Call `_process_reservation(data)` for each reservation
   - Call `_find_or_create_unit(data)` → ✅ **SUCCESS** (can create units)
   - Call `_find_or_create_property(data)` → ✅ **SUCCESS** (can create properties)
   - Call `_find_or_create_contact(data)` → ✅ **SUCCESS** (can create partners)
   - Create reservation → ✅ **SUCCESS** (all dependencies satisfied)
3. Update integration record → ✅ **SUCCESS**

**Result**: All reservations imported successfully

---

## Recommended Fixes

### Fix 1: Add res.partner Access for Staff (REQUIRED)

**File**: `/home/user/odoo/addons/onedesk_core/security/ir.model.access.csv`

Add this line after line 62:
```csv
access_res_partner_staff,res.partner.staff,base.model_res_partner,onedesk_core.group_onedesk_staff,1,1,1,0
```

This gives Staff:
- Read, Write, and Create permissions on contacts
- No Delete permission (unlink=0)

### Fix 2: Grant Staff Write Permission on Integration Records

**Option A: Update access rule** (Line 28)
```csv
access_onedesk_integration_staff,access_onedesk_integration_staff,model_onedesk_integration,onedesk_core.group_onedesk_staff,1,1,0,0
```
Change from `1,0,0,0` to `1,1,0,0` (add write permission)

**Option B: Use sudo() in sync method** (if you want to keep Staff read-only)
In `onedesk_integration.py` line 318, wrap the write in sudo():
```python
record.sudo().write({
    'last_sync_date': fields.Datetime.now(),
    'last_sync_count': count,
    'total_synced': record.total_synced + count,
    'state': 'connected',
    'error_count': 0,
})
```

### Fix 3: Use sudo() for Auto-Creation During Import

**File**: `/home/user/odoo/addons/onedesk_core/models/onedesk_integration.py`

#### 3.1 Property Creation (Line 588)
```python
prop = Property.sudo().create({
    'name': property_name,
    'address': data.get('location', ''),
    'property_type': 'apartment',
    'description': f"Propriété importée depuis {self.provider_id.name}",
})
```

#### 3.2 Unit Creation (Line 648)
```python
unit = Unit.sudo().create({
    'name': unit_name,
    'property_id': property_id.id if property_id else (self.default_property_id.id if self.default_property_id else False),
    'external_listing_id': external_listing_id,
    'integration_id': self.id,
    'available': True,
    'capacity': capacity,
    'bedrooms': bedrooms,
    'bathrooms': bathrooms,
    'price_per_night': price,
})
```

#### 3.3 Contact Creation (Line 519 and 692)
```python
# Line 519
partner = self.env['res.partner'].sudo().create({
    'name': 'Client externe',
    'comment': f"Réservation importée depuis {self.provider_id.name}",
})

# Line 692
partner = Partner.sudo().create({
    'name': contact_name,
    'email': guest_email if guest_email else False,
    'phone': guest_phone if guest_phone else False,
    'comment': f"Importé depuis {self.provider_id.name}",
})
```

#### 3.4 Ensure company_id is Set (Line 650)
Add explicit company_id when creating units:
```python
unit = Unit.sudo().create({
    'name': unit_name,
    'property_id': property_id.id if property_id else False,
    'company_id': self.company_id.id,  # ← ADD THIS
    'external_listing_id': external_listing_id,
    # ... rest of fields
})
```

---

## Implementation Priority

### Critical (Must Fix)
1. ✅ **Add res.partner access for Staff** - Without this, contacts cannot be created
2. ✅ **Add write permission on integrations for Staff OR use sudo()** - Without this, sync cannot run
3. ✅ **Use sudo() for property/unit/contact creation** - Without this, auto-creation fails

### Important (Should Fix)
4. ✅ **Ensure company_id is properly set** - Prevents record rule filtering issues
5. ✅ **Add error logging** - Currently errors are silently caught

### Recommended Approach

**Best Solution**: Combination approach
1. Add res.partner access rule for Staff (Fix 1)
2. Keep integration read-only for Staff BUT use sudo() for write operations during sync (Fix 2, Option B)
3. Use sudo() for all auto-creation operations during import (Fix 3)
4. Add explicit company_id assignment when creating units/properties

This maintains security (Staff cannot manually edit integrations) while allowing automated sync to work.

---

## Error Handling Issues

### Current Problem
**File**: `/home/user/odoo/addons/onedesk_core/models/onedesk_integration.py` (Line 328-337)

```python
except Exception as e:
    error_msg = f"Erreur synchronisation: {str(e)}"
    _logger.error(error_msg, exc_info=True)
    record.write({  # ← This also fails for Staff!
        'state': 'error',
        'last_error': error_msg,
        'last_error_date': fields.Datetime.now(),
        'error_count': record.error_count + 1,
    })
    record._log('error', error_msg)
```

The error handler also tries to write to the integration record, which fails for Staff users, hiding the actual error.

### Recommended Fix
```python
except Exception as e:
    error_msg = f"Erreur synchronisation: {str(e)}"
    _logger.error(error_msg, exc_info=True)
    record.sudo().write({  # ← Add sudo() here
        'state': 'error',
        'last_error': error_msg,
        'last_error_date': fields.Datetime.now(),
        'error_count': record.error_count + 1,
    })
    record._log('error', error_msg)
```

---

## Testing Checklist

After implementing fixes, test with Staff user:
- [ ] Can view integration records
- [ ] Can click "Sync Now" button
- [ ] Sync creates properties if they don't exist
- [ ] Sync creates units if they don't exist
- [ ] Sync creates contacts from guest data
- [ ] Reservations are created successfully
- [ ] Reservations are visible in list view
- [ ] Integration record shows updated sync stats
- [ ] Error messages are visible if something fails

---

## Files Requiring Changes

1. `/home/user/odoo/addons/onedesk_core/security/ir.model.access.csv`
   - Add res.partner access rule for Staff

2. `/home/user/odoo/addons/onedesk_core/models/onedesk_integration.py`
   - Add sudo() to integration write operations (lines 318, 331)
   - Add sudo() to property creation (line 588)
   - Add sudo() to unit creation (line 648)
   - Add sudo() to partner creation (lines 519, 692)
   - Add explicit company_id when creating units (line 650)

---

## Summary

**Why it works for Master Admin but not Staff:**
- Master Admin has unrestricted access (1,1,1,1 permissions everywhere)
- Master Admin bypasses all company_id filtering with domain_force=[(1, '=', 1)]
- Staff has read-only access to integrations, properties, and units
- Staff has NO access rule for res.partner
- Import code lacks sudo() calls, requiring user to have full CRUD permissions

**Minimal Fix Required:**
1. Add res.partner access rule: `1,1,1,0` (read/write/create)
2. Add sudo() to 6 specific create/write operations in onedesk_integration.py

This will allow Staff to successfully import integrations while maintaining security boundaries.
