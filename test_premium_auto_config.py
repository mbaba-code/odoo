#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test simple de l'auto-configuration Premium Manager
"""

import odoo
from odoo import api, SUPERUSER_ID

print("=" * 80)
print("TEST AUTO-CONFIGURATION PREMIUM MANAGER")
print("=" * 80)

# Connexion à la DB
db_name = 'base1'
with odoo.registry(db_name).cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})

    print("\n1️⃣ RECHERCHE DU GROUPE PREMIUM MANAGER...")
    try:
        premium_group = env.ref('onedesk_core.group_onedesk_premium_manager')
        print(f"   ✅ Groupe trouvé: {premium_group.name} (ID: {premium_group.id})")
    except Exception as e:
        print(f"   ❌ Groupe introuvable: {e}")
        exit(1)

    print("\n2️⃣ RECHERCHE DES UTILISATEURS PREMIUM MANAGERS...")
    premium_users = env['res.users'].sudo().search([
        ('groups_id', 'in', [premium_group.id])
    ])
    print(f"   Trouvé {len(premium_users)} utilisateur(s):")
    for user in premium_users:
        print(f"   - {user.name} (ID: {user.id}, Company: {user.company_id.name if user.company_id else 'AUCUNE'})")

    if not premium_users:
        print("\n   ⚠️ Aucun utilisateur Premium Manager trouvé!")
        print("   Création d'un utilisateur de test...")

        # Créer une company de test
        test_company = env['res.company'].sudo().search([('name', '=', 'Test Premium Company')], limit=1)
        if not test_company:
            test_company = env['res.company'].sudo().create({
                'name': 'Test Premium Company',
            })
            print(f"   ✅ Company créée: {test_company.name} (ID: {test_company.id})")

        # Créer un utilisateur de test
        test_user = env['res.users'].sudo().create({
            'name': 'Test Premium Auto',
            'login': 'test.premium.auto@example.com',
            'company_id': test_company.id,
            'company_ids': [(6, 0, [test_company.id])],
        })
        print(f"   ✅ Utilisateur créé: {test_user.name} (ID: {test_user.id})")

        # Assigner le groupe Premium Manager
        print(f"\n   📝 Attribution du groupe Premium Manager...")
        test_user.sudo().write({
            'groups_id': [(4, premium_group.id)]
        })

        cr.commit()

        # Recharger l'utilisateur
        test_user = env['res.users'].sudo().browse(test_user.id)
        premium_users = [test_user]

    print("\n3️⃣ VÉRIFICATION DE LA CONFIGURATION...")
    for user in premium_users:
        print(f"\n   👤 {user.name} (ID: {user.id})")
        print(f"   Company: {user.company_id.name if user.company_id else 'AUCUNE'}")
        print(f"   Company IDs: {[c.name for c in user.company_ids]}")

        # Vérifier les groupes requis
        required_groups = {
            'Settings': 'base.group_erp_manager',
            'CRM': 'sales_team.group_sale_manager',
            'Website': 'website.group_website_designer',
            'Accounting': 'account.group_account_manager',
            'Contacts': 'base.group_partner_manager',
        }

        print(f"\n   Groupes:")
        for name, xml_id in required_groups.items():
            try:
                group = env.ref(xml_id)
                has_group = group in user.groups_id
                status = "✅" if has_group else "❌"
                print(f"   {status} {name}")
            except:
                print(f"   ⚠️ {name} (groupe introuvable)")

        # Vérifier le website
        if user.company_id:
            websites = env['website'].sudo().search([
                ('company_id', '=', user.company_id.id)
            ])
            print(f"\n   Websites pour {user.company_id.name}:")
            if websites:
                for site in websites:
                    print(f"   ✅ {site.name} (ID: {site.id}, Domain: {site.domain})")
            else:
                print(f"   ❌ Aucun website trouvé!")

print("\n" + "=" * 80)
print("TEST TERMINÉ")
print("=" * 80)
