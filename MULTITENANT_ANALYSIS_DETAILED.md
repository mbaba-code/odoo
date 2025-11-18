# Multi-Tenant Data Filtering Investigation Report

## Summary of Findings

The multi-tenant data filtering is not working correctly due to **multiple critical issues** identified in the OneDesk implementation. Users see all companies' data mixed together because proper filtering mechanisms are missing or misconfigured.

---

## 1. VIEW DOMAINS - CRITICAL ISSUE

### Problem
**NO search views are defined** in the view files. This is a fundamental issue:

- **Property views** (`onedesk_property_views.xml`):
  - List view: No domain filter
  - Form view: No domain filter
  - Kanban view: No domain filter
  - **NO search view defined at all**

- **Unit views** (`onedesk_unit_views.xml`):
  - List view: No domain filter
  - Form view: No domain filter
  - Kanban view: No domain filter
  - **NO search view defined at all**

- **Reservation views** (`onedesk_reservation_views.xml`):
  - List view: No domain filter
  - Form view: No domain filter
  - Kanban view: No domain filter
  - **NO search view defined at all**

### Impact
1. **No default domain filtering at the view level** - The views don't restrict data display
2. **Users cannot manually filter by company** - No search/filter options available
3. **Domain expressions in ir.rules may not apply correctly** - Without search views, the framework might not properly evaluate ir.rule domains

### What Should Be There
Search views with default company_id filtering, like:
```xml
<record id="view_property_search" model="ir.ui.view">
    <field name="name">onedesk.property.search</field>
    <field name="model">onedesk.property</field>
    <field name="arch" type="xml">
        <search string="Search Properties">
            <field name="name" string="Name"/>
            <field name="company_id" string="Company"/>
            <!-- Default domain filtering would go here -->
        </search>
    </field>
</record>
```

---

## 2. IR.RULES CONFIGURATION - MOSTLY CORRECT BUT WITH CONCERNS

### Domain Force Expressions - Syntax Check

**Property Model Rules** (onedesk_security.xml lines 149-182):
```
Property Manager: [('company_id', '=', user.company_id.id)]      ✓ Correct
Staff: [('company_id', '=', user.company_id.id)]                 ✓ Correct
Viewer: [('company_id', '=', user.company_id.id)]                ✓ Correct
```

**Unit Model Rules** (onedesk_security.xml lines 211-244):
```
Property Manager: [('property_id.company_id', '=', user.company_id.id)]    ✓ Correct
Staff: [('property_id.company_id', '=', user.company_id.id)]              ✓ Correct
Viewer: [('property_id.company_id', '=', user.company_id.id)]             ✓ Correct
```

**Reservation Model Rules** (onedesk_security.xml lines 273-306):
```
Property Manager: [('unit_id.property_id.company_id', '=', user.company_id.id)]    ✓ Correct
Staff: [('unit_id.property_id.company_id', '=', user.company_id.id)]              ✓ Correct
Viewer: [('unit_id.property_id.company_id', '=', user.company_id.id)]             ✓ Correct
```

### Domain Syntax Analysis

#### Issue 1: Deeply Nested Domains (Potential Problem)
The reservation rule uses THREE levels of traversal:
- `unit_id.property_id.company_id`

This pattern can cause:
1. **Performance problems** - Requires multiple JOINs in SQL
2. **Evaluation issues** - May not work correctly if intermediate records are not fully loaded
3. **NULL value handling** - If unit_id or property_id is NULL, the entire expression becomes invalid

#### Issue 2: Unit Model company_id is COMPUTED, Not Direct
Looking at `onedesk_unit.py` lines 10-16:
```python
company_id = fields.Many2one(
    'res.company',
    string="Entreprise",
    compute='_compute_company_id',
    store=True,
    help="Entreprise (héritée de la propriété)"
)
```

**Problem**: The company_id is computed from property_id.company_id and stored.
- **When is it computed?** Only when the record is created/written
- **Database state risk**: If property_id changes, computed field might not update immediately
- **Database storage**: Even with store=True, there might be timing issues

#### Issue 3: Reservation Model company_id is COMPUTED, Not Direct
Looking at `onedesk_reservation.py` lines 13-19:
```python
company_id = fields.Many2one(
    'res.company',
    string="Entreprise",
    compute='_compute_company_id',
    store=True,
    help="Entreprise (héritée de l'unité)"
)
```

Same problem as Unit model:
- Computed from unit_id.company_id
- Depends on Unit's computed field (which depends on Property's company_id)
- Creates a cascading dependency

### Analysis of Compute Dependencies

**Property Model** (Direct):
```
Property.company_id → Set directly during creation ✓
```

**Unit Model** (Computed from Property):
```
@api.depends('property_id', 'property_id.company_id')
def _compute_company_id(self):
    record.company_id = record.property_id.company_id
```

