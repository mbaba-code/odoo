# Test simple auto-configuration Premium Manager

print("=" * 80)
print("TEST AUTO-CONFIGURATION PREMIUM MANAGER")
print("=" * 80)

# Trouver le groupe Premium Manager
try:
    premium_group = env.ref('onedesk_core.group_onedesk_premium_manager')
    print(f"\n✅ Groupe trouvé: {premium_group.name} (ID: {premium_group.id})")
except Exception as e:
    print(f"\n❌ Groupe introuvable: {e}")
    exit()

# Chercher les utilisateurs Premium Managers
premium_users = env['res.users'].sudo().search([
    ('groups_id', 'in', [premium_group.id])
])

print(f"\n📋 {len(premium_users)} utilisateur(s) Premium Manager trouvé(s):")
for user in premium_users:
    print(f"\n{'=' * 60}")
    print(f"👤 {user.name} (ID: {user.id})")
    print(f"   Company: {user.company_id.name if user.company_id else 'AUCUNE'}")
    print(f"   Company IDs: {[c.name for c in user.company_ids]}")

    # Groupes requis
    required_groups = {
        'Settings': 'base.group_erp_manager',
        'CRM': 'sales_team.group_sale_manager',
        'Website': 'website.group_website_designer',
        'Accounting': 'account.group_account_manager',
        'Contacts': 'base.group_partner_manager',
    }

    print(f"\n   Groupes:")
    missing = []
    for name, xml_id in required_groups.items():
        try:
            group = env.ref(xml_id)
            has_group = group in user.groups_id
            status = "✅" if has_group else "❌"
            print(f"      {status} {name}")
            if not has_group:
                missing.append(xml_id)
        except:
            print(f"      ⚠️ {name} (groupe introuvable)")

    # Website
    if user.company_id:
        websites = env['website'].sudo().search([
            ('company_id', '=', user.company_id.id)
        ])
        print(f"\n   Websites:")
        if websites:
            for site in websites:
                print(f"      ✅ {site.name} (ID: {site.id}, Domain: {site.domain})")
        else:
            print(f"      ❌ Aucun website")

    # Si des groupes manquent, les ajouter maintenant
    if missing:
        print(f"\n   🔧 Ajout de {len(missing)} groupe(s) manquant(s)...")
        for xml_id in missing:
            try:
                group = env.ref(xml_id)
                user.sudo().write({'groups_id': [(4, group.id)]})
                print(f"      ✅ Ajouté: {group.name}")
            except Exception as e:
                print(f"      ❌ Erreur: {e}")

        # Créer website si besoin
        if user.company_id:
            websites = env['website'].sudo().search([
                ('company_id', '=', user.company_id.id)
            ])
            if not websites:
                print(f"\n   🌐 Création du website...")
                try:
                    unique_domain = f'company-{user.company_id.id}.local'
                    new_site = env['website'].sudo().create({
                        'name': f'Site {user.company_id.name}',
                        'company_id': user.company_id.id,
                        'domain': unique_domain,
                    })
                    print(f"      ✅ Website créé: {new_site.name} (ID: {new_site.id})")
                except Exception as e:
                    print(f"      ❌ Erreur: {e}")

print("\n" + "=" * 80)
print("✅ TEST TERMINÉ")
print("=" * 80)
