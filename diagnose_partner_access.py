"""
Script de correction FORCÉE pour les règles res.partner
À exécuter dans le shell Odoo
"""

print("=" * 70)
print("🔧 CORRECTION FORCÉE DES RÈGLES RES.PARTNER")
print("=" * 70)

# --------------------------------------------------
# 1. Lister TOUTES les règles actives pour res.partner
# --------------------------------------------------
print("\n📋 1. TOUTES LES RÈGLES ACTIVES POUR RES.PARTNER")
print("-" * 70)

all_rules = env['ir.rule'].sudo().search([
    ('model_id.model', '=', 'res.partner'),
    ('active', '=', True),
])

print(f"✅ {len(all_rules)} règle(s) active(s) trouvée(s):\n")

for rule in all_rules:
    domain = rule.domain_force or "[]"
    groupes = ", ".join(rule.groups.mapped('name')) if rule.groups else "⚠️ GLOBAL (tous les utilisateurs)"

    print(f"📌 {rule.name} (ID: {rule.id})")
    print(f"   Domain: {domain}")
    print(f"   Groupes: {groupes}")
    print()

# --------------------------------------------------
# 2. Identifier les règles potentiellement bloquantes
# --------------------------------------------------
print("\n🔍 2. ANALYSE DES RÈGLES PROBLÉMATIQUES")
print("-" * 70)

problematic_rules = []

for rule in all_rules:
    domain = rule.domain_force or ""
    if 'company_id' in domain and "'|'" not in domain:
        print(f"⚠️ RÈGLE RESTRICTIVE: {rule.name}")
        print(f"   Domain: {domain}")
        problematic_rules.append(rule)

if not problematic_rules:
    print("✅ Aucune règle manifestement problématique trouvée")
else:
    print(
    f"   Groupes: {', '.join(rule.groups.mapped('name')) if rule.groups else '⚠️  GLOBAL (s applique à TOUS)'}"
)


# --------------------------------------------------
# 3. Solution 1 : Admin dans le groupe System
# --------------------------------------------------
print("\n💡 3. SOLUTION 1 (RECOMMANDÉE): Admin dans groupe System")
print("-" * 70)

admin = env['res.users'].sudo().browse(2)
system_group = env.ref('base.group_system')

if system_group.id in admin.group_ids.ids:
    print("✅ L'admin est déjà dans le groupe System")
else:
    print("⚠️ L'admin N'EST PAS dans le groupe System")
    response = input("\n❓ Appliquer la correction maintenant ? (o/n): ")

    if response.lower() in ('o', 'oui', 'y', 'yes'):
        admin.write({'group_ids': [(4, system_group.id)]})
        env.cr.commit()
        print("✅ CORRECTION APPLIQUÉE : Admin bypass toutes les record rules")
    else:
        print("❌ Correction annulée")

# --------------------------------------------------
# 4. Solution 2 : Identifier règles natives Odoo
# --------------------------------------------------
print("\n💡 4. SOLUTION 2: Règles natives Odoo actives")
print("-" * 70)

native_rules = env['ir.rule'].sudo().search([
    ('model_id.model', '=', 'res.partner'),
    ('active', '=', True),
    ('name', 'not ilike', 'onedesk'),
])

if native_rules:
    print(f"⚠️ {len(native_rules)} règle(s) native(s) trouvée(s):\n")
    for rule in native_rules:
        print(f"📌 {rule.name}")
        print(f"   Domain: {rule.domain_force or '[]'}")
        print(f"   Groupes: {', '.join(rule.groups.mapped('name')) or 'GLOBAL'}\n")

    print("🔧 Pour désactiver une règle :")
    for rule in native_rules:
        print(f"env['ir.rule'].browse({rule.id}).write({{'active': False}})")
else:
    print("✅ Aucune règle native Odoo problématique trouvée")

# --------------------------------------------------
# 5. Solution 3 : Corriger la règle Property Manager
# --------------------------------------------------
print("\n💡 5. SOLUTION 3: Mise à jour Property Manager")
print("-" * 70)

pm_rule = env['ir.rule'].sudo().search([
    ('name', '=', 'Property Manager - Company Partners')
], limit=1)

if pm_rule:
    expected_domain = "['|', ('company_id', '=', False), ('company_id', '=', user.company_id.id)]"
    print(f"Domain actuel  : {pm_rule.domain_force}")
    print(f"Domain attendu : {expected_domain}")

    if pm_rule.domain_force != expected_domain:
        pm_rule.write({'domain_force': expected_domain})
        env.cr.commit()
        print("✅ Règle Property Manager corrigée")
    else:
        print("✅ Règle déjà correcte")
else:
    print("ℹ️ Règle Property Manager non trouvée")

# --------------------------------------------------
# 6. Règles réellement appliquées à l’admin
# --------------------------------------------------
print("\n💡 6. RÈGLES APPLICABLES À L'ADMIN")
print("-" * 70)

applicable_rules = env['ir.rule'].sudo().search([
    ('model_id.model', '=', 'res.partner'),
    ('active', '=', True),
    '|',
    ('groups', '=', False),
    ('groups', 'in', admin.group_ids.ids),
])

print(f"📋 {len(applicable_rules)} règle(s) s'appliquent à l’admin:\n")

for rule in applicable_rules:
    print(f"• {rule.name}")
    print(f"  Domain: {rule.domain_force or '[]'}")
    print(f"  Create: {rule.perm_create}\n")

# --------------------------------------------------
print("=" * 70)
print("✅ SCRIPT TERMINÉ")
print("=" * 70)
