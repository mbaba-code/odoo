# OneDesk iCal Integration - Analysis Documentation

This directory contains a comprehensive analysis of the iCal integration issue in the OneDesk codebase.

## Documentation Files

### 1. ICAL_ISSUE_SUMMARY.md (START HERE)
**Best for:** Quick understanding of the problem
- Executive summary of the issue
- The three interconnected bugs
- Quick fix summary
- Model relationship diagram
- Data flow visualization

### 2. ICAL_INTEGRATION_ANALYSIS.md
**Best for:** Detailed technical understanding
- Complete HOW iCal imports are handled
- Property and Unit model structures
- Root cause chain analysis
- Mapping logic issues
- Integration flow documentation
- Code location reference table

### 3. ICAL_CODE_SNIPPETS.md
**Best for:** Implementation and fixing
- Full code snippets with annotations
- Before/after examples
- Problem visualization with code
- What should happen vs what happens
- Complete model definitions
- Configuration options reference

---

## Quick Navigation

### I Need to...

**...understand the problem**
→ Read: ICAL_ISSUE_SUMMARY.md

**...understand how the system works**
→ Read: ICAL_INTEGRATION_ANALYSIS.md (Sections 1-3)

**...find where the bugs are**
→ Read: ICAL_CODE_SNIPPETS.md (Problem 1, 2, 3 sections)

**...understand the models**
→ Read: ICAL_INTEGRATION_ANALYSIS.md (Sections 2-3) + ICAL_CODE_SNIPPETS.md (Models Structure section)

**...fix the issues**
→ Read: ICAL_CODE_SNIPPETS.md (What Should Happen section) + ICAL_ISSUE_SUMMARY.md (Quick Fix Summary)

---

## The Three Bugs at a Glance

1. **SUMMARY Not Mapped** - iCal SUMMARY field extracted but not used as unit_name
2. **LOCATION as Property Name** - Address used as property name instead of meaningful identifier
3. **Auto-Generated Unit Name** - Unit name generated from property name, causing duplication

## Key File Locations

| Purpose | Absolute Path |
|---------|--------------|
| Integration Logic | `/home/user/odoo/addons/onedesk_core/models/onedesk_integration.py` |
| Property Model | `/home/user/odoo/addons/onedesk_core/models/onedesk_property.py` |
| Unit Model | `/home/user/odoo/addons/onedesk_core/models/onedesk_unit.py` |
| Test iCal File | `/home/user/odoo/addons/onedesk_core/fichier_test/test_ical.ics` |
| Integration Tests | `/home/user/odoo/addons/onedesk_core/tests/test_integration.py` |

---

## Method Locations (onedesk_integration.py)

| Method | Lines | Issue |
|--------|-------|-------|
| `_sync_ical()` | 374-421 | Bug #1: SUMMARY not mapped to unit_name |
| `_parse_ical_description()` | 423-466 | - |
| `_process_reservation()` | 481-572 | - |
| `_find_or_create_property()` | 574-601 | Bug #2: LOCATION used as property name |
| `_find_or_create_unit()` | 603-667 | Bug #3: Unit name auto-generated |

---

## Model Relationship

```
OnedeskProperty (1)
    ↓
    has many
    ↓
OnedeskUnit (N)
    ↓
    has many
    ↓
OnedeskReservation (N)
```

---

## iCal Field Mapping (iCal Standard)

| iCal Field | Current Usage | Should Be |
|----------|---------------|-----------|
| SUMMARY | res_data['name'] | unit.name + res_data['unit_name'] |
| LOCATION | res_data['location'] | property.address + property.name |
| UID | external_id | external_id |
| DTSTART | start_date | start_date |
| DTEND | end_date | end_date |
| DESCRIPTION | parsed for details | guest info parsing |

---

## Analysis Completion Date

Created: November 19, 2025

---

## How to Use This Analysis

1. Start with ICAL_ISSUE_SUMMARY.md for overview
2. Refer to ICAL_INTEGRATION_ANALYSIS.md for technical details
3. Use ICAL_CODE_SNIPPETS.md when implementing fixes
4. Cross-reference file locations and line numbers during development

---

## Document Structure

Each document is self-contained but references the others:

**ICAL_ISSUE_SUMMARY.md**
- Structured as: Issue → Root Cause → Bugs → Expected vs Actual → Files → Fixes

**ICAL_INTEGRATION_ANALYSIS.md**
- Structured as: Overview → How it Works → Data Structures → Logic → Test Data → Summary

**ICAL_CODE_SNIPPETS.md**
- Structured as: Quick Reference → Problem Details → Solutions → Model Definitions

---

## Key Takeaways

1. The iCal SUMMARY field contains the unit name but is not being extracted as unit_name
2. The LOCATION field (property address) is being used as the property name instead of just the address
3. When unit_name is empty, a fallback name is auto-generated from property_name, causing both to be similar
4. All three bugs must be fixed together to properly resolve the issue

---

For questions or additional analysis, refer to the detailed documentation files.
