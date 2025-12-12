#!/usr/bin/env python3
"""
Forcer l'ajout des groupes implied_ids manquants pour Premium Manager
À exécuter: ./odoo-bin shell -d VOTRE_BASE < fix_premium_groups.py
"""

print("=" * 80)
print("🔧 FIX: Ajout des groupes manquants pour Premium Manager")
print("=" * 80)

# Trouver l'utilisateur Premium Test
premium_user = env['res.users'].sudo().browse(5)

print(f"\n👤 Utilisateur: {premium_user.name}")
print(f"   Company: {premium_user.company_id.name}")

# Groupes qui DEVRAIENT être présents via implied_ids
required_groups = {
    'Settings / Administration': 'base.group_erp_manager',
    'Sales / Manager': 'sales_team.group_sale_manager',
    'Website / Designer': 'website.group_website_designer',
    'Accounting / Billing': 'account.group_account_manager',
    'Contacts / Partner Manager': 'base.group_partner_manager',
}

print(f"\n🔍 Vérification et ajout des groupes manquants...")
print("-" * 80)

groups_to_add = []

for name, xml_id in required_groups.items():
    try:
        group = env.ref(xml_id)
        has_group = group in premium_user.group_ids
        
        if has_group:
            print(f"✅ {name}: Déjà présent")
        else:
            print(f"❌ {name}: MANQUANT - ajout en cours...")
            groups_to_add.append(group.id)
            
    except Exception as e:
        print(f"⚠️ {name}: Erreur - {e}")

# Ajouter tous les groupes manquants en une seule opération
if groups_to_add:
    print(f"\n⚙️ Ajout de {len(groups_to_add)} groupe(s)...")
    
    # Utiliser write pour ajouter les groupes (Odoo 19: group_ids not groups_id!)
    premium_user.write({
        'group_ids': [(4, gid) for gid in groups_to_add]
    })
    
    env.cr.commit()
    print(f"✅ Groupes ajoutés avec succès!")
else:
    print(f"\n✅ Tous les groupes sont déjà présents!")

# Vérification finale
print(f"\n{'=' * 80}")
print("✅ VÉRIFICATION FINALE")
print(f"{'=' * 80}\n")

premium_user_refreshed = env['res.users'].sudo().browse(5)

for name, xml_id in required_groups.items():
    try:
        group = env.ref(xml_id)
        has_group = group in premium_user_refreshed.group_ids
        status = "✅" if has_group else "❌"
        print(f"{status} {name}")
    except:
        pass

print(f"\n📊 Total de groupes: {len(premium_user_refreshed.group_ids)}")

print(f"\n{'=' * 80}")
print("✅ FIX TERMINÉ!")
print(f"{'=' * 80}")

print("""
🔄 PROCHAINES ÉTAPES:
   1. Vider le cache du navigateur (Ctrl+Shift+R)
   2. Se déconnecter et reconnecter avec Premium Test
   3. Les modules CRM, Accounting, Settings devraient maintenant être visibles!
""")
