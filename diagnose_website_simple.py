#!/usr/bin/env python3
"""
Diagnostic SIMPLE pour accès website Premium Manager
À exécuter: ./odoo-bin shell -d VOTRE_BASE
Puis coller ce code
"""

USER_ID = 112  # baba merveilles

print("=" * 70)
print("🔍 DIAGNOSTIC ACCÈS WEBSITE")
print("=" * 70)

# 1. Utilisateur
user = env['res.users'].sudo().browse(USER_ID)
print(f"\n👤 UTILISATEUR:")
print(f"   Nom: {user.name}")
print(f"   Login: {user.login}")
print(f"   Company: {user.company_id.name if user.company_id else '❌ AUCUNE'}")
print(f"   Company ID: {user.company_id.id if user.company_id else None}")

# 2. Groupes (méthode safe)
print(f"\n📋 GROUPES:")
try:
    # Méthode 1: Via has_group
    is_premium = user.has_group('onedesk_core.group_onedesk_premium_manager')
    is_system = user.has_group('base.group_system')
    print(f"   Premium Manager: {'✅ OUI' if is_premium else '❌ NON'}")
    print(f"   System Admin: {'✅ OUI' if is_system else '❌ NON'}")
except Exception as e:
    print(f"   ⚠️ Erreur vérification groupes: {e}")

# 3. Websites disponibles
print(f"\n🌐 WEBSITES:")
websites = env['website'].sudo().search([])
print(f"   Total dans la base: {len(websites)}")

for w in websites:
    company_info = f"{w.company_id.name} (ID: {w.company_id.id})" if w.company_id else "❌ PAS DE COMPANY (partagé)"
    print(f"   • {w.name} (ID: {w.id}) - Company: {company_info}")

# 4. Test accès utilisateur
print(f"\n🧪 TEST ACCÈS UTILISATEUR:")
user_env = env(user=user.id)
try:
    accessible = user_env['website'].search([])
    print(f"   ✅ Peut accéder à {len(accessible)} website(s):")
    for w in accessible:
        print(f"      • {w.name}")
except Exception as e:
    print(f"   ❌ ERREUR: {e}")

# 5. Règles applicables
print(f"\n📜 RÈGLES ACTIVES POUR WEBSITE:")
rules = env['ir.rule'].sudo().search([
    ('model_id.model', '=', 'website'),
    ('active', '=', True)
])
for rule in rules:
    groups_info = ', '.join(rule.groups.mapped('name')) if rule.groups else '⚠️ GLOBAL'
    print(f"   • {rule.name}")
    print(f"     Domain: {rule.domain_force}")
    print(f"     Groupes: {groups_info}")

# 6. Solution
print(f"\n💡 SOLUTION:")
if not user.company_id:
    print("   ❌ L'utilisateur n'a PAS de company_id")
    print("   → Assigner une company:")
    print(f"      user = env['res.users'].browse({USER_ID})")
    print("      user.company_id = env['res.company'].search([], limit=1)")
elif not websites.filtered(lambda w: not w.company_id or w.company_id.id == user.company_id.id):
    print("   ❌ Aucun website compatible")
    print("   → Assigner le website à la company de l'utilisateur:")
    if websites:
        print(f"      website = env['website'].browse({websites[0].id})")
        print(f"      website.company_id = {user.company_id.id}")
else:
    print("   ✅ Configuration OK!")
    print("   → Mettre à jour le module onedesk_core")
    print("   → Apps → OneDesk Core → Update")

print("\n" + "=" * 70)
