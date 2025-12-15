#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour résoudre le problème d'accès website Premium Manager

À exécuter avec: ./odoo-bin shell -d base1 -c debian/odoo.conf < fix_premium_website_access.py
"""

print("=" * 80)
print("🔧 RÉSOLUTION PROBLÈME ACCÈS WEBSITE PREMIUM MANAGER")
print("=" * 80)

# Trouver l'utilisateur "Personne test"
user = env['res.users'].sudo().search([('id', '=', 14)], limit=1)

if not user:
    print("❌ Utilisateur ID=14 non trouvé!")
    exit(1)

print(f"\n👤 Utilisateur: {user.name} (Company: {user.company_id.name})")

# 1. Vérifier si l'utilisateur a déjà un website
user_website = env['website'].sudo().search([
    ('company_id', '=', user.company_id.id)
], limit=1)

if user_website:
    print(f"✅ Website existant trouvé: {user_website.name} (ID: {user_website.id})")
else:
    print(f"❌ Aucun website pour la company {user.company_id.name}")
    print(f"🔧 Création d'un website...")

    # Créer un website pour cette company
    unique_domain = f'company-{user.company_id.id}.local'
    user_website = env['website'].sudo().create({
        'name': f'Site {user.company_id.name}',
        'company_id': user.company_id.id,
        'domain': unique_domain,
    })
    print(f"✅ Website créé: {user_website.name} (ID: {user_website.id})")

# 2. Vérifier l'accès de l'utilisateur au website
print(f"\n🔍 Test d'accès au website...")
try:
    # Tester l'accès avec le contexte de l'utilisateur
    user_env = env(user=user.id)
    test_website = user_env['website'].browse(user_website.id)
    test_name = test_website.name  # Cela va déclencher une vérification d'accès
    print(f"✅ L'utilisateur PEUT accéder au website {test_website.name}")
except Exception as e:
    print(f"❌ L'utilisateur NE PEUT PAS accéder au website: {e}")
    print(f"\n🔧 Vérification des règles de sécurité...")

    # Vérifier les règles
    rules = env['ir.rule'].sudo().search([
        ('model_id.model', '=', 'website'),
    ])
    print(f"   {len(rules)} règles de sécurité pour le modèle 'website'")

    for rule in rules:
        print(f"   - {rule.name} (Global: {rule.global})")
        print(f"     Domain: {rule.domain_force}")

# 3. S'assurer que company_ids contient UNIQUEMENT la company de l'utilisateur
print(f"\n🔧 Vérification company_ids...")
if set(user.company_ids.ids) != {user.company_id.id}:
    print(f"   ⚠️ L'utilisateur a accès à plusieurs companies: {user.company_ids.mapped('name')}")
    print(f"   🔧 Restriction à UNIQUEMENT {user.company_id.name}...")

    user.write({
        'company_ids': [(6, 0, [user.company_id.id])]
    })
    print(f"   ✅ Utilisateur restreint à sa company uniquement")
else:
    print(f"   ✅ L'utilisateur n'a accès qu'à sa company")

# 4. Vérifier que l'action du menu pointe vers le bon website
print(f"\n🔍 Vérification de l'action 'Mon Site Web'...")
try:
    action = env.ref('onedesk_core.action_open_user_website')
    print(f"   ✅ Action trouvée: {action.name}")
    print(f"   Type: {action.state}")

    if action.state == 'code':
        print(f"   ℹ️ L'action utilise du code Python pour détecter le website automatiquement")
        print(f"   ℹ️ Le code devrait créer un website si nécessaire")
except Exception as e:
    print(f"   ❌ Action non trouvée: {e}")

# 5. Commit les changements
print(f"\n💾 Enregistrement des modifications...")
env.cr.commit()
print(f"✅ Modifications enregistrées")

print("\n" + "=" * 80)
print("✅ RÉSOLUTION TERMINÉE")
print("=" * 80)
print(f"\n📋 Résumé:")
print(f"   - Utilisateur: {user.name}")
print(f"   - Company: {user.company_id.name} (ID: {user.company_id.id})")
print(f"   - Website: {user_website.name} (ID: {user_website.id})")
print(f"   - Domain: {user_website.domain}")
print(f"\n💡 L'utilisateur devrait maintenant pouvoir accéder au menu 'Site Web'")
print()
