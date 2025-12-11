#!/usr/bin/env python3
"""
Setup complet pour Premium Manager
À exécuter: ./odoo-bin shell -d VOTRE_BASE < setup_premium_manager.py
"""

print("=" * 80)
print("🔍 RECHERCHE UTILISATEURS PREMIUM MANAGER")
print("=" * 80)

# Chercher tous les utilisateurs qui ont le groupe Premium Manager
premium_group = env.ref('onedesk_core.group_onedesk_premium_manager', raise_if_not_found=False)

if not premium_group:
    print("\n❌ Le groupe Premium Manager n'existe pas!")
    print("   → Assurez-vous d'avoir mis à jour le module onedesk_core")
else:
    print(f"\n✅ Groupe Premium Manager trouvé (ID: {premium_group.id})")
    
    # Trouver tous les utilisateurs avec ce groupe
    # Note: En Odoo 19, on ne peut pas chercher directement par groups_id dans search()
    # On doit charger tous les users et filtrer avec Python
    all_internal_users = env['res.users'].sudo().search([
        ('share', '=', False),  # Exclude portal users
    ])
    premium_users = all_internal_users.filtered(lambda u: premium_group.id in u.group_ids.ids)
    
    if not premium_users:
        print("\n⚠️ Aucun utilisateur n'a le rôle Premium Manager")
        print("\n📋 Liste de TOUS les utilisateurs (sauf admin/system):")
        print("-" * 80)
        
        all_users = env['res.users'].sudo().search([
            ('id', '!=', 1),  # Skip OdooBot
            ('share', '=', False),  # Skip portal users
        ])
        
        for u in all_users:
            company = u.company_id.name if u.company_id else "❌ AUCUNE"
            print(f"   • {u.name} (ID: {u.id}, Login: {u.login})")
            print(f"     Company: {company}")
            print(f"     Groups: {', '.join(u.group_ids.mapped('name')[:3])}...")
            print()
        
        print("\n💡 POUR ASSIGNER LE RÔLE PREMIUM MANAGER:")
        print("   1. Settings → Users → Sélectionner un utilisateur")
        print("   2. Access Rights → Cocher 'OneDesk / Premium Manager'")
        print("   3. Sauvegarder")
        
    else:
        print(f"\n✅ {len(premium_users)} utilisateur(s) Premium Manager trouvé(s):\n")
        
        for user in premium_users:
            print("=" * 80)
            print(f"👤 {user.name} (ID: {user.id})")
            print("=" * 80)
            print(f"   Login: {user.login}")
            print(f"   Company: {user.company_id.name} (ID: {user.company_id.id})")
            
            # Vérifier si un website existe pour cette company
            user_websites = env['website'].sudo().search([
                ('company_id', '=', user.company_id.id)
            ])
            
            if user_websites:
                print(f"\n   ✅ Website(s) existant(s) pour {user.company_id.name}:")
                for w in user_websites:
                    print(f"      • {w.name} (ID: {w.id})")
            else:
                print(f"\n   ⚠️ AUCUN website pour {user.company_id.name}")
                print(f"   🔧 Création d'un website...")
                
                # Use unique domain to avoid constraint violation
                # Format: company-{id}.local (unique per company)
                unique_domain = f'company-{user.company_id.id}.local'

                new_website = env['website'].sudo().create({
                    'name': f'Site {user.company_id.name}',
                    'company_id': user.company_id.id,
                    'domain': unique_domain,
                })
                
                print(f"   ✅ Website créé: {new_website.name} (ID: {new_website.id})")
                env.cr.commit()
            
            # Test d'accès
            print(f"\n   🔍 Test d'accès pour {user.name}:")
            user_env = env(user=user.id)
            
            try:
                accessible = user_env['website'].search([])
                print(f"   ✅ Peut accéder à {len(accessible)} website(s):")
                for w in accessible:
                    company_name = w.company_id.name if w.company_id else "PARTAGÉ"
                    print(f"      • {w.name} (ID: {w.id}) - {company_name}")
            except Exception as e:
                print(f"   ❌ Erreur d'accès: {e}")
            
            print()

# Liste de TOUS les websites
print("\n" + "=" * 80)
print("📋 LISTE COMPLÈTE DES WEBSITES")
print("=" * 80 + "\n")

all_websites = env['website'].sudo().search([])
for w in all_websites:
    company_name = w.company_id.name if w.company_id else "⚠️ PARTAGÉ (aucune company)"
    print(f"   • {w.name} (ID: {w.id})")
    print(f"     Company: {company_name}")
    print()

print("=" * 80)
print("✅ DIAGNOSTIC TERMINÉ!")
print("=" * 80)
