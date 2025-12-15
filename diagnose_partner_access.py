#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnostic pour le problème d'accès aux partners (contacts)

À exécuter avec: ./odoo-bin shell -d base1 -c debian/odoo.conf < diagnose_partner_access.py
"""

print("=" * 80)
print("🔍 DIAGNOSTIC ACCÈS PARTNERS PREMIUM MANAGER")
print("=" * 80)

# Utilisateur Premium Manager
user = env['res.users'].sudo().search([('id', '=', 14)], limit=1)

if not user:
    print("❌ Utilisateur ID=14 non trouvé!")
    exit(1)

print(f"\n👤 UTILISATEUR: {user.name} (ID: {user.id})")
print(f"   Company: {user.company_id.name} (ID: {user.company_id.id})")
print(f"   Companies autorisées: {', '.join([f'{c.name} ({c.id})' for c in user.company_ids])}")

# Vérifier les partners problématiques
print(f"\n🔍 PARTNERS PROBLÉMATIQUES:")

partner_23 = env['res.partner'].sudo().browse(23)
if partner_23.exists():
    print(f"\n   Partner ID=23: {partner_23.name}")
    print(f"   Company: {partner_23.company_id.name if partner_23.company_id else 'AUCUNE (False)'} (ID: {partner_23.company_id.id if partner_23.company_id else 'N/A'})")
    print(f"   Type: {'Company' if partner_23.is_company else 'Contact'}")
else:
    print(f"   ❌ Partner ID=23 n'existe pas")

partner_3 = env['res.partner'].sudo().browse(3)
if partner_3.exists():
    print(f"\n   Partner ID=3: {partner_3.name}")
    print(f"   Company: {partner_3.company_id.name if partner_3.company_id else 'AUCUNE (False)'} (ID: {partner_3.company_id.id if partner_3.company_id else 'N/A'})")
    print(f"   Type: {'Company' if partner_3.is_company else 'Contact'}")
    print(f"   Lié à user: {partner_3.user_ids.mapped('name') if partner_3.user_ids else 'Aucun'}")
else:
    print(f"   ❌ Partner ID=3 n'existe pas")

# Partner de la company de l'utilisateur
user_company_partner = user.company_id.partner_id
print(f"\n🏢 PARTNER DE LA COMPANY DE L'UTILISATEUR:")
print(f"   ID: {user_company_partner.id}")
print(f"   Nom: {user_company_partner.name}")
print(f"   Company: {user_company_partner.company_id.name if user_company_partner.company_id else 'AUCUNE (False)'}")

# Règles de sécurité pour res.partner
print(f"\n📋 RÈGLES DE SÉCURITÉ RES.PARTNER:")

all_rules = env['ir.rule'].sudo().search([
    ('model_id.model', '=', 'res.partner'),
])

print(f"\n   Toutes les règles ({len(all_rules)}):")
for rule in all_rules:
    groups_str = ', '.join([g.name for g in rule.groups]) if rule.groups else 'TOUS LES UTILISATEURS'
    global_str = "GLOBAL" if rule.global else "NON-GLOBAL"
    print(f"\n   - {rule.name} ({global_str})")
    print(f"     Domain: {rule.domain_force}")
    print(f"     Groups: {groups_str}")
    print(f"     Permissions: R={rule.perm_read} W={rule.perm_write} C={rule.perm_create} D={rule.perm_unlink}")

# Test d'accès depuis le contexte de l'utilisateur
print(f"\n🧪 TEST D'ACCÈS DEPUIS LE CONTEXTE DE L'UTILISATEUR:")
user_env = env(user=user.id)

# Test partner 23
try:
    test_p23 = user_env['res.partner'].browse(23)
    name = test_p23.name  # Force l'évaluation des droits
    print(f"   ✅ Peut accéder au partner ID=23: {name}")
except Exception as e:
    print(f"   ❌ NE PEUT PAS accéder au partner ID=23: {str(e)[:100]}")

# Test partner 3
try:
    test_p3 = user_env['res.partner'].browse(3)
    name = test_p3.name
    print(f"   ✅ Peut accéder au partner ID=3: {name}")
except Exception as e:
    print(f"   ❌ NE PEUT PAS accéder au partner ID=3: {str(e)[:100]}")

# Test recherche partners
print(f"\n🔍 PARTNERS ACCESSIBLES PAR L'UTILISATEUR:")
try:
    accessible_partners = user_env['res.partner'].search([], limit=10)
    print(f"   Trouvé {len(accessible_partners)} partners (limité à 10):")
    for p in accessible_partners:
        company_str = f"{p.company_id.name} ({p.company_id.id})" if p.company_id else "AUCUNE"
        print(f"     - ID={p.id}: {p.name} (Company: {company_str})")
except Exception as e:
    print(f"   ❌ Erreur lors de la recherche: {e}")

print("\n" + "=" * 80)
print("💡 ANALYSE:")
print("=" * 80)
print("""
Le problème vient probablement d'une des situations suivantes:

1. Les partners problématiques appartiennent à une autre company
   → Solution: Mettre company_id=False pour les rendre globaux

2. Il y a une règle GLOBAL qui entre en conflit
   → Solution: Vérifier les règles globales et ajuster

3. Le partner de l'admin a une company_id différente
   → Solution: Soit mettre company_id=False, soit ajouter une exception

4. Les règles Premium Manager sont trop restrictives
   → Solution: Ajouter des exceptions pour les users système
""")
print()
