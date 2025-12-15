#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnostic pour comprendre le problème d'accès website Premium Manager

À exécuter avec: ./odoo-bin shell -d base1 -c debian/odoo.conf < diagnose_premium_website.py
"""

print("=" * 80)
print("🔍 DIAGNOSTIC ACCÈS WEBSITE PREMIUM MANAGER")
print("=" * 80)

# Trouver l'utilisateur "Personne test"
user = env['res.users'].sudo().search([('id', '=', 14)], limit=1)

if not user:
    print("❌ Utilisateur ID=14 non trouvé!")
    exit(1)

print(f"\n👤 UTILISATEUR: {user.name} (ID: {user.id})")
print(f"   Login: {user.login}")
print(f"   Company actuelle: {user.company_id.name} (ID: {user.company_id.id})")
print(f"   Companies autorisées: {', '.join([f'{c.name} (ID: {c.id})' for c in user.company_ids])}")

# Vérifier si c'est un Premium Manager
premium_group = env.ref('onedesk_core.group_onedesk_premium_manager', raise_if_not_found=False)
if premium_group and premium_group in user.group_ids:
    print(f"   ✅ Est Premium Manager")
else:
    print(f"   ❌ N'est PAS Premium Manager")

print(f"\n🌐 WEBSITE ID=1:")
website_1 = env['website'].sudo().browse(1)
if website_1.exists():
    print(f"   Nom: {website_1.name}")
    print(f"   Company: {website_1.company_id.name if website_1.company_id else 'AUCUNE'} (ID: {website_1.company_id.id if website_1.company_id else 'N/A'})")
    print(f"   Domain: {website_1.domain}")
else:
    print(f"   ❌ Website ID=1 n'existe pas")

print(f"\n🔍 WEBSITES DE LA COMPANY DE L'UTILISATEUR:")
user_websites = env['website'].sudo().search([
    ('company_id', '=', user.company_id.id)
])
if user_websites:
    for ws in user_websites:
        print(f"   - {ws.name} (ID: {ws.id}, Domain: {ws.domain})")
else:
    print(f"   ❌ AUCUN website pour la company {user.company_id.name}")

print(f"\n🔍 TOUS LES WEBSITES:")
all_websites = env['website'].sudo().search([])
for ws in all_websites:
    company_info = f"{ws.company_id.name} (ID: {ws.company_id.id})" if ws.company_id else "AUCUNE COMPANY"
    print(f"   - {ws.name} (ID: {ws.id}, Company: {company_info})")

print(f"\n📋 RÈGLES DE SÉCURITÉ APPLICABLES:")
# Règles globales pour website
global_rules = env['ir.rule'].sudo().search([
    ('model_id.model', '=', 'website'),
    ('global', '=', True),
])
print(f"   Règles GLOBALES ({len(global_rules)}):")
for rule in global_rules:
    print(f"     - {rule.name}")
    print(f"       Domain: {rule.domain_force}")
    print(f"       Groups: {', '.join([g.name for g in rule.groups]) if rule.groups else 'TOUS'}")

# Règles pour Premium Manager
premium_rules = env['ir.rule'].sudo().search([
    ('model_id.model', '=', 'website'),
    ('groups', 'in', [premium_group.id] if premium_group else []),
])
print(f"\n   Règles PREMIUM MANAGER ({len(premium_rules)}):")
for rule in premium_rules:
    print(f"     - {rule.name}")
    print(f"       Domain: {rule.domain_force}")

print(f"\n💡 SOLUTION:")
print(f"   L'utilisateur essaie d'accéder au website ID=1 qui appartient à une autre company.")
print(f"   Il faut:")
print(f"   1. Créer un website pour sa company: {user.company_id.name}")
print(f"   2. OU changer la company du website ID=1 pour correspondre à celle de l'utilisateur")
print(f"   3. OU vérifier que le menu 'Site Web' pointe vers le bon website")

print("\n" + "=" * 80)
