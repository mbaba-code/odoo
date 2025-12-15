# Stock de Documents - Troubleshooting Guide

## Problem
The "📦 Stock de documents" menu shows an empty list, even though documents ARE visible in the "✍️ Envoyer pour signature" menu.

## Quick Fixes (Try These First)

### 1. **Update the Module (MOST IMPORTANT)**
```
1. Go to: Apps → Search for "onedesk_core"
2. Click on "onedesk_core"
3. Click the "Update" button
4. Wait for it to complete (may take 30-60 seconds)
5. Try the Stock menu again
```

### 2. **Refresh Your Browser**
```
Ctrl+F5 (Windows/Linux) or Cmd+Shift+R (Mac)
```

### 3. **Restart Odoo Server**
If the module update still doesn't work:
```
1. Stop the Odoo server
2. Clear the cache: rm -rf /tmp/odoo_cache_* 2>/dev/null
3. Restart Odoo: odoo -c /path/to/odoo.conf
```

---

## Detailed Debugging

### Step 1: Verify Documents Actually Exist
1. Go to **"✍️ Envoyer pour signature"** menu
2. Check that documents are there (you mentioned they are ✅)
3. If documents appear here but not in Stock menu, continue to Step 2

### Step 2: Check Database Directly
Open Odoo shell and run the diagnostic script:
```bash
cd /home/user/odoo
odoo shell -c /home/user/odoo.conf
```

Then in the Python shell:
```python
from odoo import sql_db
db = sql_db.db_connect()
cursor = db.cursor()

# Check total document count
cursor.execute("SELECT COUNT(*) FROM onedesk_document")
total = cursor.fetchone()[0]
print(f"Total documents: {total}")

# Check documents by status
cursor.execute("""
    SELECT status, COUNT(*) FROM onedesk_document
    GROUP BY status
""")
for status, count in cursor.fetchall():
    print(f"  Status '{status}': {count} documents")

# Check active/inactive
cursor.execute("""
    SELECT active, COUNT(*) FROM onedesk_document
    GROUP BY active
""")
for active, count in cursor.fetchall():
    print(f"  Active={active}: {count} documents")

cursor.close()
```

**If `total = 0`**: No documents are being saved. This is a model issue.
**If `total > 0`**: Documents exist. Continue to Step 3.

### Step 3: Verify Stock Action Configuration
In Odoo shell:
```python
env = odoo.api.Environment(cr, 1, {})
stock_action = env.ref('onedesk_core.action_document_stock')
print(f"Stock action name: {stock_action.name}")
print(f"Stock action model: {stock_action.res_model}")
print(f"Stock action domain: {stock_action.domain}")
print(f"Stock action view_ids: {[(v.id, v.view_mode) for v in stock_action.view_ids]}")
```

Expected result:
- ✅ Domain should be empty or `False` (no filtering)
- ✅ Should have list, kanban, and form views

### Step 4: Verify Menu Items
In Odoo shell:
```python
menu_stock = env.ref('onedesk_core.menu_document_stock')
print(f"Stock menu name: {menu_stock.name}")
print(f"Stock menu action: {menu_stock.action}")
```

### Step 5: Force Update Module XML
If all else fails, reinstall the module:

```bash
# In Odoo shell
env = odoo.api.Environment(cr, uid, {})
module = env['ir.module.module'].search([('name', '=', 'onedesk_core')])
module.button_immediate_uninstall()
module.button_install()
```

Then refresh Odoo page.

---

## Common Issues and Solutions

### Issue: "I don't see the Stock menu at all"
**Solution**: Menu might not be loaded. Update the module.

### Issue: "Stock menu shows empty list"
**Solution**: See main troubleshooting steps above. Likely needs module update.

### Issue: "Documents only show in Send menu, not Stock"
**Solution**: The module hasn't fully reloaded. Try:
1. Update module
2. Log out and log back in
3. Restart Odoo server

### Issue: "Documents have status 'draft' but don't appear in list"
**Solution**: Check if they're marked as `active=False`:
```python
cursor.execute("""
    SELECT id, name, active FROM onedesk_document
    WHERE status='draft' LIMIT 5
""")
```
If `active=False`, that's the issue. Documents need `active=True` to be visible.

---

## What Each View Should Show

### ✍️ Envoyer pour signature (Send)
- **Domain Filter**: `[('status', 'in', ['draft', 'pending_signature', 'signed'])]`
- **List Columns**: Name, Type, Status, Created By, Date Created
- **Purpose**: Send documents for signature

### 📦 Stock de documents (Storage)
- **Domain Filter**: None (shows ALL documents regardless of status)
- **List Columns**: Name, Type, Category, Status, Location, Created By, Date Created
- **Purpose**: Store, organize, and classify documents
- **Kanban Grouping**: By document_category (not status)

---

## If Nothing Works

Contact support with these details:
1. Output of Step 2 (document count)
2. Output of Step 3 (stock action config)
3. Odoo logs from `/tmp/odoo.log`
