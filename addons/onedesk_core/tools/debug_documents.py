#!/usr/bin/env python3
"""
Debug script to verify documents exist in database and are accessible.
Run this from Odoo shell: odoo shell -c /path/to/odoo.conf
Then: exec(open('addons/onedesk_core/tools/debug_documents.py').read())
"""

from odoo import sql_db
import json

# Connect to database
db = sql_db.db_connect()
cursor = db.cursor()

print("=" * 80)
print("ONEDESK DOCUMENT DEBUG REPORT")
print("=" * 80)

# 1. Count total documents
cursor.execute("SELECT COUNT(*) FROM onedesk_document")
total = cursor.fetchone()[0]
print(f"\n📊 Total documents in database: {total}")

if total == 0:
    print("❌ NO DOCUMENTS FOUND! This is the root cause.")
    cursor.close()
    exit(1)

# 2. Documents by status
print("\n📈 Documents by status:")
cursor.execute("""
    SELECT status, COUNT(*) as count FROM onedesk_document
    GROUP BY status ORDER BY count DESC
""")
for status, count in cursor.fetchall():
    print(f"   • {status}: {count}")

# 3. Documents by active status
print("\n⚡ Documents by active status:")
cursor.execute("""
    SELECT active, COUNT(*) as count FROM onedesk_document
    GROUP BY active
""")
for active, count in cursor.fetchall():
    status = "Active ✅" if active else "Inactive ❌"
    print(f"   • {status}: {count}")

# 4. Documents by company
print("\n🏢 Documents by company:")
cursor.execute("""
    SELECT c.name, COUNT(*) as count FROM onedesk_document d
    LEFT JOIN res_company c ON d.company_id = c.id
    GROUP BY d.company_id, c.name
""")
for company, count in cursor.fetchall():
    print(f"   • {company or 'No company'}: {count}")

# 5. Recent documents
print("\n📄 Last 5 created documents:")
cursor.execute("""
    SELECT id, name, status, active, date_created, company_id
    FROM onedesk_document
    ORDER BY date_created DESC
    LIMIT 5
""")
for doc_id, name, status, active, date_created, company_id in cursor.fetchall():
    active_str = "✅" if active else "❌"
    print(f"   • ID {doc_id}: '{name}' | Status: {status} | Active: {active_str} | Created: {date_created} | Company: {company_id}")

# 6. Check if action_document_stock exists
print("\n🔍 Checking Stock action in database:")
cursor.execute("""
    SELECT id, name, res_model, domain FROM ir_actions_act_window
    WHERE name LIKE '%Stock%'
""")
result = cursor.fetchone()
if result:
    action_id, name, model, domain = result
    print(f"   ✅ Found: {name} (ID: {action_id})")
    print(f"   Model: {model}")
    print(f"   Domain: {domain or '(No domain - shows ALL documents)'}")
else:
    print(f"   ❌ Stock action NOT found! The menu might not be linked correctly.")

# 7. Check menu items
print("\n📋 Document menu items:")
cursor.execute("""
    SELECT id, name, action FROM ir_ui_menu
    WHERE name LIKE '%document%' OR name LIKE '%Document%'
    ORDER BY sequence, id
""")
for menu_id, menu_name, action in cursor.fetchall():
    action_str = action or "(No action)"
    print(f"   • {menu_name}: {action_str}")

cursor.close()
print("\n" + "=" * 80)
