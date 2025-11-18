# MULTI-TENANT FILTERING ISSUES - FINDINGS SUMMARY

## KEY FINDINGS AT A GLANCE

### CRITICAL ISSUES FOUND

| Issue | Severity | Impact | Status |
|-------|----------|--------|--------|
| **Missing Search Views** | CRITICAL | No view-level filtering, IR rules may not apply | NOT FOUND |
| **Computed company_id Fields** | HIGH | Multi-level cascading dependencies, data may be NULL | CONFIRMED |
| **No Manual Filter Options** | HIGH | Users cannot filter by company in UI | CONFIRMED |
| **Deeply Nested Domains** | MEDIUM | Performance issues, evaluation problems | CONFIRMED |
| **User Group Assignment** | LOW | Groups assigned correctly but only for default users | OK ✓ |

---

## DETAILED FINDINGS

### 1. VIEW DOMAINS - NO SEARCH VIEWS DEFINED

#### Files Checked:
- ❌ `/home/user/odoo/addons/onedesk_core/views/onedesk_property_views.xml` (215 lines) - NO search view
- ❌ `/home/user/odoo/addons/onedesk_core/views/onedesk_unit_views.xml` (232 lines) - NO search view
- ❌ `/home/user/odoo/addons/onedesk_core/views/onedesk_reservation_views.xml` (302 lines) - NO search view

#### What Exists:
- Property: List view (lines 3-16), Form view (lines 19-122), Kanban view (lines 125-191)
- Unit: List view (lines 2-13), Form view (lines 15-145), Kanban view (lines 148-221)
- Reservation: List view (lines 7-23), Form view (lines 26-185), Kanban view (lines 188-276)

#### What's Missing:
```xml
<!-- MISSING for ALL THREE models: -->
<record id="view_XXXXX_search" model="ir.ui.view">
    <field name="name">onedesk.XXXXX.search</field>
    <field name="model">onedesk.XXXXX</field>
    <field name="arch" type="xml">
        <search string="Search">
            <field name="company_id" string="Company"/>
            <!-- Additional search fields -->
        </search>
    </field>
</record>
```

#### Consequences:
1. Odoo cannot apply domain filtering at view level
2. No filter/search options in the UI for users
3. IR rules may not be properly enforced

---

### 2. COMPUTED COMPANY_ID FIELDS - FRAGILE ARCHITECTURE

#### Unit Model Issue
**File**: `/home/user/odoo/addons/onedesk_core/models/onedesk_unit.py` (lines 10-16)

```python
company_id = fields.Many2one(
    'res.company',
    string="Entreprise",
    compute='_compute_company_id',  # ⚠️ COMPUTED
    store=True,                      # ⚠️ STORED (should be direct)
    help="Entreprise (héritée de la propriété)"
)

@api.depends('property_id', 'property_id.company_id')
def _compute_company_id(self):
    """Hériter company_id de la propriété"""
    for record in self:
        record.company_id = record.property_id.company_id if record.property_id else False
```

**Problem**: 
- Not a direct database column, computed on-the-fly
- Depends on property_id being loaded
- May be NULL if property_id is unset
- Cascading dependency on Property.company_id

#### Reservation Model Issue
**File**: `/home/user/odoo/addons/onedesk_core/models/onedesk_reservation.py` (lines 13-19)

```python
company_id = fields.Many2one(
    'res.company',
    string="Entreprise",
    compute='_compute_company_id',  # ⚠️ COMPUTED
    store=True,                      # ⚠️ STORED (should be direct)
    help="Entreprise (héritée de l'unité)"
)

@api.depends('unit_id', 'unit_id.company_id')
def _compute_company_id(self):
    """Hériter company_id de l'unité"""
    for record in self:
        record.company_id = record.unit_id.company_id if record.unit_id else False
```

**Problem**:
- Not a direct database column
- Depends on unit_id.company_id (which is itself computed!)
- THREE-LEVEL cascading dependency:
  ```
  Reservation.company_id 
    → depends on Unit.company_id 
      → depends on Property.company_id
  ```
- May be NULL in some database states

#### Comparison: Property Model (CORRECT)
**File**: `/home/user/odoo/addons/onedesk_core/models/onedesk_property.py` (lines 9-16)

```python
company_id = fields.Many2one(
    'res.company',
    string="Entreprise",
    required=True,                  # ✓ DIRECT
    default=lambda self: self.env.company,  # ✓ Has default
    ondelete='cascade',
    help="Entreprise propriétaire de cette propriété"
)
```

**Status**: ✓ Correct - Direct field, required, has default value

---

### 3. IR.RULES DOMAIN EXPRESSIONS - CORRECT BUT PROBLEMATIC

#### Property Model Rules
**File**: `/home/user/odoo/addons/onedesk_core/data/onedesk_security.xml` (lines 149-182)

```xml
<record id="rule_property_manager_property" model="ir.rule">
    <field name="domain_force">[('company_id', '=', user.company_id.id)]</field>
    <field name="groups" eval="[(4, ref('group_onedesk_property_manager'))]"/>
    ...
</record>
```
**Status**: ✓ Syntactically correct, direct field reference

