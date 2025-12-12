#!/usr/bin/env python3
"""
Script de correction FORCÉE pour les règles res.partner
À exécuter dans le shell Odoo
"""

print("=" * 70)
print("🔧 CORRECTION FORCÉE DES RÈGLES RES.PARTNER")
print("=" * 70)

# 1. Lister TOUTES les règles actives pour res.partner
print("\n📋 1. TOUTES LES RÈGLES ACTIVES POUR RES.PARTNER")
print("-" * 70)

all_rules = env['ir.rule'].sudo().search([
    ('model_id.model', '=', 'res.partner'),
    ('active', '=', True)
])

print(f"✅ {len(all_rules)} règle(s) active(s) trouvée(s):\n")

for rule in all_rules:
    print(f"📌 {rule.name} (ID: {rule.id})")
    print(f"   Domain: {rule.domain_force}")
    print(f"   Groupes: {', '.join(rule.groups.mapped('name')) if rule.groups else '⚠️  GLOBAL (s\'applique à TOUS)'}")
    print(f"   Module: {rule.id.origin if hasattr(rule.id, 'origin') else 'N/A'}")
    print()

# 2. Identifier les règles problématiques
print("\n🔍 2. ANALYSE DES RÈGLES PROBLÉMATIQUES")
print("-" * 70)

problematic_rules = []
for rule in all_rules:
    # Règles sans OR logique qui filtrent par company_id
    if 'company_id' in rule.domain_force and "'|'" not in rule.domain_force:
        print(f"⚠️  RÈGLE RESTRICTIVE: {rule.name}")
        print(f"   Domain: {rule.domain_force}")
        problematic_rules.append(rule)

if not problematic_rules:
    print("✅ Aucune règle manifestement problématique trouvée")
else:
    print(f"\n⚠️  {len(problematic_rules)} règle(s) potentiellement problématique(s)")

# 3. Solution 1: Mettre Admin dans groupe System (BYPASS TOUTES LES RÈGLES)
print("\n💡 3. SOLUTION 1 (RECOMMANDÉE): Admin dans groupe System")
print("-" * 70)

admin = env['res.users'].browse(2)
system_group = env.ref('base.group_system')

if system_group.id in admin.groups_id.ids:
    print("✅ L'admin est DÉJÀ dans le groupe System")
else:
    print("⚠️  L'admin N'EST PAS dans le groupe System")
    print("\n🔧 APPLIQUER LA CORRECTION:")
    print("admin = env['res.users'].browse(2)")
    print("admin.write({'groups_id': [(4, env.ref('base.group_system').id)]})")
    print("env.cr.commit()")

    response = input("\n❓ Voulez-vous appliquer cette correction maintenant? (o/n): ")
    if response.lower() in ['o', 'oui', 'y', 'yes']:
        admin.write({'groups_id': [(4, system_group.id)]})
        env.cr.commit()
        print("✅ CORRECTION APPLIQUÉE!")
        print("   L'admin a maintenant TOUS les droits (bypass record rules)")
    else:
        print("❌ Correction annulée")

# 4. Solution 2: Désactiver les règles natives Odoo pour admin
print("\n💡 4. SOLUTION 2: Désactiver règles natives pour groupes admin")
print("-" * 70)

# Chercher les règles natives Odoo (non OneDesk)
native_rules = env['ir.rule'].sudo().search([
    ('model_id.model', '=', 'res.partner'),
    ('active', '=', True),
    ('name', 'not like', 'OneDesk'),
    ('name', 'not like', 'Property Manager'),
    ('name', 'not like', 'Master Admin'),
    ('name', 'not like', 'Premium')
])

if native_rules:
    print(f"⚠️  {len(native_rules)} règle(s) native(s) Odoo trouvée(s):")
    for rule in native_rules:
        print(f"\n   📌 {rule.name}")
        print(f"      Domain: {rule.domain_force}")
        print(f"      Groupes: {', '.join(rule.groups.mapped('name')) if rule.groups else 'GLOBAL'}")

    print("\n🔧 Pour désactiver ces règles:")
    for rule in native_rules:
        print(f"env['ir.rule'].browse({rule.id}).write({{'active': False}})")
else:
    print("✅ Aucune règle native Odoo problématique trouvée")

# 5. Solution 3: Forcer la mise à jour de la règle Property Manager
print("\n💡 5. SOLUTION 3: Forcer mise à jour règle Property Manager")
print("-" * 70)

pm_rule = env['ir.rule'].sudo().search([
    ('name', '=', 'Property Manager - Company Partners')
], limit=1)

if pm_rule:
    new_domain = "['|', ('company_id', '=', False), ('company_id', '=', user.company_id.id)]"
    print(f"Règle actuelle: {pm_rule.domain_force}")
    print(f"Règle attendue:  {new_domain}")

    if pm_rule.domain_force != new_domain:
        print("\n⚠️  LA RÈGLE N'EST PAS À JOUR!")
        print("\n🔧 CORRECTION:")
        pm_rule.write({'domain_force': new_domain})
        env.cr.commit()
        print("✅ Règle mise à jour et commitée!")
    else:
        print("✅ La règle est déjà à jour")

# 6. Solution 4: Vérifier les conflits de règles
print("\n💡 6. SOLUTION 4: Vérifier conflits de règles")
print("-" * 70)

admin = env['res.users'].browse(2)
applicable_rules = env['ir.rule'].sudo().search([
    ('model_id.model', '=', 'res.partner'),
    ('active', '=', True),
    '|',
    ('groups', '=', False),
    ('groups', 'in', admin.groups_id.ids)
])

print(f"📋 {len(applicable_rules)} règle(s) s'appliquent à l'admin:")
for rule in applicable_rules:
    print(f"\n   • {rule.name}")
    print(f"     Domain: {rule.domain_force}")
    print(f"     Create: {rule.perm_create}")

# 7. Résumé des actions
print("\n" + "=" * 70)
print("📊 RÉSUMÉ DES ACTIONS RECOMMANDÉES")
print("=" * 70)

print("\n🎯 ACTION IMMÉDIATE (choisir UNE solution):")
print("\n✅ SOLUTION A (RECOMMANDÉE): Mettre admin dans groupe System")
print("   admin = env['res.users'].browse(2)")
print("   admin.write({'groups_id': [(4, env.ref('base.group_system').id)]})")
print("   env.cr.commit()")
print("   → L'admin bypass TOUTES les record rules")

print("\n✅ SOLUTION B: Désactiver règle native Odoo conflictuelle")
if native_rules:
    for rule in native_rules:
        if 'company_id' in rule.domain_force and "'|'" not in rule.domain_force:
            print(f"   env['ir.rule'].browse({rule.id}).write({{'active': False}})")
            print("   env.cr.commit()")

print("\n✅ SOLUTION C: Redémarrer Odoo (vider cache)")
print("   sudo systemctl restart odoo")

print("\n" + "=" * 70)
print("✅ SCRIPT TERMINÉ")
print("=" * 70)
