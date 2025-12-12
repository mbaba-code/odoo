#!/usr/bin/env python3
"""
Vérifie que l'administrateur est dans le groupe System (base.group_system)
À exécuter: ./odoo-bin shell -d VOTRE_BASE < verify_admin_system_group.py
"""

print("=" * 70)
print("🔍 VÉRIFICATION GROUPE SYSTEM POUR ADMINISTRATEUR")
print("=" * 70)

# 1. Trouver l'administrateur (user ID 2 généralement)
admin = env['res.users'].browse(2)

print(f"\n👤 Utilisateur: {admin.name} (ID: {admin.id})")
print(f"📧 Email: {admin.login}")
print(f"🏢 Company: {admin.company_id.name}")

# 2. Vérifier le groupe System
system_group = env.ref('base.group_system')
print(f"\n🔐 Groupe System: {system_group.name} (ID: {system_group.id})")

# 3. Vérifier si admin est dans System
if system_group.id in admin.groups_id.ids:
    print("✅ L'administrateur EST DANS le groupe System")
    print("   → Il devrait voir TOUS les utilisateurs et companies")
else:
    print("❌ L'administrateur N'EST PAS dans le groupe System")
    print("   → C'est pourquoi il ne voit pas tous les utilisateurs!")

    print("\n🔧 CORRECTION AUTOMATIQUE...")
    admin.write({'groups_id': [(4, system_group.id)]})
    env.cr.commit()
    print("✅ Administrateur ajouté au groupe System!")
    print("   → Redémarrez Odoo pour appliquer les changements")

# 4. Liste tous les groupes de l'admin
print(f"\n📋 TOUS LES GROUPES DE L'ADMIN ({len(admin.groups_id)} groupes):")
for group in admin.groups_id.sorted(key=lambda g: g.full_name):
    print(f"   • {group.full_name}")

# 5. Vérifier les autres admins potentiels
print("\n" + "=" * 70)
print("👥 AUTRES UTILISATEURS AVEC ACCÈS ADMINISTRATION")
print("=" * 70)

admin_users = env['res.users'].search([
    ('groups_id', 'in', [env.ref('base.group_system').id])
])

if admin_users:
    print(f"✅ {len(admin_users)} utilisateur(s) dans le groupe System:")
    for user in admin_users:
        print(f"   • {user.name} ({user.login}) - Company: {user.company_id.name}")
else:
    print("⚠️ AUCUN utilisateur dans le groupe System!")
    print("   C'est un PROBLÈME - il devrait y avoir au moins un admin")

# 6. Test de visibilité
print("\n" + "=" * 70)
print("🧪 TEST DE VISIBILITÉ POUR L'ADMIN")
print("=" * 70)

# Se connecter en tant qu'admin
admin_env = env(user=admin.id)

# Compter ce que l'admin voit
users_count = admin_env['res.users'].search_count([])
companies_count = admin_env['res.company'].search_count([])
websites_count = admin_env['website'].search_count([])

print(f"\n👁️ Ce que l'admin voit actuellement:")
print(f"   • Utilisateurs: {users_count}")
print(f"   • Companies: {companies_count}")
print(f"   • Websites: {websites_count}")

# Compter le total réel (avec sudo)
total_users = env['res.users'].sudo().search_count([])
total_companies = env['res.company'].sudo().search_count([])
total_websites = env['website'].sudo().search_count([])

print(f"\n📊 Total réel dans la base:")
print(f"   • Utilisateurs: {total_users}")
print(f"   • Companies: {total_companies}")
print(f"   • Websites: {total_websites}")

if users_count == total_users and companies_count == total_companies:
    print("\n✅ PARFAIT! L'admin voit TOUT!")
else:
    print("\n⚠️ PROBLÈME! L'admin ne voit pas tout!")
    print("   → Vérifiez que le module onedesk_core est bien à jour")
    print("   → Redémarrez Odoo après avoir mis à jour le module")

print("\n" + "=" * 70)
print("✅ VÉRIFICATION TERMINÉE")
print("=" * 70)