#### Unit Model Rules
**File**: `/home/user/odoo/addons/onedesk_core/data/onedesk_security.xml` (lines 211-244)

```xml
<record id="rule_property_manager_unit" model="ir.rule">
    <field name="domain_force">[('property_id.company_id', '=', user.company_id.id)]</field>
    ...
</record>
```
**Status**: ✓ Syntactically correct, but joins through property_id

#### Reservation Model Rules  
**File**: `/home/user/odoo/addons/onedesk_core/data/onedesk_security.xml` (lines 273-306)

```xml
<record id="rule_property_manager_reservation" model="ir.rule">
    <field name="domain_force">[('unit_id.property_id.company_id', '=', user.company_id.id)]</field>
    ...
</record>
```
**Status**: ⚠️ Syntactically correct BUT:
- THREE-level nested domain traversal
- Performance: Requires multiple SQL JOINs
- Reliability: May fail if intermediate record is NULL
- May conflict with computed company_id field

**Why This Is A Problem**:
1. Domain: `unit_id.property_id.company_id` traverses:
   - unit_id (Many2one to Unit)
   - property_id (Many2one to Property)  
   - company_id (Many2one to Company)
2. If any intermediate step fails, entire filter breaks
3. Database queries must load all intermediate records

---

### 4. USER GROUP ASSIGNMENT - CORRECT

#### Implementation
**File**: `/home/user/odoo/addons/onedesk_core/models/onedesk_client.py` (lines 221-265)

```python
def _create_default_users(self, client):
    # Groups exist and are correctly referenced
    manager_group = self.env.ref('onedesk_core.group_onedesk_property_manager')  ✓
    staff_group = self.env.ref('onedesk_core.group_onedesk_staff')                ✓
    viewer_group = self.env.ref('onedesk_core.group_onedesk_viewer')              ✓
    
    # Groups assigned correctly
    pm_user.write({'group_ids': [(4, manager_group.id)]})          ✓
    staff_user.write({'group_ids': [(4, staff_group.id)]})         ✓
    viewer_user.write({'group_ids': [(4, viewer_group.id)]})       ✓
```

#### Verification
- ✓ Group definitions exist in `onedesk_groups.xml`
- ✓ Syntax is correct (4 = add operation)
- ✓ Groups are referenced properly with env.ref()

#### Limitation
Groups are ONLY assigned to default users created during client setup:
- `pm_{client_code}@onedesk.local`
- `staff_{client_code}@onedesk.local`
- `viewer_{client_code}@onedesk.local`

If users are imported/created through other means, groups may not be assigned.

---

## ROOT CAUSE ANALYSIS

### Why Users See All Companies' Data

1. **Property data** (might work due to direct company_id):
   - Has direct company_id field
   - IR rule: `[('company_id', '=', user.company_id.id)]`
   - Should work, BUT no search view to apply it

2. **Unit data** (problematic):
   - Has computed company_id field (depends on Property)
   - IR rule: `[('property_id.company_id', '=', user.company_id.id)]`
   - May work if property_id is properly loaded
   - NO search view

3. **Reservation data** (most problematic):
   - Has computed company_id (depends on Unit's computed company_id!)
   - IR rule: `[('unit_id.property_id.company_id', '=', user.company_id.id)]`
   - THREE-level traversal required
   - Cascading computed field dependency
   - NO search view

4. **Missing Search Views**:
   - Without search views, Odoo's domain filtering system doesn't work properly
   - IR rules may only apply at database level, not UI level
   - Users have no filter/search options

### The Cascade Failure Pattern

```
User logs in with Company X
    ↓
Loads Property list
    → IR rule should filter: company_id = Company X.id
    ↓ (but no search view to enable it)
Sees some Properties from Company X ✓
    ↓
Loads Unit list
    → IR rule should filter: property_id.company_id = Company X.id
    → Problem: Unit.company_id is COMPUTED, not guaranteed in DB
    ↓
Might see Units from OTHER companies ❌
    ↓
Loads Reservation list
    → IR rule should filter: unit_id.property_id.company_id = Company X.id
    → Problem: Reservation.company_id is COMPUTED from Unit.company_id!
    ↓
SEES ALL RESERVATIONS from ALL COMPANIES ❌
```

---

## SUMMARY TABLE

| Component | Status | Issue | Priority |
|-----------|--------|-------|----------|
| View Domains | ❌ MISSING | No search views defined | CRITICAL |
| Property.company_id | ✓ OK | Direct field, required | - |
| Unit.company_id | ⚠️ RISK | Computed field, cascading | HIGH |
| Reservation.company_id | ⚠️ CRITICAL | Computed, 3-level cascade | HIGH |
| IR.Rule Syntax | ✓ OK | Domain expressions correct | - |
| Nested Domains | ⚠️ RISK | 3-level traversal for Reservation | MEDIUM |
| User Groups | ✓ OK | Correctly assigned to defaults | - |
| Manual Filtering | ❌ MISSING | No search/filter options in UI | MEDIUM |

