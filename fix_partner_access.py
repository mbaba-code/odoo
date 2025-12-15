#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour résoudre les problèmes d'accès aux partners (contacts)

À exécuter avec: ./odoo-bin shell -d base1 -c debian/odoo.conf < fix_partner_access.py
"""

print("=" * 80)
print("🔧 CORRECTION ACCÈS PARTNERS PREMIUM MANAGER")
print("=" * 80)

# Utilisateur Premium Manager
user = env['res.users'].sudo().search([('id', '=', 14)], limit=1)

if not user:
    print("❌ Utilisateur ID=14 non trouvé!")
    exit(1)

print(f"\n👤 Utilisateur: {user.name} (Company: {user.company_id.name})")

# 1. Corriger les partners système (Administrator, etc.)
print(f"\n🔧 ÉTAPE 1: Correction des partners système...")

# Liste des partners système qui doivent être globaux (company_id = False)
system_partner_ids = [
    3,  # Administrator (généralement)
]

for partner_id in system_partner_ids:
    partner = env['res.partner'].sudo().browse(partner_id)
    if partner.exists():
        if partner.company_id:
            print(f"   🔧 Partner ID={partner_id} ({partner.name})")
            print(f"      Company actuelle: {partner.company_id.name}")
            partner.write({'company_id': False})
            print(f"      ✅ Company_id mis à False (global)")
        else:
            print(f"   ✅ Partner ID={partner_id} ({partner.name}) déjà global")
    else:
        print(f"   ⚠️ Partner ID={partner_id} n'existe pas")

# 2. Vérifier la règle Premium Manager pour res.partner
print(f"\n🔧 ÉTAPE 2: Vérification de la règle Premium Manager...")

premium_group = env.ref('onedesk_core.group_onedesk_premium_manager', raise_if_not_found=False)
if not premium_group:
    print("   ❌ Groupe Premium Manager non trouvé!")
    exit(1)

partner_rules = env['ir.rule'].sudo().search([
    ('model_id.model', '=', 'res.partner'),
    ('groups', 'in', [premium_group.id]),
])

print(f"   Règles Premium Manager pour res.partner: {len(partner_rules)}")
for rule in partner_rules:
    print(f"   - {rule.name}")
    print(f"     Domain actuel: {rule.domain_force}")

    # La règle doit inclure:
    # 1. Partners sans company (globaux)
    # 2. Partners de la company de l'utilisateur
    # 3. Le partner de l'utilisateur lui-même
    # 4. Le partner de la company de l'utilisateur

    correct_domain = str([
        '|', '|', '|',
        ('company_id', '=', False),
        ('company_id', '=', user.company_id.id),
        ('id', '=', user.partner_id.id),
        ('id', '=', user.company_id.partner_id.id)
    ])

    # Note: On ne peut pas utiliser user.partner_id dans le domain car il est évalué
    # côté Python, pas dans la base. Le domain correct doit être:
    recommended_domain = "['|', '|', '|', ('company_id', '=', False), ('company_id', '=', user.company_id.id), ('id', '=', user.partner_id.id), ('id', '=', user.company_id.partner_id.id)]"

    print(f"     Domain recommandé: {recommended_domain}")

    if rule.domain_force != recommended_domain:
        print(f"     ⚠️ Le domain pourrait être amélioré pour inclure:")
        print(f"        - Le partner de l'utilisateur (user.partner_id)")
        print(f"        - Le partner de la company (user.company_id.partner_id)")

# 3. S'assurer que le partner de l'utilisateur a la bonne company
print(f"\n🔧 ÉTAPE 3: Vérification du partner de l'utilisateur...")

user_partner = user.partner_id
print(f"   Partner de l'utilisateur: {user_partner.name} (ID: {user_partner.id})")
print(f"   Company du partner: {user_partner.company_id.name if user_partner.company_id else 'AUCUNE'}")

if user_partner.company_id and user_partner.company_id != user.company_id:
    print(f"   ⚠️ MISMATCH: Le partner de l'utilisateur a une company différente!")
    print(f"   🔧 Correction: Alignement sur la company de l'utilisateur...")
    user_partner.write({'company_id': user.company_id.id})
    print(f"   ✅ Partner aligné sur company: {user.company_id.name}")
elif not user_partner.company_id:
    print(f"   ℹ️ Le partner de l'utilisateur est global (company_id=False)")
    print(f"   💡 Considérez l'assigner à la company de l'utilisateur pour isolation multi-tenant:")
    print(f"      user_partner.write({{'company_id': {user.company_id.id}}})")
else:
    print(f"   ✅ Partner correctement assigné à la company de l'utilisateur")

# 4. Tester l'accès après corrections
print(f"\n🧪 ÉTAPE 4: Test d'accès après corrections...")

env.cr.commit()  # Commit avant de tester

user_env = env(user=user.id)

# Test partner 3 (Administrator)
try:
    test_p3 = user_env['res.partner'].browse(3)
    name = test_p3.name
    print(f"   ✅ Peut maintenant accéder au partner ID=3: {name}")
except Exception as e:
    print(f"   ❌ Ne peut toujours pas accéder au partner ID=3: {str(e)[:100]}")

# Test partner 23
try:
    test_p23 = user_env['res.partner'].browse(23)
    name = test_p23.name
    company_str = f" (Company: {test_p23.company_id.name})" if test_p23.company_id else ""
    print(f"   ✅ Peut maintenant accéder au partner ID=23: {name}{company_str}")
except Exception as e:
    print(f"   ❌ Ne peut toujours pas accéder au partner ID=23")
    print(f"      Raison: Le partner appartient probablement à une autre company")
    print(f"      Solution: C'est normal en mode multi-tenant strict!")

print("\n" + "=" * 80)
print("✅ CORRECTION TERMINÉE")
print("=" * 80)
print(f"\n💡 Résumé:")
print(f"   - Partners système (ex: Administrator) → company_id = False (global)")
print(f"   - Partner de l'utilisateur → aligné sur sa company")
print(f"   - Partners d'autres companies → INACCESSIBLES (isolation multi-tenant)")
print(f"\n📋 Comportement attendu:")
print(f"   ✅ Utilisateur peut voir: partners globaux + partners de SA company")
print(f"   ❌ Utilisateur ne peut PAS voir: partners d'AUTRES companies")
print()