**Reservation Model** (Computed from Unit):
```
@api.depends('unit_id', 'unit_id.company_id')
def _compute_company_id(self):
    record.company_id = record.unit_id.company_id
```

**Issue**: Three-level cascading dependency creates fragility.

---

## 3. USER GROUP ASSIGNMENT - CORRECT IMPLEMENTATION

Looking at `onedesk_client.py` lines 221-265:

### Group References
```python
manager_group = self.env.ref('onedesk_core.group_onedesk_property_manager')
staff_group = self.env.ref('onedesk_core.group_onedesk_staff')
viewer_group = self.env.ref('onedesk_core.group_onedesk_viewer')
```

**Status**: ✓ Group references are correct and exist in `onedesk_groups.xml`

### Group Assignment
```python
pm_user.write({'group_ids': [(4, manager_group.id)]})
staff_user.write({'group_ids': [(4, staff_group.id)]})
viewer_user.write({'group_ids': [(4, viewer_group.id)]})
```

**Status**: ✓ Group assignment uses correct syntax (4 = add operation)

### Potential Issue
The groups are only assigned to **default users created during client setup**:
- Property Manager user: `pm_{client_code}@onedesk.local`
- Staff user: `staff_{client_code}@onedesk.local`
- Viewer user: `viewer_{client_code}@onedesk.local`

**Risk**: If users are created or imported through other means, groups might not be assigned.

---

## 4. MODEL ACCESS CONTROL - PROPERLY CONFIGURED

The `ir.model.access.csv` file correctly defines permissions per group:
- Property Manager: Read/Write/Create (no Delete)
- Staff: Read only (no Write/Create/Delete)
- Viewer: Read only (no Write/Create/Delete)
- Master Admin: Full access
- Support: Read/Write access

---

## 5. ROOT CAUSES OF MULTI-TENANT FILTERING FAILURE

### Critical Issues (Must Fix):

1. **Missing Search Views with Default Domains** (CRITICAL)
   - No filtering at the view level
   - No search options for users
   - Domain expressions in ir.rules may not be enforced properly

2. **Computed company_id Fields** (HIGH RISK)
   - Unit and Reservation models inherit company_id through computation
   - Not stored directly in database
   - Cascading dependencies create fragility
   - Database queries might not find NULL values correctly

### Secondary Issues:

3. **Deeply Nested Domain Expressions** (MEDIUM)
   - Reservation rule uses `unit_id.property_id.company_id`
   - Three-level JOINs can cause performance issues
   - May not evaluate correctly in all contexts

4. **No Manual Filtering Capability** (MEDIUM)
   - Users cannot manually filter by company_id
   - No search filters available in the UI

---

## 6. WHY DATA IS MIXED TOGETHER

### The Actual Problem Flow:

1. **User logs in** → IR Rules should apply domain filter
2. **User loads Property list** → No search view, no default domain in list view
3. **IR Rule tries to apply** → Checks user.company_id against property.company_id
4. **Property data is fetched** → Might work IF ir.rules are being enforced by the ORM
5. **BUT Units and Reservations fail** → Their company_id is computed, might not be in database query
6. **User sees all data** → IR rules not properly applied due to missing search views and computed fields

### Example Scenario:

```
User A (Company X) creates Property A
  ↓ Triggers Unit creation with computed company_id
    ↓ Unit.company_id = Property.company_id = Company X ✓
      ↓ Triggers Reservation creation with computed company_id
        ↓ Reservation.company_id computed from Unit.company_id
          ↓ Might be NULL in some database states

When User B (Company Y) loads Reservations:
- IR rule should filter: unit_id.property_id.company_id = Company Y
- But if Reservation.company_id is NULL or not stored, filtering fails
- User B sees User A's reservations!
```

---

## 7. RECOMMENDATIONS

### Immediate Fixes (Priority 1):

1. **Add Search Views with Default Domains**
   - Create search views for Property, Unit, Reservation
   - Include company_id filter fields
   - This enables proper domain evaluation

2. **Change Computed Fields to Direct Fields**
   - Unit.company_id: Add `onchange` trigger to update when property_id changes
   - Reservation.company_id: Add `onchange` trigger to update when unit_id changes
   - Or use database-level constraints

3. **Verify company_id Default Values**
   - Ensure Unit and Reservation get company_id value on creation
   - Add validation to prevent NULL company_id

### Secondary Fixes (Priority 2):

4. **Simplify Domain Expressions**
   - Consider storing company_id directly on Unit and Reservation
   - Reduces nested domain traversal
   - Improves query performance

5. **Add Explicit Filtering in List Views**
   - Add `<field name="company_id" string="Company"/>` to search views
   - Provides manual filtering capability to users

6. **Test User Group Assignment**
   - Verify all users are in correct groups
   - Check that ir.rules are being applied
   - Debug domain expression evaluation

