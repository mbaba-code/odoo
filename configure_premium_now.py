# Configuration manuelle Premium Manager
print("=" * 80)
print("CONFIGURATION PREMIUM MANAGER")
print("=" * 80)

# Chercher l'utilisateur "Jeo booby" (ID: 5)
user = env['res.users'].sudo().browse(5)

if not user.exists():
    print("❌ Utilisateur ID 5 introuvable")
    exit()

print(f"\n👤 Utilisateur: {user.name} (ID: {user.id})")
print(f"   Login: {user.login}")
print(f"   Company: {user.company_id.name if user.company_id else 'AUCUNE'}")

# Vérifier s'il a le groupe Premium Manager
try:
    premium_group = env.ref('onedesk_core.group_onedesk_premium_manager')
    has_premium = premium_group in user.groups_id
    print(f"   Premium Manager: {'✅ OUI' if has_premium else '❌ NON'}")
except:
    print("   ❌ Groupe Premium Manager introuvable!")
    exit()

if not has_premium:
    print("\n⚠️ L'utilisateur n'a pas le groupe Premium Manager!")
    exit()

# Vérifier les groupes requis
print("\n📋 GROUPES REQUIS:")
required = {
    'Settings': 'base.group_erp_manager',
    'CRM': 'sales_team.group_sale_manager',
    'Website': 'website.group_website_designer',
    'Accounting': 'account.group_account_manager',
    'Contacts': 'base.group_partner_manager',
}

missing = []
for name, xml_id in required.items():
    try:
        group = env.ref(xml_id)
        has = group in user.groups_id
        print(f"   {'✅' if has else '❌'} {name}")
        if not has:
            missing.append((name, group))
    except:
        print(f"   ⚠️ {name} (introuvable)")

# Vérifier le website
print(f"\n🌐 WEBSITE:")
if not user.company_id:
    print("   ❌ Pas de company assignée!")
else:
    websites = env['website'].sudo().search([('company_id', '=', user.company_id.id)])
    if websites:
        for site in websites:
            print(f"   ✅ {site.name} (ID: {site.id}, Domain: {site.domain})")
    else:
        print(f"   ❌ Aucun website pour {user.company_id.name}")

# CONFIGURATION MAINTENANT
if missing or (user.company_id and not websites):
    print("\n" + "=" * 80)
    print("🔧 CONFIGURATION AUTOMATIQUE EN COURS...")
    print("=" * 80)

    # Ajouter les groupes manquants
    if missing:
        print(f"\n➕ Ajout de {len(missing)} groupe(s)...")
        for name, group in missing:
            try:
                user.write({'groups_id': [(4, group.id)]})
                print(f"   ✅ {name}")
            except Exception as e:
                print(f"   ❌ {name}: {e}")

    # Restreindre company_ids
    if user.company_id and set(user.company_ids.ids) != {user.company_id.id}:
        print(f"\n🔒 Restriction à la company {user.company_id.name}...")
        try:
            user.write({'company_ids': [(6, 0, [user.company_id.id])]})
            print(f"   ✅ Fait")
        except Exception as e:
            print(f"   ❌ Erreur: {e}")

    # Créer le website
    if user.company_id:
        websites = env['website'].sudo().search([('company_id', '=', user.company_id.id)])
        if not websites:
            print(f"\n🌐 Création du website pour {user.company_id.name}...")
            try:
                domain = f'company-{user.company_id.id}.local'
                new_site = env['website'].sudo().create({
                    'name': f'Site {user.company_id.name}',
                    'company_id': user.company_id.id,
                    'domain': domain,
                })
                print(f"   ✅ Website créé: {new_site.name} (ID: {new_site.id})")
                print(f"   URL: /website/force/{new_site.id}")
            except Exception as e:
                print(f"   ❌ Erreur: {e}")

    env.cr.commit()
    print("\n✅ CONFIGURATION TERMINÉE ET SAUVEGARDÉE!")
else:
    print("\n✅ TOUT EST DÉJÀ CONFIGURÉ!")

print("\n" + "=" * 80)
