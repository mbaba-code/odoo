#!/bin/bash
# Script pour ajouter les implied_ids au groupe Premium Manager

cd /home/user/odoo

cat <<'PYTHON' | ./odoo-bin shell -d base1 -c debian/odoo_test.conf
print("=" * 80)
print("AJOUT IMPLIED_IDS AU GROUPE PREMIUM MANAGER")
print("=" * 80)

# Trouver le groupe
premium_group = env.ref('onedesk_core.group_onedesk_premium_manager')
print(f"\n✅ Groupe: {premium_group.name} (ID: {premium_group.id})")
print(f"   Implied_ids actuels: {len(premium_group.implied_ids)}")

# Groupes requis
required_groups_refs = [
    'onedesk_core.group_onedesk_property_manager',
    'base.group_erp_manager',
    'sales_team.group_sale_manager',
    'website.group_website_designer',
    'account.group_account_manager',
    'base.group_partner_manager',
]

implied_group_ids = []
print(f"\n📋 Ajout des groupes:")
for ref_id in required_groups_refs:
    try:
        group = env.ref(ref_id)
        implied_group_ids.append(group.id)
        print(f"  ✅ {group.name}")
    except Exception as e:
        print(f"  ❌ {ref_id}: {e}")

# Mettre à jour
if implied_group_ids:
    premium_group.write({
        'implied_ids': [(6, 0, implied_group_ids)]
    })
    env.cr.commit()
    print(f"\n✅ Groupe mis à jour avec {len(implied_group_ids)} implied_ids!")

    # Forcer le rechargement pour voir les changements
    premium_group.invalidate_recordset()
    updated_group = env['res.groups'].browse(premium_group.id)

    print(f"\n📋 Implied_ids après mise à jour ({len(updated_group.implied_ids)}):")
    for implied in updated_group.implied_ids:
        print(f"  - {implied.name}")

print("\n" + "=" * 80)
print("✅ TERMINÉ - Redémarrez Odoo et reconnectez l'utilisateur!")
print("=" * 80)
PYTHON
