#!/usr/bin/env python3
"""
Diagnostic pour utilisateur Premium Manager ne pouvant pas accéder au website
À exécuter: ./odoo-bin shell -d VOTRE_BASE < diagnose_premium_website_access.py
"""

print("=" * 70)
print("🔍 DIAGNOSTIC ACCÈS WEBSITE POUR PREMIUM MANAGER")
print("=" * 70)

# ID de l'utilisateur qui a le problème (à modifier si nécessaire)
USER_ID = 112  # baba merveilles

# 1. Informations sur l'utilisateur
print(f"\n👤 UTILISATEUR (ID: {USER_ID})")
print("-" * 70)

try:
    user = env['res.users'].sudo().browse(USER_ID)
    print(f"Nom: {user.name}")
    print(f"Login: {user.login}")
    print(f"Company: {user.company_id.name if user.company_id else '❌ AUCUNE COMPANY!'}")
    print(f"Company ID: {user.company_id.id if user.company_id else 'None'}")

    # Vérifier les groupes
    print(f"\n📋 GROUPES DE L'UTILISATEUR:")
    for group in user.groups_id.filtered(lambda g: 'OneDesk' in g.name or 'Premium' in g.name or 'System' in g.name):
        print(f"   • {group.name}")

    is_premium = env.ref('onedesk_core.group_onedesk_premium_manager').id in user.groups_id.ids
    is_system = env.ref('base.group_system').id in user.groups_id.ids

    print(f"\n✅ Premium Manager: {'OUI' if is_premium else 'NON'}")
    print(f"✅ System Admin: {'OUI' if is_system else 'NON'}")

except Exception as e:
    print(f"❌ ERREUR: Utilisateur {USER_ID} introuvable - {e}")
    exit(1)

# 2. Informations sur les websites
print(f"\n🌐 WEBSITES DANS LA BASE")
print("-" * 70)

websites = env['website'].sudo().search([])
print(f"Total: {len(websites)} website(s)")

for website in websites:
    print(f"\n   📌 {website.name} (ID: {website.id})")
    print(f"      Company: {website.company_id.name if website.company_id else '❌ Pas de company (partagé)'}")
    print(f"      Company ID: {website.company_id.id if website.company_id else 'False'}")
    print(f"      Domain: {website.domain or 'Non défini'}")

# 3. Test d'accès avec les règles actuelles
print(f"\n🧪 TEST D'ACCÈS POUR L'UTILISATEUR")
print("-" * 70)

# Se connecter en tant que l'utilisateur
user_env = env(user=user.id)

try:
    accessible_websites = user_env['website'].search([])
    print(f"✅ L'utilisateur peut accéder à {len(accessible_websites)} website(s):")
    for website in accessible_websites:
        print(f"   • {website.name} (Company: {website.company_id.name if website.company_id else 'Partagé'})")
except Exception as e:
    print(f"❌ ERREUR D'ACCÈS: {e}")

# 4. Vérifier les règles qui s'appliquent
print(f"\n📜 RÈGLES QUI S'APPLIQUENT À CET UTILISATEUR")
print("-" * 70)

applicable_rules = env['ir.rule'].sudo().search([
    ('model_id.model', '=', 'website'),
    ('active', '=', True),
    '|',
    ('groups', '=', False),
    ('groups', 'in', user.groups_id.ids)
])

print(f"Total: {len(applicable_rules)} règle(s)")
for rule in applicable_rules:
    print(f"\n   📌 {rule.name}")
    print(f"      Domain: {rule.domain_force}")
    print(f"      Groupes: {', '.join(rule.groups.mapped('name')) if rule.groups else '⚠️ GLOBAL (tous)'}")
    print(f"      Permissions: R:{rule.perm_read} W:{rule.perm_write} C:{rule.perm_create} D:{rule.perm_unlink}")

# 5. Diagnostics et solutions
print(f"\n💡 DIAGNOSTICS ET SOLUTIONS")
print("=" * 70)

# Vérifier si user a une company
if not user.company_id:
    print("\n❌ PROBLÈME 1: L'utilisateur N'A PAS de company_id!")
    print("   Solution:")
    print(f"   user = env['res.users'].browse({USER_ID})")
    print(f"   user.write({{'company_id': env['res.company'].search([], limit=1).id}})")
    print("   env.cr.commit()")

# Vérifier si website a une company
websites_without_company = websites.filtered(lambda w: not w.company_id)
if websites_without_company:
    print(f"\n⚠️ PROBLÈME 2: {len(websites_without_company)} website(s) SANS company_id")
    print("   Ces websites sont 'partagés' - accessibles à tous avec OR logic")
    print("   Solution: Assigner une company ou laisser partagé")
    for website in websites_without_company:
        print(f"   • {website.name} (ID: {website.id})")

# Vérifier si company_id correspondent
if user.company_id:
    matching_websites = websites.filtered(lambda w: w.company_id and w.company_id.id == user.company_id.id)
    shared_websites = websites.filtered(lambda w: not w.company_id)

    print(f"\n✅ RÉSUMÉ POUR {user.name}:")
    print(f"   • Websites de sa company: {len(matching_websites)}")
    print(f"   • Websites partagés: {len(shared_websites)}")
    print(f"   • TOTAL accessible: {len(matching_websites) + len(shared_websites)}")

    if len(matching_websites) + len(shared_websites) == 0:
        print("\n❌ PROBLÈME 3: Aucun website accessible!")
        print("   Solution:")
        print("   1. Créer un website pour cette company")
        print("   2. Ou assigner un website existant à cette company")

# Vérifier si user est dans Premium Manager
if not is_premium:
    print("\n❌ PROBLÈME 4: L'utilisateur N'EST PAS dans le groupe Premium Manager!")
    print("   Solution:")
    print(f"   user = env['res.users'].browse({USER_ID})")
    print("   user.write({'groups_id': [(4, env.ref('onedesk_core.group_onedesk_premium_manager').id)]})")
    print("   env.cr.commit()")

# 6. Solution rapide recommandée
print(f"\n🚀 SOLUTION RAPIDE RECOMMANDÉE")
print("=" * 70)

if not user.company_id:
    print("1. Assigner une company à l'utilisateur")
elif not websites.filtered(lambda w: not w.company_id or w.company_id.id == user.company_id.id):
    print("1. Assigner le website à la company de l'utilisateur:")
    if websites:
        website = websites[0]
        print(f"   website = env['website'].browse({website.id})")
        print(f"   website.write({{'company_id': {user.company_id.id}}})")
        print("   env.cr.commit()")
else:
    print("✅ Configuration correcte!")
    print("   → Mettez à jour le module onedesk_core")
    print("   → Redémarrez Odoo")
    print("   → L'utilisateur devrait maintenant avoir accès")

print("\n" + "=" * 70)
print("✅ DIAGNOSTIC TERMINÉ")
print("=" * 70)
