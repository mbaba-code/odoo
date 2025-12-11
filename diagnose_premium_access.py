#!/usr/bin/env python3
"""
Diagnostic complet des accès Premium Manager
À exécuter: ./odoo-bin shell -d VOTRE_BASE < diagnose_premium_access.py
"""

print("=" * 80)
print("🔍 DIAGNOSTIC PREMIUM MANAGER ACCESS")
print("=" * 80)

# Trouver l'utilisateur Premium Test
premium_user = env['res.users'].sudo().browse(116)  # ID du Premium Test

print(f"\n👤 Utilisateur: {premium_user.name} (ID: {premium_user.id})")
print(f"   Login: {premium_user.login}")
print(f"   Company: {premium_user.company_id.name}")

# Lister TOUS les groupes de l'utilisateur
print(f"\n📋 GROUPES ASSIGNÉS ({len(premium_user.group_ids)} au total):")
print("-" * 80)

for group in premium_user.group_ids:
    print(f"   ✅ {group.name} (ID: {group.id})")

# Vérifier les groupes clés attendus
print(f"\n🔑 VÉRIFICATION DES GROUPES CLÉS:")
print("-" * 80)

expected_groups = {
    'OneDesk / Premium Manager': 'onedesk_core.group_onedesk_premium_manager',
    'Settings': 'base.group_erp_manager',
    'Sales Manager': 'sales_team.group_sale_manager',
    'Website Designer': 'website.group_website_designer',
    'Billing Manager': 'account.group_account_manager',
    'Contact Creation': 'base.group_partner_manager',
}

for name, xml_id in expected_groups.items():
    try:
        expected_group = env.ref(xml_id)
        has_group = expected_group in premium_user.group_ids
        status = "✅" if has_group else "❌"
        print(f"{status} {name}: {'OUI' if has_group else 'NON'}")
    except Exception as e:
        print(f"⚠️ {name}: Groupe introuvable ({xml_id})")

# Vérifier les menus accessibles
print(f"\n🗂️ MENUS ACCESSIBLES:")
print("-" * 80)

# Se mettre dans le contexte de l'utilisateur Premium
premium_env = env(user=premium_user.id)

try:
    # Chercher les menus principaux (parent_id = False)
    main_menus = premium_env['ir.ui.menu'].search([
        ('parent_id', '=', False)
    ])
    
    print(f"   Menus principaux accessibles: {len(main_menus)}")
    for menu in main_menus:
        print(f"      • {menu.name}")
        
except Exception as e:
    print(f"   ❌ Erreur lors de la lecture des menus: {e}")

# Vérifier les applications installées
print(f"\n📦 APPLICATIONS INSTALLÉES:")
print("-" * 80)

key_apps = ['crm', 'sale', 'account', 'website', 'contacts']
for app_name in key_apps:
    module = env['ir.module.module'].sudo().search([
        ('name', '=', app_name)
    ], limit=1)
    
    if module:
        status = "✅" if module.state == 'installed' else "❌"
        print(f"{status} {app_name.upper()}: {module.state}")
    else:
        print(f"⚠️ {app_name.upper()}: Module non trouvé")

print("\n" + "=" * 80)
print("✅ DIAGNOSTIC TERMINÉ")
print("=" * 80)

print("""
💡 SI DES GROUPES SONT MANQUANTS:
   1. Mettre à jour onedesk_core: Apps → OneDesk Core → Update
   2. Redémarrer Odoo
   3. Vider le cache navigateur (Ctrl+Shift+R)
   
💡 SI LES MENUS NE S'AFFICHENT PAS:
   - Vérifier que les groupes implied_ids sont bien chargés
   - Les menus dépendent des groupes hérités
""")
