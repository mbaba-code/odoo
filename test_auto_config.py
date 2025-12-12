#!/usr/bin/env python3
"""
Test si le code auto-configuration est bien chargé
"""

print("=" * 80)
print("🔍 TEST AUTO-CONFIGURATION PREMIUM MANAGER")
print("=" * 80)

# 1. Vérifier que le override res.users existe
print("\n1️⃣ Vérification du code Python...")

try:
    # Tester si la méthode existe
    user_model = env['res.users']
    has_method = hasattr(user_model, '_auto_configure_premium_manager')
    
    if has_method:
        print("✅ Méthode _auto_configure_premium_manager trouvée !")
    else:
        print("❌ Méthode _auto_configure_premium_manager NON TROUVÉE")
        print("   → Le module n'a pas été mis à jour correctement")
except Exception as e:
    print(f"❌ Erreur: {e}")

# 2. Forcer l'exécution manuelle pour Premium Test
print("\n2️⃣ Exécution MANUELLE de l'auto-configuration...")

premium_user = env['res.users'].sudo().browse(116)
print(f"   Utilisateur: {premium_user.name}")

try:
    # Appeler directement la méthode
    if has_method:
        user_model._auto_configure_premium_manager(premium_user)
        env.cr.commit()
        print("✅ Auto-configuration exécutée manuellement")
    else:
        print("❌ Impossible - méthode manquante")
except Exception as e:
    print(f"❌ Erreur lors de l'exécution: {e}")
    import traceback
    traceback.print_exc()

# 3. Vérifier le résultat
print("\n3️⃣ Vérification du résultat...")

premium_user_check = env['res.users'].sudo().browse(116)

expected_groups = {
    'Settings': 'base.group_erp_manager',
    'Sales Manager': 'sales_team.group_sale_manager',
    'Website Designer': 'website.group_website_designer',
    'Billing': 'account.group_account_manager',
    'Contacts': 'base.group_partner_manager',
}

for name, xml_id in expected_groups.items():
    try:
        group = env.ref(xml_id)
        has_group = group in premium_user_check.group_ids
        status = "✅" if has_group else "❌"
        print(f"{status} {name}")
    except:
        print(f"⚠️ {name}: Groupe non trouvé")

# 4. Vérifier le website
print("\n4️⃣ Vérification du website...")

if premium_user_check.company_id:
    websites = env['website'].sudo().search([
        ('company_id', '=', premium_user_check.company_id.id)
    ])
    
    if websites:
        print(f"✅ Website trouvé: {websites[0].name}")
    else:
        print(f"❌ Aucun website pour {premium_user_check.company_id.name}")
else:
    print("❌ Utilisateur sans company")

print("\n" + "=" * 80)
print("✅ TEST TERMINÉ")
print("=" * 80)
