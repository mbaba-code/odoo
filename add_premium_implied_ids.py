#!/usr/bin/env python3
"""
Script pour ajouter les implied_ids au groupe Premium Manager
Exécute manuellement ce que la migration 19.0.1.0.1 devrait faire
"""

import sys
import os

# Ajouter le chemin Odoo
sys.path.insert(0, '/home/user/odoo')
os.chdir('/home/user/odoo')

import odoo
from odoo import api

# Configuration
config = odoo.tools.config
config['db_name'] = 'base1'
config['db_host'] = 'localhost'
config['db_port'] = 5432
config['addons_path'] = '/home/user/odoo/addons'

# Connexion
odoo.cli.server.report_configuration()
db_name = 'base1'

registry = odoo.registry(db_name)
with registry.cursor() as cr:
    env = api.Environment(cr, odoo.SUPERUSER_ID, {})

    print("=" * 80)
    print("AJOUT IMPLIED_IDS AU GROUPE PREMIUM MANAGER")
    print("=" * 80)

    # Trouver le groupe
    try:
        premium_group = env.ref('onedesk_core.group_onedesk_premium_manager')
        print(f"\n✅ Groupe trouvé: {premium_group.name} (ID: {premium_group.id})")
        print(f"   Implied_ids actuels: {len(premium_group.implied_ids)}")

        # Groupes à ajouter
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
            cr.commit()
            print(f"\n✅ Groupe mis à jour avec {len(implied_group_ids)} implied_ids")

            # Vérifier
            premium_group.invalidate_recordset()
            print(f"   Implied_ids après mise à jour: {len(premium_group.implied_ids)}")
            for implied in premium_group.implied_ids:
                print(f"     - {implied.name}")

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("TERMINÉ")
    print("=" * 80)
