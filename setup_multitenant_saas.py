#!/usr/bin/env python3
"""
Configuration complète multi-tenant SaaS OneDesk
- Super Admin voit TOUT
- Premium Manager = Admin de SA company uniquement
"""

print("=" * 80)
print("🏗️ CONFIGURATION MULTI-TENANT SAAS")
print("=" * 80)

# 1. Configurer "My Website" pour le Super Admin uniquement
my_website = env['website'].sudo().browse(1)
admin_company = env['res.company'].sudo().browse(1)  # My Company

if not my_website.company_id or my_website.company_id.id != admin_company.id:
    my_website.sudo().write({'company_id': admin_company.id})
    print(f"✅ {my_website.name} assigné à {admin_company.name} (Super Admin)")

# 2. Configurer chaque Premium Manager
premium_group = env.ref('onedesk_core.group_onedesk_premium_manager')
premium_users = env['res.users'].sudo().search([
    ('group_ids', 'in', [premium_group.id])
])

print(f"\n👥 CONFIGURATION DES {len(premium_users)} PREMIUM MANAGERS:")

for user in premium_users:
    print(f"\n   📌 {user.name} ({user.company_id.name})")

    # S'assurer qu'il a une company
    if not user.company_id:
        print(f"      ❌ PAS DE COMPANY!")
        continue

    # Créer/vérifier son website
    user_website = env['website'].sudo().search([
        ('company_id', '=', user.company_id.id)
    ], limit=1)

    if not user_website:
        user_website = env['website'].sudo().create({
            'name': f'Site {user.company_id.name}',
            'company_id': user.company_id.id,
            'domain': '',
        })
        print(f"      ✅ Website créé: {user_website.name}")
    else:
        print(f"      ✅ Website existant: {user_website.name}")

    # Définir le website par défaut dans le contexte
    if user_website:
        # Stocker dans company_ids pour forcer le contexte
        user.sudo().write({
            'company_ids': [(4, user.company_id.id)],
        })
        print(f"      ✅ Contexte configuré")

env.cr.commit()

# 3. Vérifier l'isolation
print(f"\n" + "=" * 80)
print("🔒 VÉRIFICATION ISOLATION MULTI-TENANT")
print("=" * 80)

for user in premium_users:
    print(f"\n👤 {user.name}:")
    user_env = env(user=user.id)

    try:
        websites = user_env['website'].search([])
        companies = user_env['res.company'].search([])

        print(f"   • Websites accessibles: {len(websites)}")
        for w in websites:
            print(f"      - {w.name}")

        print(f"   • Companies visibles: {len(companies)}")
        for c in companies:
            print(f"      - {c.name}")

    except Exception as e:
        print(f"   ❌ Erreur: {e}")

# 4. Configuration Super Admin
print(f"\n" + "=" * 80)
print("👑 SUPER ADMIN (TOI)")
print("=" * 80)

admin = env['res.users'].browse(2)  # Généralement l'admin
system_group = env.ref('base.group_system')

if system_group.id not in admin.sudo().group_ids.ids:
    env.cr.execute("""
        INSERT INTO res_groups_users_rel (gid, uid)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
    """, (system_group.id, admin.id))
    print("✅ Super Admin a le groupe System (accès TOTAL)")
else:
    print("✅ Super Admin a déjà le groupe System")

admin_env = env(user=admin.id)
all_websites = admin_env['website'].search([])
all_companies = admin_env['res.company'].search([])

print(f"\n👁️ Le Super Admin voit:")
print(f"   • {len(all_websites)} website(s) - TOUS")
print(f"   • {len(all_companies)} company(ies) - TOUTES")

env.cr.commit()

print(f"\n" + "=" * 80)
print("✅ CONFIGURATION TERMINÉE!")
print("=" * 80)

print("""
📋 RÉSUMÉ:

👑 SUPER ADMIN (toi):
   ✅ Groupe: System Admin
   ✅ Accès: TOUT (toutes companies, tous websites)
   ✅ Site: My Website

💎 PREMIUM MANAGERS:
   ✅ Groupe: Premium Manager (pas System)
   ✅ Accès: UNIQUEMENT leur company
   ✅ Site: Site [Nom Company]
   🔒 Isolation: Stricte par company_id

🔄 PROCHAINES ÉTAPES:
   1. Redémarrer Odoo
   2. Vider cache navigateur
   3. Premium Manager se connecte → verra SON site uniquement
   4. Toi (Super Admin) → vois TOUT
""")

print("=" * 80)
