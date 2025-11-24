"""
Post-migration script for onedesk_core module
Cleans up orphaned action references in ir_ui_menu
"""

def migrate(cr, installed_version):
    """
    Remove menu references to deleted/invalid actions
    This prevents 404 errors when accessing menus
    """
    cr.execute("""
        DELETE FROM ir_ui_menu
        WHERE action LIKE 'ir.actions.act_window,%'
        AND action NOT IN (
            SELECT 'ir.actions.act_window,' || id
            FROM ir_actions_act_window
        )
    """)

    print("✅ Cleaned up orphaned menu action references")
