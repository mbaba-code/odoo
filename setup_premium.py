# -*- coding: utf-8 -*-
"""Configuration MANUELLE unique des Premium Managers - À exécuter UNE FOIS"""

print("\n" + "=" * 80)
print("CONFIGURATION PREMIUM MANAGERS")
print("=" * 80)

# Chercher le groupe Premium Manager
try:
    premium_group = env.ref('onedesk_core.group_onedesk_premium_manager')
    print(f"\n✅ Groupe trouvé: {premium_group.name}")
except:
    print("\n❌ Groupe Premium Manager introuvable!")
    exit()

# Chercher tous les utilisateurs
premium_users = env['res.users'].sudo().search([
    ('group_ids', 'in', [premium_group.id])
])

if not premium_users:
    print("❌ Aucun utilisateur Premium Manager trouvé")
    exit()

print(f"\n📋 {len(premium_users)} utilisateur(s) trouvé(s):")
for u in premium_users:
    print(f"  - {u.name} (ID: {u.id})")

# Groupes requis
required = [
    ('Settings', 'base.group_erp_manager'),
    ('CRM', 'sales_team.group_sale_manager'),
    ('Website', 'website.group_website_designer'),
    ('Accounting', 'account.group_account_manager'),
    ('Contacts', 'base.group_partner_manager'),
]

# Configuration
for user in premium_users:
    print(f"\n{'='*60}")
    print(f"👤 {user.name}")

    # 1. Groupes
    missing = []
    for name, xml_id in required:
        try:
            g = env.ref(xml_id)
            if g not in user.group_ids:
                missing.append((name, g))
        except:
            pass

    if missing:
        print(f"  ➕ Ajout de {len(missing)} groupe(s)...")
        for name, g in missing:
            user.write({'group_ids': [(4, g.id)]})
            print(f"     ✅ {name}")
    else:
        print("  ✅ Tous les groupes présents")

    # 2. Company restriction
    if user.company_id:
        if set(user.company_ids.ids) != {user.company_id.id}:
            user.write({'company_ids': [(6, 0, [user.company_id.id])]})
            print(f"  ✅ Restreint à: {user.company_id.name}")
        else:
            print(f"  ✅ Déjà restreint à: {user.company_id.name}")

    # 3. Website
    if user.company_id:
        sites = env['website'].sudo().search([('company_id', '=', user.company_id.id)])
        if sites:
            print(f"  ✅ Website existe: {sites[0].name}")
        else:
            domain = f'company-{user.company_id.id}.local'
            site = env['website'].sudo().create({
                'name': f'Site {user.company_id.name}',
                'company_id': user.company_id.id,
                'domain': domain,
            })
            print(f"  ✅ Website créé: {site.name} (ID: {site.id})")

env.cr.commit()

print("\n" + "=" * 80)
print("✅ CONFIGURATION TERMINÉE ET SAUVEGARDÉE")
print("=" * 80 + "\n")
